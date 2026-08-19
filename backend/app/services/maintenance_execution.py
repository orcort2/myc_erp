from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from weasyprint import HTML

from app.models.client_portal_membership import ClientPortalMembership
from app.models.equipment import Equipment
from app.models.maintenance_execution import (
    MaintenanceChangeRequest,
    MaintenanceExecution,
    MaintenanceMaterial,
    MaintenancePause,
)
from app.models.quotation import QuotationItem, QuotationItemDecision
from app.models.service_execution import ServiceStage, ServiceUnit
from app.models.service_order import ServiceOrder, ServiceOrderItem
from app.models.user import User
from app.schemas.maintenance_execution import (
    MaintenanceCapture,
    MaintenanceChangeCreate,
    MaintenanceChangeResolve,
    MaintenanceEquipmentCreate,
    MaintenanceMaterialCreate,
    MaintenancePauseCreate,
    MaintenancePrepare,
    MaintenanceSignature,
)
from app.services.audit_logs import write_audit_log
from app.services.auth import user_has_permission
from app.services.storage_service import resolve_storage_path


MAIN_MAINTENANCE_STATUSES = {
    "pending_arrival",
    "pending_assignment",
    "assigned",
    "in_maintenance",
    "technically_completed",
    "pending_release",
    "closed",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require(actor: User, permission: str) -> None:
    if not user_has_permission(actor, permission):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para esta operación de Mantenimiento",
        )


def _require_any(actor: User, *permissions: str) -> None:
    if any(user_has_permission(actor, permission) for permission in permissions):
        return

    raise HTTPException(
        status_code=403,
        detail="No tienes permiso para esta operación de Mantenimiento",
    )


def _active_order(db: Session, service_order_id: int) -> ServiceOrder:
    order = db.get(ServiceOrder, service_order_id)

    if order is None or not order.is_active:
        raise HTTPException(
            status_code=404,
            detail="ETS no encontrado",
        )

    if order.status in {"closed", "cancelled"}:
        raise HTTPException(
            status_code=409,
            detail="El ETS no admite cambios operativos",
        )

    return order


def _query(service_order_id: int):
    return (
        select(MaintenanceExecution)
        .where(
            MaintenanceExecution.service_order_id == service_order_id,
        )
        .options(
            selectinload(MaintenanceExecution.pauses),
            selectinload(MaintenanceExecution.materials),
            selectinload(MaintenanceExecution.changes),
            selectinload(MaintenanceExecution.service_unit),
            selectinload(MaintenanceExecution.service_stage),
        )
        .order_by(MaintenanceExecution.id)
        .execution_options(populate_existing=True)
    )


def _execution(
    db: Session,
    service_order_id: int,
    execution_id: int,
) -> MaintenanceExecution:
    execution = db.scalar(
        _query(service_order_id).where(
            MaintenanceExecution.id == execution_id,
        )
    )

    if execution is None:
        raise HTTPException(
            status_code=404,
            detail="Ejecución de Mantenimiento no encontrada",
        )

    return execution


def _maintenance_configuration(item: ServiceOrderItem) -> dict:
    snapshot = item.service_snapshot or {}
    config = snapshot.get("maintenance_configuration_snapshot") or {}

    maintenance_type = (
        config.get("maintenance_type")
        or snapshot.get("calibration_scope_snapshot")
        or "preventive"
    )

    if maintenance_type not in {"preventive", "corrective"}:
        maintenance_type = "preventive"

    return {
        "maintenance_type": maintenance_type,
        "base_materials": list(
            config.get("base_materials") or []
        ),
        "source": (
            "quotation_snapshot"
            if config
            else "legacy_structured_default"
        ),
    }


def initialize_maintenance_execution(
    db: Session,
    order: ServiceOrder,
    *,
    user_id: int,
) -> None:
    items = [
        item
        for item in order.items
        if item.is_active
        and item.operational_category == "maintenance"
    ]

    if not items:
        return

    work_orders = sorted(
        (
            work_order
            for work_order in order.work_orders
            if work_order.is_active
        ),
        key=lambda value: value.sequence,
    )

    if not work_orders:
        raise HTTPException(
            status_code=409,
            detail=(
                "Mantenimiento requiere al menos una Orden de Trabajo "
                "activa antes de inicializarse"
            ),
        )

    unit_offset = 0

    for item in items:
        if db.scalar(
            select(MaintenanceExecution.id).where(
                MaintenanceExecution.service_order_item_id == item.id
            )
        ):
            continue

        config = _maintenance_configuration(item)

        for _ in range(item.quantity):
            work_order = work_orders[
                min(
                    unit_offset // 10,
                    len(work_orders) - 1,
                )
            ]

            unit = ServiceUnit(
                service_order_id=order.id,
                work_order_id=work_order.id,
                origin_service_order_item_id=item.id,
                initial_category="maintenance",
                evolution_enabled=False,
                name=item.service_name,
                identification_status="pending",
                status="active",
            )

            db.add(unit)
            db.flush()

            stage = ServiceStage(
                service_unit_id=unit.id,
                sequence=1,
                category="maintenance",
                status="authorized",
                origin="approved_quotation",
                quotation_item_id=item.quotation_item_id,
            )

            db.add(stage)
            db.flush()

            execution = MaintenanceExecution(
                service_order_id=order.id,
                service_order_item_id=item.id,
                service_unit_id=unit.id,
                service_stage_id=stage.id,
                maintenance_type=config["maintenance_type"],
                location_mode=None,
                configuration_snapshot=config,
                status="pending_assignment",
            )

            db.add(execution)
            db.flush()

            for material in config["base_materials"]:
                if not material.get("name"):
                    continue

                db.add(
                    MaintenanceMaterial(
                        maintenance_execution_id=execution.id,
                        material_type="required",
                        name=str(material["name"])[:180],
                        quantity=material.get("quantity") or 1,
                        unit=str(
                            material.get("unit") or "pieza"
                        )[:40],
                        component=material.get("component"),
                        notes=material.get("notes"),
                        internal_unit_cost=material.get(
                            "internal_unit_cost"
                        ),
                        decision="pending",
                        source="catalog_snapshot",
                    )
                )

            unit_offset += 1

    write_audit_log(
        db,
        action="maintenance.initialized",
        entity="service_orders",
        entity_id=order.id,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# BLOCKERS / READINESS
# ---------------------------------------------------------------------------


def _blocker(
    execution: MaintenanceExecution,
    message: str,
    section: str,
    field: str,
    *,
    severity: str = "blocker",
) -> dict:
    return {
        "execution_id": execution.id,
        "severity": severity,
        "message": message,
        "section": section,
        "field": field,
    }

def _location_blockers(
    execution: MaintenanceExecution,
) -> list[dict]:
    if execution.location_mode in {
        "laboratory",
        "field",
    }:
        return []

    return [
        _blocker(
            execution,
            "Define la modalidad operativa de esta unidad.",
            "assignment",
            "location_mode",
        )
    ]

def _equipment_blockers(
    execution: MaintenanceExecution,
) -> list[dict]:
    if execution.service_unit.equipment_id is not None:
        return []

    if execution.location_mode is None:
        return []

    if execution.location_mode == "laboratory":
        message = (
            "Registra el arribo y vincula el equipo."
        )
        section = "arrival"
    else:
        message = (
            "Da de alta o vincula el equipo "
            "que será atendido en campo."
        )
        section = "equipment"

    return [
        _blocker(
            execution,
            message,
            section,
            "equipment",
        )
    ]


def _assignment_blockers(
    execution: MaintenanceExecution,
) -> list[dict]:
    blockers: list[dict] = []

    if execution.technician_id is None:
        blockers.append(
            _blocker(
                execution,
                "Asigna un técnico responsable.",
                "assignment",
                "technician_id",
            )
        )

    return blockers


def _field_visit_blockers(
    execution: MaintenanceExecution,
) -> list[dict]:
    if execution.location_mode != "field":
        return []

    if execution.field_request_status == "accepted":
        return []

    return [
        _blocker(
            execution,
            (
                "El técnico debe aceptar y programar "
                "la visita de campo."
            ),
            "assignment",
            "field_request_status",
        )
    ]


def _active_pause_blockers(
    execution: MaintenanceExecution,
) -> list[dict]:
    blockers: list[dict] = []

    for pause in execution.pauses:
        if pause.status != "active":
            continue

        blockers.append(
            _blocker(
                execution,
                f"Resuelve la pausa: {pause.reason}",
                "pauses",
                f"pause-{pause.id}",
            )
        )

    return blockers


def _commercial_blockers(
    execution: MaintenanceExecution,
) -> list[dict]:
    blockers: list[dict] = []

    for change in execution.changes:
        if change.status != "requested":
            continue

        if change.change_type == "corrective":
            message = (
                "Existe una revisión comercial pendiente para "
                "convertir el alcance a mantenimiento correctivo."
            )
        elif change.change_type == "repair":
            message = (
                "Existe una solicitud pendiente para vincular "
                "un servicio de Reparación."
            )
        else:
            message = (
                "Existe una solicitud de Investigación pendiente "
                "de resolución administrativa."
            )

        blockers.append(
            _blocker(
                execution,
                message,
                "future",
                f"change-{change.id}",
            )
        )

    return blockers


def _investigation_blockers(
    execution: MaintenanceExecution,
) -> list[dict]:
    if execution.investigation_status not in {
        "required",
        "open",
    }:
        return []

    if execution.investigation_status == "required":
        message = (
            "El equipo quedó inoperable o requiere investigación. "
            "Un autorizador debe revisar el caso antes del cierre."
        )
    else:
        message = (
            "Existe una investigación administrativa abierta "
            "que debe resolverse antes del cierre."
        )

    return [
        _blocker(
            execution,
            message,
            "investigation",
            "investigation_status",
        )
    ]


def _technical_capture_blockers(
    execution: MaintenanceExecution,
) -> list[dict]:
    blockers: list[dict] = []

    if execution.initial_condition is None:
        blockers.append(
            _blocker(
                execution,
                "Completa la condición inicial.",
                "before",
                "initial_condition",
            )
        )

    if not execution.initial_description:
        blockers.append(
            _blocker(
                execution,
                "Describe brevemente cómo llegó el equipo.",
                "before",
                "initial_description",
            )
        )

    if not execution.before_photos:
        blockers.append(
            _blocker(
                execution,
                "Adjunta al menos una evidencia fotográfica inicial.",
                "before",
                "before_photos",
            )
        )

    unresolved_findings = [
        item
        for item in execution.findings or []
        if (
            not item.get("classification")
            or not item.get("resolution")
        )
    ]

    if unresolved_findings:
        blockers.append(
            _blocker(
                execution,
                "Clasifica y resuelve todos los hallazgos.",
                "before",
                "findings",
            )
        )

    if execution.final_condition is None:
        blockers.append(
            _blocker(
                execution,
                "Completa la condición final.",
                "after",
                "final_condition",
            )
        )

    if not execution.functional_result:
        blockers.append(
            _blocker(
                execution,
                "Documenta el resultado funcional.",
                "after",
                "functional_result",
            )
        )

    if not execution.technical_conclusion:
        blockers.append(
            _blocker(
                execution,
                "Registra la conclusión técnica del mantenimiento.",
                "after",
                "technical_conclusion",
            )
        )

    if not execution.after_photos:
        blockers.append(
            _blocker(
                execution,
                "Adjunta al menos una evidencia fotográfica final.",
                "after",
                "after_photos",
            )
        )

    invalid_materials = [
        material
        for material in execution.materials
        if material.material_type == "used"
        and (
            not material.name
            or material.quantity is None
            or material.quantity <= 0
        )
    ]

    if invalid_materials:
        blockers.append(
            _blocker(
                execution,
                "Completa la información de los materiales utilizados.",
                "materials",
                "materials",
            )
        )

    return blockers


def _technical_completion_blockers(
    execution: MaintenanceExecution,
) -> list[dict]:
    blockers: list[dict] = []

    blockers.extend(
        _location_blockers(execution)
    )
    blockers.extend(
        _equipment_blockers(execution)
    )
    blockers.extend(
        _assignment_blockers(execution)
    )
    blockers.extend(
        _field_visit_blockers(execution)
    )
    blockers.extend(
        _active_pause_blockers(execution)
    )
    blockers.extend(
        _commercial_blockers(execution)
    )
    blockers.extend(
        _investigation_blockers(execution)
    )
    blockers.extend(
        _technical_capture_blockers(execution)
    )

    return blockers


def _release_blockers(
    execution: MaintenanceExecution,
) -> list[dict]:
    blockers: list[dict] = []

    blockers.extend(_active_pause_blockers(execution))
    blockers.extend(_commercial_blockers(execution))
    blockers.extend(_investigation_blockers(execution))

    if execution.technical_completed_at is None:
        blockers.append(
            _blocker(
                execution,
                "El trabajo técnico todavía no ha sido terminado.",
                "completion",
                "technical_completed_at",
            )
        )

    if execution.report_status != "generated":
        blockers.append(
            _blocker(
                execution,
                "Genera el reporte de Mantenimiento.",
                "report",
                "report_status",
            )
        )

    if (
        execution.signed_report_version
        != execution.report_version
        or execution.signed_at is None
    ):
        blockers.append(
            _blocker(
                execution,
                "Obtén la firma sobre la versión vigente del reporte.",
                "signature",
                "signature_data_url",
            )
        )

    return blockers


def _closure_blockers(
    execution: MaintenanceExecution,
) -> list[dict]:
    blockers = _technical_completion_blockers(execution)

    if execution.technical_completed_at is None:
        blockers.append(
            _blocker(
                execution,
                "Marca el mantenimiento como técnicamente terminado.",
                "completion",
                "technical_completed_at",
            )
        )

    if execution.report_status != "generated":
        blockers.append(
            _blocker(
                execution,
                "Genera el reporte de Mantenimiento.",
                "report",
                "report_status",
            )
        )

    if (
        execution.signed_report_version
        != execution.report_version
        or execution.signed_at is None
    ):
        blockers.append(
            _blocker(
                execution,
                "Obtén la firma sobre la versión vigente del reporte.",
                "signature",
                "signature_data_url",
            )
        )

    return blockers


def _current_blockers(
    execution: MaintenanceExecution,
) -> list[dict]:
    if execution.status == "closed":
        return []

    if execution.status == "pending_arrival":
        return _equipment_blockers(execution)

    if execution.status == "pending_assignment":
        return (
            _location_blockers(execution)
            + _assignment_blockers(execution)
        )

    if execution.status == "assigned":
        blockers = _equipment_blockers(execution)
        blockers.extend(_assignment_blockers(execution))
        blockers.extend(_field_visit_blockers(execution))
        return blockers

    if execution.status == "in_maintenance":
        return _technical_completion_blockers(execution)

    if execution.status == "technically_completed":
        blockers: list[dict] = []

        if execution.report_status != "generated":
            blockers.append(
                _blocker(
                    execution,
                    "Genera el reporte de Mantenimiento.",
                    "report",
                    "report_status",
                )
            )

        return blockers

    if execution.status == "pending_release":
        return _release_blockers(execution)

    # Compatibilidad temporal con datos viejos.
    if execution.status == "paused":
        return [
            _blocker(
                execution,
                (
                    "Este registro utiliza el estado legado 'paused'. "
                    "Debe reconciliarse con el lifecycle vigente."
                ),
                "pauses",
                "legacy_status",
            ),
            *_active_pause_blockers(execution),
        ]

    return [
        _blocker(
            execution,
            f"Estado de Mantenimiento no reconocido: {execution.status}",
            "status",
            "status",
        )
    ]


def _notices(
    execution: MaintenanceExecution,
) -> list[dict]:
    notices: list[dict] = []

    for item in execution.recommendations or []:
        decision = item.get("decision")

        if decision not in {"pending", "rejected"}:
            continue

        notices.append(
            {
                "execution_id": execution.id,
                "severity": (
                    "warning"
                    if decision == "pending"
                    else "recommendation"
                ),
                "message": str(
                    item.get("description")
                    or item.get("recommendation")
                    or "Recomendación documentada"
                ),
                "section": "future",
                "field": "recommendations",
            }
        )

    return notices


def maintenance_board(
    db: Session,
    service_order_id: int,
) -> dict:
    order = db.get(ServiceOrder, service_order_id)

    if order is None or not order.is_active:
        raise HTTPException(
            status_code=404,
            detail="ETS no encontrado",
        )

    executions = list(
        db.scalars(
            _query(service_order_id)
        ).all()
    )

    if not executions:
        raise HTTPException(
            status_code=404,
            detail="El ETS no contiene Mantenimiento",
        )

    all_current_blockers: list[dict] = []
    all_closure_blockers: list[dict] = []
    rendered: list[dict] = []

    for execution in executions:
        current_blockers = _current_blockers(execution)
        closure_blockers = (
            []
            if execution.status == "closed"
            else _closure_blockers(execution)
        )

        all_current_blockers.extend(current_blockers)
        all_closure_blockers.extend(closure_blockers)

        original_type = (
            (execution.configuration_snapshot or {}).get(
                "maintenance_type"
            )
            or execution.maintenance_type
        )

        rendered.append(
            {
                **execution.__dict__,
                "equipment_id": (
                    execution.service_unit.equipment_id
                ),
                "equipment_name": execution.service_unit.name,
                "work_order_number": (
                    execution.service_unit.work_order.work_order_number
                ),
                "original_maintenance_type": original_type,
                "maintenance_type_evolved": (
                    original_type
                    != execution.maintenance_type
                ),
                "has_active_pause": any(
                    pause.status == "active"
                    for pause in execution.pauses
                ),
                "active_pauses": [
                    pause
                    for pause in execution.pauses
                    if pause.status == "active"
                ],
                "blockers": current_blockers,
                "closure_blockers": closure_blockers,
                "notices": _notices(execution),
            }
        )

    return {
        "service_order_id": service_order_id,
        "executions": rendered,
        "blockers": all_current_blockers,
        "closure_blockers": all_closure_blockers,
        "can_close": not all_closure_blockers,
    }


# ---------------------------------------------------------------------------
# EQUIPMENT / ARRIVAL
# ---------------------------------------------------------------------------


def register_arrival(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: MaintenanceEquipmentCreate,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.manage",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if (
        execution.location_mode != "laboratory"
        or execution.status != "pending_arrival"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Sólo un mantenimiento de laboratorio "
                "pendiente admite arribo"
            ),
        )

    unit = execution.service_unit

    if payload.equipment_id:
        equipment = db.get(
            Equipment,
            payload.equipment_id,
        )

        if (
            equipment is None
            or equipment.service_order_id
            != service_order_id
            or equipment.service_unit is not None
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "El equipo no puede vincularse "
                    "a esta unidad"
                ),
            )
    else:
        equipment = Equipment(
            service_order_id=service_order_id,
            work_order_id=unit.work_order_id,
            service_order_item_id=(
                execution.service_order_item_id
            ),
            name=payload.name,
            brand=payload.brand,
            model=payload.model,
            serial_number=payload.serial_number,
            internal_id=payload.internal_id,
            range_or_capacity=payload.range_or_capacity,
            status="registered",
        )

        db.add(equipment)
        db.flush()

    unit.equipment_id = equipment.id
    unit.name = equipment.name
    unit.brand = equipment.brand
    unit.model = equipment.model
    unit.serial_number = equipment.serial_number

    unit.identification_status = (
        "complete"
        if (
            equipment.brand
            and equipment.model
            and equipment.serial_number
        )
        else "partial"
    )

    execution.status = (
        "assigned"
        if execution.technician_id is not None
        else "pending_assignment"
    )

    write_audit_log(
        db,
        action="maintenance.arrival_registered",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "equipment_id": equipment.id,
        },
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


def register_field_equipment(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: MaintenanceEquipmentCreate,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.manage",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if (
        execution.location_mode != "field"
        or execution.status != "assigned"
        or execution.service_unit.equipment_id is not None
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Sólo un mantenimiento de campo "
                "asignado y sin equipo vinculado "
                "admite este registro"
            ),
        )

    unit = execution.service_unit

    if payload.equipment_id:
        equipment = db.get(
            Equipment,
            payload.equipment_id,
        )

        if (
            equipment is None
            or equipment.service_order_id
            != service_order_id
            or equipment.service_unit is not None
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "El equipo no puede vincularse "
                    "a esta unidad"
                ),
            )
    else:
        equipment = Equipment(
            service_order_id=service_order_id,
            work_order_id=unit.work_order_id,
            service_order_item_id=(
                execution.service_order_item_id
            ),
            name=payload.name,
            brand=payload.brand,
            model=payload.model,
            serial_number=payload.serial_number,
            internal_id=payload.internal_id,
            range_or_capacity=payload.range_or_capacity,
            status="registered",
        )

        db.add(equipment)
        db.flush()

    unit.equipment_id = equipment.id
    unit.name = equipment.name
    unit.brand = equipment.brand
    unit.model = equipment.model
    unit.serial_number = equipment.serial_number

    unit.identification_status = (
        "complete"
        if (
            equipment.brand
            and equipment.model
            and equipment.serial_number
        )
        else "partial"
    )

    write_audit_log(
        db,
        action="maintenance.field_equipment_registered",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "equipment_id": equipment.id,
        },
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


# ---------------------------------------------------------------------------
# ASSIGNMENT / FIELD
# ---------------------------------------------------------------------------


def prepare_execution(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: MaintenancePrepare,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.manage",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if execution.status != "pending_assignment":
        raise HTTPException(
            status_code=409,
            detail=(
                "El mantenimiento no está "
                "pendiente de asignación"
            ),
        )

    technician = db.get(
        User,
        payload.technician_id,
    )

    if (
        technician is None
        or not technician.is_active
        or not user_has_permission(
            technician,
            "service_orders.maintenance.execute",
        )
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Selecciona un técnico activo con "
                "capacidad de ejecutar Mantenimiento"
            ),
        )

    execution.technician_id = (
        payload.technician_id
    )

    execution.location_mode = (
        payload.location_mode
    )

    execution.scheduled_for = (
        payload.scheduled_for
    )

    if payload.location_mode == "laboratory":
        execution.field_address = None
        execution.field_request_status = None

        execution.status = (
            "assigned"
            if execution.service_unit.equipment_id
            is not None
            else "pending_arrival"
        )

    else:
        if not payload.field_address:
            raise HTTPException(
                status_code=422,
                detail=(
                    "La modalidad de campo "
                    "requiere dirección"
                ),
            )

        execution.field_address = (
            payload.field_address
        )

        execution.field_request_status = (
            "requested"
        )

        # El equipo puede identificarse después
        # de la asignación. start_execution()
        # seguirá siendo la autoridad que impida
        # iniciar sin equipo.
        execution.status = "assigned"

    write_audit_log(
        db,
        action="maintenance.assigned",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "technician_id": (
                execution.technician_id
            ),
            "location_mode": (
                execution.location_mode
            ),
            "scheduled_for": (
                execution.scheduled_for.isoformat()
                if execution.scheduled_for
                else None
            ),
        },
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )

def accept_field_visit(
    db: Session,
    service_order_id: int,
    execution_id: int,
    scheduled_for: datetime,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.execute",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if execution.status != "assigned":
        raise HTTPException(
            status_code=409,
            detail=(
                "El mantenimiento no se encuentra "
                "en etapa de asignación"
            ),
        )

    if execution.location_mode != "field":
        raise HTTPException(
            status_code=409,
            detail=(
                "Sólo un mantenimiento de campo "
                "puede aceptar una visita"
            ),
        )

    if execution.technician_id != actor.id:
        raise HTTPException(
            status_code=409,
            detail=(
                "La visita no está asignada "
                "a este técnico"
            ),
        )

    if execution.field_request_status != "requested":
        raise HTTPException(
            status_code=409,
            detail=(
                "La visita de campo no se encuentra "
                "pendiente de aceptación"
            ),
        )

    if execution.service_unit.equipment_id is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "La visita de campo requiere "
                "un equipo vinculado"
            ),
        )

    execution.field_request_status = "accepted"
    execution.scheduled_for = scheduled_for

    write_audit_log(
        db,
        action="maintenance.field_visit_accepted",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "scheduled_for": (
                scheduled_for.isoformat()
            ),
            "field_request_status": "accepted",
        },
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


def start_execution(
    db: Session,
    service_order_id: int,
    execution_id: int,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.execute",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if (
        execution.technician_id != actor.id
        or execution.status != "assigned"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "El mantenimiento no está "
                "asignado a este técnico"
            ),
        )

    if execution.service_unit.equipment_id is None:
        raise HTTPException(
            status_code=409,
            detail="El mantenimiento no tiene equipo vinculado",
        )

    if (
        execution.location_mode == "field"
        and execution.field_request_status != "accepted"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "La visita de campo debe aceptarse "
                "y programarse"
            ),
        )

    execution.status = "in_maintenance"
    execution.service_stage.status = "in_progress"

    if execution.service_stage.started_at is None:
        execution.service_stage.started_at = _now()

    write_audit_log(
        db,
        action="maintenance.started",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


# ---------------------------------------------------------------------------
# TECHNICAL CAPTURE
# ---------------------------------------------------------------------------


def save_capture(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: MaintenanceCapture,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.execute",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if (
        execution.technician_id != actor.id
        or execution.status != "in_maintenance"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "La captura requiere una intervención "
                "activa asignada"
            ),
        )

    for key, value in payload.model_dump().items():
        setattr(execution, key, value)

    # El técnico determina el resultado técnico.
    # No tiene autoridad para convertir esto por sí mismo
    # en una pausa administrativa del lifecycle.
    if execution.final_condition == "not_operational":
        if execution.investigation_status not in {
            "open",
            "resolved",
        }:
            execution.investigation_status = "required"

    elif (
        execution.investigation_status == "required"
        and execution.linked_investigation_stage_id is None
    ):
        # Si el técnico corrige la captura antes de que la
        # investigación haya sido formalmente abierta,
        # eliminamos el requerimiento automático.
        execution.investigation_status = None

    execution.report_status = "pending"

    write_audit_log(
        db,
        action="maintenance.capture_saved",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "initial_condition": execution.initial_condition,
            "final_condition": execution.final_condition,
            "investigation_status": (
                execution.investigation_status
            ),
        },
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


# ---------------------------------------------------------------------------
# PAUSES
# ---------------------------------------------------------------------------


def add_pause(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: MaintenancePauseCreate,
    *,
    actor: User,
):
    _require_any(
        actor,
        "service_orders.maintenance.execute",
        "service_orders.maintenance.authorize",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if execution.status != "in_maintenance":
        raise HTTPException(
            status_code=409,
            detail=(
                "Sólo una intervención activa "
                "puede registrar una pausa"
            ),
        )

    is_technician = (
        execution.technician_id == actor.id
        and user_has_permission(
            actor,
            "service_orders.maintenance.execute",
        )
    )

    is_authorizer = user_has_permission(
        actor,
        "service_orders.maintenance.authorize",
    )

    if not is_technician and not is_authorizer:
        raise HTTPException(
            status_code=403,
            detail=(
                "Sólo el técnico asignado o un "
                "autorizador puede registrar una pausa"
            ),
        )

    if (
        payload.pause_type
        == "administrative_investigation"
        and not is_authorizer
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "La investigación administrativa "
                "sólo puede ser abierta por un autorizador"
            ),
        )

    responsible = db.get(
        User,
        payload.responsible_user_id,
    )

    if (
        responsible is None
        or not responsible.is_active
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "El responsable de la pausa "
                "no existe o está inactivo"
            ),
        )

    duplicate = next(
        (
            item
            for item in execution.pauses
            if (
                item.status == "active"
                and item.pause_type == payload.pause_type
            )
        ),
        None,
    )

    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ya existe una pausa activa "
                "del mismo tipo"
            ),
        )

    pause = MaintenancePause(
        maintenance_execution_id=execution.id,
        **payload.model_dump(),
    )

    db.add(pause)

    # Importante:
    # NO modificamos execution.status.
    # La pausa es una condición paralela.
    write_audit_log(
        db,
        action="maintenance.pause_added",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "pause_type": payload.pause_type,
            "reason": payload.reason,
            "responsible_user_id": (
                payload.responsible_user_id
            ),
        },
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


def resolve_pause(
    db: Session,
    service_order_id: int,
    execution_id: int,
    pause_id: int,
    resolution: str,
    *,
    actor: User,
):
    _require_any(
        actor,
        "service_orders.maintenance.execute",
        "service_orders.maintenance.authorize",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    pause = next(
        (
            item
            for item in execution.pauses
            if item.id == pause_id
        ),
        None,
    )

    if (
        pause is None
        or pause.status != "active"
    ):
        raise HTTPException(
            status_code=409,
            detail="Pausa activa no encontrada",
        )

    if (
        execution.technician_id != actor.id
        and not user_has_permission(
            actor,
            "service_orders.maintenance.authorize",
        )
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Sólo el técnico asignado o un "
                "autorizador puede resolver esta pausa"
            ),
        )

    if (
        pause.pause_type
        == "administrative_investigation"
        and not user_has_permission(
            actor,
            "service_orders.maintenance.authorize",
        )
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "La pausa de investigación "
                "requiere resolución administrativa"
            ),
        )

    pause.status = "resolved"
    pause.resolution = resolution
    pause.resolved_by_id = actor.id
    pause.resolved_at = _now()

    # NO reconstruimos execution.status.
    # Siempre permaneció en su estado principal.
    write_audit_log(
        db,
        action="maintenance.pause_resolved",
        entity="maintenance_pauses",
        entity_id=pause.id,
        user_id=actor.id,
        new_values={
            "resolution": resolution,
        },
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


# ---------------------------------------------------------------------------
# MATERIALS
# ---------------------------------------------------------------------------


def add_material(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: MaintenanceMaterialCreate,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.execute",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if execution.technician_id != actor.id:
        raise HTTPException(
            status_code=403,
            detail=(
                "Sólo el técnico asignado "
                "documenta materiales"
            ),
        )

    if execution.status != "in_maintenance":
        raise HTTPException(
            status_code=409,
            detail=(
                "Los materiales técnicos sólo pueden "
                "registrarse durante la intervención"
            ),
        )

    material = MaintenanceMaterial(
        maintenance_execution_id=execution.id,
        source="technician",
        **payload.model_dump(),
    )

    db.add(material)

    write_audit_log(
        db,
        action="maintenance.material_added",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "material_type": payload.material_type,
            "name": payload.name,
            "quantity": str(payload.quantity),
            "unit": payload.unit,
        },
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


# ---------------------------------------------------------------------------
# COMMERCIAL / DERIVED CHANGES
# ---------------------------------------------------------------------------


def request_change(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: MaintenanceChangeCreate,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.execute",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if execution.technician_id != actor.id:
        raise HTTPException(
            status_code=403,
            detail=(
                "Sólo el técnico asignado "
                "registra hallazgos derivados"
            ),
        )

    if execution.status != "in_maintenance":
        raise HTTPException(
            status_code=409,
            detail=(
                "Las solicitudes derivadas sólo pueden "
                "originarse durante la intervención"
            ),
        )

    if (
        payload.change_type == "corrective"
        and execution.maintenance_type != "preventive"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Sólo un mantenimiento preventivo "
                "puede solicitar alcance correctivo"
            ),
        )

    duplicate = next(
        (
            item
            for item in execution.changes
            if (
                item.status == "requested"
                and item.change_type == payload.change_type
            )
        ),
        None,
    )

    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ya existe una solicitud pendiente "
                "del mismo tipo"
            ),
        )

    change = MaintenanceChangeRequest(
        maintenance_execution_id=execution.id,
        **payload.model_dump(),
    )

    db.add(change)
    db.flush()

    if payload.change_type == "corrective":
        active_authorization_pause = next(
            (
                item
                for item in execution.pauses
                if (
                    item.status == "active"
                    and item.pause_type
                    in {
                        "authorization",
                        "commercial_review",
                    }
                )
            ),
            None,
        )

        if active_authorization_pause is None:
            db.add(
                MaintenancePause(
                    maintenance_execution_id=execution.id,
                    pause_type="commercial_review",
                    reason=(
                        "Pendiente de revisión comercial "
                        "para alcance correctivo"
                    ),
                    responsible_user_id=actor.id,
                )
            )

    if payload.change_type == "investigation":
        execution.investigation_status = "required"

    # NO modificamos execution.status.
    # Una revisión comercial o investigación es paralela
    # al lifecycle principal.
    write_audit_log(
        db,
        action="maintenance.change_requested",
        entity="maintenance_change_requests",
        entity_id=change.id,
        user_id=actor.id,
        new_values={
            "change_type": payload.change_type,
            "summary": payload.summary,
        },
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


def _approved_linked_item(
    db: Session,
    execution: MaintenanceExecution,
    quotation_item_id: int | None,
) -> bool:
    if quotation_item_id is None:
        return False

    item = db.get(
        QuotationItem,
        quotation_item_id,
    )

    if (
        item is None
        or item.operational_category != "maintenance"
    ):
        return False

    if (
        item.source_service_order_id
        != execution.service_order_id
        or item.source_service_unit_id
        != execution.service_unit_id
        or item.source_stage_id
        != execution.service_stage_id
    ):
        return False

    return (
        db.scalar(
            select(
                QuotationItemDecision.id
            ).where(
                QuotationItemDecision.quotation_item_id
                == item.id,
                QuotationItemDecision.decision
                == "approved",
            )
        )
        is not None
    )


def resolve_change(
    db: Session,
    service_order_id: int,
    execution_id: int,
    change_id: int,
    payload: MaintenanceChangeResolve,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.authorize",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    change = next(
        (
            item
            for item in execution.changes
            if item.id == change_id
        ),
        None,
    )

    if (
        change is None
        or change.status != "requested"
    ):
        raise HTTPException(
            status_code=409,
            detail="Solicitud pendiente no encontrada",
        )

    if (
        payload.decision == "approved"
        and change.change_type == "corrective"
        and not _approved_linked_item(
            db,
            execution,
            payload.quotation_item_id,
        )
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "El correctivo requiere una partida "
                "aprobada vinculada a esta unidad y etapa"
            ),
        )

    if (
        payload.decision == "overridden"
        and len(payload.reason.strip()) < 10
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "El override administrativo requiere "
                "justificación suficiente"
            ),
        )

    if (
        change.change_type in {
            "repair",
            "investigation",
        }
        and payload.decision == "linked"
        and payload.linked_service_order_id is None
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "La vinculación requiere ETS destino"
            ),
        )

    if payload.decision == "linked":
        target = db.get(
            ServiceOrder,
            payload.linked_service_order_id,
        )

        source_order = db.get(
            ServiceOrder,
            execution.service_order_id,
        )

        expected_category = (
            "repair"
            if change.change_type == "repair"
            else "general_service"
        )

        if (
            target is None
            or not target.is_active
            or target.client_id
            != source_order.client_id
            or not any(
                item.is_active
                and item.operational_category
                == expected_category
                for item in target.items
            )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "El ETS vinculado debe pertenecer "
                    f"al mismo cliente y contener "
                    f"{expected_category}"
                ),
            )

    change.status = payload.decision
    change.quotation_item_id = (
        payload.quotation_item_id
    )
    change.linked_service_order_id = (
        payload.linked_service_order_id
    )
    change.decision_reason = payload.reason
    change.decided_by_id = actor.id
    change.decided_at = _now()

    if (
        change.change_type == "corrective"
        and payload.decision
        in {
            "approved",
            "overridden",
        }
    ):
        # configuration_snapshot conserva el tipo original.
        # maintenance_type representa el alcance vigente.
        execution.maintenance_type = "corrective"

    if (
        change.change_type == "investigation"
        and payload.decision == "linked"
    ):
        execution.investigation_status = "open"

        next_sequence = (
            int(
                db.scalar(
                    select(
                        func.max(
                            ServiceStage.sequence
                        )
                    ).where(
                        ServiceStage.service_unit_id
                        == execution.service_unit_id
                    )
                )
                or 0
            )
            + 1
        )

        investigation = ServiceStage(
            service_unit_id=execution.service_unit_id,
            sequence=next_sequence,
            category="diagnosis",
            status="authorized",
            origin="maintenance_investigation",
            source_stage_id=execution.service_stage_id,
        )

        db.add(investigation)
        db.flush()

        execution.linked_investigation_stage_id = (
            investigation.id
        )

        existing_investigation_pause = next(
            (
                item
                for item in execution.pauses
                if (
                    item.status == "active"
                    and item.pause_type
                    == "administrative_investigation"
                )
            ),
            None,
        )

        if existing_investigation_pause is None:
            db.add(
                MaintenancePause(
                    maintenance_execution_id=execution.id,
                    pause_type="administrative_investigation",
                    reason=(
                        "Investigación administrativa abierta "
                        "por condición inoperable del equipo"
                    ),
                    responsible_user_id=actor.id,
                )
            )

    if change.change_type == "corrective":
        for pause in execution.pauses:
            if (
                pause.status == "active"
                and pause.pause_type
                in {
                    "authorization",
                    "commercial_review",
                }
            ):
                pause.status = "resolved"
                pause.resolution = payload.reason
                pause.resolved_by_id = actor.id
                pause.resolved_at = _now()

    # NO restauramos execution.status.
    # Nunca abandonó su estado principal.
    write_audit_log(
        db,
        action="maintenance.change_resolved",
        entity="maintenance_change_requests",
        entity_id=change.id,
        user_id=actor.id,
        new_values=payload.model_dump(),
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


# ---------------------------------------------------------------------------
# INVESTIGATION
# ---------------------------------------------------------------------------


def resolve_investigation(
    db: Session,
    service_order_id: int,
    execution_id: int,
    reason: str,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.authorize",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if execution.investigation_status not in {
        "required",
        "open",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "No existe una investigación pendiente"
            ),
        )

    if len(reason.strip()) < 10:
        raise HTTPException(
            status_code=422,
            detail=(
                "La resolución de investigación requiere "
                "una justificación suficiente"
            ),
        )

    execution.investigation_status = "resolved"

    if execution.linked_investigation_stage_id:
        stage = db.get(
            ServiceStage,
            execution.linked_investigation_stage_id,
        )

        if stage is not None:
            stage.status = "completed"
            stage.completed_at = _now()
            stage.result = {
                "administrative_resolution": reason,
            }

    for pause in execution.pauses:
        if (
            pause.status == "active"
            and pause.pause_type
            == "administrative_investigation"
        ):
            pause.status = "resolved"
            pause.resolution = reason
            pause.resolved_by_id = actor.id
            pause.resolved_at = _now()

    # NO modificamos execution.status.
    write_audit_log(
        db,
        action="maintenance.investigation_resolved",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "reason": reason,
        },
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


# ---------------------------------------------------------------------------
# TECHNICAL COMPLETION
# ---------------------------------------------------------------------------


def complete_technical(
    db: Session,
    service_order_id: int,
    execution_id: int,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.execute",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if (
        execution.technician_id != actor.id
        or execution.status != "in_maintenance"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "El mantenimiento no está activo "
                "para este técnico"
            ),
        )

    blockers = _technical_completion_blockers(
        execution
    )

    if blockers:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "El mantenimiento todavía tiene "
                    "bloqueantes técnicos"
                ),
                "blockers": blockers,
            },
        )

    execution.status = "technically_completed"
    execution.technical_completed_at = _now()

    execution.service_stage.status = "completed"
    execution.service_stage.completed_at = (
        execution.technical_completed_at
    )

    execution.service_stage.result = {
        "maintenance_type": execution.maintenance_type,
        "original_maintenance_type": (
            (
                execution.configuration_snapshot
                or {}
            ).get("maintenance_type")
            or execution.maintenance_type
        ),
        "initial_condition": execution.initial_condition,
        "final_condition": execution.final_condition,
    }

    write_audit_log(
        db,
        action="maintenance.technical_completed",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


# ---------------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------------


def _report_html(
    order: ServiceOrder,
    execution: MaintenanceExecution,
) -> str:
    equipment = execution.service_unit.equipment

    equipment_name = (
        equipment.name
        if equipment
        else execution.service_unit.name
    )

    original_type = (
        (
            execution.configuration_snapshot
            or {}
        ).get("maintenance_type")
        or execution.maintenance_type
    )

    used_materials = "".join(
        (
            f"<li>{escape(str(item.name))}: "
            f"{escape(str(item.quantity))} "
            f"{escape(item.unit)}</li>"
        )
        for item in execution.materials
        if item.material_type == "used"
    ) or "<li>Sin materiales utilizados documentados</li>"

    required_materials = "".join(
        (
            f"<li>{escape(str(item.name))}: "
            f"{escape(str(item.quantity))} "
            f"{escape(item.unit)}"
            f"{' — ' + escape(str(item.notes)) if item.notes else ''}"
            f"</li>"
        )
        for item in execution.materials
        if item.material_type == "required"
    ) or "<li>Sin materiales recomendados documentados</li>"

    findings = "".join(
        (
            f"<li>"
            f"{escape(str(item.get('component', 'General')))}: "
            f"{escape(str(item.get('description', '')))}"
            f" — {escape(str(item.get('resolution', '')))}"
            f"</li>"
        )
        for item in execution.findings or []
    ) or "<li>Sin hallazgos relevantes</li>"

    actions = "".join(
        (
            f"<li>"
            f"{escape(str(item.get('action', 'Acción')))}"
            f" — "
            f"{escape(str(item.get('component', 'General')))}"
            f"{' — ' + escape(str(item.get('result'))) if item.get('result') else ''}"
            f"</li>"
        )
        for item in execution.actions or []
    ) or "<li>Sin acciones registradas</li>"

    recommendations = "".join(
        (
            f"<li>"
            f"{escape(str(item.get('description', item.get('recommendation', ''))))}"
            f" — decisión: "
            f"{escape(str(item.get('decision', 'pending')))}"
            f"</li>"
        )
        for item in execution.recommendations or []
    ) or "<li>Sin recomendaciones</li>"

    def photos(
        refs: list,
        label: str,
    ) -> str:
        rendered: list[str] = []

        for reference in refs:
            path = resolve_storage_path(reference)
            caption = escape(str(reference))

            if (
                path is not None
                and path.is_file()
                and not path.is_symlink()
                and path.suffix.lower()
                in {
                    ".png",
                    ".jpg",
                    ".jpeg",
                }
            ):
                rendered.append(
                    "<figure>"
                    f"<img src='{escape(path.as_uri(), quote=True)}' "
                    "style='max-width:240px;max-height:180px'>"
                    f"<figcaption>{caption}</figcaption>"
                    "</figure>"
                )
            else:
                rendered.append(
                    f"<p>Evidencia fotográfica: {caption}</p>"
                )

        return (
            f"<h4>{escape(label)}</h4>"
            f"{''.join(rendered)}"
        )

    evolution = ""

    if original_type != execution.maintenance_type:
        evolution = (
            "<p>"
            "<b>Alcance original:</b> "
            f"{escape(original_type)}"
            " · "
            "<b>Alcance final autorizado:</b> "
            f"{escape(execution.maintenance_type)}"
            "</p>"
        )

    return f"""
    <html>
      <body style="font-family:sans-serif">
        <h1>Reporte de Mantenimiento</h1>

        <p>
          <b>ETS:</b> {escape(str(order.folio))}
          ·
          <b>OT:</b>
          {escape(str(execution.service_unit.work_order.work_order_number))}
        </p>

        <h2>{escape(equipment_name)}</h2>

        <p>
          <b>Tipo:</b> {escape(execution.maintenance_type)}
          ·
          <b>Modalidad:</b>
            {escape(execution.location_mode or "No definida")}
        </p>

        {evolution}

        <h3>Cómo se encontró</h3>

        <p>
          {escape(execution.initial_condition or "")}:
          {escape(execution.initial_description or "")}
        </p>

        {photos(
            execution.before_photos or [],
            "Fotografías iniciales",
        )}

        <h3>Hallazgos</h3>
        <ul>{findings}</ul>

        <h3>Intervención realizada</h3>
        <ul>{actions}</ul>

        <h3>Materiales utilizados</h3>
        <ul>{used_materials}</ul>

        <h3>Materiales requeridos o recomendados</h3>
        <ul>{required_materials}</ul>

        <h3>Cómo quedó</h3>

        <p>
          {escape(execution.final_condition or "")}:
          {escape(execution.functional_result or "")}
        </p>

        {photos(
            execution.after_photos or [],
            "Fotografías finales",
        )}

        <h3>Recomendaciones</h3>
        <ul>{recommendations}</ul>

        <p>
          <b>Conclusión:</b>
          {escape(execution.technical_conclusion or "")}
        </p>

        <p>
          <b>Técnico:</b>
          {
              escape(
                  execution.technician.full_name
                  if execution.technician
                  else "Pendiente"
              )
          }
          ·
          <b>Fecha:</b>
          {escape(str(execution.technical_completed_at or ""))}
        </p>

        <p>
          <b>Firmante:</b>
          {escape(execution.signer_name or "Pendiente")}
          ·
          <b>Decisión:</b>
          {escape(execution.client_decision or "Pendiente")}
        </p>
      </body>
    </html>
    """


def generate_report(
    db: Session,
    service_order_id: int,
    execution_id: int,
    *,
    actor: User,
) -> tuple[bytes, str]:
    _require(
        actor,
        "service_orders.maintenance.manage",
    )

    order = _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if execution.status not in {
        "technically_completed",
        "pending_release",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "El reporte sólo puede generarse después "
                "de terminar técnicamente el mantenimiento"
            ),
        )

    if execution.technical_completed_at is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "El mantenimiento aún no está "
                "técnicamente terminado"
            ),
        )

    pre_report_blockers = (
        _active_pause_blockers(execution)
        + _commercial_blockers(execution)
        + _investigation_blockers(execution)
    )

    if pre_report_blockers:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "El reporte no puede generarse "
                    "mientras existan bloqueantes"
                ),
                "blockers": pre_report_blockers,
            },
        )

    if execution.report_status != "generated":
        execution.report_version += 1

    execution.report_status = "generated"
    execution.report_generated_at = _now()
    execution.status = "pending_release"

    html = _report_html(
        order,
        execution,
    )

    write_audit_log(
        db,
        action="maintenance.report_generated",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "report_version": execution.report_version,
        },
    )

    db.commit()

    return (
        HTML(string=html).write_pdf(),
        (
            f"{order.folio}"
            f"-MANTENIMIENTO-"
            f"{execution.id}"
            f"-V{execution.report_version}.pdf"
        ),
    )


# ---------------------------------------------------------------------------
# SIGNATURE / RELEASE
# ---------------------------------------------------------------------------


def sign_report(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: MaintenanceSignature,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.sign",
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if execution.status != "pending_release":
        raise HTTPException(
            status_code=409,
            detail=(
                "La firma sólo puede recabarse "
                "cuando el mantenimiento está "
                "pendiente de liberación"
            ),
        )

    if not (
        user_has_permission(
            actor,
            "service_orders.maintenance.manage",
        )
        or user_has_permission(
            actor,
            "service_orders.maintenance.execute",
        )
    ):
        source_order = db.get(
            ServiceOrder,
            execution.service_order_id,
        )

        membership = db.scalar(
            select(
                ClientPortalMembership.id
            ).where(
                ClientPortalMembership.user_id
                == actor.id,
                ClientPortalMembership.client_id
                == source_order.client_id,
                ClientPortalMembership.status
                == "active",
            )
        )

        if membership is None:
            raise HTTPException(
                status_code=404,
                detail="Mantenimiento no encontrado",
            )

    if (
        execution.report_status != "generated"
        or execution.report_version < 1
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Primero genera el reporte "
                "que será firmado"
            ),
        )

    execution.signer_name = payload.signer_name
    execution.signature_data_url = (
        payload.signature_data_url
    )
    execution.client_decision = (
        payload.client_decision
    )
    execution.signed_report_version = (
        execution.report_version
    )
    execution.signed_at = _now()

    write_audit_log(
        db,
        action="maintenance.report_signed",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "report_version": execution.report_version,
            "signer_name": payload.signer_name,
            "client_decision": payload.client_decision,
        },
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )


def close_execution(
    db: Session,
    service_order_id: int,
    execution_id: int,
    *,
    actor: User,
):
    _require(
        actor,
        "service_orders.maintenance.close",
    )

    _active_order(
        db,
        service_order_id,
    )

    execution = _execution(
        db,
        service_order_id,
        execution_id,
    )

    if execution.status != "pending_release":
        raise HTTPException(
            status_code=409,
            detail=(
                "El mantenimiento debe estar pendiente "
                "de liberación antes de cerrarse"
            ),
        )

    blockers = _closure_blockers(
        execution
    )

    if blockers:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Mantenimiento con bloqueantes "
                    "de cierre"
                ),
                "blockers": blockers,
            },
        )

    execution.status = "closed"
    execution.closed_at = _now()
    execution.service_unit.status = "completed"

    write_audit_log(
        db,
        action="maintenance.closed",
        entity="maintenance_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "closed_at": execution.closed_at.isoformat(),
        },
    )

    db.commit()

    return maintenance_board(
        db,
        service_order_id,
    )