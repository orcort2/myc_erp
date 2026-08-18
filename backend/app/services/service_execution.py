from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.activity import ActivityMessage
from app.models.catalog_item import CatalogItem
from app.models.equipment import Equipment
from app.models.quotation import QuotationItem, QuotationItemDecision
from app.models.quotation import Quotation
from app.models.service_execution import (
    ServiceStage,
    ServiceTask,
    ServiceTaskAssignee,
    ServiceUnit,
    TechnicalServiceRequest,
)
from app.models.service_order import ServiceOrder, ServiceOrderItem, ServiceWorkOrder
from app.schemas.service_execution import (
    QuotationItemDecisionCreate,
    ServiceStageCreate,
    ServiceStageUpdate,
    ServiceUnitBatchCreate,
    TechnicalServiceRequestCreate,
)
from app.services.activity import publish_event
from app.services.audit_logs import write_audit_log
from app.schemas.operational_category import operational_category_from_structured_fields


def _active_service_order(db: Session, service_order_id: int) -> ServiceOrder:
    service_order = db.scalar(
        select(ServiceOrder).where(
            ServiceOrder.id == service_order_id,
            ServiceOrder.is_active.is_(True),
        )
    )
    if service_order is None:
        raise HTTPException(status_code=404, detail="ETS no encontrado")
    if service_order.status in {"closed", "cancelled"}:
        raise HTTPException(status_code=409, detail="El ETS no admite cambios operativos")
    return service_order


def _work_order(db: Session, service_order_id: int, work_order_id: int | None) -> ServiceWorkOrder:
    query = select(ServiceWorkOrder).where(
        ServiceWorkOrder.service_order_id == service_order_id,
        ServiceWorkOrder.is_active.is_(True),
    )
    if work_order_id is not None:
        query = query.where(ServiceWorkOrder.id == work_order_id)
    else:
        query = query.order_by(ServiceWorkOrder.sequence.asc())
    result = db.scalar(query)
    if result is None:
        raise HTTPException(status_code=404, detail="OT activa no encontrada dentro del ETS")
    return result


def _catalog_category(catalog_item: CatalogItem | None) -> str | None:
    if catalog_item is None:
        return None
    return catalog_item.operational_category or operational_category_from_structured_fields(
        item_type=catalog_item.item_type,
        category=catalog_item.category,
        commodity=catalog_item.commodity,
    )


def _service_order_item_category(
    origin: ServiceOrderItem | None,
    catalog_item: CatalogItem | None,
) -> str | None:
    if origin is None:
        return None
    snapshot = origin.service_snapshot or {}
    return (
        origin.operational_category
        or snapshot.get("operational_category_snapshot")
        or _catalog_category(catalog_item)
    )


def _resolve_unit_origin(
    db: Session,
    service_order_id: int,
    unit_data,
) -> tuple[ServiceOrderItem | None, str, bool]:
    items = list(
        db.scalars(
            select(ServiceOrderItem).where(
                ServiceOrderItem.service_order_id == service_order_id,
                ServiceOrderItem.is_active.is_(True),
            )
        ).all()
    )
    origin = None
    if unit_data.origin_service_order_item_id is not None:
        origin = next(
            (item for item in items if item.id == unit_data.origin_service_order_item_id),
            None,
        )
        if origin is None:
            raise HTTPException(status_code=422, detail="La partida origen no pertenece al ETS")
    elif len(items) == 1:
        origin = items[0]
    else:
        quotation_item_ids = {
            stage.quotation_item_id
            for stage in unit_data.initial_stages
            if stage.quotation_item_id is not None
        }
        matches = [item for item in items if item.quotation_item_id in quotation_item_ids]
        if len(matches) == 1:
            origin = matches[0]
        elif len(items) > 1:
            raise HTTPException(
                status_code=422,
                detail="Una unidad de un ETS mixto debe indicar su partida operativa origen",
            )

    catalog_item = db.get(CatalogItem, origin.catalog_item_id) if origin and origin.catalog_item_id else None
    origin_category = _service_order_item_category(origin, catalog_item)
    if origin_category is None:
        initial = {stage.category for stage in unit_data.initial_stages}
        origin_category = next(iter(initial)) if len(initial) == 1 else "multiple"
    return origin, origin_category, origin_category == "general_service"


def _quotation_item_categories(db: Session, item: QuotationItem) -> set[str]:
    categories: set[str] = set()
    snapshot = item.operational_snapshot or {}
    item_category = (
        item.operational_category
        or snapshot.get("operational_category")
        or (snapshot.get("commercial_service_snapshot") or {}).get(
            "operational_category_snapshot"
        )
    )
    if item_category:
        categories.add("diagnosis" if item_category == "general_service" else item_category)
    snapshot_items = snapshot.get("operational_items") or []
    for snapshot_item in snapshot_items:
        component_category = (
            snapshot_item.get("operational_category")
            or (snapshot_item.get("service_snapshot") or {}).get(
                "operational_category_snapshot"
            )
        )
        if component_category and component_category != "general_service":
            categories.add(component_category)
    if not categories:
        catalog_item = db.get(CatalogItem, item.catalog_item_id) if item.catalog_item_id else None
        catalog_category = _catalog_category(catalog_item)
        if catalog_category:
            categories.add("diagnosis" if catalog_category == "general_service" else catalog_category)
    if not categories:
        # Adaptador legacy exacto para partidas previas al campo canónico. No se
        # buscan palabras ni descripciones y nunca prevalece sobre el snapshot.
        legacy_category = operational_category_from_structured_fields(
            item_type=None,
            category=item.service_name,
            commodity=item.service_name,
        )
        if legacy_category:
            categories.add("diagnosis" if legacy_category == "general_service" else legacy_category)
    if not categories and item.technical_request_id is not None:
        request = db.get(TechnicalServiceRequest, item.technical_request_id)
        if request is not None:
            categories.update(request.requested_categories or [])
    return categories


def _identification_status(brand: str | None, model: str | None, serial: str | None) -> str:
    return "complete" if brand and model and serial else "partial"


def _approved_item_decision(
    db: Session,
    *,
    quotation_item_id: int | None,
    unit_id: int,
    category: str,
    source_stage_id: int | None,
) -> QuotationItemDecision | None:
    if quotation_item_id is None:
        return None
    item = db.get(QuotationItem, quotation_item_id)
    if item is None:
        return None
    is_initial_commercial_item = (
        item.source_service_unit_id is None and item.source_stage_id is None
    )
    if not is_initial_commercial_item and (
        item.source_service_unit_id != unit_id or item.source_stage_id != source_stage_id
    ):
        return None
    decision = db.scalar(
        select(QuotationItemDecision)
        .where(
            QuotationItemDecision.quotation_item_id == quotation_item_id,
            QuotationItemDecision.decision == "approved",
        )
        .order_by(QuotationItemDecision.created_at.desc())
    )
    if decision is None or category not in (decision.enabled_stage_categories or []):
        return None
    return decision


def _unit_query(service_order_id: int):
    return (
        select(ServiceUnit)
        .where(ServiceUnit.service_order_id == service_order_id)
        .options(
            selectinload(ServiceUnit.stages).selectinload(ServiceStage.documents)
        )
        .order_by(ServiceUnit.id.asc())
        .execution_options(populate_existing=True)
    )


def create_service_units(
    db: Session,
    service_order_id: int,
    payload: ServiceUnitBatchCreate,
    *,
    user_id: int,
) -> list[ServiceUnit]:
    _active_service_order(db, service_order_id)
    created: list[ServiceUnit] = []
    for unit_data in payload.units:
        origin_item, initial_category, evolution_enabled = _resolve_unit_origin(
            db, service_order_id, unit_data
        )
        work_order = _work_order(db, service_order_id, unit_data.work_order_id)
        equipment = None
        if unit_data.equipment_id is not None:
            equipment = db.get(Equipment, unit_data.equipment_id)
            if equipment is None or equipment.service_order_id != service_order_id:
                raise HTTPException(status_code=422, detail="El equipo no pertenece al ETS")
            existing = db.scalar(select(ServiceUnit.id).where(ServiceUnit.equipment_id == equipment.id))
            if existing is not None:
                raise HTTPException(status_code=409, detail="El equipo ya tiene unidad operativa")

        if evolution_enabled and any(stage.category != "diagnosis" for stage in unit_data.initial_stages):
            raise HTTPException(
                status_code=422,
                detail="Servicio General inicia únicamente con diagnóstico; las demás etapas requieren flujo comercial",
            )
        unit = ServiceUnit(
            service_order_id=service_order_id,
            work_order_id=work_order.id,
            equipment_id=equipment.id if equipment else None,
            origin_service_order_item_id=origin_item.id if origin_item else None,
            initial_category=initial_category,
            evolution_enabled=evolution_enabled,
            name=unit_data.name if equipment is None else equipment.name,
            brand=unit_data.brand if equipment is None else equipment.brand,
            model=unit_data.model if equipment is None else equipment.model,
            serial_number=unit_data.serial_number if equipment is None else equipment.serial_number,
            identification_status=_identification_status(
                unit_data.brand if equipment is None else equipment.brand,
                unit_data.model if equipment is None else equipment.model,
                unit_data.serial_number if equipment is None else equipment.serial_number,
            ),
            identification_notes=unit_data.identification_notes,
            status="active",
        )
        db.add(unit)
        db.flush()
        for sequence, stage_data in enumerate(unit_data.initial_stages, start=1):
            initial_status = stage_data.status
            if evolution_enabled and stage_data.category == "diagnosis":
                initial_status = "authorized"
            decision = _approved_item_decision(
                db,
                quotation_item_id=stage_data.quotation_item_id,
                unit_id=unit.id,
                category=stage_data.category,
                source_stage_id=stage_data.source_stage_id,
            )
            if initial_status in {"authorized", "in_progress"} and not (
                evolution_enabled and stage_data.category == "diagnosis"
            ) and decision is None:
                raise HTTPException(
                    status_code=409,
                    detail="Una etapa ejecutable requiere aprobación explícita de su partida",
                )
            db.add(
                ServiceStage(
                    service_unit_id=unit.id,
                    sequence=sequence,
                    category=stage_data.category,
                    status=initial_status,
                    origin="general_service" if evolution_enabled else stage_data.origin,
                    source_stage_id=stage_data.source_stage_id,
                    quotation_item_id=stage_data.quotation_item_id,
                    commercial_decision_id=decision.id if decision else None,
                    responsible_user_id=stage_data.responsible_user_id,
                )
            )
        created.append(unit)

    db.flush()
    write_audit_log(
        db,
        action="service_execution.units_created",
        entity="service_orders",
        entity_id=service_order_id,
        user_id=user_id,
        new_values={"service_unit_ids": [unit.id for unit in created]},
    )
    publish_event(
        db,
        entity_type="service_order",
        entity_id=service_order_id,
        event_code="service_execution.units_created",
        idempotency_key=f"service-order:{service_order_id}:units:{','.join(str(unit.id) for unit in created)}",
        body=f"Se registraron {len(created)} unidades operativas en el ETS.",
        actor_id=user_id,
        metadata={"service_unit_ids": [unit.id for unit in created]},
    )
    db.commit()
    return list(db.scalars(_unit_query(service_order_id)).all())


def add_service_stage(
    db: Session,
    unit_id: int,
    payload: ServiceStageCreate,
    *,
    user_id: int,
) -> ServiceStage:
    unit = db.scalar(
        select(ServiceUnit).where(ServiceUnit.id == unit_id).with_for_update()
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unidad operativa no encontrada")
    _active_service_order(db, unit.service_order_id)
    if not unit.evolution_enabled:
        raise HTTPException(
            status_code=409,
            detail="La unidad no tiene origen comercial evolutivo",
        )
    if payload.source_stage_id is not None:
        source = db.get(ServiceStage, payload.source_stage_id)
        if source is None or source.service_unit_id != unit.id:
            raise HTTPException(status_code=422, detail="La etapa origen no pertenece a la unidad")

    approved_decision = _approved_item_decision(
        db,
        quotation_item_id=payload.quotation_item_id,
        unit_id=unit.id,
        category=payload.category,
        source_stage_id=payload.source_stage_id,
    )
    can_start_general_diagnosis = (
        payload.category == "diagnosis"
        and unit.evolution_enabled
        and db.scalar(select(func.count(ServiceStage.id)).where(ServiceStage.service_unit_id == unit.id)) == 0
    )
    if payload.status in {"authorized", "in_progress"} and approved_decision is None and not can_start_general_diagnosis:
        raise HTTPException(
            status_code=409,
            detail="La etapa no puede ejecutarse sin una decisión comercial aprobada",
        )
    next_sequence = int(
        db.scalar(select(func.max(ServiceStage.sequence)).where(ServiceStage.service_unit_id == unit.id)) or 0
    ) + 1
    stage = ServiceStage(
        service_unit_id=unit.id,
        sequence=next_sequence,
        category=payload.category,
        status=payload.status,
        origin=payload.origin,
        source_stage_id=payload.source_stage_id,
        quotation_item_id=payload.quotation_item_id,
        commercial_decision_id=approved_decision.id if approved_decision else None,
        responsible_user_id=payload.responsible_user_id,
        started_at=datetime.now(timezone.utc) if payload.status == "in_progress" else None,
    )
    db.add(stage)
    db.flush()
    write_audit_log(
        db, action="service_execution.stage_added", entity="service_stages",
        entity_id=stage.id, user_id=user_id,
        new_values={"unit_id": unit.id, "category": stage.category, "status": stage.status},
    )
    db.commit()
    return db.scalar(
        select(ServiceStage).where(ServiceStage.id == stage.id).options(selectinload(ServiceStage.documents))
    )


STAGE_TRANSITIONS = {
    "planned": {"pending_quote", "pending_approval", "cancelled"},
    "pending_quote": {"pending_approval", "authorized", "client_rejected", "not_executable", "cancelled"},
    "pending_approval": {"authorized", "client_rejected", "paused", "not_executable", "cancelled"},
    "authorized": {"in_progress", "paused", "cancelled"},
    "in_progress": {"paused", "completed", "not_executable"},
    "paused": {"authorized", "in_progress", "not_executable", "exception_closed", "cancelled"},
    "completed": set(),
    "client_rejected": set(),
    "not_executable": set(),
    "exception_closed": set(),
    "cancelled": set(),
}


def update_service_stage(
    db: Session,
    stage_id: int,
    payload: ServiceStageUpdate,
    *,
    user_id: int,
) -> ServiceStage:
    stage = db.scalar(
        select(ServiceStage).where(ServiceStage.id == stage_id).with_for_update()
    )
    if stage is None:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    unit = db.get(ServiceUnit, stage.service_unit_id)
    _active_service_order(db, unit.service_order_id)
    if payload.status not in STAGE_TRANSITIONS.get(stage.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Transición de etapa no permitida: {stage.status} → {payload.status}",
        )
    if payload.status in {"authorized", "in_progress"} and stage.status not in {"authorized", "in_progress"}:
        general_diagnosis = (
            unit.evolution_enabled
            and stage.category == "diagnosis"
            and stage.origin == "general_service"
        )
        decision = _approved_item_decision(
            db,
            quotation_item_id=stage.quotation_item_id,
            unit_id=unit.id,
            category=stage.category,
            source_stage_id=stage.source_stage_id,
        )
        if decision is None and not general_diagnosis:
            raise HTTPException(status_code=409, detail="La etapa no tiene aprobación comercial vigente")
        if decision is not None:
            stage.commercial_decision_id = decision.id
    previous_status = stage.status
    stage.status = payload.status
    if payload.evidence_summary is not None:
        stage.evidence_summary = payload.evidence_summary
    if payload.result is not None:
        stage.result = payload.result
    now = datetime.now(timezone.utc)
    if payload.status == "in_progress" and stage.started_at is None:
        stage.started_at = now
    if payload.status in {"completed", "not_executable", "exception_closed"}:
        stage.completed_at = now
    write_audit_log(
        db,
        action="service_execution.stage_status_changed",
        entity="service_stages",
        entity_id=stage.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": stage.status},
    )
    publish_event(
        db,
        entity_type="service_stage",
        entity_id=stage.id,
        event_code="service_execution.stage_status_changed",
        idempotency_key=(
            f"service-stage:{stage.id}:status:{previous_status}:{stage.status}:"
            f"{now.isoformat()}"
        ),
        body=f"La etapa cambió de {previous_status} a {stage.status}.",
        actor_id=user_id,
        metadata={"previous_status": previous_status, "status": stage.status},
    )
    db.commit()
    return db.scalar(
        select(ServiceStage).where(ServiceStage.id == stage.id).options(selectinload(ServiceStage.documents))
    )


def create_technical_request(
    db: Session,
    stage_id: int,
    payload: TechnicalServiceRequestCreate,
    *,
    user_id: int,
) -> TechnicalServiceRequest:
    stage = db.get(ServiceStage, stage_id)
    if stage is None:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    unit = db.get(ServiceUnit, stage.service_unit_id)
    _active_service_order(db, unit.service_order_id)
    if not unit.evolution_enabled:
        raise HTTPException(
            status_code=409,
            detail="La unidad no tiene origen comercial evolutivo",
        )
    if payload.source_message_id is not None:
        message = db.get(ActivityMessage, payload.source_message_id)
        if message is None:
            raise HTTPException(status_code=404, detail="Mensaje origen no encontrado")
        existing = db.scalar(
            select(TechnicalServiceRequest).where(
                TechnicalServiceRequest.source_message_id == payload.source_message_id
            )
        )
        if existing is not None:
            return existing
    request = TechnicalServiceRequest(
        service_order_id=unit.service_order_id,
        service_unit_id=unit.id,
        source_stage_id=stage.id,
        source_message_id=payload.source_message_id,
        requested_by_id=user_id,
        summary=payload.summary,
        requested_categories=list(dict.fromkeys(payload.requested_categories)),
        status="requested",
    )
    db.add(request)
    db.flush()
    publish_event(
        db,
        entity_type="service_stage",
        entity_id=stage.id,
        event_code="service_execution.technical_request_created",
        idempotency_key=f"technical-request:{request.id}:created",
        body="Solicitud comercial creada desde la etapa técnica.",
        actor_id=user_id,
        metadata={"technical_request_id": request.id, "requested_categories": request.requested_categories},
        related_entity_type="service_order",
        related_entity_id=unit.service_order_id,
    )
    db.commit()
    return request


def decide_quotation_item(
    db: Session,
    quotation_id: int,
    item_id: int,
    payload: QuotationItemDecisionCreate,
    *,
    user_id: int,
) -> tuple[QuotationItemDecision, list[int]]:
    item = db.scalar(
        select(QuotationItem).where(
            QuotationItem.id == item_id,
            QuotationItem.quotation_id == quotation_id,
            QuotationItem.is_active.is_(True),
        ).with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    quotation = db.get(Quotation, quotation_id)
    if quotation is None or quotation.status not in {"sent", "waiting", "accepted"}:
        raise HTTPException(
            status_code=409,
            detail="La partida sólo puede decidirse cuando la cotización fue enviada al cliente",
        )
    if payload.source != "internal":
        raise HTTPException(
            status_code=403,
            detail="El origen de la decisión se deriva del contexto autenticado",
        )
    latest = db.scalar(
        select(QuotationItemDecision)
        .where(QuotationItemDecision.quotation_item_id == item.id)
        .order_by(QuotationItemDecision.created_at.desc())
    )
    if latest is not None:
        raise HTTPException(
            status_code=409,
            detail="La partida ya tiene decisión; una corrección requiere una rama formal, no sobrescritura",
        )
    is_initial_commercial_item = (
        item.source_service_unit_id is None
        and item.source_stage_id is None
        and item.technical_request_id is None
    )
    enabled_categories = set(payload.enabled_stage_categories)
    if payload.decision == "approved":
        item_categories = _quotation_item_categories(db, item)
        if not enabled_categories.issubset(item_categories):
            raise HTTPException(
                status_code=422,
                detail="La categoría habilitada no corresponde al servicio cotizado",
            )
    source_stage = None
    if not is_initial_commercial_item:
        if item.source_service_unit_id is None or item.source_stage_id is None:
            raise HTTPException(
                status_code=422,
                detail="La partida derivada no contiene contexto ETS suficiente",
            )
        source_stage = db.get(ServiceStage, item.source_stage_id)
        if source_stage is None or source_stage.service_unit_id != item.source_service_unit_id:
            raise HTTPException(status_code=409, detail="El contexto ETS de la partida es inconsistente")
        unit = db.get(ServiceUnit, item.source_service_unit_id)
        if unit is None or not unit.evolution_enabled:
            raise HTTPException(
                status_code=409,
                detail="La unidad no tiene origen comercial evolutivo",
            )
        technical_request = db.get(TechnicalServiceRequest, item.technical_request_id)
        if (
            technical_request is None
            or technical_request.service_unit_id != unit.id
            or technical_request.source_stage_id != source_stage.id
        ):
            raise HTTPException(status_code=409, detail="La solicitud técnica de la partida es inconsistente")
        requested_categories = set(technical_request.requested_categories or [])
        if not enabled_categories.issubset(requested_categories):
            raise HTTPException(
                status_code=422,
                detail="La partida intenta habilitar una categoría no solicitada",
            )
    decision = QuotationItemDecision(
        quotation_item_id=item.id,
        decision=payload.decision,
        decided_by_id=user_id,
        decided_at=datetime.now(timezone.utc),
        source="internal",
        comment=payload.comment,
        enabled_stage_categories=list(dict.fromkeys(payload.enabled_stage_categories)),
    )
    try:
        with db.begin_nested():
            db.add(decision)
            db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La partida ya tiene decisión; una corrección requiere una rama formal, no sobrescritura",
        ) from exc
    created_ids: list[int] = []
    if payload.decision == "approved" and not is_initial_commercial_item:
        db.scalar(
            select(ServiceUnit)
            .where(ServiceUnit.id == item.source_service_unit_id)
            .with_for_update()
        )
        next_sequence = int(
            db.scalar(select(func.max(ServiceStage.sequence)).where(
                ServiceStage.service_unit_id == item.source_service_unit_id
            )) or 0
        )
        for category in decision.enabled_stage_categories:
            next_sequence += 1
            stage = ServiceStage(
                service_unit_id=item.source_service_unit_id,
                sequence=next_sequence,
                category=category,
                status="authorized",
                origin="derived_quotation",
                source_stage_id=item.source_stage_id,
                quotation_item_id=item.id,
                commercial_decision_id=decision.id,
            )
            db.add(stage)
            db.flush()
            created_ids.append(stage.id)
    if item.technical_request_id is not None:
        technical_request = db.get(TechnicalServiceRequest, item.technical_request_id)
        request_items = list(
            db.scalars(
                select(QuotationItem).where(
                    QuotationItem.technical_request_id == item.technical_request_id,
                    QuotationItem.is_active.is_(True),
                )
            ).all()
        )
        decisions = [
            db.scalar(
                select(QuotationItemDecision)
                .where(QuotationItemDecision.quotation_item_id == request_item.id)
                .order_by(QuotationItemDecision.created_at.desc())
            )
            for request_item in request_items
        ]
        decided = [request_decision for request_decision in decisions if request_decision is not None]
        if technical_request is not None:
            if len(decided) < len(request_items):
                technical_request.status = (
                    "partially_approved"
                    if any(request_decision.decision == "approved" for request_decision in decided)
                    else "quoted"
                )
            elif all(request_decision.decision == "approved" for request_decision in decided):
                technical_request.status = "approved"
            elif all(request_decision.decision == "rejected" for request_decision in decided):
                technical_request.status = "rejected"
            else:
                technical_request.status = "partially_approved"
    publish_event(
        db,
        entity_type="quotation" if is_initial_commercial_item else "service_stage",
        entity_id=quotation_id if is_initial_commercial_item else source_stage.id,
        event_code=f"service_execution.commercial_{payload.decision}",
        idempotency_key=f"quotation-item:{item.id}:decision:{decision.id}",
        body=f"La partida comercial fue {payload.decision}.",
        actor_id=user_id,
        metadata={"decision_id": decision.id, "created_stage_ids": created_ids},
        related_entity_type="quotation",
        related_entity_id=quotation_id,
    )
    write_audit_log(
        db, action="quotation.item_decided", entity="quotation_items", entity_id=item.id,
        user_id=user_id,
        new_values={"decision": payload.decision, "created_stage_ids": created_ids},
    )
    db.commit()
    return decision, created_ids


def execution_board(db: Session, service_order_id: int) -> dict:
    service_order = db.get(ServiceOrder, service_order_id)
    if service_order is None:
        raise HTTPException(status_code=404, detail="ETS no encontrado")
    units = list(db.scalars(_unit_query(service_order_id)).all())
    tasks = list(
        db.scalars(
            select(ServiceTask)
            .where(ServiceTask.service_order_id == service_order_id)
            .options(selectinload(ServiceTask.assignees))
            .order_by(ServiceTask.created_at.desc())
        ).all()
    )
    requests = list(
        db.scalars(
            select(TechnicalServiceRequest)
            .where(TechnicalServiceRequest.service_order_id == service_order_id)
            .order_by(TechnicalServiceRequest.created_at.desc())
        ).all()
    )
    return {
        "service_order_id": service_order_id,
        "categories": sorted({stage.category for unit in units for stage in unit.stages}),
        "units": units,
        "tasks": [
            {
                "id": task.id,
                "source_message_id": task.source_message_id,
                "created_by_id": task.created_by_id,
                "service_order_id": task.service_order_id,
                "service_unit_id": task.service_unit_id,
                "service_stage_id": task.service_stage_id,
                "title": task.title,
                "status": task.status,
                "due_at": task.due_at,
                "completed_at": task.completed_at,
                "assignee_user_ids": [assignment.user_id for assignment in task.assignees],
            }
            for task in tasks
        ],
        "technical_requests": requests,
    }


def task_from_activity_message(db: Session, message: ActivityMessage) -> ServiceTask | None:
    """Materializa #tarea de forma idempotente dentro de la transacción de Activity."""
    marker = "#tarea"
    marker_index = message.body.lower().find(marker)
    if marker_index < 0 or message.author_id is None:
        return None
    existing = db.scalar(select(ServiceTask).where(ServiceTask.source_message_id == message.id))
    if existing is not None:
        return existing
    context = {"service_order_id": None, "service_unit_id": None, "service_stage_id": None}
    entity_type = message.thread.entity_type
    entity_id = message.thread.entity_id
    if entity_type == "service_order":
        context["service_order_id"] = entity_id
    elif entity_type == "service_unit":
        unit = db.get(ServiceUnit, entity_id)
        if unit is not None:
            context.update(service_order_id=unit.service_order_id, service_unit_id=unit.id)
    elif entity_type == "service_stage":
        stage = db.get(ServiceStage, entity_id)
        unit = db.get(ServiceUnit, stage.service_unit_id) if stage else None
        if stage is not None and unit is not None:
            context.update(
                service_order_id=unit.service_order_id,
                service_unit_id=unit.id,
                service_stage_id=stage.id,
            )
    else:
        return None
    title = message.body[marker_index + len(marker):].strip()
    if not title:
        return None
    task = ServiceTask(
        source_message_id=message.id,
        created_by_id=message.author_id,
        title=title[:255],
        **context,
    )
    db.add(task)
    db.flush()
    for mention in message.mentions:
        db.add(ServiceTaskAssignee(task_id=task.id, user_id=mention.mentioned_user_id))
    message.metadata_json = {
        **(message.metadata_json or {}),
        "service_task_id": task.id,
        "service_context": context,
    }
    return task
