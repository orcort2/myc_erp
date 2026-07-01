from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.folios import FolioRequest, generate_folio
from app.models.client import Client
from app.models.quotation import Quotation
from app.models.service_order import ServiceOrder, ServiceOrderItem
from app.models.user import User
from app.schemas.service_order import (
    ServiceOrderCreate,
    ServiceOrderStatusChange,
    ServiceOrderUpdate,
)
from app.services.audit_logs import write_audit_log


TERMINAL_STATUSES = {"closed", "cancelled"}
ALLOWED_TRANSITIONS = {
    "scheduled": {"confirmed", "cancelled"},
    "confirmed": {"called", "in_progress", "cancelled"},
    "called": {"in_progress", "cancelled"},
    "in_progress": {"technical_review", "capture", "cancelled"},
    "technical_review": {"capture", "cancelled"},
    "capture": {"quality_review", "cancelled"},
    "quality_review": {"pending_payment", "released", "cancelled"},
    "pending_payment": {"released", "cancelled"},
    "released": {"closed"},
    "closed": set(),
    "cancelled": set(),
}


def _json_safe(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _ensure_active_client(db: Session, client_id: int) -> None:
    exists = db.scalar(
        select(Client.id).where(Client.id == client_id, Client.is_active.is_(True))
    )
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )


def _ensure_active_user(db: Session, user_id: int | None, label: str) -> None:
    if user_id is None:
        return
    exists = db.scalar(
        select(User.id).where(User.id == user_id, User.is_active.is_(True))
    )
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{label} no encontrado",
        )


def _get_active_quotation(db: Session, quotation_id: int | None) -> Quotation | None:
    if quotation_id is None:
        return None
    quotation = db.scalar(
        select(Quotation)
        .where(Quotation.id == quotation_id, Quotation.is_active.is_(True))
        .options(selectinload(Quotation.items))
    )
    if quotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotizacion no encontrada",
        )
    return quotation


def _next_service_order_folio(db: Session, issued_on: date) -> str:
    prefix = f"OSMYC-{issued_on:%y}-{issued_on:%m}-"
    last_folio = db.scalar(
        select(ServiceOrder.folio)
        .where(ServiceOrder.folio.like(f"{prefix}%"))
        .order_by(ServiceOrder.folio.desc())
        .limit(1)
    )
    sequence = 1 if not last_folio else int(last_folio.rsplit("-", 1)[-1]) + 1
    return generate_folio(
        FolioRequest(
            document_type="orden_servicio",
            issued_on=issued_on,
            sequence=sequence,
        )
    )


def _next_work_order_number(db: Session) -> int:
    last_number = db.scalar(select(func.max(ServiceOrder.work_order_number)))
    return max(int(last_number or 7000) + 1, 7001)


def list_service_orders(
    db: Session, *, include_inactive: bool = False
) -> list[ServiceOrder]:
    query = (
        select(ServiceOrder)
        .options(
            selectinload(ServiceOrder.items),
            selectinload(ServiceOrder.equipment),
            selectinload(ServiceOrder.client).selectinload(Client.contacts),
            selectinload(ServiceOrder.quotation),
            selectinload(ServiceOrder.certificates),
        )
        .order_by(ServiceOrder.created_at.desc())
    )
    if not include_inactive:
        query = query.where(ServiceOrder.is_active.is_(True))
    return list(db.scalars(query).all())


def get_service_order(db: Session, service_order_id: int) -> ServiceOrder:
    service_order = db.scalar(
        select(ServiceOrder)
        .where(ServiceOrder.id == service_order_id)
        .options(
            selectinload(ServiceOrder.items),
            selectinload(ServiceOrder.equipment),
            selectinload(ServiceOrder.client).selectinload(Client.contacts),
            selectinload(ServiceOrder.quotation),
            selectinload(ServiceOrder.certificates),
        )
    )
    if service_order is None or not service_order.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden de servicio no encontrada",
        )
    return service_order


def create_service_order(
    db: Session, payload: ServiceOrderCreate, *, user_id: int | None = None
) -> ServiceOrder:
    _ensure_active_client(db, payload.client_id)
    _ensure_active_user(db, payload.advisor_id, "Asesor")
    _ensure_active_user(db, payload.technician_id, "Tecnico")
    quotation = _get_active_quotation(db, payload.quotation_id)
    if quotation is not None and quotation.client_id != payload.client_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La cotizacion no pertenece al cliente indicado",
        )

    service_order = ServiceOrder(
        folio=_next_service_order_folio(db, date.today()),
        work_order_number=_next_work_order_number(db),
        client_id=payload.client_id,
        quotation_id=payload.quotation_id,
        advisor_id=payload.advisor_id,
        technician_id=payload.technician_id,
        agenda_date=payload.agenda_date,
        service_date=payload.service_date,
        total_equipment=payload.total_equipment,
        completed_equipment=payload.completed_equipment,
        requires_payment=payload.requires_payment,
        notes=payload.notes,
        status="scheduled",
    )
    if payload.items:
        service_order.items = [
            ServiceOrderItem(**item.model_dump()) for item in payload.items
        ]
    elif quotation is not None:
        service_order.items = [
            ServiceOrderItem(
                quotation_item_id=item.id,
                service_name=item.service_name,
                quantity=item.quantity,
                status="pending",
            )
            for item in quotation.items
            if item.is_active
        ]

    db.add(service_order)
    db.flush()
    write_audit_log(
        db,
        action="service_order.created",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        new_values={
            "folio": service_order.folio,
            "work_order_number": service_order.work_order_number,
            "client_id": service_order.client_id,
            "quotation_id": service_order.quotation_id,
            "status": service_order.status,
        },
    )
    db.commit()
    return get_service_order(db, service_order.id)


def update_service_order(
    db: Session,
    service_order_id: int,
    payload: ServiceOrderUpdate,
    *,
    user_id: int | None = None,
) -> ServiceOrder:
    service_order = get_service_order(db, service_order_id)
    if service_order.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede editar una orden de servicio cerrada o cancelada",
        )
    updates = payload.model_dump(exclude_unset=True)
    _ensure_active_user(db, updates.get("advisor_id"), "Asesor")
    _ensure_active_user(db, updates.get("technician_id"), "Tecnico")
    previous_values = {key: getattr(service_order, key) for key in updates}
    for key, value in updates.items():
        setattr(service_order, key, value)
    if (
        service_order.status == "scheduled"
        and service_order.agenda_date
        and service_order.service_date
        and service_order.technician_id
    ):
        previous_values.setdefault("status", "scheduled")
        updates["status"] = "confirmed"
        service_order.status = "confirmed"
    write_audit_log(
        db,
        action="service_order.updated",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        previous_values=_json_safe(previous_values),
        new_values=_json_safe(updates),
    )
    db.commit()
    return get_service_order(db, service_order.id)


def change_status(
    db: Session,
    service_order_id: int,
    new_status: str,
    payload: ServiceOrderStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> ServiceOrder:
    service_order = get_service_order(db, service_order_id)
    allowed = ALLOWED_TRANSITIONS.get(service_order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transicion no permitida: {service_order.status} -> {new_status}",
        )
    previous_status = service_order.status
    service_order.status = new_status
    if new_status == "closed":
        service_order.closed_at = date.today()
    write_audit_log(
        db,
        action=f"service_order.{new_status}",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": new_status},
        comment=payload.comment if payload else None,
    )
    db.commit()
    return get_service_order(db, service_order.id)


def close_service_order(
    db: Session,
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> ServiceOrder:
    return change_status(db, service_order_id, "closed", payload, user_id=user_id)


def deactivate_service_order(
    db: Session, service_order_id: int, *, user_id: int | None = None
) -> ServiceOrder:
    service_order = get_service_order(db, service_order_id)
    service_order.is_active = False
    service_order.deleted_at = datetime.now(timezone.utc)
    service_order.deleted_by = user_id
    write_audit_log(
        db,
        action="service_order.deactivated",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        previous_values={"is_active": True},
        new_values={"is_active": False},
    )
    db.commit()
    return service_order
