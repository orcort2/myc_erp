from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.certificate import Certificate
from app.models.controlled_document import ControlledDocument, ControlledDocumentVersion
from app.models.equipment import Equipment
from app.models.service_order import ServiceOrder, ServiceOrderItem, ServiceWorkOrder
from app.schemas.certificate import CertificateCreate
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentStatusChange,
    EquipmentUpdate,
)
from app.services.audit_logs import write_audit_log
from app.services.activity import publish_event
from app.services.certificates import create_certificate
from app.services.service_order_certificate_capacity import (
    auto_service_order_item_id_for_scope,
    certificate_type_for_equipment,
    resolve_equipment_calibration_scope,
    resolve_equipment_metrological_context,
)


FINISHED_STATUSES = {"calibrated", "labeled", "not_done"}
TERMINAL_STATUSES = {"labeled", "not_done", "cancelled"}
MAX_EQUIPMENT_PER_WORK_ORDER = 10

ALLOWED_TRANSITIONS = {
    "registered": {"realizing", "not_done", "cancelled"},
    "realizing": {"calibrated", "not_done", "cancelled"},
    "calibrated": {"labeled", "not_done", "cancelled"},
    "labeled": set(),
    "not_done": set(),
    "cancelled": set(),
}


def _ensure_active_service_order(db: Session, service_order_id: int) -> ServiceOrder:
    service_order = db.scalar(
        select(ServiceOrder)
        .where(
            ServiceOrder.id == service_order_id,
            ServiceOrder.is_active.is_(True),
        )
        .options(selectinload(ServiceOrder.work_orders))
    )
    if service_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden de servicio no encontrada",
        )
    if service_order.status in {"closed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede modificar equipo de una orden cerrada o cancelada",
        )
    return service_order


def _ensure_service_order_item(
    db: Session, service_order_id: int, service_order_item_id: int | None
) -> None:
    if service_order_item_id is None:
        return

    exists = db.scalar(
        select(ServiceOrderItem.id).where(
            ServiceOrderItem.id == service_order_item_id,
            ServiceOrderItem.service_order_id == service_order_id,
            ServiceOrderItem.is_active.is_(True),
        )
    )
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partida de orden de servicio no encontrada",
        )


def _work_order_equipment_count(db: Session, work_order_id: int) -> int:
    total = db.scalar(
        select(func.count(Equipment.id)).where(
            Equipment.work_order_id == work_order_id,
            Equipment.is_active.is_(True),
        )
    )
    return int(total or 0)


def _ensure_work_order_belongs_to_service_order(
    db: Session,
    *,
    service_order_id: int,
    work_order_id: int | None,
) -> ServiceWorkOrder | None:
    if work_order_id is None:
        return None

    work_order = db.scalar(
        select(ServiceWorkOrder).where(
            ServiceWorkOrder.id == work_order_id,
            ServiceWorkOrder.service_order_id == service_order_id,
            ServiceWorkOrder.is_active.is_(True),
        )
    )
    if work_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden de trabajo no encontrada para este servicio",
        )

    return work_order


def _first_available_work_order(
    db: Session,
    service_order: ServiceOrder,
) -> ServiceWorkOrder:
    active_work_orders = [
        item
        for item in service_order.work_orders
        if item.is_active
    ]

    if not active_work_orders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El servicio no tiene órdenes de trabajo activas",
        )

    ordered_work_orders = sorted(active_work_orders, key=lambda item: item.sequence)

    for work_order in ordered_work_orders:
        equipment_limit = work_order.equipment_limit or MAX_EQUIPMENT_PER_WORK_ORDER
        if _work_order_equipment_count(db, work_order.id) < equipment_limit:
            return work_order

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Todas las órdenes de trabajo están llenas. "
            "Se requiere crear una nueva OT mediante una excepción administrativa."
        ),
    )


def sync_service_order_equipment_counts(db: Session, service_order_id: int) -> None:
    total_equipment = db.scalar(
        select(func.count(Equipment.id)).where(
            Equipment.service_order_id == service_order_id,
            Equipment.is_active.is_(True),
        )
    )
    completed_equipment = db.scalar(
        select(func.count(Equipment.id)).where(
            Equipment.service_order_id == service_order_id,
            Equipment.is_active.is_(True),
            Equipment.status.in_(FINISHED_STATUSES),
        )
    )

    service_order = db.get(ServiceOrder, service_order_id)
    if service_order is not None:
        service_order.total_equipment = int(total_equipment or 0)
        service_order.completed_equipment = int(completed_equipment or 0)


def list_equipment(
    db: Session,
    *,
    service_order_id: int | None = None,
    work_order_id: int | None = None,
    include_inactive: bool = False,
) -> list[Equipment]:
    query = (
        select(Equipment)
        .options(selectinload(Equipment.work_order))
        .order_by(Equipment.created_at.desc())
    )

    if service_order_id is not None:
        query = query.where(Equipment.service_order_id == service_order_id)

    if work_order_id is not None:
        query = query.where(Equipment.work_order_id == work_order_id)

    if not include_inactive:
        query = query.where(Equipment.is_active.is_(True))

    return list(db.scalars(query).all())


def get_equipment(db: Session, equipment_id: int) -> Equipment:
    equipment = db.scalar(
        select(Equipment)
        .where(Equipment.id == equipment_id)
        .options(selectinload(Equipment.work_order))
    )
    if equipment is None or not equipment.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipo no encontrado",
        )
    return equipment


def _ensure_expected_certificate_for_equipment(
    db: Session,
    equipment: Equipment,
    *,
    user_id: int | None = None,
) -> None:
    exists = db.scalar(
        select(Certificate.id).where(
            Certificate.equipment_id == equipment.id,
            Certificate.is_active.is_(True),
        )
    )
    if exists is not None:
        return

    certificate_type = certificate_type_for_equipment(db, equipment)
    if certificate_type is None:
        return

    create_certificate(
        db,
        CertificateCreate(
            service_order_id=equipment.service_order_id,
            equipment_id=equipment.id,
            field_sheet_id=None,
            certificate_type=certificate_type,
            issued_on=date.today(),
            title=f"Certificado esperado - {equipment.name}",
            notes="Certificado esperado creado automáticamente desde alta de equipo.",
        ),
        user_id=user_id,
    )


def snapshot_certificate_master(
    db: Session,
    equipment: Equipment,
    document_id: int | None,
) -> None:
    """Freeze the exact active certificate template used by an equipment."""
    if document_id is None:
        return
    document = db.get(ControlledDocument, document_id)
    version = db.scalar(select(ControlledDocumentVersion).where(
        ControlledDocumentVersion.document_id == document_id,
        ControlledDocumentVersion.status == "active",
    ))
    if document is None or document.document_type != "certificate_master" or document.status != "active" or version is None:
        raise HTTPException(status_code=422, detail="La plantilla esperada debe ser un Master de Certificado activo con versión disponible")
    if version.expires_on and version.expires_on < date.today():
        raise HTTPException(status_code=422, detail="La plantilla esperada de certificado está caducada")
    equipment.certificate_master_document_id = document.id
    equipment.certificate_master_version_id = version.id
    equipment.certificate_template_path_snapshot = version.file_path
    equipment.certificate_template_filename_snapshot = version.original_filename
    equipment.certificate_template_checksum_snapshot = version.checksum
    equipment.certificate_template_effective_date_snapshot = version.effective_date
    equipment.certificate_template_expires_on_snapshot = version.expires_on


def freeze_certificate_operational_context(
    db: Session,
    equipment: Equipment,
) -> int | None:
    """Freeze certificate inputs from the ETS item; never consult the live catalog."""
    item = (
        db.get(ServiceOrderItem, equipment.service_order_item_id)
        if equipment.service_order_item_id
        else None
    )
    expected_master_id = (
        item.expected_certificate_master_id
        if item is not None
        else None
    )
    service_snapshot = item.service_snapshot if item is not None else None
    if service_snapshot:
        equipment.service_type_snapshot = service_snapshot.get("service_type_snapshot")
        equipment.linked_company_id = service_snapshot.get("linked_company_id")
        equipment.linked_company_name_snapshot = service_snapshot.get(
            "linked_company_name_snapshot"
        )
        equipment.certificate_prefix_snapshot = service_snapshot.get(
            "certificate_prefix_snapshot"
        )
    context_snapshot = {
        "schema_version": 1,
        "calibration_scope": equipment.calibration_scope,
        "certificate_type": certificate_type_for_equipment(db, equipment),
        "expected_certificate_master_id": expected_master_id,
        "service_order_item_id": equipment.service_order_item_id,
        "source_catalog_item_id": item.catalog_item_id if item is not None else None,
    }
    if item is not None and item.operational_category is not None:
        context_snapshot["operational_category"] = item.operational_category
    if service_snapshot is not None:
        context_snapshot["service_snapshot"] = service_snapshot
    equipment.certificate_operational_context_snapshot = context_snapshot
    return expected_master_id


def create_equipment(
    db: Session, payload: EquipmentCreate, *, user_id: int | None = None
) -> Equipment:
    service_order = _ensure_active_service_order(db, payload.service_order_id)

    data = payload.model_dump()

    selected_work_order = _ensure_work_order_belongs_to_service_order(
        db,
        service_order_id=payload.service_order_id,
        work_order_id=data.get("work_order_id"),
    )

    if selected_work_order is None:
        selected_work_order = _first_available_work_order(db, service_order)

    equipment_limit = selected_work_order.equipment_limit or MAX_EQUIPMENT_PER_WORK_ORDER
    if _work_order_equipment_count(db, selected_work_order.id) >= equipment_limit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta Orden de Trabajo ya tiene 10 equipos. Selecciona otra OT.",
        )

    resolved_item_id, resolved_scope, certificate_type = resolve_equipment_metrological_context(
        db,
        payload.service_order_id,
        service_order_item_id=data.get("service_order_item_id"),
        requested_scope=data.get("calibration_scope"),
    )
    data["calibration_scope"] = resolved_scope
    data["work_order_id"] = selected_work_order.id
    data["service_order_item_id"] = resolved_item_id

    _ensure_service_order_item(
        db,
        payload.service_order_id,
        data.get("service_order_item_id"),
    )

    equipment = Equipment(**data, status="registered")
    db.add(equipment)
    db.flush()
    expected_master_id = freeze_certificate_operational_context(db, equipment)
    snapshot_certificate_master(db, equipment, expected_master_id)

    if certificate_type:
        create_certificate(
            db,
            CertificateCreate(
                service_order_id=equipment.service_order_id,
                equipment_id=equipment.id,
                field_sheet_id=None,
                certificate_type=certificate_type,
                title=(
                    f"Certificado de Verificación - {equipment.name}"
                    if certificate_type == "verification"
                    else f"Certificado de Calibración - {equipment.name}"
                ),
                notes="Certificado esperado generado automaticamente al dar de alta el equipo.",
            ),
            user_id=user_id,
        )

    sync_service_order_equipment_counts(db, equipment.service_order_id)

    write_audit_log(
        db,
        action="equipment.created",
        entity="equipment",
        entity_id=equipment.id,
        user_id=user_id,
        new_values={
            "service_order_id": equipment.service_order_id,
            "work_order_id": equipment.work_order_id,
            "work_order_number": selected_work_order.work_order_number,
            "calibration_scope": equipment.calibration_scope,
            "service_order_item_id": equipment.service_order_item_id,
            "expected_certificate_master_id": expected_master_id,
            "name": equipment.name,
            "status": equipment.status,
        },
    )

    db.commit()
    return get_equipment(db, equipment.id)


def update_equipment(
    db: Session,
    equipment_id: int,
    payload: EquipmentUpdate,
    *,
    user_id: int | None = None,
) -> Equipment:
    equipment = get_equipment(db, equipment_id)
    _ensure_active_service_order(db, equipment.service_order_id)

    if equipment.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede editar equipo en estado terminal",
        )

    updates = payload.model_dump(exclude_unset=True)

    if "work_order_id" in updates:
        requested_work_order = _ensure_work_order_belongs_to_service_order(
            db,
            service_order_id=equipment.service_order_id,
            work_order_id=updates.get("work_order_id"),
        )
        if requested_work_order is not None and requested_work_order.id != equipment.work_order_id:
            equipment_limit = requested_work_order.equipment_limit or MAX_EQUIPMENT_PER_WORK_ORDER
            if _work_order_equipment_count(db, requested_work_order.id) >= equipment_limit:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="La Orden de Trabajo destino ya tiene 10 equipos.",
                )

    if "calibration_scope" in updates:
        requested_scope = updates.get("calibration_scope")
        if requested_scope == equipment.calibration_scope:
            resolved_scope = equipment.calibration_scope
            updates["service_order_item_id"] = equipment.service_order_item_id
        else:
            active_certificate_exists = db.scalar(
                select(Certificate.id).where(
                    Certificate.equipment_id == equipment.id,
                    Certificate.is_active.is_(True),
                )
            )
            if active_certificate_exists is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "El equipo ya tiene un certificado activo. No se puede cambiar el tipo de certificado "
                        "desde edición; da de baja el equipo y regístralo nuevamente si el tipo fue incorrecto."
                    ),
                )
            resolved_scope = resolve_equipment_calibration_scope(
                db,
                equipment.service_order_id,
                requested_scope,
            )
            updates["service_order_item_id"] = auto_service_order_item_id_for_scope(
                db,
                equipment.service_order_id,
                resolved_scope,
            )

        updates["calibration_scope"] = resolved_scope

    _ensure_service_order_item(
        db,
        equipment.service_order_id,
        updates.get("service_order_item_id"),
    )

    previous_values = {key: getattr(equipment, key) for key in updates}

    for key, value in updates.items():
        setattr(equipment, key, value)

    write_audit_log(
        db,
        action="equipment.updated",
        entity="equipment",
        entity_id=equipment.id,
        user_id=user_id,
        previous_values=previous_values,
        new_values=updates,
    )

    db.commit()
    return get_equipment(db, equipment.id)


def change_status(
    db: Session,
    equipment_id: int,
    new_status: str,
    payload: EquipmentStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Equipment:
    equipment = get_equipment(db, equipment_id)
    _ensure_active_service_order(db, equipment.service_order_id)

    allowed = ALLOWED_TRANSITIONS.get(equipment.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transicion no permitida: {equipment.status} -> {new_status}",
        )

    previous_status = equipment.status
    equipment.status = new_status

    sync_service_order_equipment_counts(db, equipment.service_order_id)

    write_audit_log(
        db,
        action=f"equipment.{new_status}",
        entity="equipment",
        entity_id=equipment.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": new_status},
        comment=payload.comment if payload else None,
    )
    publish_event(
        db,
        entity_type="equipment",
        entity_id=equipment.id,
        event_code="equipment.status_changed",
        idempotency_key=f"equipment:{equipment.id}:status:{new_status}",
        body=f"Estado del equipo actualizado de {previous_status} a {new_status}.",
        actor_id=user_id,
        metadata={"previous_status": previous_status, "status": new_status},
        related_entity_type="service_order",
        related_entity_id=equipment.service_order_id,
    )

    db.commit()
    return get_equipment(db, equipment.id)


def deactivate_equipment(
    db: Session, equipment_id: int, *, user_id: int | None = None
) -> Equipment:
    equipment = get_equipment(db, equipment_id)
    _ensure_active_service_order(db, equipment.service_order_id)

    equipment.is_active = False
    equipment.status = "cancelled"
    equipment.deleted_at = datetime.now(timezone.utc)
    equipment.deleted_by = user_id

    sync_service_order_equipment_counts(db, equipment.service_order_id)

    write_audit_log(
        db,
        action="equipment.deactivated",
        entity="equipment",
        entity_id=equipment.id,
        user_id=user_id,
        previous_values={"is_active": True},
        new_values={
            "is_active": False,
            "status": "cancelled",
            "work_order_id": equipment.work_order_id,
        },
    )

    db.commit()
    return equipment
