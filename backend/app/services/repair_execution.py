"""Servicio de la vertical ETS Reparación.

Espejo arquitectónico de app/services/maintenance_execution.py. Fase 1:
laboratorio únicamente (sin location_mode/field_address). Sigue el mismo
patrón _require/_active_order/_execution/_blocker/board que Mantenimiento.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from weasyprint import HTML

from app.models.maintenance_execution import MaintenanceChangeRequest
from app.models.repair_execution import (
    RepairChangeRequest,
    RepairExecution,
    RepairIntervention,
    RepairPause,
    RepairTest,
)
from app.models.service_execution import ServiceStage, ServiceUnit
from app.models.service_order import ServiceOrder, ServiceOrderItem
from app.models.user import User
from app.schemas.repair_execution import (
    RepairAssign,
    RepairCancel,
    RepairChangeCreate,
    RepairChangeResolve,
    RepairConclude,
    RepairDiagnosis,
    RepairEquipmentCreate,
    RepairInterventionCreate,
    RepairPauseCreate,
    RepairPauseResolve,
    RepairSignature,
    RepairTestCreate,
    RepairWarrantyReopen,
)
from app.services.audit_logs import write_audit_log
from app.services.auth import user_has_permission


# Decisión funcional #9:
# SLA de ~14 días como alerta suave, NO bloqueante duro.
REPAIR_SLA_DAYS = 14


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(
    value: datetime | None,
) -> datetime | None:
    """Normaliza datetimes recuperados de BD a UTC aware.

    PostgreSQL conserva correctamente timezone=True, pero SQLite puede
    devolver DateTime(timezone=True) sin tzinfo durante tests. La lógica
    de dominio trabaja siempre con UTC aware.
    """
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc,
        )

    return value.astimezone(
        timezone.utc,
    )


def _require(
    actor: User,
    permission: str,
) -> None:
    if not user_has_permission(
        actor,
        permission,
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "No tienes permiso para esta "
                "operación de Reparación"
            ),
        )


def _active_order(
    db: Session,
    service_order_id: int,
) -> ServiceOrder:
    order = db.get(
        ServiceOrder,
        service_order_id,
    )

    if (
        order is None
        or not order.is_active
    ):
        raise HTTPException(
            status_code=404,
            detail="ETS no encontrado",
        )

    if order.status in {
        "closed",
        "cancelled",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "El ETS no admite cambios "
                "operativos"
            ),
        )

    return order


def _query(
    service_order_id: int,
):
    return (
        select(RepairExecution)
        .where(
            RepairExecution.service_order_id
            == service_order_id,
        )
        .options(
            selectinload(
                RepairExecution.pauses,
            ),
            selectinload(
                RepairExecution.interventions,
            ),
            selectinload(
                RepairExecution.tests,
            ),
            selectinload(
                RepairExecution.changes,
            ),
            selectinload(
                RepairExecution.service_unit,
            ),
            selectinload(
                RepairExecution.service_stage,
            ),
        )
        .order_by(
            RepairExecution.id,
        )
        .execution_options(
            populate_existing=True,
        )
    )


def _execution(
    db: Session,
    service_order_id: int,
    execution_id: int,
) -> RepairExecution:
    execution = db.scalar(
        _query(
            service_order_id,
        ).where(
            RepairExecution.id
            == execution_id,
        ),
    )

    if execution is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Ejecución de Reparación "
                "no encontrada"
            ),
        )

    return execution


def _repair_configuration(
    item: ServiceOrderItem,
) -> dict:
    snapshot = (
        item.service_snapshot
        or {}
    )

    config = (
        snapshot.get(
            "repair_configuration_snapshot",
        )
        or {}
    )

    return {
        "scope_notes":
            config.get(
                "scope_notes",
            ),
        "source": (
            "quotation_snapshot"
            if config
            else "legacy_structured_default"
        ),
    }


def initialize_repair_execution(
    db: Session,
    order: ServiceOrder,
    *,
    user_id: int,
) -> None:
    items = [
        item
        for item in order.items
        if (
            item.is_active
            and item.operational_category
            == "repair"
        )
    ]

    if not items:
        return

    work_orders = sorted(
        (
            work_order
            for work_order
            in order.work_orders
            if work_order.is_active
        ),
        key=lambda value: value.sequence,
    )

    if not work_orders:
        raise HTTPException(
            status_code=409,
            detail=(
                "Reparación requiere al menos "
                "una Orden de Trabajo activa "
                "antes de inicializarse"
            ),
        )

    # Decisión funcional #1:
    # búsqueda de solo lectura de un
    # MaintenanceChangeRequest que haya
    # vinculado este ETS como destino.
    linked_change = db.scalar(
        select(
            MaintenanceChangeRequest,
        )
        .where(
            MaintenanceChangeRequest
            .linked_service_order_id
            == order.id,

            MaintenanceChangeRequest
            .change_type
            == "repair",

            MaintenanceChangeRequest
            .status
            == "linked",
        )
        .order_by(
            MaintenanceChangeRequest
            .id
            .desc(),
        ),
    )

    origin = (
        "maintenance_linked"
        if linked_change is not None
        else "quotation"
    )

    unit_offset = 0

    for item in items:
        existing = db.scalar(
            select(
                RepairExecution.id,
            ).where(
                RepairExecution
                .service_order_item_id
                == item.id,
            ),
        )

        if existing:
            continue

        config = (
            _repair_configuration(
                item,
            )
        )

        for _ in range(
            item.quantity,
        ):
            work_order = work_orders[
                min(
                    unit_offset // 10,
                    len(work_orders) - 1,
                )
            ]

            unit = ServiceUnit(
                service_order_id=order.id,
                work_order_id=work_order.id,
                origin_service_order_item_id=(
                    item.id
                ),
                initial_category="repair",
                evolution_enabled=False,
                name=item.service_name,
                identification_status=(
                    "pending"
                ),
                status="active",
            )

            db.add(unit)
            db.flush()

            stage = ServiceStage(
                service_unit_id=unit.id,
                sequence=1,
                category="repair",
                status="authorized",
                origin=(
                    "approved_quotation"
                ),
                quotation_item_id=(
                    item.quotation_item_id
                ),
            )

            db.add(stage)
            db.flush()

            execution = RepairExecution(
                service_order_id=order.id,
                service_order_item_id=(
                    item.id
                ),
                service_unit_id=unit.id,
                service_stage_id=stage.id,
                origin=origin,
                source_maintenance_change_request_id=(
                    linked_change.id
                    if linked_change
                    is not None
                    else None
                ),
                configuration_snapshot=(
                    config
                ),
                status="pending_arrival",
                sla_due_at=(
                    _now()
                    + timedelta(
                        days=REPAIR_SLA_DAYS,
                    )
                ),
            )

            db.add(execution)
            db.flush()

            unit_offset += 1

    write_audit_log(
        db,
        action="repair.initialized",
        entity="service_orders",
        entity_id=order.id,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# BLOCKERS / NOTICES / BOARD
# ---------------------------------------------------------------------------


def _blocker(
    execution: RepairExecution,
    message: str,
    section: str,
    field: str,
    *,
    severity: str = "blocker",
) -> dict:
    return {
        "execution_id":
            execution.id,
        "severity":
            severity,
        "message":
            message,
        "section":
            section,
        "field":
            field,
    }


def _current_blockers(
    execution: RepairExecution,
) -> list[dict]:
    blockers: list[dict] = []

    if (
        execution.status
        == "pending_assignment"
        and execution.technician_id
        is None
    ):
        blockers.append(
            _blocker(
                execution,
                (
                    "Requiere asignar "
                    "técnico responsable"
                ),
                "assignment",
                "technician_id",
            ),
        )

    if (
        execution.status
        == "in_repair"
        and not execution.interventions
    ):
        blockers.append(
            _blocker(
                execution,
                (
                    "Requiere al menos "
                    "una intervención "
                    "registrada"
                ),
                "interventions",
                "interventions",
            ),
        )

    if (
        execution.status
        == "testing"
        and not execution.tests
    ):
        blockers.append(
            _blocker(
                execution,
                (
                    "Requiere al menos "
                    "una prueba registrada"
                ),
                "tests",
                "tests",
            ),
        )

    for pause in execution.pauses:
        if pause.status == "active":
            blockers.append(
                _blocker(
                    execution,
                    (
                        "Ejecución pausada "
                        f"({pause.pause_type}): "
                        f"{pause.reason}"
                    ),
                    "pauses",
                    "status",
                    severity="pause",
                ),
            )

    return blockers


def _closure_blockers(
    execution: RepairExecution,
) -> list[dict]:
    blockers: list[dict] = []

    if (
        execution.status
        != "pending_release"
    ):
        blockers.append(
            _blocker(
                execution,
                (
                    "Debe completarse el "
                    "ciclo técnico y la firma "
                    "antes de cerrar"
                ),
                "status",
                "status",
            ),
        )

    for pause in execution.pauses:
        if pause.status == "active":
            blockers.append(
                _blocker(
                    execution,
                    (
                        "Existen pausas activas "
                        "sin resolver"
                    ),
                    "pauses",
                    "status",
                ),
            )
            break

    for change in execution.changes:
        if change.status == "requested":
            blockers.append(
                _blocker(
                    execution,
                    (
                        "Existen solicitudes "
                        "de cambio pendientes "
                        "de resolución"
                    ),
                    "changes",
                    "status",
                ),
            )
            break

    return blockers


def _notices(
    execution: RepairExecution,
) -> list[dict]:
    notices: list[dict] = []

    sla_due_at = _as_utc(
        execution.sla_due_at,
    )

    if (
        sla_due_at is not None
        and execution.status
        not in {
            "closed",
            "cancelled",
        }
        and _now() > sla_due_at
    ):
        notices.append(
            {
                "execution_id":
                    execution.id,
                "severity":
                    "notice",
                "message": (
                    "SLA de reparación "
                    f"(~{REPAIR_SLA_DAYS} días) "
                    "excedido"
                ),
                "section":
                    "sla",
                "field":
                    "sla_due_at",
            },
        )

    if (
        execution.warranty_reopened_count
        > 0
    ):
        notices.append(
            {
                "execution_id":
                    execution.id,
                "severity":
                    "notice",
                "message": (
                    "Ejecución reabierta "
                    "por garantía "
                    f"({execution.warranty_reopened_count}x)"
                ),
                "section":
                    "warranty",
                "field":
                    "warranty_reopened_count",
            },
        )

    return notices


def repair_board(
    db: Session,
    service_order_id: int,
) -> dict:
    order = db.get(
        ServiceOrder,
        service_order_id,
    )

    if (
        order is None
        or not order.is_active
    ):
        raise HTTPException(
            status_code=404,
            detail="ETS no encontrado",
        )

    executions = list(
        db.scalars(
            _query(
                service_order_id,
            ),
        ).all(),
    )

    if not executions:
        raise HTTPException(
            status_code=404,
            detail=(
                "El ETS no contiene "
                "Reparación"
            ),
        )

    all_current_blockers: list[dict] = []
    all_closure_blockers: list[dict] = []
    rendered: list[dict] = []

    for execution in executions:
        current_blockers = (
            _current_blockers(
                execution,
            )
        )

        closure_blockers = (
            []
            if execution.status == "closed"
            else _closure_blockers(
                execution,
            )
        )

        all_current_blockers.extend(
            current_blockers,
        )

        all_closure_blockers.extend(
            closure_blockers,
        )

        rendered.append(
            {
                **execution.__dict__,
                "equipment_id":
                    execution
                    .service_unit
                    .equipment_id,
                "equipment_name":
                    execution
                    .service_unit
                    .name,
                "work_order_number":
                    execution
                    .service_unit
                    .work_order
                    .work_order_number,
                "blockers":
                    current_blockers,
                "closure_blockers":
                    closure_blockers,
                "notices":
                    _notices(
                        execution,
                    ),
            },
        )

    return {
        "service_order_id":
            service_order_id,
        "executions":
            rendered,
        "blockers":
            all_current_blockers,
        "closure_blockers":
            all_closure_blockers,
        "can_close":
            not all_closure_blockers,
    }


# ---------------------------------------------------------------------------
# ARRIVAL / ASSIGNMENT / EVALUATION
# ---------------------------------------------------------------------------


def register_arrival(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: RepairEquipmentCreate,
    *,
    actor: User,
) -> dict:
    _require(
        actor,
        "service_orders.repair.manage",
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
        execution.status
        != "pending_arrival"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "El equipo ya fue "
                "registrado como recibido"
            ),
        )

    unit = execution.service_unit

    if (
        payload.equipment_id
        is not None
    ):
        unit.equipment_id = (
            payload.equipment_id
        )

    if payload.name:
        unit.name = payload.name

    unit.brand = payload.brand
    unit.model = payload.model
    unit.serial_number = (
        payload.serial_number
    )

    unit.identification_status = (
        "identified"
        if (
            payload.equipment_id
            or payload.serial_number
        )
        else "partial"
    )

    execution.status = (
        "pending_assignment"
    )

    write_audit_log(
        db,
        action=(
            "repair.arrival_registered"
        ),
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values=(
            payload.model_dump()
        ),
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


def assign_technician(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: RepairAssign,
    *,
    actor: User,
) -> dict:
    _require(
        actor,
        "service_orders.repair.manage",
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
        execution.status
        != "pending_assignment"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "La ejecución no está "
                "pendiente de asignación"
            ),
        )

    execution.technician_id = (
        payload.technician_id
    )

    execution.status = "assigned"

    write_audit_log(
        db,
        action=(
            "repair.technician_assigned"
        ),
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "technician_id":
                payload.technician_id,
        },
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


def start_evaluation(
    db: Session,
    service_order_id: int,
    execution_id: int,
    *,
    actor: User,
) -> dict:
    _require(
        actor,
        "service_orders.repair.execute",
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
                "La ejecución no está "
                "lista para iniciar "
                "evaluación"
            ),
        )

    execution.status = "in_evaluation"

    write_audit_log(
        db,
        action=(
            "repair.evaluation_started"
        ),
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


def save_diagnosis(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: RepairDiagnosis,
    *,
    actor: User,
) -> dict:
    """El diagnóstico es opcional y no bloquea el avance."""

    _require(
        actor,
        "service_orders.repair.execute",
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
        execution.status
        != "in_evaluation"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "El diagnóstico solo puede "
                "registrarse durante "
                "la evaluación"
            ),
        )

    execution.diagnosis_notes = (
        payload.diagnosis_notes
    )

    execution.diagnosis_completed_at = (
        _now()
    )

    write_audit_log(
        db,
        action="repair.diagnosis_saved",
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values=(
            payload.model_dump()
        ),
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


def conclude_evaluation(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: RepairConclude,
    *,
    actor: User,
) -> dict:
    """equipment_not_suitable salta reparación/pruebas."""

    _require(
        actor,
        "service_orders.repair.execute",
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
        execution.status
        != "in_evaluation"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "La conclusión solo puede "
                "registrarse durante "
                "la evaluación"
            ),
        )

    execution.conclusion = (
        payload.conclusion
    )

    execution.conclusion_reason = (
        payload.conclusion_reason
    )

    if (
        payload.conclusion
        == "equipment_not_suitable"
    ):
        execution.status = (
            "equipment_not_suitable"
        )

        execution.technical_completed_at = (
            _now()
        )
    else:
        execution.status = "in_repair"

    write_audit_log(
        db,
        action=(
            "repair.evaluation_concluded"
        ),
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values=(
            payload.model_dump()
        ),
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


# ---------------------------------------------------------------------------
# INTERVENCIONES / PRUEBAS
# ---------------------------------------------------------------------------


def add_intervention(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: RepairInterventionCreate,
    *,
    actor: User,
) -> dict:
    _require(
        actor,
        "service_orders.repair.execute",
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

    if execution.status != "in_repair":
        raise HTTPException(
            status_code=409,
            detail=(
                "Solo pueden registrarse "
                "intervenciones mientras "
                "la ejecución está "
                "en reparación"
            ),
        )

    sequence = (
        len(
            execution.interventions,
        )
        + 1
    )

    intervention = RepairIntervention(
        repair_execution_id=execution.id,
        sequence=sequence,
        technician_id=(
            execution.technician_id
            or actor.id
        ),
        description=payload.description,
        actions=payload.actions,
        removed_components=[
            {
                **component,
                "disposition":
                    component.get(
                        "disposition",
                        "return_to_client",
                    ),
            }
            for component
            in payload.removed_components
        ],
        outcome=payload.outcome,
        started_at=_now(),
        completed_at=_now(),
    )

    db.add(intervention)

    write_audit_log(
        db,
        action=(
            "repair.intervention_added"
        ),
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values=(
            payload.model_dump()
        ),
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


def add_test(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: RepairTestCreate,
    *,
    actor: User,
) -> dict:
    """Ciclo intervención <-> prueba.

    Una prueba fallida regresa a in_repair.
    """

    _require(
        actor,
        "service_orders.repair.execute",
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

    if execution.status not in {
        "in_repair",
        "testing",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "Solo pueden registrarse "
                "pruebas en reparación "
                "o pruebas"
            ),
        )

    if (
        payload.intervention_id
        is not None
        and not any(
            intervention.id
            == payload.intervention_id
            for intervention
            in execution.interventions
        )
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "intervention_id no pertenece "
                "a esta ejecución"
            ),
        )

    sequence = (
        len(
            execution.tests,
        )
        + 1
    )

    test = RepairTest(
        repair_execution_id=execution.id,
        intervention_id=(
            payload.intervention_id
        ),
        sequence=sequence,
        test_type=payload.test_type,
        result=payload.result,
        notes=payload.notes,
        performed_by_id=actor.id,
        performed_at=_now(),
    )

    db.add(test)

    execution.status = (
        "in_repair"
        if payload.result == "fail"
        else "testing"
    )

    write_audit_log(
        db,
        action="repair.test_added",
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values=(
            payload.model_dump()
        ),
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


def complete_technical(
    db: Session,
    service_order_id: int,
    execution_id: int,
    *,
    actor: User,
) -> dict:
    _require(
        actor,
        "service_orders.repair.execute",
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

    if execution.status != "testing":
        raise HTTPException(
            status_code=409,
            detail=(
                "Solo puede completarse "
                "técnicamente desde "
                "la fase de pruebas"
            ),
        )

    if (
        not execution.tests
        or execution.tests[-1].result
        != "pass"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "La última prueba registrada "
                "debe tener resultado 'pass'"
            ),
        )

    execution.conclusion = (
        execution.conclusion
        or "repaired"
    )

    execution.technical_completed_at = (
        _now()
    )

    execution.status = (
        "technically_completed"
    )

    write_audit_log(
        db,
        action="repair.technical_completed",
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


# ---------------------------------------------------------------------------
# PAUSAS
# ---------------------------------------------------------------------------


def add_pause(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: RepairPauseCreate,
    *,
    actor: User,
) -> dict:
    _require(
        actor,
        "service_orders.repair.execute",
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

    db.add(
        RepairPause(
            repair_execution_id=(
                execution.id
            ),
            pause_type=(
                payload.pause_type
            ),
            reason=payload.reason,
            responsible_user_id=(
                payload.responsible_user_id
            ),
            tentative_resume_at=(
                payload
                .tentative_resume_at
            ),
        ),
    )

    write_audit_log(
        db,
        action="repair.pause_added",
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values=(
            payload.model_dump(
                mode="json",
            )
        ),
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


def resolve_pause(
    db: Session,
    service_order_id: int,
    execution_id: int,
    pause_id: int,
    payload: RepairPauseResolve,
    *,
    actor: User,
) -> dict:
    _require(
        actor,
        "service_orders.repair.execute",
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
            for item
            in execution.pauses
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
            detail=(
                "Pausa activa "
                "no encontrada"
            ),
        )

    pause.status = "resolved"
    pause.resolution = (
        payload.resolution
    )
    pause.resolved_by_id = actor.id
    pause.resolved_at = _now()

    write_audit_log(
        db,
        action="repair.pause_resolved",
        entity="repair_pauses",
        entity_id=pause.id,
        user_id=actor.id,
        new_values=(
            payload.model_dump()
        ),
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


# ---------------------------------------------------------------------------
# CAMBIOS DE ALCANCE / INVESTIGACIÓN
# ---------------------------------------------------------------------------


def request_change(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: RepairChangeCreate,
    *,
    actor: User,
) -> dict:
    _require(
        actor,
        "service_orders.repair.execute",
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

    db.add(
        RepairChangeRequest(
            repair_execution_id=(
                execution.id
            ),
            change_type=(
                payload.change_type
            ),
            summary=payload.summary,
        ),
    )

    write_audit_log(
        db,
        action=(
            "repair.change_requested"
        ),
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values=(
            payload.model_dump()
        ),
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


def resolve_change(
    db: Session,
    service_order_id: int,
    execution_id: int,
    change_id: int,
    payload: RepairChangeResolve,
    *,
    actor: User,
) -> dict:
    """Resuelve ampliaciones/investigaciones."""

    _require(
        actor,
        "service_orders.repair.authorize",
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
            for item
            in execution.changes
            if item.id == change_id
        ),
        None,
    )

    if (
        change is None
        or change.status
        != "requested"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Solicitud pendiente "
                "no encontrada"
            ),
        )

    if (
        change.change_type
        == "investigation"
        and payload.decision
        == "linked"
        and payload.linked_service_order_id
        is None
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "La vinculación de "
                "investigación requiere "
                "ETS destino"
            ),
        )

    if (
        payload.decision == "linked"
        and payload.linked_service_order_id
        is not None
    ):
        target = db.get(
            ServiceOrder,
            payload.linked_service_order_id,
        )

        source_order = db.get(
            ServiceOrder,
            execution.service_order_id,
        )

        if (
            target is None
            or not target.is_active
            or (
                target.client_id
                != source_order.client_id
            )
            or not any(
                item.is_active
                and item.operational_category
                == "general_service"
                for item in target.items
            )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "El ETS vinculado debe "
                    "pertenecer al mismo cliente "
                    "y contener servicios "
                    "generales"
                ),
            )

    change.status = payload.decision

    change.quotation_item_id = (
        payload.quotation_item_id
    )

    change.linked_service_order_id = (
        payload.linked_service_order_id
    )

    change.decision_reason = (
        payload.reason
    )

    change.decided_by_id = actor.id
    change.decided_at = _now()

    if (
        change.change_type
        == "investigation"
        and payload.decision
        == "linked"
    ):
        next_sequence = (
            db.scalar(
                select(
                    ServiceStage.sequence,
                )
                .where(
                    ServiceStage
                    .service_unit_id
                    == execution
                    .service_unit_id,
                )
                .order_by(
                    ServiceStage
                    .sequence
                    .desc(),
                )
                .limit(1),
            )
            or 0
        ) + 1

        investigation = ServiceStage(
            service_unit_id=(
                execution
                .service_unit_id
            ),
            sequence=next_sequence,
            category="diagnosis",
            status="authorized",
            origin=(
                "repair_investigation"
            ),
            source_stage_id=(
                execution
                .service_stage_id
            ),
        )

        db.add(investigation)
        db.flush()

        existing_investigation_pause = next(
            (
                item
                for item
                in execution.pauses
                if (
                    item.status == "active"
                    and item.pause_type
                    == (
                        "administrative_"
                        "investigation"
                    )
                )
            ),
            None,
        )

        if (
            existing_investigation_pause
            is None
        ):
            db.add(
                RepairPause(
                    repair_execution_id=(
                        execution.id
                    ),
                    pause_type=(
                        "administrative_"
                        "investigation"
                    ),
                    reason=(
                        "Investigación "
                        "administrativa abierta: "
                        "equipo en peor condición "
                        "que la recibida"
                    ),
                    responsible_user_id=(
                        actor.id
                    ),
                ),
            )

    write_audit_log(
        db,
        action=(
            "repair.change_resolved"
        ),
        entity=(
            "repair_change_requests"
        ),
        entity_id=change.id,
        user_id=actor.id,
        new_values=(
            payload.model_dump()
        ),
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


# ---------------------------------------------------------------------------
# REPORTES / FIRMA / CIERRE
# ---------------------------------------------------------------------------


def _report_html(
    execution: RepairExecution,
) -> str:
    unit = execution.service_unit

    interventions_rows = "".join(
        (
            "<tr>"
            f"<td>{intervention.sequence}</td>"
            f"<td>{escape(intervention.description)}</td>"
            f"<td>{escape(intervention.outcome or '')}</td>"
            "</tr>"
        )
        for intervention
        in execution.interventions
    )

    tests_rows = "".join(
        (
            "<tr>"
            f"<td>{test.sequence}</td>"
            f"<td>{escape(test.test_type)}</td>"
            f"<td>{escape(test.result)}</td>"
            "</tr>"
        )
        for test
        in execution.tests
    )

    return f"""
    <html>
      <body>
        <h1>Reporte técnico de Reparación</h1>

        <p>
          Equipo: {escape(unit.name or '')}
        </p>

        <p>
          Estado: {escape(execution.status)}
        </p>

        <p>
          Conclusión:
          {escape(execution.conclusion or '')}
        </p>

        <p>
          Razón de conclusión:
          {escape(execution.conclusion_reason or '')}
        </p>

        <h2>Intervenciones</h2>

        <table border="1">
          <tr>
            <th>#</th>
            <th>Descripción</th>
            <th>Resultado</th>
          </tr>
          {interventions_rows}
        </table>

        <h2>Pruebas</h2>

        <table border="1">
          <tr>
            <th>#</th>
            <th>Tipo</th>
            <th>Resultado</th>
          </tr>
          {tests_rows}
        </table>
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
        "service_orders.repair.manage",
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

    if execution.status not in {
        "technically_completed",
        "equipment_not_suitable",
        "pending_release",
        "closed",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "La ejecución aún no tiene "
                "conclusión técnica"
            ),
        )

    execution.report_version += 1
    execution.report_status = "generated"
    execution.report_generated_at = (
        _now()
    )

    write_audit_log(
        db,
        action=(
            "repair.report_generated"
        ),
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
    )

    db.commit()

    content = HTML(
        string=_report_html(
            execution,
        ),
    ).write_pdf()

    filename = (
        f"reparacion-{execution.id}"
        f"-v{execution.report_version}.pdf"
    )

    return content, filename


def sign_report(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: RepairSignature,
    *,
    actor: User,
) -> dict:
    _require(
        actor,
        "service_orders.repair.sign",
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

    if execution.status not in {
        "technically_completed",
        "equipment_not_suitable",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "Solo puede firmarse tras "
                "la conclusión técnica"
            ),
        )

    execution.signer_name = (
        payload.signer_name
    )

    execution.signature_data_url = (
        payload.signature_data_url
    )

    execution.client_decision = (
        payload.client_decision
    )

    execution.signed_at = _now()

    execution.signed_report_version = (
        execution.report_version
        or 1
    )

    execution.status = (
        "pending_release"
    )

    write_audit_log(
        db,
        action="repair.report_signed",
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "client_decision":
                payload.client_decision,
        },
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


def close_execution(
    db: Session,
    service_order_id: int,
    execution_id: int,
    *,
    actor: User,
) -> dict:
    _require(
        actor,
        "service_orders.repair.close",
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

    closure_blockers = (
        _closure_blockers(
            execution,
        )
    )

    if closure_blockers:
        raise HTTPException(
            status_code=409,
            detail=(
                "La ejecución tiene "
                "bloqueantes de cierre "
                "pendientes"
            ),
        )

    execution.status = "closed"
    execution.closed_at = _now()

    # El cierre histórico original
    # nunca se sobrescribe.
    if (
        execution.original_closed_at
        is None
    ):
        execution.original_closed_at = (
            execution.closed_at
        )

    write_audit_log(
        db,
        action="repair.closed",
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


def cancel_execution(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: RepairCancel,
    *,
    actor: User,
) -> dict:
    """Cancelación actual de Fase 1.

    Nota:
    La política definitiva después de primera intervención
    queda pendiente de revisión funcional.
    """

    _require(
        actor,
        "service_orders.repair.manage",
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

    if execution.status in {
        "closed",
        "cancelled",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "La ejecución ya está "
                "finalizada"
            ),
        )

    execution.cancelled_after_intervention = (
        bool(
            execution.interventions,
        )
    )

    execution.cancellation_reason = (
        payload.reason
    )

    execution.cancelled_at = _now()
    execution.status = "cancelled"

    write_audit_log(
        db,
        action="repair.cancelled",
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "reason":
                payload.reason,
            "cancelled_after_intervention":
                execution
                .cancelled_after_intervention,
        },
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )


def reopen_for_warranty(
    db: Session,
    service_order_id: int,
    execution_id: int,
    payload: RepairWarrantyReopen,
    *,
    actor: User,
) -> dict:
    """Preparación para garantía.

    No implementa todavía un ciclo histórico completo.
    """

    _require(
        actor,
        "service_orders.repair.authorize",
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

    if execution.status != "closed":
        raise HTTPException(
            status_code=409,
            detail=(
                "Solo puede reabrirse "
                "una ejecución cerrada"
            ),
        )

    execution.warranty_reopened_count += 1

    execution.status = (
        "pending_assignment"
    )

    execution.closed_at = None
    execution.conclusion = None
    execution.conclusion_reason = None
    execution.technical_completed_at = None

    write_audit_log(
        db,
        action=(
            "repair.warranty_reopened"
        ),
        entity="repair_executions",
        entity_id=execution.id,
        user_id=actor.id,
        new_values={
            "reason":
                payload.reason,
            "cycle":
                execution
                .warranty_reopened_count,
        },
    )

    db.commit()

    return repair_board(
        db,
        service_order_id,
    )