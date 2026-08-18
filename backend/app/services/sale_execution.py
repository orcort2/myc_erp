from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload
from weasyprint import HTML

from app.models.catalog_item import CatalogItem
from app.models.client_portal_membership import ClientPortalMembership
from app.models.equipment import Equipment
from app.models.notification import Notification
from app.models.quotation import QuotationItem, QuotationItemDecision
from app.models.sale_execution import (
    SaleAuthorization,
    SaleDelivery,
    SaleDeliveryLine,
    SaleOrderItem,
    SaleUnitState,
)
from app.models.service_execution import ServiceStage, ServiceUnit
from app.models.service_order import ServiceOrder, ServiceOrderItem
from app.models.user import User
from app.schemas.sale_execution import (
    SaleArrivalCreate,
    SaleAuthorizationCreate,
    SaleAuthorizationResolve,
    SaleDeliveryAccept,
    SaleDeliveryConfirm,
    SaleDeliveryCreate,
)
from app.schemas.certificate import CertificateCreate
from app.services.activity import publish_event
from app.services.audit_logs import write_audit_log
from app.services.auth import user_has_permission
from app.services.certificates import create_certificate
from app.services.service_order_certificate_capacity import certificate_type_from_scope


TERMINAL_UNIT_STATUSES = {"delivered", "resolved"}
OPEN_DELIVERY_STATUSES = {
    "prepared", "pickup_notified", "technician_requested", "technician_accepted",
    "scheduled", "sent", "delivery_reported",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sale_item_query(service_order_id: int):
    return (
        select(SaleOrderItem)
        .where(SaleOrderItem.service_order_id == service_order_id)
        .options(selectinload(SaleOrderItem.units))
        .order_by(SaleOrderItem.id)
    )


def _delivery_query(service_order_id: int):
    return (
        select(SaleDelivery)
        .where(SaleDelivery.service_order_id == service_order_id)
        .options(selectinload(SaleDelivery.lines))
        .order_by(SaleDelivery.id.desc())
    )


def _authorization_query(service_order_id: int):
    return (
        select(SaleAuthorization)
        .where(SaleAuthorization.service_order_id == service_order_id)
        .order_by(SaleAuthorization.created_at.desc())
    )


def _active_sale_order(db: Session, service_order_id: int) -> ServiceOrder:
    order = db.get(ServiceOrder, service_order_id)
    if order is None or not order.is_active:
        raise HTTPException(status_code=404, detail="ETS de Venta no encontrado")
    if order.status in {"closed", "cancelled"}:
        raise HTTPException(status_code=409, detail="El ETS no admite cambios de Venta")
    exists = db.scalar(select(SaleOrderItem.id).where(SaleOrderItem.service_order_id == order.id))
    if exists is None:
        raise HTTPException(status_code=409, detail="El ETS no contiene partidas de Venta")
    return order


def _ensure_advisor(order: ServiceOrder, actor: User) -> None:
    if not user_has_permission(actor, "service_orders.sales.manage"):
        raise HTTPException(status_code=403, detail="La operación de Venta corresponde al asesor")
    if order.advisor_id is not None and order.advisor_id != actor.id and not user_has_permission(
        actor, "service_orders.sales.authorize"
    ):
        raise HTTPException(status_code=403, detail="Sólo el asesor asignado puede operar esta Venta")


def _configuration(service_item: ServiceOrderItem) -> dict:
    snapshot = service_item.service_snapshot or {}
    return dict(snapshot.get("sale_configuration_snapshot") or {})


def initialize_sale_execution(db: Session, order: ServiceOrder, *, user_id: int) -> None:
    """Materializa el estado inicial desde el snapshot; no consulta el catálogo vigente."""
    existing = db.scalar(select(SaleOrderItem.id).where(SaleOrderItem.service_order_id == order.id))
    if existing is not None:
        return
    work_orders = sorted((item for item in order.work_orders if item.is_active), key=lambda item: item.sequence)
    if not work_orders:
        raise HTTPException(status_code=409, detail="El ETS requiere una OT para materializar Venta")
    serial_index = 0
    created_item_ids: list[int] = []
    for service_item in order.items:
        if not service_item.is_active or service_item.operational_category != "sale":
            continue
        config = _configuration(service_item)
        sale_item = SaleOrderItem(
            service_order_id=order.id,
            service_order_item_id=service_item.id,
            requires_individual_identification=bool(config.get("requires_individual_identification", False)),
            included_calibration_catalog_item_id=config.get("included_calibration_catalog_item_id"),
            frozen_configuration=config,
            ordered_quantity=int(service_item.quantity),
            status="pending_arrival",
        )
        db.add(sale_item)
        db.flush()
        created_item_ids.append(sale_item.id)
        if not sale_item.requires_individual_identification:
            continue
        for sequence in range(1, sale_item.ordered_quantity + 1):
            work_order = work_orders[min(serial_index // 10, len(work_orders) - 1)]
            serial_index += 1
            unit = ServiceUnit(
                service_order_id=order.id,
                work_order_id=work_order.id,
                origin_service_order_item_id=service_item.id,
                initial_category="sale",
                evolution_enabled=False,
                name=service_item.service_name,
                brand=config.get("brand"),
                model=config.get("model"),
                identification_status="pending",
                identification_notes=f"Unidad de Venta {sequence} pendiente de arribo",
                status="pending_arrival",
            )
            db.add(unit)
            db.flush()
            db.add(ServiceStage(
                service_unit_id=unit.id,
                sequence=1,
                category="sale",
                status="planned",
                origin="quotation",
                quotation_item_id=service_item.quotation_item_id,
            ))
            db.add(SaleUnitState(
                sale_order_item_id=sale_item.id,
                service_unit_id=unit.id,
                status="pending_arrival",
            ))
    if created_item_ids:
        write_audit_log(
            db, action="sale.execution_initialized", entity="service_orders",
            entity_id=order.id, user_id=user_id,
            new_values={"sale_order_item_ids": created_item_ids, "source": "quotation_snapshot"},
        )


def initialize_existing_sale_execution(
    db: Session, service_order_id: int, *, actor: User,
):
    """Materializa explícitamente una Venta histórica usando sólo su snapshot persistido."""
    order = db.get(ServiceOrder, service_order_id)
    if order is None or not order.is_active:
        raise HTTPException(status_code=404, detail="ETS no encontrado")
    if order.status in {"closed", "cancelled"}:
        raise HTTPException(status_code=409, detail="El ETS no admite inicialización de Venta")
    _ensure_advisor(order, actor)
    if not any(item.is_active and item.operational_category == "sale" for item in order.items):
        raise HTTPException(status_code=409, detail="El ETS no contiene partidas de Venta")
    initialize_sale_execution(db, order, user_id=actor.id)
    db.commit()
    return sale_board(db, order.id)


def delete_pristine_sale_execution(db: Session, service_order_id: int) -> None:
    """Elimina sólo la proyección automática que el validador declaró reconstruible."""
    sale_item_ids = list(db.scalars(select(SaleOrderItem.id).where(
        SaleOrderItem.service_order_id == service_order_id
    )).all())
    if not sale_item_ids:
        return
    unit_ids = list(db.scalars(select(SaleUnitState.service_unit_id).where(
        SaleUnitState.sale_order_item_id.in_(sale_item_ids)
    )).all())
    db.execute(delete(SaleUnitState).where(SaleUnitState.sale_order_item_id.in_(sale_item_ids)))
    if unit_ids:
        db.execute(delete(ServiceStage).where(ServiceStage.service_unit_id.in_(unit_ids)))
        db.execute(delete(ServiceUnit).where(ServiceUnit.id.in_(unit_ids)))
    db.execute(delete(SaleOrderItem).where(SaleOrderItem.id.in_(sale_item_ids)))


def count_non_pristine_sale_dependencies(db: Session, service_order_id: int) -> int:
    item_activity = int(db.scalar(select(func.count(SaleOrderItem.id)).where(
        SaleOrderItem.service_order_id == service_order_id,
        or_(SaleOrderItem.arrived_quantity > 0, SaleOrderItem.delivered_quantity > 0,
            SaleOrderItem.resolved_quantity > 0, SaleOrderItem.status != "pending_arrival"),
    )) or 0)
    unit_activity = int(db.scalar(select(func.count(SaleUnitState.id)).join(SaleOrderItem).where(
        SaleOrderItem.service_order_id == service_order_id,
        or_(SaleUnitState.status != "pending_arrival", SaleUnitState.arrived_at.is_not(None)),
    )) or 0)
    deliveries = int(db.scalar(select(func.count(SaleDelivery.id)).where(
        SaleDelivery.service_order_id == service_order_id
    )) or 0)
    authorizations = int(db.scalar(select(func.count(SaleAuthorization.id)).where(
        SaleAuthorization.service_order_id == service_order_id
    )) or 0)
    return item_activity + unit_activity + deliveries + authorizations


def _calibration_closed(db: Session, state: SaleUnitState) -> bool:
    if state.calibration_stage_id is None:
        return True
    stage = db.get(ServiceStage, state.calibration_stage_id)
    return stage is not None and stage.status in {"completed", "not_executable", "exception_closed"}


def _refresh_statuses(db: Session, service_order_id: int) -> None:
    for item in db.scalars(_sale_item_query(service_order_id)).all():
        if item.requires_individual_identification:
            fulfillment_units = [unit for unit in item.units if unit.status != "replaced"]
            for unit in fulfillment_units:
                if unit.status == "calibration_pending" and _calibration_closed(db, unit):
                    unit.status = "ready_for_delivery"
            item.arrived_quantity = sum(unit.arrived_at is not None for unit in fulfillment_units)
            item.delivered_quantity = sum(unit.status == "delivered" for unit in fulfillment_units)
            item.resolved_quantity = sum(unit.status == "resolved" for unit in fulfillment_units)
            statuses = {unit.status for unit in fulfillment_units}
            if statuses <= TERMINAL_UNIT_STATUSES and len(fulfillment_units) == item.ordered_quantity:
                item.status = "delivered" if statuses == {"delivered"} else "resolved"
            elif "commercial_review" in statuses:
                item.status = "commercial_review"
            elif "warranty_return" in statuses:
                item.status = "warranty_return"
            elif any(unit.calibration_stage_id and not _calibration_closed(db, unit) for unit in fulfillment_units):
                item.status = "calibration_pending"
            elif item.delivered_quantity or item.resolved_quantity:
                item.status = "partially_delivered"
            elif item.arrived_quantity:
                item.status = "ready_for_delivery" if all(
                    unit.status in {"ready_for_delivery", "delivery_prepared"}
                    for unit in fulfillment_units if unit.arrived_at is not None
                ) else "partially_arrived"
            else:
                item.status = "pending_arrival"
        else:
            completed = item.delivered_quantity + item.resolved_quantity
            if completed >= item.ordered_quantity:
                item.status = "delivered" if item.resolved_quantity == 0 else "resolved"
            elif item.status in {"commercial_review", "warranty_return"}:
                continue
            elif completed:
                item.status = "partially_delivered"
            elif item.arrived_quantity >= item.ordered_quantity:
                item.status = "ready_for_delivery"
            elif item.arrived_quantity:
                item.status = "partially_arrived"
            else:
                item.status = "pending_arrival"


def sale_blockers(db: Session, service_order_id: int) -> list[str]:
    _refresh_statuses(db, service_order_id)
    blockers: list[str] = []
    items = list(db.scalars(_sale_item_query(service_order_id)).all())
    if not items:
        return ["El ETS no contiene proyección de Venta"]
    for item in items:
        pending = item.ordered_quantity - item.delivered_quantity - item.resolved_quantity
        if pending > 0:
            blockers.append(f"Partida {item.service_order_item_id}: {pending} unidad(es) pendientes")
        for unit in item.units:
            if unit.status == "replaced":
                continue
            if unit.status == "commercial_review":
                blockers.append(f"Unidad {unit.id}: revisión comercial pendiente")
            if unit.status == "warranty_return":
                blockers.append(f"Unidad {unit.id}: retorno por garantía pendiente")
            if unit.calibration_stage_id and not _calibration_closed(db, unit):
                blockers.append(f"Unidad {unit.id}: calibración obligatoria pendiente")
    open_deliveries = int(db.scalar(select(func.count(SaleDelivery.id)).where(
        SaleDelivery.service_order_id == service_order_id,
        SaleDelivery.status.in_(OPEN_DELIVERY_STATUSES),
    )) or 0)
    if open_deliveries:
        blockers.append(f"{open_deliveries} entrega(s) sin evidencia de recepción")
    return blockers


def sale_board(db: Session, service_order_id: int) -> dict:
    order = db.get(ServiceOrder, service_order_id)
    if order is None or not order.is_active:
        raise HTTPException(status_code=404, detail="ETS no encontrado")
    blockers = sale_blockers(db, service_order_id)
    return {
        "service_order_id": order.id,
        "status": order.status,
        "items": list(db.scalars(_sale_item_query(order.id)).all()),
        "deliveries": list(db.scalars(_delivery_query(order.id)).all()),
        "authorizations": list(db.scalars(_authorization_query(order.id)).all()),
        "blockers": blockers,
        "can_close": not blockers,
    }


def list_technician_deliveries(db: Session, technician_id: int) -> list[SaleDelivery]:
    return list(db.scalars(
        select(SaleDelivery)
        .where(
            SaleDelivery.technician_id == technician_id,
            SaleDelivery.status.in_(("technician_requested", "scheduled")),
        )
        .options(selectinload(SaleDelivery.lines))
        .order_by(SaleDelivery.created_at.desc())
    ).all())


def _matches(expected: str | None, actual: str | None) -> bool:
    return not expected or (actual or "").strip().casefold() == expected.strip().casefold()


def _consume_authorization(
    db: Session, authorization_id: int | None, *, expected_type: str, actor_id: int,
    service_order_id: int, sale_item_id: int | None = None, unit_state_id: int | None = None,
) -> SaleAuthorization | None:
    if authorization_id is None:
        return None
    authorization = db.get(SaleAuthorization, authorization_id)
    if (
        authorization is None or authorization.status != "authorized"
        or authorization.service_order_id != service_order_id
        or authorization.authorization_type != expected_type
        or (sale_item_id is not None and authorization.sale_order_item_id != sale_item_id)
        or (unit_state_id is not None and authorization.sale_unit_state_id != unit_state_id)
    ):
        raise HTTPException(status_code=409, detail="La autorización no es válida para esta operación")
    authorization.status = "consumed"
    authorization.consumed_by_id = actor_id
    authorization.consumed_at = _now()
    return authorization


def _included_calibration_snapshot(item: SaleOrderItem) -> dict | None:
    return (item.frozen_configuration or {}).get("included_calibration_snapshot")


def _append_calibration_stage(db: Session, state: SaleUnitState, item: SaleOrderItem) -> ServiceStage:
    unit = db.get(ServiceUnit, state.service_unit_id)
    snapshot = _included_calibration_snapshot(item) or {}
    next_sequence = int(db.scalar(select(func.max(ServiceStage.sequence)).where(
        ServiceStage.service_unit_id == unit.id
    )) or 0) + 1
    stage = ServiceStage(
        service_unit_id=unit.id,
        sequence=next_sequence,
        category="calibration",
        status="authorized",
        origin="sale_included_calibration",
        quotation_item_id=db.get(ServiceOrderItem, item.service_order_item_id).quotation_item_id,
        result={"calibration_snapshot": snapshot},
    )
    db.add(stage)
    db.flush()
    state.calibration_stage_id = stage.id
    state.status = "calibration_pending"
    return stage


def register_arrival(
    db: Session, service_order_id: int, sale_item_id: int, payload: SaleArrivalCreate,
    *, actor: User, sale_unit_state_id: int | None = None,
):
    order = _active_sale_order(db, service_order_id)
    _ensure_advisor(order, actor)
    item = db.get(SaleOrderItem, sale_item_id)
    if item is None or item.service_order_id != order.id:
        raise HTTPException(status_code=404, detail="Partida de Venta no encontrada")
    if payload.catalog_item_id != db.get(ServiceOrderItem, item.service_order_item_id).catalog_item_id:
        raise HTTPException(status_code=409, detail="El producto seleccionado no corresponde al snapshot vendido")
    expected = item.frozen_configuration or {}
    discrepancy = not all((
        _matches(expected.get("brand"), payload.brand),
        _matches(expected.get("model"), payload.model),
        _matches(expected.get("specification"), payload.specification),
    ))
    state = None
    if item.requires_individual_identification:
        if sale_unit_state_id is None:
            raise HTTPException(status_code=422, detail="Selecciona la unidad pendiente de arribo")
        state = db.get(SaleUnitState, sale_unit_state_id)
        if state is None or state.sale_order_item_id != item.id:
            raise HTTPException(status_code=404, detail="Unidad de Venta no encontrada")
        if state.arrived_at is not None:
            raise HTTPException(status_code=409, detail="La unidad ya fue dada de alta")
        if not payload.serial_unknown and not (payload.serial_number or "").strip():
            raise HTTPException(status_code=422, detail="Captura la serie o marca que es desconocida")
    if discrepancy:
        authorization = _consume_authorization(
            db, payload.substitution_authorization_id, expected_type="substitution",
            actor_id=actor.id, service_order_id=order.id, sale_item_id=item.id,
            unit_state_id=state.id if state else None,
        )
        if authorization is None:
            reason = "El modelo, marca o especificación recibida no coincide con el snapshot cotizado"
            if state:
                state.status = "commercial_review"
                state.discrepancy_reason = reason
            item.status = "commercial_review"
            write_audit_log(db, action="sale.arrival_blocked_discrepancy", entity="sale_order_items",
                            entity_id=item.id, user_id=actor.id, new_values={"reason": reason})
            db.commit()
            raise HTTPException(status_code=409, detail="Alta bloqueada: requiere corrección comercial o sustitución autorizada")
    now = _now()
    if not item.requires_individual_identification:
        if item.arrived_quantity + payload.quantity > item.ordered_quantity:
            raise HTTPException(status_code=409, detail="El arribo excede la cantidad vendida")
        item.arrived_quantity += payload.quantity
        _refresh_statuses(db, order.id)
        entity_id = item.id
    else:
        unit = db.get(ServiceUnit, state.service_unit_id)
        equipment = Equipment(
            service_order_id=order.id,
            work_order_id=unit.work_order_id,
            service_order_item_id=item.service_order_item_id,
            name=db.get(ServiceOrderItem, item.service_order_item_id).service_name,
            brand=payload.brand,
            model=payload.model,
            serial_number=None if payload.serial_unknown else payload.serial_number,
            range_or_capacity=payload.specification,
            initial_condition="Recibido físicamente por el asesor",
            notes="Serie desconocida" if payload.serial_unknown else None,
            status="registered",
        )
        calibration_snapshot = _included_calibration_snapshot(item)
        if calibration_snapshot:
            equipment.calibration_scope = calibration_snapshot.get("calibration_scope_snapshot")
            equipment.service_type_snapshot = calibration_snapshot.get("service_type_snapshot")
            equipment.linked_company_id = calibration_snapshot.get("linked_company_id")
            equipment.linked_company_name_snapshot = calibration_snapshot.get("linked_company_name_snapshot")
            equipment.certificate_prefix_snapshot = calibration_snapshot.get("certificate_prefix_snapshot")
            equipment.certificate_operational_context_snapshot = {
                "schema_version": 1, "source": "sale_included_calibration",
                "service_snapshot": calibration_snapshot,
            }
        db.add(equipment)
        db.flush()
        unit.equipment_id = equipment.id
        unit.brand = payload.brand
        unit.model = payload.model
        unit.serial_number = equipment.serial_number
        unit.identification_status = "partial" if payload.serial_unknown else "complete"
        unit.status = "active"
        state.equipment_id = equipment.id
        state.serial_number = equipment.serial_number
        state.brand = payload.brand
        state.model = payload.model
        state.specification = payload.specification
        state.arrived_at = now
        state.status = "arrived"
        if item.included_calibration_catalog_item_id:
            _append_calibration_stage(db, state, item)
            certificate_type = certificate_type_from_scope(equipment.calibration_scope)
            if certificate_type:
                create_certificate(
                    db,
                    CertificateCreate(
                        service_order_id=order.id,
                        equipment_id=equipment.id,
                        certificate_type=certificate_type,
                        title=f"Certificado de calibración incluida - {equipment.name}",
                        notes="Generado exclusivamente por el componente de Calibración incluido en Venta.",
                    ),
                    user_id=actor.id,
                    commit=False,
                )
        else:
            state.status = "ready_for_delivery"
        _refresh_statuses(db, order.id)
        entity_id = state.id
    write_audit_log(db, action="sale.arrival_registered", entity="sale_unit_states" if state else "sale_order_items",
                    entity_id=entity_id, user_id=actor.id,
                    new_values={"quantity": payload.quantity, "arrived_at": now.isoformat()})
    publish_event(db, entity_type="service_order", entity_id=order.id,
                  event_code="sale.arrival_registered",
                  idempotency_key=f"sale-arrival:{entity_id}:{now.isoformat()}",
                  body="Arribo de Venta registrado por el asesor.", actor_id=actor.id)
    db.commit()
    return sale_board(db, order.id)


def mark_warranty_return(db: Session, service_order_id: int, unit_state_id: int, reason: str, *, actor: User):
    order = _active_sale_order(db, service_order_id)
    _ensure_advisor(order, actor)
    state = db.get(SaleUnitState, unit_state_id)
    if state is None or state.sale_order_item.service_order_id != order.id or state.arrived_at is None:
        raise HTTPException(status_code=409, detail="Sólo una unidad arribada puede retornar por garantía")
    if state.status in TERMINAL_UNIT_STATUSES:
        raise HTTPException(status_code=409, detail="La unidad ya fue resuelta o entregada")
    state.status = "warranty_return"
    state.warranty_returned_at = _now()
    state.discrepancy_reason = reason
    _refresh_statuses(db, order.id)
    write_audit_log(db, action="sale.warranty_returned", entity="sale_unit_states",
                    entity_id=state.id, user_id=actor.id, new_values={"reason": reason})
    db.commit()
    return sale_board(db, order.id)


def resolve_warranty_return(
    db: Session, service_order_id: int, unit_state_id: int, resolution: str,
    reason: str, *, actor: User,
):
    if not user_has_permission(actor, "service_orders.sales.authorize"):
        raise HTTPException(status_code=403, detail="La resolución de garantía requiere autorización administrativa")
    order = _active_sale_order(db, service_order_id)
    state = db.get(SaleUnitState, unit_state_id)
    if state is None or state.sale_order_item.service_order_id != order.id or state.status != "warranty_return":
        raise HTTPException(status_code=409, detail="La unidad no tiene un retorno por garantía abierto")
    if resolution == "return_to_flow":
        state.status = "ready_for_delivery" if _calibration_closed(db, state) else "calibration_pending"
    elif resolution == "replacement":
        original_unit = db.get(ServiceUnit, state.service_unit_id)
        if state.calibration_stage_id and not _calibration_closed(db, state):
            stage = db.get(ServiceStage, state.calibration_stage_id)
            stage.status = "not_executable"
            stage.result = {**(stage.result or {}), "warranty_resolution": "replacement"}
        state.status = "replaced"
        replacement = ServiceUnit(
            service_order_id=order.id,
            work_order_id=original_unit.work_order_id,
            origin_service_order_item_id=original_unit.origin_service_order_item_id,
            initial_category="sale",
            evolution_enabled=False,
            name=original_unit.name,
            brand=original_unit.brand,
            model=original_unit.model,
            identification_status="pending",
            identification_notes=f"Reemplazo en garantía de unidad Venta {state.id}",
            status="pending_arrival",
        )
        db.add(replacement)
        db.flush()
        db.add(ServiceStage(
            service_unit_id=replacement.id,
            sequence=1,
            category="sale",
            status="planned",
            origin="warranty_replacement",
            quotation_item_id=db.get(ServiceOrderItem, state.sale_order_item.service_order_item_id).quotation_item_id,
        ))
        replacement_state = SaleUnitState(
            service_unit_id=replacement.id,
            status="pending_arrival",
            discrepancy_reason=f"Reemplaza unidad {state.id}",
        )
        state.sale_order_item.units.append(replacement_state)
    elif resolution == "commercial_cancellation":
        if state.calibration_stage_id and not _calibration_closed(db, state):
            stage = db.get(ServiceStage, state.calibration_stage_id)
            stage.status = "not_executable"
            stage.result = {**(stage.result or {}), "warranty_resolution": "commercial_cancellation"}
        state.status = "resolved"
    else:
        raise HTTPException(status_code=422, detail="Resolución de garantía no soportada")
    state.discrepancy_reason = f"Garantía {resolution}: {reason}"
    _refresh_statuses(db, order.id)
    write_audit_log(db, action="sale.warranty_resolved", entity="sale_unit_states",
                    entity_id=state.id, user_id=actor.id,
                    new_values={"resolution": resolution, "reason": reason})
    db.commit()
    return sale_board(db, order.id)


def request_authorization(db: Session, service_order_id: int, payload: SaleAuthorizationCreate, *, actor: User):
    order = _active_sale_order(db, service_order_id)
    _ensure_advisor(order, actor)
    if payload.sale_order_item_id is not None:
        item = db.get(SaleOrderItem, payload.sale_order_item_id)
        if item is None or item.service_order_id != order.id:
            raise HTTPException(status_code=404, detail="Partida de Venta no encontrada")
    if payload.sale_unit_state_id is not None:
        state = db.get(SaleUnitState, payload.sale_unit_state_id)
        if state is None or state.sale_order_item.service_order_id != order.id:
            raise HTTPException(status_code=404, detail="Unidad de Venta no encontrada")
    authorization = SaleAuthorization(
        service_order_id=order.id, sale_order_item_id=payload.sale_order_item_id,
        sale_unit_state_id=payload.sale_unit_state_id,
        authorization_type=payload.authorization_type, reason=payload.reason,
        requested_by_id=actor.id, status="requested",
    )
    db.add(authorization)
    db.flush()
    write_audit_log(db, action="sale.authorization_requested", entity="sale_authorizations",
                    entity_id=authorization.id, user_id=actor.id,
                    new_values={"type": authorization.authorization_type, "reason": authorization.reason})
    db.commit()
    db.refresh(authorization)
    return authorization


def resolve_authorization(db: Session, service_order_id: int, authorization_id: int,
                          payload: SaleAuthorizationResolve, *, actor: User):
    if not user_has_permission(actor, "service_orders.sales.authorize"):
        raise HTTPException(status_code=403, detail="Se requiere autorización administrativa")
    authorization = db.get(SaleAuthorization, authorization_id)
    if authorization is None or authorization.service_order_id != service_order_id:
        raise HTTPException(status_code=404, detail="Autorización de Venta no encontrada")
    if authorization.status != "requested":
        raise HTTPException(status_code=409, detail="La autorización ya fue resuelta")
    authorization.status = "authorized" if payload.authorized else "rejected"
    authorization.authorized_by_id = actor.id
    authorization.authorized_at = _now()
    authorization.resolution_comment = payload.comment
    write_audit_log(db, action=f"sale.authorization_{authorization.status}", entity="sale_authorizations",
                    entity_id=authorization.id, user_id=actor.id,
                    new_values={"status": authorization.status}, comment=payload.comment)
    db.commit()
    db.refresh(authorization)
    return authorization


def individualize_sale_item(db: Session, service_order_id: int, sale_item_id: int,
                            authorization_id: int, *, actor: User):
    order = _active_sale_order(db, service_order_id)
    _ensure_advisor(order, actor)
    item = db.get(SaleOrderItem, sale_item_id)
    if item is None or item.service_order_id != order.id or item.requires_individual_identification:
        raise HTTPException(status_code=409, detail="La partida no admite esta conversión")
    if item.arrived_quantity or item.delivered_quantity or item.resolved_quantity:
        raise HTTPException(status_code=409, detail="No se puede convertir una partida con movimiento previo")
    _consume_authorization(db, authorization_id, expected_type="individual_identification",
                           actor_id=actor.id, service_order_id=order.id, sale_item_id=item.id)
    work_order = sorted(order.work_orders, key=lambda value: value.sequence)[0]
    service_item = db.get(ServiceOrderItem, item.service_order_item_id)
    for sequence in range(item.ordered_quantity):
        unit = ServiceUnit(
            service_order_id=order.id, work_order_id=work_order.id,
            origin_service_order_item_id=service_item.id, initial_category="sale",
            evolution_enabled=False, name=service_item.service_name,
            identification_status="pending", status="pending_arrival",
        )
        db.add(unit); db.flush()
        db.add(ServiceStage(service_unit_id=unit.id, sequence=1, category="sale", status="planned",
                            origin="authorized_exception", quotation_item_id=service_item.quotation_item_id))
        db.add(SaleUnitState(sale_order_item_id=item.id, service_unit_id=unit.id, status="pending_arrival"))
    item.requires_individual_identification = True
    item.frozen_configuration = {**item.frozen_configuration, "authorized_individualization": True}
    write_audit_log(db, action="sale.item_individualized", entity="sale_order_items", entity_id=item.id,
                    user_id=actor.id, new_values={"authorization_id": authorization_id})
    db.commit()
    return sale_board(db, order.id)


def add_later_calibration(db: Session, service_order_id: int, unit_state_id: int, *, actor: User,
                          quotation_item_id: int | None = None, authorization_id: int | None = None):
    order = _active_sale_order(db, service_order_id)
    _ensure_advisor(order, actor)
    state = db.get(SaleUnitState, unit_state_id)
    if state is None or state.sale_order_item.service_order_id != order.id or state.equipment_id is None:
        raise HTTPException(status_code=409, detail="La unidad debe estar dada de alta")
    if state.calibration_stage_id is not None:
        raise HTTPException(status_code=409, detail="La unidad ya tiene calibración asociada")
    if quotation_item_id is not None:
        quotation_item = db.get(QuotationItem, quotation_item_id)
        belongs_to_sale = quotation_item is not None and (
            quotation_item.quotation_id == order.quotation_id
            or (
                quotation_item.source_service_order_id == order.id
                and quotation_item.source_service_unit_id in {None, state.service_unit_id}
            )
        )
        decision = db.scalar(select(QuotationItemDecision).where(
            QuotationItemDecision.quotation_item_id == quotation_item_id,
            QuotationItemDecision.decision == "approved",
        ))
        if (
            quotation_item is None
            or not belongs_to_sale
            or quotation_item.operational_category != "calibration"
            or decision is None
        ):
            raise HTTPException(status_code=409, detail="La calibración con costo requiere partida comercial aprobada")
    else:
        _consume_authorization(db, authorization_id, expected_type="zero_cost_calibration",
                               actor_id=actor.id, service_order_id=order.id, unit_state_id=state.id)
    item = state.sale_order_item
    unit = db.get(ServiceUnit, state.service_unit_id)
    next_sequence = int(db.scalar(select(func.max(ServiceStage.sequence)).where(ServiceStage.service_unit_id == unit.id)) or 0) + 1
    stage = ServiceStage(service_unit_id=unit.id, sequence=next_sequence, category="calibration",
                         status="authorized", origin="commercial_quote" if quotation_item_id else "zero_cost_authorization",
                         quotation_item_id=quotation_item_id)
    db.add(stage); db.flush()
    state.calibration_stage_id = stage.id
    state.status = "calibration_pending"
    write_audit_log(db, action="sale.calibration_added", entity="sale_unit_states", entity_id=state.id,
                    user_id=actor.id, new_values={"stage_id": stage.id, "quotation_item_id": quotation_item_id,
                                                   "authorization_id": authorization_id})
    db.commit()
    return sale_board(db, order.id)


def _pending_delivery_quantity(db: Session, sale_item_id: int) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(SaleDeliveryLine.quantity), 0)).join(SaleDelivery).where(
        SaleDeliveryLine.sale_order_item_id == sale_item_id,
        SaleDelivery.status.in_(OPEN_DELIVERY_STATUSES),
    )) or 0)


def create_delivery(db: Session, service_order_id: int, payload: SaleDeliveryCreate, *, actor: User):
    order = _active_sale_order(db, service_order_id)
    _ensure_advisor(order, actor)
    delivery = SaleDelivery(
        service_order_id=order.id, mode=payload.mode, status="prepared",
        courier_name=payload.courier_name, tracking_number=payload.tracking_number,
        shipped_on=payload.shipped_on, estimated_arrival_on=payload.estimated_arrival_on,
        technician_id=payload.technician_id, address_source=payload.address_source,
        delivery_address=(order.source_snapshot or {}).get("client", {}).get("address")
        if payload.address_source == "client" else payload.delivery_address,
        created_by_id=actor.id,
    )
    if payload.mode == "myc_technician":
        technician = db.get(User, payload.technician_id)
        if technician is None or not user_has_permission(technician, "service_orders.sales.deliver"):
            raise HTTPException(status_code=422, detail="Selecciona un técnico autorizado para entrega")
        delivery.status = "technician_requested"
    db.add(delivery); db.flush()
    seen_units: set[int] = set()
    for line in payload.lines:
        item = db.get(SaleOrderItem, line.sale_order_item_id)
        if item is None or item.service_order_id != order.id:
            raise HTTPException(status_code=404, detail="Partida de entrega no encontrada")
        state = None
        if item.requires_individual_identification:
            if line.sale_unit_state_id is None or line.quantity != 1 or line.sale_unit_state_id in seen_units:
                raise HTTPException(status_code=422, detail="Cada unidad serializada debe seleccionarse una sola vez")
            seen_units.add(line.sale_unit_state_id)
            state = db.get(SaleUnitState, line.sale_unit_state_id)
            if state is None or state.sale_order_item_id != item.id or state.status != "ready_for_delivery":
                raise HTTPException(status_code=409, detail="La unidad no está liberada para entrega")
            if not _calibration_closed(db, state):
                raise HTTPException(status_code=409, detail="La calibración obligatoria sigue pendiente")
            state.status = "delivery_prepared"
        else:
            available = item.arrived_quantity - item.delivered_quantity - _pending_delivery_quantity(db, item.id)
            if line.quantity > available:
                raise HTTPException(status_code=409, detail="La cantidad excede el saldo arribado disponible")
        db.add(SaleDeliveryLine(delivery_id=delivery.id, sale_order_item_id=item.id,
                                sale_unit_state_id=state.id if state else None, quantity=line.quantity))
    if delivery.mode == "myc_technician":
        db.add(Notification(recipient_user_id=delivery.technician_id, actor_user_id=actor.id,
                            notification_type="sale_delivery_assigned",
                            event_key=f"sale-delivery:{delivery.id}:assigned",
                            title="Nueva entrega de Venta asignada",
                            body=f"Acepta y agenda la entrega del ETS {order.folio}.",
                            entity_type="service_order", entity_id=order.id,
                            metadata_json={"delivery_id": delivery.id, "frontend_path": "/dashboard#servicios"}))
    write_audit_log(db, action="sale.delivery_created", entity="sale_deliveries", entity_id=delivery.id,
                    user_id=actor.id, new_values={"mode": delivery.mode, "status": delivery.status})
    db.commit()
    return sale_board(db, order.id)


def dispatch_delivery(db: Session, service_order_id: int, delivery_id: int, *, actor: User):
    order = _active_sale_order(db, service_order_id); _ensure_advisor(order, actor)
    delivery = db.get(SaleDelivery, delivery_id)
    if delivery is None or delivery.service_order_id != order.id or delivery.status != "prepared":
        raise HTTPException(status_code=409, detail="La entrega no puede despacharse")
    if delivery.mode == "courier":
        delivery.status = "sent"
    elif delivery.mode == "client_pickup":
        delivery.status = "pickup_notified"
        memberships = db.scalars(select(ClientPortalMembership).where(
            ClientPortalMembership.client_id == order.client_id,
            ClientPortalMembership.status == "active",
        )).all()
        for membership in memberships:
            db.add(Notification(recipient_user_id=membership.user_id, actor_user_id=actor.id,
                                notification_type="sale_ready_for_pickup",
                                event_key=f"sale-delivery:{delivery.id}:pickup:{membership.user_id}",
                                title="Pedido listo para recolección",
                                body=f"La Venta {order.folio} está lista para recolección.",
                                entity_type="service_order", entity_id=order.id,
                                metadata_json={"delivery_id": delivery.id, "frontend_path": "/portal/servicios"}))
    else:
        raise HTTPException(status_code=409, detail="La entrega por técnico se atiende desde su solicitud")
    write_audit_log(db, action="sale.delivery_dispatched", entity="sale_deliveries", entity_id=delivery.id,
                    user_id=actor.id, new_values={"status": delivery.status})
    db.commit(); return sale_board(db, order.id)


def accept_technician_delivery(db: Session, service_order_id: int, delivery_id: int,
                               payload: SaleDeliveryAccept, *, actor: User):
    _active_sale_order(db, service_order_id)
    if not user_has_permission(actor, "service_orders.sales.deliver"):
        raise HTTPException(status_code=403, detail="Permiso de entrega insuficiente")
    delivery = db.get(SaleDelivery, delivery_id)
    if delivery is None or delivery.service_order_id != service_order_id or delivery.technician_id != actor.id:
        raise HTTPException(status_code=404, detail="Solicitud de entrega no asignada")
    if delivery.status != "technician_requested":
        raise HTTPException(status_code=409, detail="La solicitud ya fue atendida")
    delivery.status = "scheduled"; delivery.accepted_at = _now(); delivery.scheduled_for = payload.scheduled_for
    write_audit_log(db, action="sale.delivery_accepted", entity="sale_deliveries", entity_id=delivery.id,
                    user_id=actor.id, new_values={"scheduled_for": payload.scheduled_for.isoformat()})
    db.commit(); return sale_board(db, service_order_id)


def report_courier_delivery(db: Session, service_order_id: int, delivery_id: int, *, actor: User):
    order = _active_sale_order(db, service_order_id); _ensure_advisor(order, actor)
    delivery = db.get(SaleDelivery, delivery_id)
    if delivery is None or delivery.service_order_id != order.id or delivery.mode != "courier" or delivery.status != "sent":
        raise HTTPException(status_code=409, detail="El envío no puede confirmarse")
    delivery.status = "delivery_reported"
    write_audit_log(db, action="sale.courier_delivery_reported", entity="sale_deliveries", entity_id=delivery.id,
                    user_id=actor.id, new_values={"status": delivery.status})
    db.commit(); return sale_board(db, order.id)


def confirm_delivery(db: Session, service_order_id: int, delivery_id: int, payload: SaleDeliveryConfirm,
                     *, actor: User, portal_client_id: int | None = None):
    order = _active_sale_order(db, service_order_id)
    delivery = db.get(SaleDelivery, delivery_id)
    if delivery is None or delivery.service_order_id != order.id:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    if portal_client_id is not None and portal_client_id != order.client_id:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    if portal_client_id is None and not (
        user_has_permission(actor, "service_orders.sales.manage")
        or (delivery.technician_id == actor.id and user_has_permission(actor, "service_orders.sales.deliver"))
    ):
        raise HTTPException(status_code=403, detail="No puedes confirmar esta recepción")
    if delivery.status not in {"pickup_notified", "scheduled", "delivery_reported"}:
        raise HTTPException(status_code=409, detail="La entrega aún no puede recibirse")
    if delivery.mode in {"courier", "client_pickup"} and not payload.signature_data_url:
        raise HTTPException(status_code=422, detail="Paquetería y recolección requieren firma del receptor")
    if delivery.mode == "myc_technician" and not payload.signature_data_url:
        if payload.evidence is None or payload.evidence.type != "technician_attestation":
            raise HTTPException(status_code=422, detail="La entrega técnica requiere firma o atestación del técnico")
    now = _now(); delivery.status = "delivered"; delivery.receiver_name = payload.receiver_name
    delivery.received_at = now; delivery.received_by_user_id = actor.id
    delivery.signature_data_url = payload.signature_data_url
    delivery.evidence = payload.evidence.model_dump(exclude_none=True) if payload.evidence else None
    delivery.confirmed_by_id = actor.id
    for line in delivery.lines:
        item = db.get(SaleOrderItem, line.sale_order_item_id)
        if line.sale_unit_state_id:
            db.get(SaleUnitState, line.sale_unit_state_id).status = "delivered"
        else:
            item.delivered_quantity += line.quantity
    _refresh_statuses(db, order.id)
    write_audit_log(db, action="sale.delivery_confirmed", entity="sale_deliveries", entity_id=delivery.id,
                    user_id=actor.id, new_values={"receiver": payload.receiver_name, "received_at": now.isoformat(),
                                                   "mode": delivery.mode, "has_signature": bool(payload.signature_data_url),
                                                   "has_evidence": bool(payload.evidence)})
    db.commit(); return sale_board(db, order.id)


def close_sale(db: Session, service_order_id: int, *, actor: User):
    order = _active_sale_order(db, service_order_id); _ensure_advisor(order, actor)
    blockers = sale_blockers(db, order.id)
    if blockers:
        raise HTTPException(status_code=409, detail={"message": "La Venta no puede cerrarse", "blockers": blockers})
    previous = order.status
    for item in order.items:
        if item.operational_category == "sale":
            item.status = "completed"
    has_open_non_sale_items = bool(db.scalar(select(ServiceOrderItem.id).where(
        ServiceOrderItem.service_order_id == order.id,
        ServiceOrderItem.is_active.is_(True),
        or_(ServiceOrderItem.operational_category.is_(None), ServiceOrderItem.operational_category != "sale"),
        ServiceOrderItem.status.not_in({"completed", "cancelled"}),
    ).limit(1)))
    if not has_open_non_sale_items:
        order.status = "closed"
        order.closed_at = _now().date()
    action = "sale.completed" if has_open_non_sale_items else "sale.closed"
    write_audit_log(db, action=action, entity="service_orders", entity_id=order.id,
                    user_id=actor.id, previous_values={"status": previous},
                    new_values={"status": order.status, "mixed_ets": has_open_non_sale_items})
    db.commit(); return sale_board_closed(db, order.id)


def sale_board_closed(db: Session, service_order_id: int) -> dict:
    order = db.get(ServiceOrder, service_order_id)
    blockers = sale_blockers(db, service_order_id)
    return {"service_order_id": order.id, "status": order.status,
            "items": list(db.scalars(_sale_item_query(order.id)).all()),
            "deliveries": list(db.scalars(_delivery_query(order.id)).all()),
            "authorizations": list(db.scalars(_authorization_query(order.id)).all()),
            "blockers": blockers, "can_close": not blockers}


def delivery_note_pdf(db: Session, service_order_id: int, delivery_id: int) -> tuple[bytes, str]:
    order = db.get(ServiceOrder, service_order_id)
    delivery = db.scalar(select(SaleDelivery).where(
        SaleDelivery.id == delivery_id, SaleDelivery.service_order_id == service_order_id,
    ).options(selectinload(SaleDelivery.lines)))
    if order is None or delivery is None:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    rows = []
    for line in delivery.lines:
        item = db.get(SaleOrderItem, line.sale_order_item_id)
        service_item = db.get(ServiceOrderItem, item.service_order_item_id)
        unit = db.get(SaleUnitState, line.sale_unit_state_id) if line.sale_unit_state_id else None
        rows.append(
            f"<tr><td>{escape(str(service_item.service_name), quote=True)}</td>"
            f"<td>{escape(str(line.quantity), quote=True)}</td>"
            f"<td>{escape(str(unit.serial_number if unit and unit.serial_number else '-'), quote=True)}</td></tr>"
        )
    html = f"""<html><body style='font-family:sans-serif'><h1>Nota de entrega</h1>
    <p><strong>ETS:</strong> {escape(str(order.folio), quote=True)}</p><p><strong>Modalidad:</strong> {escape(str(delivery.mode), quote=True)}</p>
    <table style='width:100%;border-collapse:collapse' border='1'><tr><th>Concepto</th><th>Cantidad</th><th>Serie</th></tr>{''.join(rows)}</table>
    <p>Receptor: {escape(str(delivery.receiver_name or 'Pendiente'), quote=True)} &nbsp; Fecha: {escape(str(delivery.received_at or 'Pendiente'), quote=True)}</p></body></html>"""
    return HTML(string=html).write_pdf(), f"{order.folio}-NOTA-ENTREGA-{delivery.id}.pdf"
