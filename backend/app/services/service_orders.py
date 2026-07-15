from datetime import date, datetime, timezone
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.folios import FolioRequest, generate_folio
from app.models.client import Client
from app.models.quotation import Quotation
from app.models.service_order import (
    ServiceOrder,
    ServiceOrderItem,
    ServiceWorkOrder,
    ServiceOrderSignatureCycle,
    ServiceOrderSignatureCycleWorkOrder,
)
from app.models.user import User
from app.schemas.service_order import (
    ServiceOrderCreate,
    ServiceOrderExceptionCreate,
    ServiceOrderStatusChange,
    ServiceOrderUpdate,
)
from app.services.audit_logs import write_audit_log



TERMINAL_STATUSES = {"closed", "cancelled"}
WORK_ORDER_EQUIPMENT_LIMIT = 10

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

STAGE_STATUS_MAP = {
    "info": "confirmed",
    "resumen": "confirmed",
    "equipment": "technical_review",
    "equipos": "technical_review",
    "field-sheet": "technical_review",
    "hojas": "technical_review",
    "capture": "capture",
    "captura": "capture",
    "quality": "quality_review",
    "calidad": "quality_review",
    "certificates": "quality_review",
    "certificados": "quality_review",
    "documents": "released",
    "documentos": "released",
    "billing": "pending_payment",
    "facturacion": "pending_payment",
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
        raise HTTPException(status_code=404, detail="Cliente no encontrado")


def _ensure_active_user(db: Session, user_id: int | None, label: str) -> None:
    if user_id is None:
        return
    exists = db.scalar(
        select(User.id).where(User.id == user_id, User.is_active.is_(True))
    )
    if exists is None:
        raise HTTPException(status_code=404, detail=f"{label} no encontrado")


def _get_active_quotation(db: Session, quotation_id: int | None) -> Quotation | None:
    if quotation_id is None:
        return None
    quotation = db.scalar(
        select(Quotation)
        .where(Quotation.id == quotation_id, Quotation.is_active.is_(True))
        .options(selectinload(Quotation.items))
    )
    if quotation is None:
        raise HTTPException(status_code=404, detail="Cotizacion no encontrada")
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
    legacy_last = db.scalar(select(func.max(ServiceOrder.work_order_number)))
    work_order_last = db.scalar(select(func.max(ServiceWorkOrder.work_order_number)))
    last_number = max(int(legacy_last or 7000), int(work_order_last or 7000))
    return max(last_number + 1, 7001)


def _count_expected_equipment(items: list[ServiceOrderItem]) -> int:
    total = sum(int(item.quantity or 0) for item in items if item.is_active)
    return max(total, 1)


def _build_work_orders_for_service_order(db: Session, service_order: ServiceOrder) -> None:
    expected_equipment = _count_expected_equipment(service_order.items)
    required_work_orders = max(ceil(expected_equipment / WORK_ORDER_EQUIPMENT_LIMIT), 1)

    next_number = _next_work_order_number(db)

    service_order.work_orders = [
        ServiceWorkOrder(
            service_order_id=service_order.id,
            work_order_number=next_number + index,
            sequence=index + 1,
            status="pending",
            equipment_limit=WORK_ORDER_EQUIPMENT_LIMIT,
            notes=None,
        )
        for index in range(required_work_orders)
    ]


def list_service_orders(
    db: Session, *, include_inactive: bool = False
) -> list[ServiceOrder]:
    query = (
        select(ServiceOrder)
        .options(
            selectinload(ServiceOrder.items),
            selectinload(ServiceOrder.work_orders).selectinload(
                ServiceWorkOrder.signature_cycle_links
            ),
            selectinload(ServiceOrder.equipment),
            selectinload(ServiceOrder.client).selectinload(Client.contacts),
            selectinload(ServiceOrder.quotation),
            selectinload(ServiceOrder.certificates),
            selectinload(ServiceOrder.advisor),
            selectinload(ServiceOrder.technician),
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
            selectinload(ServiceOrder.work_orders).selectinload(
                ServiceWorkOrder.signature_cycle_links
            ),
            selectinload(ServiceOrder.equipment),
            selectinload(ServiceOrder.client).selectinload(Client.contacts),
            selectinload(ServiceOrder.quotation),
            selectinload(ServiceOrder.certificates),
            selectinload(ServiceOrder.advisor),
            selectinload(ServiceOrder.technician),
        )
    )
    if service_order is None or not service_order.is_active:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada")
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

    primary_work_order_number = _next_work_order_number(db)

    service_order = ServiceOrder(
        folio=_next_service_order_folio(db, date.today()),
        work_order_number=primary_work_order_number,
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
                calibration_scope=item.calibration_scope,
                quantity=item.quantity,
                status="pending",
            )
            for item in quotation.items
            if item.is_active
        ]

    db.add(service_order)
    db.flush()

    _build_work_orders_for_service_order(db, service_order)
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
            "work_orders": [
                {
                    "id": work_order.id,
                    "work_order_number": work_order.work_order_number,
                    "sequence": work_order.sequence,
                    "equipment_limit": work_order.equipment_limit,
                }
                for work_order in service_order.work_orders
            ],
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
    signature_fields = [
        (
            "technician_signature_data_url",
            "technician_signed_at",
        ),
        (
            "client_received_signature_data_url",
            "client_received_signed_at",
        ),
        (
            "client_acceptance_signature_data_url",
            "client_acceptance_signed_at",
        ),
    ]

    for signature_field, signed_at_field in signature_fields:
        if signature_field in updates:
            updates[signed_at_field] = (
                datetime.now(timezone.utc)
                if updates[signature_field]
                else None
            )
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

def confirm_signature_cycle(
    db: Session,
    service_order_id: int,
    *,
    user_id: int | None = None,
) -> ServiceOrder:
    service_order = get_service_order(db, service_order_id)

    required_signature_fields = {
        "technician_signature_data_url": service_order.technician_signature_data_url,
        "client_received_signature_data_url": (
            service_order.client_received_signature_data_url
        ),
        "client_acceptance_signature_data_url": (
            service_order.client_acceptance_signature_data_url
        ),
        "technician_signed_name": service_order.technician_signed_name,
        "client_received_signed_name": service_order.client_received_signed_name,
        "client_acceptance_signed_name": (
            service_order.client_acceptance_signed_name
        ),
        "technician_signed_at": service_order.technician_signed_at,
        "client_received_signed_at": service_order.client_received_signed_at,
        "client_acceptance_signed_at": (
            service_order.client_acceptance_signed_at
        ),
    }

    missing_fields = [
        field_name
        for field_name, field_value in required_signature_fields.items()
        if not field_value
    ]

    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No se pueden confirmar las firmas porque faltan datos: "
                + ", ".join(missing_fields)
            ),
        )

    active_work_orders = list(
        db.scalars(
            select(ServiceWorkOrder)
            .where(
                ServiceWorkOrder.service_order_id == service_order.id,
                ServiceWorkOrder.is_active.is_(True),
                ServiceWorkOrder.status != "cancelled",
            )
            .order_by(ServiceWorkOrder.sequence.asc())
        ).all()
    )

    if not active_work_orders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La orden de servicio no tiene órdenes de trabajo activas",
        )

    active_work_order_ids = [work_order.id for work_order in active_work_orders]

    already_signed_work_order_ids = set(
        db.scalars(
            select(ServiceOrderSignatureCycleWorkOrder.work_order_id).where(
                ServiceOrderSignatureCycleWorkOrder.work_order_id.in_(
                    active_work_order_ids
                ),
                ServiceOrderSignatureCycleWorkOrder.is_current.is_(True),
            )
        ).all()
    )

    pending_work_orders = [
        work_order
        for work_order in active_work_orders
        if work_order.id not in already_signed_work_order_ids
    ]

    if not pending_work_orders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Todas las órdenes de trabajo activas ya tienen una firma vigente"
            ),
        )

    last_cycle_number = db.scalar(
        select(func.max(ServiceOrderSignatureCycle.cycle_number)).where(
            ServiceOrderSignatureCycle.service_order_id == service_order.id
        )
    )

    next_cycle_number = int(last_cycle_number or 0) + 1
    confirmed_at = datetime.now(timezone.utc)

    trigger = "initial" if next_cycle_number == 1 else "additional_work_order"

    signature_cycle = ServiceOrderSignatureCycle(
        service_order_id=service_order.id,
        cycle_number=next_cycle_number,
        trigger=trigger,
        comment=None,
        status="confirmed",
        technician_signature_data_url=(
            service_order.technician_signature_data_url
        ),
        client_received_signature_data_url=(
            service_order.client_received_signature_data_url
        ),
        client_acceptance_signature_data_url=(
            service_order.client_acceptance_signature_data_url
        ),
        technician_signed_name=service_order.technician_signed_name,
        client_received_signed_name=(
            service_order.client_received_signed_name
        ),
        client_acceptance_signed_name=(
            service_order.client_acceptance_signed_name
        ),
        technician_signed_at=service_order.technician_signed_at,
        client_received_signed_at=service_order.client_received_signed_at,
        client_acceptance_signed_at=(
            service_order.client_acceptance_signed_at
        ),
        authorized_by_id=(
            user_id if trigger != "initial" else None
        ),
        authorization_comment=None,
        confirmed_at=confirmed_at,
    )

    db.add(signature_cycle)
    db.flush()

    assignment_type = (
        "initial"
        if next_cycle_number == 1
        else "additional_work_order"
    )

    signature_links = [
        ServiceOrderSignatureCycleWorkOrder(
            signature_cycle_id=signature_cycle.id,
            work_order_id=work_order.id,
            assignment_type=assignment_type,
            is_current=True,
            applied_at=confirmed_at,
        )
        for work_order in pending_work_orders
    ]

    db.add_all(signature_links)

    previous_signature_status = service_order.signature_status
    previous_cycle_number = service_order.signature_cycle_number

    service_order.signature_status = "confirmed"
    service_order.signature_cycle_number = next_cycle_number
    service_order.signatures_confirmed_at = confirmed_at
    service_order.signature_reopen_available = False
    service_order.signature_reopened_by_id = None
    service_order.signature_reopened_at = None
    service_order.signature_reopen_source = None

    write_audit_log(
        db,
        action="service_order.signatures_confirmed",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        previous_values={
            "signature_status": previous_signature_status,
            "signature_cycle_number": previous_cycle_number,
        },
        new_values={
            "signature_status": "confirmed",
            "signature_cycle_number": next_cycle_number,
            "signature_cycle_id": signature_cycle.id,
            "trigger": trigger,
            "work_orders": [
                {
                    "id": work_order.id,
                    "work_order_number": work_order.work_order_number,
                    "sequence": work_order.sequence,
                }
                for work_order in pending_work_orders
            ],
            "confirmed_at": confirmed_at.isoformat(),
        },
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


def register_service_order_exception(
    db: Session,
    service_order_id: int,
    payload: ServiceOrderExceptionCreate,
    *,
    user_id: int | None = None,
) -> ServiceOrder:
    service_order = get_service_order(db, service_order_id)
    source_stage = payload.source_stage.strip()
    target_stage = payload.target_stage.strip()
    target_status = STAGE_STATUS_MAP.get(target_stage.lower())
    previous_status = service_order.status

    if target_status and previous_status not in TERMINAL_STATUSES:
        service_order.status = target_status

    # A draft/pending invoice is still derived from this commercial source.
    # Emitted invoices are intentionally excluded by the invoice service.
    from app.services.invoices import resync_invoices_for_service_exception

    resync_invoices_for_service_exception(
        db,
        service_order.id,
        comment=payload.reason,
        user_id=user_id,
    )

    write_audit_log(
        db,
        action="service_order.exception_requested",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        previous_values={
            "status": previous_status,
            "source_stage": source_stage,
        },
        new_values={
            "status": service_order.status,
            "target_stage": target_stage,
            "target_status": target_status,
        },
        comment=payload.reason,
    )
    db.commit()
    return get_service_order(db, service_order.id)


def deactivate_service_order(
    db: Session, service_order_id: int, *, user_id: int | None = None
) -> ServiceOrder:
    service_order = get_service_order(db, service_order_id)
    service_order.is_active = False
    service_order.deleted_at = datetime.now(timezone.utc)
    service_order.deleted_by = user_id

    for work_order in service_order.work_orders:
        work_order.is_active = False
        work_order.status = "cancelled"
        work_order.deleted_at = service_order.deleted_at
        work_order.deleted_by = user_id

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
