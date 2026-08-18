from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from weasyprint import HTML

from app.models.equipment import Equipment
from app.models.client_portal_membership import ClientPortalMembership
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


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require(actor: User, permission: str) -> None:
    if not user_has_permission(actor, permission):
        raise HTTPException(status_code=403, detail="No tienes permiso para esta operación de Mantenimiento")


def _active_order(db: Session, service_order_id: int) -> ServiceOrder:
    order = db.get(ServiceOrder, service_order_id)
    if order is None or not order.is_active:
        raise HTTPException(status_code=404, detail="ETS no encontrado")
    if order.status in {"closed", "cancelled"}:
        raise HTTPException(status_code=409, detail="El ETS no admite cambios operativos")
    return order


def _query(service_order_id: int):
    return (
        select(MaintenanceExecution)
        .where(MaintenanceExecution.service_order_id == service_order_id)
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


def _execution(db: Session, service_order_id: int, execution_id: int) -> MaintenanceExecution:
    execution = db.scalar(_query(service_order_id).where(MaintenanceExecution.id == execution_id))
    if execution is None:
        raise HTTPException(status_code=404, detail="Ejecución de Mantenimiento no encontrada")
    return execution


def _maintenance_configuration(item: ServiceOrderItem) -> dict:
    snapshot = item.service_snapshot or {}
    config = snapshot.get("maintenance_configuration_snapshot") or {}
    return {
        "maintenance_type": config.get("maintenance_type") or snapshot.get("calibration_scope_snapshot") or "preventive",
        "location_mode": config.get("location_mode") or "laboratory",
        "base_materials": list(config.get("base_materials") or []),
        "source": "quotation_snapshot" if config else "legacy_structured_default",
    }


def initialize_maintenance_execution(db: Session, order: ServiceOrder, *, user_id: int) -> None:
    items = [item for item in order.items if item.is_active and item.operational_category == "maintenance"]
    if not items:
        return
    work_orders = sorted((work_order for work_order in order.work_orders if work_order.is_active), key=lambda value: value.sequence)
    unit_offset = 0
    for item in items:
        if db.scalar(select(MaintenanceExecution.id).where(MaintenanceExecution.service_order_item_id == item.id)):
            continue
        config = _maintenance_configuration(item)
        for _ in range(item.quantity):
            work_order = work_orders[min(unit_offset // 10, len(work_orders) - 1)]
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
                location_mode=config["location_mode"],
                configuration_snapshot=config,
                status="pending_arrival" if config["location_mode"] == "laboratory" else "pending_assignment",
            )
            db.add(execution)
            db.flush()
            for material in config["base_materials"]:
                if not material.get("name"):
                    continue
                db.add(MaintenanceMaterial(
                    maintenance_execution_id=execution.id,
                    material_type="required",
                    name=str(material["name"])[:180],
                    quantity=material.get("quantity") or 1,
                    unit=str(material.get("unit") or "pieza")[:40],
                    component=material.get("component"),
                    notes=material.get("notes"),
                    internal_unit_cost=material.get("internal_unit_cost"),
                    decision="pending",
                    source="catalog_snapshot",
                ))
            unit_offset += 1
    write_audit_log(db, action="maintenance.initialized", entity="service_orders", entity_id=order.id, user_id=user_id)


def _blockers(execution: MaintenanceExecution) -> list[dict]:
    blockers: list[dict] = []

    def add(message: str, section: str, field: str, *, severity: str = "blocker"):
        blockers.append({
            "execution_id": execution.id,
            "severity": severity,
            "message": message,
            "section": section,
            "field": field,
        })

    if execution.service_unit.equipment_id is None:
        message = "Registra el arribo y vincula el equipo." if execution.location_mode == "laboratory" else "Da de alta o vincula el equipo que será atendido en campo."
        add(message, "arrival" if execution.location_mode == "laboratory" else "equipment", "equipment")
    if execution.technician_id is None:
        add("Asigna un técnico responsable.", "assignment", "technician_id")
    if execution.location_mode == "field" and execution.field_request_status != "accepted":
        add("El técnico debe aceptar y programar la visita de campo.", "assignment", "field_request_status")
    for pause in execution.pauses:
        if pause.status == "active":
            add(f"Resuelve la pausa: {pause.reason}", "pauses", f"pause-{pause.id}")
    if execution.initial_condition is None:
        add("Completa la condición inicial.", "before", "initial_condition")
    if not execution.initial_description:
        add("Describe brevemente cómo llegó el equipo.", "before", "initial_description")
    if not execution.before_photos:
        add("Adjunta al menos una evidencia fotográfica inicial.", "before", "before_photos")
    if execution.final_condition is None:
        add("Completa la condición final.", "after", "final_condition")
    if not execution.functional_result:
        add("Documenta el resultado funcional.", "after", "functional_result")
    if not execution.after_photos:
        add("Adjunta al menos una evidencia fotográfica final.", "after", "after_photos")
    unresolved_findings = [item for item in execution.findings or [] if not item.get("classification") or not item.get("resolution")]
    if unresolved_findings:
        add("Clasifica y resuelve todos los hallazgos.", "before", "findings")
    if any(change.status == "requested" and change.change_type == "corrective" for change in execution.changes):
        add("Existe una autorización comercial de correctivo pendiente.", "future", "changes")
    if execution.investigation_status in {"required", "open"}:
        add("El equipo inoperable requiere resolución de la investigación administrativa.", "investigation", "investigation_status")
    if execution.technical_completed_at is None:
        add("Marca el mantenimiento como técnicamente terminado.", "completion", "technical_completed_at")
    if execution.report_status != "generated":
        add("Genera el reporte de Mantenimiento.", "report", "report_status")
    if execution.signed_report_version != execution.report_version or execution.signed_at is None:
        add("Obtén la firma sobre la versión vigente del reporte.", "signature", "signature_data_url")
    return blockers


def maintenance_board(db: Session, service_order_id: int) -> dict:
    order = db.get(ServiceOrder, service_order_id)
    if order is None or not order.is_active:
        raise HTTPException(status_code=404, detail="ETS no encontrado")
    executions = list(db.scalars(_query(service_order_id)).all())
    if not executions:
        raise HTTPException(status_code=404, detail="El ETS no contiene Mantenimiento")
    all_blockers = []
    rendered = []
    for execution in executions:
        blockers = [] if execution.status == "closed" else _blockers(execution)
        notices = [
            {
                "execution_id": execution.id,
                "severity": "warning" if item.get("decision") == "pending" else "recommendation",
                "message": str(item.get("description") or item.get("recommendation") or "Recomendación documentada"),
                "section": "future",
                "field": "recommendations",
            }
            for item in execution.recommendations or []
            if item.get("decision") in {"pending", "rejected"}
        ]
        all_blockers.extend(blockers)
        rendered.append({
            **execution.__dict__,
            "equipment_id": execution.service_unit.equipment_id,
            "equipment_name": execution.service_unit.name,
            "work_order_number": execution.service_unit.work_order.work_order_number,
            "blockers": blockers,
            "notices": notices,
        })
    return {"service_order_id": service_order_id, "executions": rendered, "blockers": all_blockers, "can_close": not all_blockers}


def register_arrival(db: Session, service_order_id: int, execution_id: int, payload: MaintenanceEquipmentCreate, *, actor: User):
    _require(actor, "service_orders.maintenance.manage")
    _active_order(db, service_order_id)
    execution = _execution(db, service_order_id, execution_id)
    if execution.location_mode != "laboratory" or execution.status != "pending_arrival":
        raise HTTPException(status_code=409, detail="Sólo un mantenimiento de laboratorio pendiente admite arribo")
    unit = execution.service_unit
    if payload.equipment_id:
        equipment = db.get(Equipment, payload.equipment_id)
        if equipment is None or equipment.service_order_id != service_order_id or equipment.service_unit is not None:
            raise HTTPException(status_code=409, detail="El equipo no puede vincularse a esta unidad")
    else:
        equipment = Equipment(
            service_order_id=service_order_id,
            work_order_id=unit.work_order_id,
            service_order_item_id=execution.service_order_item_id,
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
    unit.name, unit.brand, unit.model, unit.serial_number = equipment.name, equipment.brand, equipment.model, equipment.serial_number
    unit.identification_status = "complete" if equipment.brand and equipment.model and equipment.serial_number else "partial"
    execution.status = "pending_assignment"
    write_audit_log(db, action="maintenance.arrival_registered", entity="maintenance_executions", entity_id=execution.id, user_id=actor.id, new_values={"equipment_id": equipment.id})
    db.commit()
    return maintenance_board(db, service_order_id)


def register_field_equipment(db: Session, service_order_id: int, execution_id: int, payload: MaintenanceEquipmentCreate, *, actor: User):
    _require(actor, "service_orders.maintenance.manage")
    _active_order(db, service_order_id)
    execution = _execution(db, service_order_id, execution_id)
    if execution.location_mode != "field" or execution.status != "pending_assignment" or execution.service_unit.equipment_id is not None:
        raise HTTPException(status_code=409, detail="La unidad de campo no admite este vínculo de equipo")
    unit = execution.service_unit
    if payload.equipment_id:
        equipment = db.get(Equipment, payload.equipment_id)
        if equipment is None or equipment.service_order_id != service_order_id or equipment.service_unit is not None:
            raise HTTPException(status_code=409, detail="El equipo no puede vincularse a esta unidad")
    else:
        equipment = Equipment(
            service_order_id=service_order_id,
            work_order_id=unit.work_order_id,
            service_order_item_id=execution.service_order_item_id,
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
    unit.name, unit.brand, unit.model, unit.serial_number = equipment.name, equipment.brand, equipment.model, equipment.serial_number
    unit.identification_status = "complete" if equipment.brand and equipment.model and equipment.serial_number else "partial"
    db.commit()
    return maintenance_board(db, service_order_id)


def prepare_execution(db: Session, service_order_id: int, execution_id: int, payload: MaintenancePrepare, *, actor: User):
    _require(actor, "service_orders.maintenance.manage")
    _active_order(db, service_order_id)
    execution = _execution(db, service_order_id, execution_id)
    if execution.status != "pending_assignment":
        raise HTTPException(status_code=409, detail="El mantenimiento no está pendiente de asignación")
    technician = db.get(User, payload.technician_id)
    if technician is None or not technician.is_active or not user_has_permission(technician, "service_orders.maintenance.execute"):
        raise HTTPException(status_code=422, detail="Selecciona un técnico activo con capacidad de ejecutar Mantenimiento")
    execution.technician_id = payload.technician_id
    if execution.location_mode == "field":
        if not payload.field_address:
            raise HTTPException(status_code=422, detail="La visita de campo requiere dirección")
        execution.field_address = payload.field_address
        execution.field_request_status = "requested"
        execution.status = "assigned"
    else:
        execution.status = "assigned"
    execution.scheduled_for = payload.scheduled_for
    db.commit()
    return maintenance_board(db, service_order_id)


def accept_field_visit(db: Session, service_order_id: int, execution_id: int, scheduled_for: datetime, *, actor: User):
    _require(actor, "service_orders.maintenance.execute")
    execution = _execution(db, service_order_id, execution_id)
    if execution.location_mode != "field" or execution.field_request_status != "requested" or execution.technician_id != actor.id:
        raise HTTPException(status_code=409, detail="La visita no está asignada a este técnico")
    execution.field_request_status = "accepted"
    execution.scheduled_for = scheduled_for
    db.commit()
    return maintenance_board(db, service_order_id)


def start_execution(db: Session, service_order_id: int, execution_id: int, *, actor: User):
    _require(actor, "service_orders.maintenance.execute")
    execution = _execution(db, service_order_id, execution_id)
    if execution.technician_id != actor.id or execution.status != "assigned":
        raise HTTPException(status_code=409, detail="El mantenimiento no está asignado a este técnico")
    if execution.location_mode == "field" and execution.field_request_status != "accepted":
        raise HTTPException(status_code=409, detail="La visita de campo debe aceptarse y programarse")
    execution.status = "in_maintenance"
    execution.service_stage.status = "in_progress"
    execution.service_stage.started_at = _now()
    db.commit()
    return maintenance_board(db, service_order_id)


def save_capture(db: Session, service_order_id: int, execution_id: int, payload: MaintenanceCapture, *, actor: User):
    _require(actor, "service_orders.maintenance.execute")
    execution = _execution(db, service_order_id, execution_id)
    if execution.technician_id != actor.id or execution.status not in {"in_maintenance", "paused"}:
        raise HTTPException(status_code=409, detail="La captura requiere una intervención activa asignada")
    for key, value in payload.model_dump().items():
        setattr(execution, key, value)
    if execution.final_condition == "not_operational":
        execution.investigation_status = "required"
        if not any(item.status == "active" and item.pause_type == "administrative_investigation" for item in execution.pauses):
            db.add(MaintenancePause(
                maintenance_execution_id=execution.id,
                pause_type="administrative_investigation",
                reason="Equipo inoperable después de la intervención; requiere investigación administrativa",
                responsible_user_id=actor.id,
            ))
        execution.status = "paused"
        execution.service_stage.status = "paused"
    execution.report_status = "pending"
    db.commit()
    return maintenance_board(db, service_order_id)


def add_pause(db: Session, service_order_id: int, execution_id: int, payload: MaintenancePauseCreate, *, actor: User):
    _require(actor, "service_orders.maintenance.execute")
    execution = _execution(db, service_order_id, execution_id)
    if execution.technician_id != actor.id and not user_has_permission(actor, "service_orders.maintenance.authorize"):
        raise HTTPException(status_code=403, detail="Sólo el técnico asignado o un autorizador puede pausar")
    responsible = db.get(User, payload.responsible_user_id)
    if responsible is None or not responsible.is_active:
        raise HTTPException(status_code=422, detail="El responsable de la pausa no existe o está inactivo")
    pause = MaintenancePause(maintenance_execution_id=execution.id, **payload.model_dump())
    db.add(pause)
    execution.status = "paused"
    execution.service_stage.status = "paused"
    db.commit()
    return maintenance_board(db, service_order_id)


def resolve_pause(db: Session, service_order_id: int, execution_id: int, pause_id: int, resolution: str, *, actor: User):
    _require(actor, "service_orders.maintenance.execute")
    execution = _execution(db, service_order_id, execution_id)
    pause = next((item for item in execution.pauses if item.id == pause_id), None)
    if pause is None or pause.status != "active":
        raise HTTPException(status_code=409, detail="Pausa activa no encontrada")
    pause.status, pause.resolution, pause.resolved_by_id, pause.resolved_at = "resolved", resolution, actor.id, _now()
    if not any(item.status == "active" for item in execution.pauses):
        execution.status = "in_maintenance"
        execution.service_stage.status = "in_progress"
    db.commit()
    return maintenance_board(db, service_order_id)


def add_material(db: Session, service_order_id: int, execution_id: int, payload: MaintenanceMaterialCreate, *, actor: User):
    _require(actor, "service_orders.maintenance.execute")
    execution = _execution(db, service_order_id, execution_id)
    if execution.technician_id != actor.id:
        raise HTTPException(status_code=403, detail="Sólo el técnico asignado documenta materiales")
    material = MaintenanceMaterial(maintenance_execution_id=execution.id, source="technician", **payload.model_dump())
    db.add(material)
    db.commit()
    return maintenance_board(db, service_order_id)


def request_change(db: Session, service_order_id: int, execution_id: int, payload: MaintenanceChangeCreate, *, actor: User):
    _require(actor, "service_orders.maintenance.execute")
    execution = _execution(db, service_order_id, execution_id)
    if execution.technician_id != actor.id:
        raise HTTPException(status_code=403, detail="Sólo el técnico asignado registra hallazgos derivados")
    if payload.change_type == "corrective" and execution.maintenance_type != "preventive":
        raise HTTPException(status_code=409, detail="Sólo un preventivo puede solicitar alcance correctivo")
    change = MaintenanceChangeRequest(maintenance_execution_id=execution.id, **payload.model_dump())
    db.add(change)
    if payload.change_type == "corrective":
        db.add(MaintenancePause(
            maintenance_execution_id=execution.id,
            pause_type="authorization",
            reason="Pendiente de autorización comercial para alcance correctivo",
            responsible_user_id=actor.id,
        ))
        execution.status = "paused"
        execution.service_stage.status = "paused"
    if payload.change_type == "investigation":
        execution.investigation_status = "required"
    db.commit()
    return maintenance_board(db, service_order_id)


def _approved_linked_item(db: Session, execution: MaintenanceExecution, quotation_item_id: int | None) -> bool:
    if quotation_item_id is None:
        return False
    item = db.get(QuotationItem, quotation_item_id)
    if item is None or item.operational_category != "maintenance":
        return False
    if item.source_service_order_id != execution.service_order_id or item.source_service_unit_id != execution.service_unit_id or item.source_stage_id != execution.service_stage_id:
        return False
    return db.scalar(select(QuotationItemDecision.id).where(
        QuotationItemDecision.quotation_item_id == item.id,
        QuotationItemDecision.decision == "approved",
    )) is not None


def resolve_change(db: Session, service_order_id: int, execution_id: int, change_id: int, payload: MaintenanceChangeResolve, *, actor: User):
    _require(actor, "service_orders.maintenance.authorize")
    execution = _execution(db, service_order_id, execution_id)
    change = next((item for item in execution.changes if item.id == change_id), None)
    if change is None or change.status != "requested":
        raise HTTPException(status_code=409, detail="Solicitud pendiente no encontrada")
    if payload.decision == "approved" and change.change_type == "corrective" and not _approved_linked_item(db, execution, payload.quotation_item_id):
        raise HTTPException(status_code=409, detail="El correctivo requiere partida aprobada vinculada a esta unidad y etapa")
    if payload.decision == "overridden" and len(payload.reason.strip()) < 10:
        raise HTTPException(status_code=422, detail="El override administrativo requiere justificación suficiente")
    if change.change_type in {"repair", "investigation"} and payload.decision == "linked" and payload.linked_service_order_id is None:
        raise HTTPException(status_code=422, detail="La vinculación requiere ETS destino")
    if payload.decision == "linked":
        target = db.get(ServiceOrder, payload.linked_service_order_id)
        source_order = db.get(ServiceOrder, execution.service_order_id)
        expected_category = "repair" if change.change_type == "repair" else "general_service"
        if (
            target is None
            or not target.is_active
            or target.client_id != source_order.client_id
            or not any(item.is_active and item.operational_category == expected_category for item in target.items)
        ):
            raise HTTPException(status_code=409, detail=f"El ETS vinculado debe pertenecer al mismo cliente y contener {expected_category}")
    change.status, change.quotation_item_id = payload.decision, payload.quotation_item_id
    change.linked_service_order_id, change.decision_reason = payload.linked_service_order_id, payload.reason
    change.decided_by_id, change.decided_at = actor.id, _now()
    if change.change_type == "corrective" and payload.decision in {"approved", "overridden"}:
        execution.maintenance_type = "corrective"
    if change.change_type == "investigation" and payload.decision == "linked":
        execution.investigation_status = "open"
        next_sequence = int(db.scalar(select(func.max(ServiceStage.sequence)).where(ServiceStage.service_unit_id == execution.service_unit_id)) or 0) + 1
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
        execution.linked_investigation_stage_id = investigation.id
    for pause in execution.pauses:
        if pause.status == "active" and pause.pause_type in {"authorization", "commercial_review"}:
            pause.status, pause.resolution, pause.resolved_by_id, pause.resolved_at = "resolved", payload.reason, actor.id, _now()
    if not any(item.status == "active" for item in execution.pauses):
        execution.status, execution.service_stage.status = "in_maintenance", "in_progress"
    write_audit_log(db, action="maintenance.change_resolved", entity="maintenance_change_requests", entity_id=change.id, user_id=actor.id, new_values=payload.model_dump())
    db.commit()
    return maintenance_board(db, service_order_id)


def resolve_investigation(db: Session, service_order_id: int, execution_id: int, reason: str, *, actor: User):
    _require(actor, "service_orders.maintenance.authorize")
    execution = _execution(db, service_order_id, execution_id)
    if execution.investigation_status not in {"required", "open"}:
        raise HTTPException(status_code=409, detail="No existe una investigación pendiente")
    execution.investigation_status = "resolved"
    if execution.linked_investigation_stage_id:
        stage = db.get(ServiceStage, execution.linked_investigation_stage_id)
        stage.status, stage.completed_at = "completed", _now()
        stage.result = {"administrative_resolution": reason}
    for pause in execution.pauses:
        if pause.status == "active" and pause.pause_type == "administrative_investigation":
            pause.status, pause.resolution, pause.resolved_by_id, pause.resolved_at = "resolved", reason, actor.id, _now()
    if execution.status == "paused" and not any(item.status == "active" for item in execution.pauses):
        execution.status, execution.service_stage.status = "in_maintenance", "in_progress"
    write_audit_log(db, action="maintenance.investigation_resolved", entity="maintenance_executions", entity_id=execution.id, user_id=actor.id, new_values={"reason": reason})
    db.commit()
    return maintenance_board(db, service_order_id)


def complete_technical(db: Session, service_order_id: int, execution_id: int, *, actor: User):
    _require(actor, "service_orders.maintenance.execute")
    execution = _execution(db, service_order_id, execution_id)
    if execution.technician_id != actor.id or execution.status != "in_maintenance":
        raise HTTPException(status_code=409, detail="El mantenimiento no está activo para este técnico")
    blockers = [item for item in _blockers(execution) if item["section"] not in {"completion", "report", "signature"}]
    if blockers:
        raise HTTPException(status_code=409, detail={"message": "Captura técnica incompleta", "blockers": blockers})
    execution.status = "technically_completed"
    execution.technical_completed_at = _now()
    execution.service_stage.status = "completed"
    execution.service_stage.completed_at = execution.technical_completed_at
    execution.service_stage.result = {
        "maintenance_type": execution.maintenance_type,
        "initial_condition": execution.initial_condition,
        "final_condition": execution.final_condition,
    }
    db.commit()
    return maintenance_board(db, service_order_id)


def _report_html(order: ServiceOrder, execution: MaintenanceExecution) -> str:
    equipment = execution.service_unit.equipment
    equipment_name = equipment.name if equipment else execution.service_unit.name
    materials = "".join(
        f"<li>{escape(str(item.name))}: {escape(str(item.quantity))} {escape(item.unit)} ({'utilizado' if item.material_type == 'used' else 'recomendado'})</li>"
        for item in execution.materials
    ) or "<li>Sin materiales documentados</li>"
    findings = "".join(f"<li>{escape(str(item.get('component', 'General')))}: {escape(str(item.get('description', '')))}</li>" for item in execution.findings) or "<li>Sin hallazgos relevantes</li>"
    actions = "".join(f"<li>{escape(str(item.get('action', 'Acción')))} — {escape(str(item.get('component', 'General')))}</li>" for item in execution.actions) or "<li>Sin acciones registradas</li>"
    recommendations = "".join(f"<li>{escape(str(item.get('description', item.get('recommendation', ''))))} — {escape(str(item.get('decision', 'pending')))}</li>" for item in execution.recommendations) or "<li>Sin recomendaciones</li>"
    def photos(refs: list, label: str) -> str:
        rendered = []
        for reference in refs:
            path = resolve_storage_path(reference)
            caption = escape(str(reference))
            if path is not None and path.is_file() and not path.is_symlink() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                rendered.append(f"<figure><img src='{escape(path.as_uri(), quote=True)}' style='max-width:240px;max-height:180px'><figcaption>{caption}</figcaption></figure>")
            else:
                rendered.append(f"<p>Evidencia fotográfica: {caption}</p>")
        return f"<h4>{escape(label)}</h4>{''.join(rendered)}"
    return f"""<html><body style='font-family:sans-serif'>
    <h1>Reporte de Mantenimiento</h1><p><b>ETS:</b> {escape(order.folio)} · <b>OT:</b> {execution.service_unit.work_order.work_order_number}</p>
    <h2>{escape(equipment_name)}</h2><p><b>Tipo:</b> {escape(execution.maintenance_type)} · <b>Modalidad:</b> {escape(execution.location_mode)}</p>
    <h3>Cómo llegó</h3><p>{escape(execution.initial_condition or '')}: {escape(execution.initial_description or '')}</p>{photos(execution.before_photos, 'Fotografías iniciales')}
    <h3>Qué encontramos</h3><ul>{findings}</ul><h3>Qué hicimos</h3><ul>{actions}</ul>
    <h3>Materiales</h3><ul>{materials}</ul><h3>Cómo quedó</h3><p>{escape(execution.final_condition or '')}: {escape(execution.functional_result or '')}</p>{photos(execution.after_photos, 'Fotografías finales')}
    <h3>Qué recomendamos</h3><ul>{recommendations}</ul><p><b>Conclusión:</b> {escape(execution.technical_conclusion or '')}</p>
    <p><b>Técnico:</b> {escape(execution.technician.full_name if execution.technician else 'Pendiente')} · <b>Fecha:</b> {escape(str(execution.technical_completed_at or ''))}</p>
    <p><b>Firmante:</b> {escape(execution.signer_name or 'Pendiente')} · <b>Decisión:</b> {escape(execution.client_decision or 'Pendiente')}</p>
    </body></html>"""


def generate_report(db: Session, service_order_id: int, execution_id: int, *, actor: User) -> tuple[bytes, str]:
    _require(actor, "service_orders.maintenance.manage")
    order = _active_order(db, service_order_id)
    execution = _execution(db, service_order_id, execution_id)
    if execution.technical_completed_at is None:
        raise HTTPException(status_code=409, detail="El mantenimiento aún no está técnicamente terminado")
    if execution.report_status != "generated":
        execution.report_version += 1
    execution.report_status = "generated"
    execution.report_generated_at = _now()
    execution.status = "pending_release"
    html = _report_html(order, execution)
    write_audit_log(db, action="maintenance.report_generated", entity="maintenance_executions", entity_id=execution.id, user_id=actor.id, new_values={"report_version": execution.report_version})
    db.commit()
    return HTML(string=html).write_pdf(), f"{order.folio}-MANTENIMIENTO-{execution.id}-V{execution.report_version}.pdf"


def sign_report(db: Session, service_order_id: int, execution_id: int, payload: MaintenanceSignature, *, actor: User):
    _require(actor, "service_orders.maintenance.sign")
    execution = _execution(db, service_order_id, execution_id)
    if not (
        user_has_permission(actor, "service_orders.maintenance.manage")
        or user_has_permission(actor, "service_orders.maintenance.execute")
    ):
        source_order = db.get(ServiceOrder, execution.service_order_id)
        membership = db.scalar(select(ClientPortalMembership.id).where(
            ClientPortalMembership.user_id == actor.id,
            ClientPortalMembership.client_id == source_order.client_id,
            ClientPortalMembership.status == "active",
        ))
        if membership is None:
            raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")
    if execution.report_status != "generated" or execution.report_version < 1:
        raise HTTPException(status_code=409, detail="Primero genera el reporte que será firmado")
    execution.signer_name = payload.signer_name
    execution.signature_data_url = payload.signature_data_url
    execution.client_decision = payload.client_decision
    execution.signed_report_version = execution.report_version
    execution.signed_at = _now()
    db.commit()
    return maintenance_board(db, service_order_id)


def close_execution(db: Session, service_order_id: int, execution_id: int, *, actor: User):
    _require(actor, "service_orders.maintenance.close")
    execution = _execution(db, service_order_id, execution_id)
    blockers = _blockers(execution)
    if blockers:
        raise HTTPException(status_code=409, detail={"message": "Mantenimiento con bloqueantes", "blockers": blockers})
    execution.status = "closed"
    execution.closed_at = _now()
    execution.service_unit.status = "completed"
    db.commit()
    return maintenance_board(db, service_order_id)
