"""Operaciones propietarias del ETS para equipo adicional autorizado."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.models.catalog_item import CatalogItem
from app.models.certificate import Certificate
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.models.invoice import Invoice
from app.models.service_order import ServiceOrder, ServiceOrderItem, ServiceWorkOrder
from app.schemas.certificate import CertificateCreate
from app.schemas.service_scope import ACCREDITATION_SCOPE_VALUES
from app.services.audit_logs import write_audit_log
from app.services.certificates import create_certificate
from app.services.equipment import (
    MAX_EQUIPMENT_PER_WORK_ORDER,
    freeze_certificate_operational_context,
    snapshot_certificate_master,
    sync_service_order_equipment_counts,
)
from app.services.service_order_certificate_capacity import (
    certificate_type_from_scope,
)


class AdditionalEquipmentOperationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class AdditionalEquipmentOperationResult:
    equipment_id: int
    service_order_id: int
    work_order_id: int
    work_order_number: int
    reconciliation_id: str
    created_work_order: bool
    certificate_id: int | None
    before_snapshot: dict
    after_snapshot: dict

    @property
    def domain_transaction_reference(self) -> str:
        return f"additional-equipment:{self.reconciliation_id}:{self.equipment_id}"


def register_additional_equipment(
    db: Session,
    *,
    resolution_id: int,
    service_order_id: int,
    reconciliation_id: str,
    request_hash: str,
    expected_service_order_status: str,
    catalog_item_id: int,
    service_order_item_id: int | None,
    calibration_scope: str,
    name: str,
    brand: str | None,
    model: str | None,
    serial_number: str | None,
    internal_id: str | None,
    range_or_capacity: str | None,
    notes: str | None,
    preferred_work_order_id: int | None,
    allow_new_work_order: bool,
    requires_signature: bool,
    requires_commercial_adjustment: bool,
    actor_id: str,
) -> AdditionalEquipmentOperationResult:
    existing = db.scalar(
        select(Equipment).where(
            Equipment.resolution_reconciliation_id == reconciliation_id
        )
    )
    if existing is not None:
        if (
            existing.resolution_request_hash != request_hash
            or existing.resolution_id != resolution_id
        ):
            raise AdditionalEquipmentOperationError(
                "idempotency_conflict",
                "El identificador de conciliación pertenece a otra operación.",
            )
        return _result(db, existing, created_work_order=False)

    service_order = db.scalar(
        select(ServiceOrder)
        .where(ServiceOrder.id == service_order_id)
        .with_for_update()
    )
    if service_order is None or not service_order.is_active:
        raise AdditionalEquipmentOperationError(
            "service_order_not_found", "El ETS ya no se encuentra disponible."
        )
    if service_order.status in {"closed", "cancelled"}:
        raise AdditionalEquipmentOperationError(
            "blocked_service_state", "El ETS está cerrado o cancelado."
        )
    if service_order.status != expected_service_order_status:
        raise AdditionalEquipmentOperationError(
            "revalidation_required", "El estado crítico del ETS cambió."
        )
    existing = db.scalar(
        select(Equipment).where(
            Equipment.resolution_reconciliation_id == reconciliation_id
        )
    )
    if existing is not None:
        if (
            existing.resolution_request_hash != request_hash
            or existing.resolution_id != resolution_id
        ):
            raise AdditionalEquipmentOperationError(
                "idempotency_conflict",
                "El identificador de conciliación pertenece a otra operación.",
            )
        return _result(db, existing, created_work_order=False)
    catalog = db.get(CatalogItem, catalog_item_id)
    if catalog is None or not catalog.is_active:
        raise AdditionalEquipmentOperationError(
            "missing_catalog", "El servicio de catálogo ya no está disponible."
        )
    if (
        calibration_scope not in ACCREDITATION_SCOPE_VALUES
        or catalog.calibration_scope != calibration_scope
    ):
        raise AdditionalEquipmentOperationError(
            "invalid_classification",
            "La clasificación de acreditación no coincide con el catálogo.",
        )
    if service_order_item_id is not None:
        item = db.scalar(
            select(ServiceOrderItem).where(
                ServiceOrderItem.id == service_order_item_id,
                ServiceOrderItem.service_order_id == service_order_id,
                ServiceOrderItem.is_active.is_(True),
            )
        )
        if item is None:
            raise AdditionalEquipmentOperationError(
                "service_order_item_changed",
                "La partida operativa autorizada ya no está disponible.",
            )
    duplicate = _duplicate_equipment(
        db,
        service_order_id=service_order_id,
        serial_number=serial_number,
        internal_id=internal_id,
    )
    if duplicate is not None:
        raise AdditionalEquipmentOperationError(
            "duplicate_equipment",
            f"El equipo ya está registrado con ID {duplicate}.",
        )

    work_order = _select_work_order(
        db,
        service_order_id=service_order_id,
        preferred_work_order_id=preferred_work_order_id,
    )
    created_work_order = False
    if work_order is None:
        if not allow_new_work_order:
            raise AdditionalEquipmentOperationError(
                "work_order_capacity_exhausted",
                "No existe una OT con capacidad disponible.",
            )
        work_order = _create_work_order(
            db,
            service_order=service_order,
            reconciliation_id=reconciliation_id,
        )
        created_work_order = True

    equipment = Equipment(
        service_order_id=service_order_id,
        work_order_id=work_order.id,
        service_order_item_id=service_order_item_id,
        resolution_id=resolution_id,
        resolution_reconciliation_id=reconciliation_id,
        resolution_request_hash=request_hash,
        calibration_scope=calibration_scope,
        status="registered",
        name=name.strip(),
        brand=brand,
        model=model,
        serial_number=serial_number,
        internal_id=internal_id,
        range_or_capacity=range_or_capacity,
        notes=notes,
    )
    db.add(equipment)
    db.flush()
    expected_master_id = freeze_certificate_operational_context(db, equipment)
    snapshot_certificate_master(db, equipment, expected_master_id)
    certificate_type = certificate_type_from_scope(calibration_scope)
    certificate = None
    if certificate_type is not None:
        _acquire_global_number_lock(db, 140020)
        certificate = create_certificate(
            db,
            CertificateCreate(
                service_order_id=service_order_id,
                equipment_id=equipment.id,
                field_sheet_id=None,
                certificate_type=certificate_type,
                issued_on=date.today(),
                title=f"Certificado esperado - {equipment.name}",
                notes=(
                    "Reserva generada por resolución autorizada de equipo adicional."
                ),
            ),
            user_id=_user_id(actor_id),
            commit=False,
        )
    if requires_signature:
        service_order.signature_reopen_available = True
        service_order.signature_reopen_source = (
            "resolution_engine.additional_equipment"
        )
    sync_service_order_equipment_counts(db, service_order_id)
    write_audit_log(
        db,
        action="service_order.additional_equipment_registered",
        entity="equipment",
        entity_id=equipment.id,
        user_id=_user_id(actor_id),
        new_values={
            "resolution_id": resolution_id,
            "reconciliation_id": reconciliation_id,
            "service_order_id": service_order_id,
            "work_order_id": work_order.id,
            "catalog_item_id": catalog_item_id,
            "calibration_scope": calibration_scope,
            "requires_signature": requires_signature,
            "requires_commercial_adjustment": requires_commercial_adjustment,
        },
    )
    db.flush()
    return _result(
        db,
        equipment,
        created_work_order=created_work_order,
        certificate=certificate,
    )


def compensate_additional_equipment(
    db: Session,
    *,
    service_order_id: int,
    reconciliation_id: str,
    actor_id: str,
) -> AdditionalEquipmentOperationResult:
    equipment = db.scalar(
        select(Equipment)
        .where(
            Equipment.service_order_id == service_order_id,
            Equipment.resolution_reconciliation_id == reconciliation_id,
        )
        .with_for_update()
    )
    if equipment is None:
        raise AdditionalEquipmentOperationError(
            "source_effect_not_found",
            "No se encontró el equipo conciliado.",
        )
    work_order = db.get(ServiceWorkOrder, equipment.work_order_id)
    assert work_order is not None
    before = _snapshot(equipment, work_order)
    if not equipment.is_active:
        return _result(db, equipment, created_work_order=False, before=before)
    if equipment.status != "registered":
        raise AdditionalEquipmentOperationError(
            "equipment_no_longer_reversible",
            "El equipo ya inició operación y no puede compensarse.",
        )
    field_sheet_exists = db.scalar(
        select(FieldSheet.id).where(
            FieldSheet.equipment_id == equipment.id,
            FieldSheet.is_active.is_(True),
        )
    )
    if field_sheet_exists is not None:
        raise AdditionalEquipmentOperationError(
            "field_sheet_evidence_preserved",
            "Existe una Hoja de Campo y debe preservarse.",
        )
    certificates = list(
        db.scalars(
            select(Certificate).where(
                Certificate.equipment_id == equipment.id,
                Certificate.is_active.is_(True),
            )
        ).all()
    )
    if any(item.status != "expected" for item in certificates):
        raise AdditionalEquipmentOperationError(
            "certificate_evidence_preserved",
            "Existe evidencia de certificado consumida y debe preservarse.",
        )
    now = datetime.now(timezone.utc)
    for certificate in certificates:
        certificate.is_active = False
        certificate.deleted_at = now
        certificate.deleted_by = _user_id(actor_id)
        certificate.status = "cancelled"
    equipment.is_active = False
    equipment.deleted_at = now
    equipment.deleted_by = _user_id(actor_id)
    equipment.status = "cancelled"
    remaining = db.scalar(
        select(func.count(Equipment.id)).where(
            Equipment.work_order_id == work_order.id,
            Equipment.is_active.is_(True),
            Equipment.id != equipment.id,
        )
    )
    created_marker = f"resolution:{reconciliation_id}"
    removed_work_order = bool(
        int(remaining or 0) == 0 and work_order.notes == created_marker
    )
    if removed_work_order:
        work_order.is_active = False
        work_order.deleted_at = now
        work_order.deleted_by = _user_id(actor_id)
        work_order.status = "cancelled"
    service_order = db.get(ServiceOrder, service_order_id)
    if (
        service_order is not None
        and service_order.signature_reopen_source
        == "resolution_engine.additional_equipment"
    ):
        service_order.signature_reopen_available = False
        service_order.signature_reopen_source = None
    sync_service_order_equipment_counts(db, service_order_id)
    write_audit_log(
        db,
        action="service_order.additional_equipment_compensated",
        entity="equipment",
        entity_id=equipment.id,
        user_id=_user_id(actor_id),
        previous_values=before,
        new_values={
            "is_active": False,
            "status": "cancelled",
            "work_order_cancelled": removed_work_order,
        },
    )
    db.flush()
    return _result(
        db,
        equipment,
        created_work_order=removed_work_order,
        before=before,
    )


def _select_work_order(
    db: Session,
    *,
    service_order_id: int,
    preferred_work_order_id: int | None,
) -> ServiceWorkOrder | None:
    rows = list(
        db.scalars(
            select(ServiceWorkOrder)
            .where(
                ServiceWorkOrder.service_order_id == service_order_id,
                ServiceWorkOrder.is_active.is_(True),
                ServiceWorkOrder.status != "cancelled",
            )
            .order_by(ServiceWorkOrder.sequence, ServiceWorkOrder.id)
            .with_for_update()
        ).all()
    )
    if preferred_work_order_id is not None:
        rows.sort(key=lambda item: item.id != preferred_work_order_id)
    for work_order in rows:
        count = db.scalar(
            select(func.count(Equipment.id)).where(
                Equipment.work_order_id == work_order.id,
                Equipment.is_active.is_(True),
            )
        )
        limit = work_order.equipment_limit or MAX_EQUIPMENT_PER_WORK_ORDER
        if int(count or 0) < min(limit, MAX_EQUIPMENT_PER_WORK_ORDER):
            return work_order
    return None


def _create_work_order(
    db: Session,
    *,
    service_order: ServiceOrder,
    reconciliation_id: str,
) -> ServiceWorkOrder:
    _acquire_global_number_lock(db, 140010)
    next_number = int(
        db.scalar(select(func.max(ServiceWorkOrder.work_order_number))) or 0
    ) + 1
    next_sequence = int(
        db.scalar(
            select(func.max(ServiceWorkOrder.sequence)).where(
                ServiceWorkOrder.service_order_id == service_order.id
            )
        )
        or 0
    ) + 1
    work_order = ServiceWorkOrder(
        service_order_id=service_order.id,
        work_order_number=next_number,
        sequence=next_sequence,
        status="pending",
        equipment_limit=MAX_EQUIPMENT_PER_WORK_ORDER,
        notes=f"resolution:{reconciliation_id}",
    )
    db.add(work_order)
    db.flush()
    return work_order


def _duplicate_equipment(
    db: Session,
    *,
    service_order_id: int,
    serial_number: str | None,
    internal_id: str | None,
) -> int | None:
    predicates = []
    if serial_number and serial_number.strip():
        predicates.append(
            func.lower(Equipment.serial_number) == serial_number.strip().lower()
        )
    if internal_id and internal_id.strip():
        predicates.append(
            func.lower(Equipment.internal_id) == internal_id.strip().lower()
        )
    if not predicates:
        return None
    return db.scalar(
        select(Equipment.id).where(
            Equipment.service_order_id == service_order_id,
            Equipment.is_active.is_(True),
            or_(*predicates),
        )
    )


def _result(
    db: Session,
    equipment: Equipment,
    *,
    created_work_order: bool,
    certificate: Certificate | None = None,
    before: dict | None = None,
) -> AdditionalEquipmentOperationResult:
    work_order = db.get(ServiceWorkOrder, equipment.work_order_id)
    assert work_order is not None
    if certificate is None:
        certificate = db.scalar(
            select(Certificate).where(
                Certificate.equipment_id == equipment.id,
            )
            .order_by(Certificate.id.desc())
        )
    return AdditionalEquipmentOperationResult(
        equipment_id=equipment.id,
        service_order_id=equipment.service_order_id,
        work_order_id=work_order.id,
        work_order_number=work_order.work_order_number,
        reconciliation_id=equipment.resolution_reconciliation_id or "",
        created_work_order=(
            created_work_order
            or work_order.notes
            == f"resolution:{equipment.resolution_reconciliation_id}"
        ),
        certificate_id=certificate.id if certificate is not None else None,
        before_snapshot=before or {},
        after_snapshot=_snapshot(equipment, work_order),
    )


def _snapshot(equipment: Equipment, work_order: ServiceWorkOrder) -> dict:
    return {
        "equipment_id": equipment.id,
        "service_order_id": equipment.service_order_id,
        "work_order_id": work_order.id,
        "work_order_number": work_order.work_order_number,
        "calibration_scope": equipment.calibration_scope,
        "status": equipment.status,
        "is_active": equipment.is_active,
        "reconciliation_id": equipment.resolution_reconciliation_id,
    }


def _user_id(actor_id: str) -> int | None:
    if actor_id.startswith("user:"):
        value = actor_id.removeprefix("user:")
        return int(value) if value.isdigit() else None
    return None


def _acquire_global_number_lock(db: Session, lock_key: int) -> None:
    """Serializa asignaciones globales en PostgreSQL; SQLite ya serializa pruebas."""

    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        )
