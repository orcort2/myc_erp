from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.catalog_item import CatalogItem
from app.models.equipment import Equipment
from app.models.notification import Notification
from app.models.quotation import Quotation, QuotationItem
from app.models.quotation_service_change import QuotationServiceChangeRequest
from app.models.service_order import ServiceOrder, ServiceOrderItem
from app.models.user import User
from app.schemas.quotation_service_change import (
    QuotationServiceChangeCreate,
    QuotationServiceChangeReview,
)
from app.services.activity import publish_event
from app.services.audit_logs import write_audit_log
from app.services.auth import user_has_permission
from app.services.quotations import _build_operational_snapshot, _write_snapshot
from app.services.service_orders import _service_order_items_from_quotation


REQUEST_PERMISSION = "quotations.exceptions.request_change_service"
AUTHORIZE_PERMISSION = "quotations.exceptions.authorize_change_service"
APPLY_PERMISSION = "quotations.exceptions.apply_change_service"
INSPECT_PERMISSION = "quotations.exceptions.inspect_change_service"
SELF_AUTHORIZE_PERMISSION = "quotations.exceptions.self_authorize_change_service"
CAPABILITY = "quotation.change_service_type"

ACTIVE_STATUSES = {"pending_review", "information_required", "authorized"}
STATUS_LABELS = {
    "pending_review": "Pendiente de revisión",
    "information_required": "Información requerida",
    "authorized": "Disponible para aplicar",
    "applying": "Aplicando",
    "completed": "Completada",
    "rejected": "Rechazada",
    "blocked": "Bloqueada",
    "expired": "Vencida",
    "revoked": "Revocada",
    "cancelled": "Cancelada",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _require(user: User, permission: str) -> None:
    if not user_has_permission(user, permission):
        raise HTTPException(status_code=403, detail=f"Falta el permiso {permission}")


def _require_all(user: User, *permissions: str) -> None:
    for permission in permissions:
        _require(user, permission)


def _client_name(quotation: Quotation) -> str:
    client = quotation.client
    return (
        getattr(client, "commercial_name", None)
        or getattr(client, "legal_name", None)
        or "Cliente sin nombre"
    )


def _request_options():
    return (
        selectinload(QuotationServiceChangeRequest.quotation).selectinload(
            Quotation.client
        ),
        selectinload(QuotationServiceChangeRequest.quotation).selectinload(
            Quotation.items
        ),
        selectinload(QuotationServiceChangeRequest.service_order),
        selectinload(QuotationServiceChangeRequest.quotation_item),
        selectinload(QuotationServiceChangeRequest.current_catalog_item),
        selectinload(QuotationServiceChangeRequest.requested_catalog_item),
        selectinload(QuotationServiceChangeRequest.requester),
        selectinload(QuotationServiceChangeRequest.reviewer),
        selectinload(QuotationServiceChangeRequest.authorized_apply_user),
        selectinload(QuotationServiceChangeRequest.applied_by),
    )


def _load_quotation_context(
    db: Session, quotation_folio: str, *, lock: bool = False
) -> tuple[Quotation, ServiceOrder]:
    query = (
        select(Quotation)
        .where(
            Quotation.folio == quotation_folio,
            Quotation.is_active.is_(True),
        )
        .options(
            selectinload(Quotation.items),
            selectinload(Quotation.client),
        )
    )
    if lock:
        query = query.with_for_update()
    quotation = db.scalar(query)
    if quotation is None:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    service_order_query = select(ServiceOrder).where(
        ServiceOrder.quotation_id == quotation.id,
        ServiceOrder.is_active.is_(True),
    )
    if lock:
        service_order_query = service_order_query.with_for_update()
    service_order = db.scalar(service_order_query)
    if service_order is None:
        raise HTTPException(
            status_code=409,
            detail=f"La cotización {quotation.folio} todavía no tiene un ETS relacionado",
        )
    return quotation, service_order


def _equipment_count(db: Session, service_order_id: int) -> int:
    # Cualquier registro físico cuenta, incluso si fue cancelado o dado de baja lógica.
    return int(
        db.scalar(
            select(func.count(Equipment.id)).where(
                Equipment.service_order_id == service_order_id
            )
        )
        or 0
    )


def _validate_base_context(
    db: Session, quotation: Quotation, service_order: ServiceOrder
) -> int:
    if quotation.status != "accepted":
        raise HTTPException(
            status_code=409,
            detail=f"La cotización {quotation.folio} debe estar aprobada",
        )
    if service_order.quotation_id != quotation.id:
        raise HTTPException(
            status_code=409,
            detail="El ETS relacionado ya no pertenece a esta cotización",
        )
    equipment_count = _equipment_count(db, service_order.id)
    if equipment_count:
        raise HTTPException(
            status_code=409,
            detail=(
                f"No es posible cambiar el servicio porque el ETS "
                f"{service_order.folio} ya tiene equipos registrados. "
                "La excepción debe revisarse nuevamente."
            ),
        )
    return equipment_count


def _validate_catalog_item(item: CatalogItem | None) -> CatalogItem:
    if item is None or not item.is_active:
        raise HTTPException(status_code=422, detail="El nuevo servicio no está activo")
    if item.item_type != "service":
        raise HTTPException(
            status_code=422,
            detail="El concepto seleccionado no es un servicio vigente",
        )
    if not item.category or not item.commodity or not item.service_kind:
        raise HTTPException(
            status_code=422,
            detail="El servicio no tiene configuración operativa suficiente",
        )
    if item.category.lower() in {"calibracion", "calibración"} and not item.calibration_scope:
        raise HTTPException(
            status_code=422,
            detail="El servicio no tiene una regla válida de acreditación o trazabilidad",
        )
    return item


def _service_snapshot(item: CatalogItem) -> dict:
    return {
        "catalog_item_id": item.id,
        "internal_key": item.internal_key,
        "name": item.name,
        "category": item.category,
        "commodity": item.commodity,
        "service_kind": item.service_kind,
        "calibration_scope": item.calibration_scope,
        "expected_certificate_master_id": item.expected_certificate_master_id,
        "tax_object": item.tax_object,
        "tax_rate": str(item.tax_rate),
        "price_mxn": str(item.final_price_mxn),
    }


def _impact(quotation_item: QuotationItem, requested: CatalogItem) -> dict:
    fields = {
        "price": Decimal(quotation_item.unit_price) != Decimal(requested.final_price_mxn),
        "tax_object": quotation_item.tax_object != requested.tax_object,
        "tax_rate": Decimal(quotation_item.tax_rate) != Decimal(requested.tax_rate),
        "category": quotation_item.commodity != requested.commodity,
        "accreditation": quotation_item.calibration_scope != requested.calibration_scope,
        "template": (
            (quotation_item.operational_snapshot or {}).get(
                "expected_certificate_master_id"
            )
            != requested.expected_certificate_master_id
        ),
    }
    commercial = any(fields[key] for key in ("price", "tax_object", "tax_rate"))
    return {
        "changed_fields": [key for key, changed in fields.items() if changed],
        "commercial_changes_required": commercial,
        "message": (
            "Requiere una excepción comercial más amplia; precio o impuestos cambiarían."
            if commercial
            else "Sólo cambia la configuración técnica autorizada del servicio."
        ),
    }


def _next_folio(db: Session, now: datetime) -> str:
    prefix = f"EXV-{now:%Y}-"
    last = db.scalar(
        select(QuotationServiceChangeRequest.folio)
        .where(QuotationServiceChangeRequest.folio.like(f"{prefix}%"))
        .order_by(QuotationServiceChangeRequest.folio.desc())
        .limit(1)
    )
    sequence = 1 if not last else int(last.rsplit("-", 1)[-1]) + 1
    return f"{prefix}{sequence:05d}"


def _notify(
    db: Session,
    *,
    recipient_id: int,
    actor_id: int | None,
    notification_type: str,
    title: str,
    body: str,
    quotation: Quotation,
    event_message_id: int,
    exception_folio: str,
) -> None:
    existing = db.scalar(
        select(Notification.id).where(
            Notification.recipient_user_id == recipient_id,
            Notification.notification_type == notification_type,
            Notification.activity_message_id == event_message_id,
        )
    )
    if existing is not None:
        return
    db.add(
        Notification(
            recipient_user_id=recipient_id,
            actor_user_id=actor_id,
            notification_type=notification_type,
            title=title,
            body=body,
            entity_type="quotation",
            entity_id=quotation.id,
            activity_message_id=event_message_id,
            priority="high",
            metadata_json={
                "exception_folio": exception_folio,
                "quotation_folio": quotation.folio,
                "frontend_path": (
                    f"/dashboard?quotation_folio={quotation.folio}"
                    f"&exception_folio={exception_folio}#cotizaciones"
                ),
            },
        )
    )


def _reviewer_ids(db: Session, requester_id: int) -> list[int]:
    users = db.scalars(
        select(User)
        .where(User.is_active.is_(True))
        .options(selectinload(User.roles))
    ).all()
    return [
        user.id
        for user in users
        if user.id != requester_id and user_has_permission(user, AUTHORIZE_PERMISSION)
    ]


def _resource(
    db: Session, request: QuotationServiceChangeRequest, user: User
) -> dict:
    equipment_count = _equipment_count(db, request.service_order_id)
    expires_at = request.expires_at
    expired = bool(
        request.status == "authorized"
        and expires_at is not None
        and _as_utc(expires_at) <= _now()
    )
    status_value = "expired" if expired else request.status
    can_apply = (
        status_value == "authorized"
        and request.authorized_apply_user_id == user.id
        and user_has_permission(user, APPLY_PERMISSION)
        and equipment_count == 0
    )
    return {
        "folio": request.folio,
        "status": status_value,
        "status_label": STATUS_LABELS.get(status_value, status_value),
        "capability": request.capability,
        "quotation_folio": request.quotation.folio,
        "service_order_folio": request.service_order.folio,
        "client_name": _client_name(request.quotation),
        "quotation_line_number": next(
            (
                index
                for index, item in enumerate(
                    sorted(
                        (
                            item
                            for item in request.quotation.items
                            if item.is_active is not False
                        ),
                        key=lambda item: item.id,
                    ),
                    start=1,
                )
                if item.id == request.quotation_item_id
            ),
            0,
        ),
        "current_service_key": request.current_service_snapshot.get("internal_key"),
        "requested_service_key": request.requested_service_snapshot["internal_key"],
        "current_service_name": request.current_service_snapshot["name"],
        "requested_service_name": request.requested_service_snapshot["name"],
        "requester_name": request.requester.full_name,
        "reviewer_name": request.reviewer.full_name if request.reviewer else None,
        "authorized_apply_user_name": (
            request.authorized_apply_user.full_name
            if request.authorized_apply_user
            else None
        ),
        "service_order_status": request.service_order.status,
        "equipment_count": equipment_count,
        "reason": request.reason,
        "observation": request.observation,
        "review_comment": request.review_comment,
        "block_reason": request.block_reason,
        "impact": request.impact_snapshot,
        "requested_at": request.requested_at,
        "reviewed_at": request.reviewed_at,
        "expires_at": request.expires_at,
        "applied_at": request.applied_at,
        "can_apply": can_apply,
        "can_review": user_has_permission(user, AUTHORIZE_PERMISSION),
        "can_request": user_has_permission(user, REQUEST_PERMISSION),
    }


def _get_request(
    db: Session, exception_folio: str, *, lock: bool = False
) -> QuotationServiceChangeRequest:
    query = (
        select(QuotationServiceChangeRequest)
        .where(QuotationServiceChangeRequest.folio == exception_folio)
        .options(*_request_options())
    )
    if lock:
        query = query.with_for_update()
    request = db.scalar(query)
    if request is None:
        raise HTTPException(status_code=404, detail="Excepción no encontrada")
    return request


def list_requests(
    db: Session,
    user: User,
    *,
    quotation_folio: str | None = None,
) -> list[dict]:
    _require_all(
        user,
        INSPECT_PERMISSION,
        "quotations.read",
        "service_orders.read",
    )
    query = (
        select(QuotationServiceChangeRequest)
        .options(*_request_options())
        .order_by(QuotationServiceChangeRequest.requested_at.desc())
    )
    if quotation_folio:
        query = query.join(Quotation).where(Quotation.folio == quotation_folio)
    return [_resource(db, item, user) for item in db.scalars(query).unique().all()]


def quotation_context(
    db: Session,
    quotation_folio: str,
    user: User,
) -> dict:
    """Describe elegibilidad using only visible business references."""

    _require(user, "quotations.read")
    can_request = all(
        user_has_permission(user, permission)
        for permission in (
            REQUEST_PERMISSION,
            "quotations.update",
            "service_orders.read",
            "activity.create",
        )
    )
    quotation = db.scalar(
        select(Quotation)
        .where(
            Quotation.folio == quotation_folio,
            Quotation.is_active.is_(True),
        )
        .options(selectinload(Quotation.items), selectinload(Quotation.client))
    )
    if quotation is None:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    service_order = db.scalar(
        select(ServiceOrder).where(
            ServiceOrder.quotation_id == quotation.id,
            ServiceOrder.is_active.is_(True),
        )
    )
    reasons: list[str] = []
    if not can_request:
        reasons.append("No tienes permiso para solicitar esta excepción.")
    if quotation.status != "accepted":
        reasons.append("La cotización todavía no está aprobada.")
    if service_order is None:
        reasons.append("La cotización todavía no tiene un ETS relacionado.")
        equipment_count = 0
    else:
        equipment_count = _equipment_count(db, service_order.id)
        if equipment_count:
            reasons.append(
                f"El ETS {service_order.folio} ya tiene equipos registrados."
            )
    active = db.scalar(
        select(QuotationServiceChangeRequest)
        .where(
            QuotationServiceChangeRequest.quotation_id == quotation.id,
            QuotationServiceChangeRequest.status.in_(ACTIVE_STATUSES),
        )
        .options(*_request_options())
        .order_by(QuotationServiceChangeRequest.requested_at.desc())
    )
    return {
        "quotation_folio": quotation.folio,
        "service_order_folio": service_order.folio if service_order else None,
        "service_order_status": service_order.status if service_order else None,
        "equipment_count": equipment_count,
        "eligible": not reasons,
        "reason": " ".join(reasons) if reasons else None,
        "can_request": can_request,
        "can_review": user_has_permission(user, AUTHORIZE_PERMISSION),
        "can_apply": user_has_permission(user, APPLY_PERMISSION),
        "active_request": _resource(db, active, user) if active else None,
    }


def request_change(
    db: Session,
    quotation_folio: str,
    payload: QuotationServiceChangeCreate,
    user: User,
) -> dict:
    _require_all(
        user,
        REQUEST_PERMISSION,
        "quotations.read",
        "quotations.update",
        "service_orders.read",
        "activity.create",
    )
    quotation, service_order = _load_quotation_context(db, quotation_folio)
    _validate_base_context(db, quotation, service_order)
    active_items = sorted(
        (item for item in quotation.items if item.is_active),
        key=lambda item: item.id,
    )
    quotation_item = (
        active_items[payload.quotation_line_number - 1]
        if payload.quotation_line_number <= len(active_items)
        else None
    )
    if quotation_item is None or quotation_item.catalog_item_id is None:
        raise HTTPException(
            status_code=422,
            detail="Selecciona una partida vigente vinculada al catálogo",
        )
    requested = db.scalar(
        select(CatalogItem).where(
            CatalogItem.internal_key == payload.requested_service_key.strip(),
        )
    )
    if requested is not None and quotation_item.catalog_item_id == requested.id:
        raise HTTPException(
            status_code=422,
            detail="El nuevo servicio debe ser distinto del servicio actual",
        )
    current = _validate_catalog_item(db.get(CatalogItem, quotation_item.catalog_item_id))
    requested = _validate_catalog_item(requested)
    now = _now()
    active_scope_key = (
        f"{quotation.id}:{service_order.id}:{quotation_item.id}:"
        f"{current.id}:{requested.id}:{user.id}"
    )
    existing = db.scalar(
        select(QuotationServiceChangeRequest)
        .where(QuotationServiceChangeRequest.active_scope_key == active_scope_key)
        .options(*_request_options())
    )
    if existing is not None:
        if (
            existing.status == "authorized"
            and existing.expires_at is not None
            and _as_utc(existing.expires_at) <= now
        ):
            existing.status = "expired"
            existing.active_scope_key = None
            db.flush()
        else:
            return _resource(db, existing, user)
    request = QuotationServiceChangeRequest(
        folio=_next_folio(db, now),
        quotation_id=quotation.id,
        service_order_id=service_order.id,
        quotation_item_id=quotation_item.id,
        current_catalog_item_id=current.id,
        requested_catalog_item_id=requested.id,
        requester_id=user.id,
        status="pending_review",
        capability=CAPABILITY,
        active_scope_key=active_scope_key,
        reason=payload.reason.strip(),
        observation=payload.observation.strip() if payload.observation else None,
        current_service_snapshot=_service_snapshot(current),
        requested_service_snapshot=_service_snapshot(requested),
        impact_snapshot=_impact(quotation_item, requested),
        quotation_version_at_request=quotation.updated_at,
        requested_at=now,
    )
    try:
        db.add(request)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(QuotationServiceChangeRequest)
            .where(QuotationServiceChangeRequest.active_scope_key == active_scope_key)
            .options(*_request_options())
        )
        if existing is None:
            raise
        return _resource(db, existing, user)
    body = (
        f"{user.full_name} solicitó cambiar el tipo de servicio en "
        f"{quotation.folio}. Servicio actual: {current.name}. "
        f"Servicio solicitado: {requested.name}. La excepción {request.folio} "
        "fue enviada para autorización."
    )
    quotation_event = publish_event(
        db,
        entity_type="quotation",
        entity_id=quotation.id,
        event_code="quotation.service_change.requested",
        idempotency_key=f"{request.folio}:requested:quotation",
        body=body,
        actor_id=user.id,
        metadata={"exception_folio": request.folio, "service_order_folio": service_order.folio},
        related_entity_type="service_order",
        related_entity_id=service_order.id,
    )
    publish_event(
        db,
        entity_type="service_order",
        entity_id=service_order.id,
        event_code="quotation.service_change.requested",
        idempotency_key=f"{request.folio}:requested:service_order",
        body=body,
        actor_id=user.id,
        metadata={"exception_folio": request.folio, "quotation_folio": quotation.folio},
        related_entity_type="quotation",
        related_entity_id=quotation.id,
    )
    for reviewer_id in _reviewer_ids(db, user.id):
        _notify(
            db,
            recipient_id=reviewer_id,
            actor_id=user.id,
            notification_type="quotation_service_change_requested",
            title=f"Revisar excepción {request.folio}",
            body=f"{quotation.folio} · {service_order.folio} · {current.name} → {requested.name}",
            quotation=quotation,
            event_message_id=quotation_event.id,
            exception_folio=request.folio,
        )
    write_audit_log(
        db,
        action="quotation.service_change_requested",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user.id,
        new_values={
            "exception_folio": request.folio,
            "quotation_folio": quotation.folio,
            "service_order_folio": service_order.folio,
            "current_service": current.name,
            "requested_service": requested.name,
        },
    )
    db.commit()
    return _resource(db, _get_request(db, request.folio), user)


def review_request(
    db: Session,
    exception_folio: str,
    payload: QuotationServiceChangeReview,
    user: User,
) -> dict:
    _require_all(
        user,
        AUTHORIZE_PERMISSION,
        INSPECT_PERMISSION,
        "quotations.read",
        "service_orders.read",
        "activity.create",
    )
    request = _get_request(db, exception_folio, lock=True)
    if request.status not in {"pending_review", "information_required"}:
        raise HTTPException(status_code=409, detail="La solicitud ya fue revisada")
    if (
        request.requester_id == user.id
        and not user_has_permission(user, SELF_AUTHORIZE_PERMISSION)
    ):
        raise HTTPException(
            status_code=403,
            detail="El solicitante no puede autorizar su propia excepción",
        )
    now = _now()
    request.reviewer_id = user.id
    request.reviewed_at = now
    request.review_comment = payload.comment.strip() if payload.comment else None
    notification_type = "quotation_service_change_reviewed"
    if payload.decision == "request_information":
        request.status = "information_required"
        title = f"Información requerida para {request.folio}"
        body = request.review_comment or "El revisor solicitó información adicional."
    elif payload.decision == "reject":
        request.status = "rejected"
        request.active_scope_key = None
        title = f"Excepción {request.folio} rechazada"
        body = request.review_comment or "La solicitud de cambio fue rechazada."
    else:
        _validate_base_context(db, request.quotation, request.service_order)
        requested = _validate_catalog_item(request.requested_catalog_item)
        if request.impact_snapshot.get("commercial_changes_required"):
            raise HTTPException(
                status_code=409,
                detail=(
                    "El cambio modificaría precio o impuestos. "
                    "Se requiere una excepción comercial más amplia."
                ),
            )
        conflicting = db.scalar(
            select(QuotationServiceChangeRequest.id).where(
                QuotationServiceChangeRequest.quotation_id == request.quotation_id,
                QuotationServiceChangeRequest.status == "authorized",
                QuotationServiceChangeRequest.expires_at > now,
                QuotationServiceChangeRequest.id != request.id,
            )
        )
        if conflicting:
            raise HTTPException(
                status_code=409,
                detail="Ya existe otra capacidad activa para esta cotización",
            )
        apply_user_id = request.requester_id
        apply_user = db.get(User, apply_user_id)
        if apply_user is None or not apply_user.is_active:
            raise HTTPException(status_code=422, detail="Usuario aplicador no disponible")
        if not user_has_permission(apply_user, APPLY_PERMISSION):
            raise HTTPException(
                status_code=422,
                detail="El usuario aplicador no tiene permiso para aplicar la excepción",
            )
        request.status = "authorized"
        request.authorized_apply_user_id = apply_user_id
        request.expires_at = now + timedelta(hours=payload.validity_hours)
        title = f"Excepción {request.folio} autorizada"
        body = (
            f"Puedes aplicar una sola vez {requested.name} en "
            f"{request.quotation.folio} hasta {request.expires_at.isoformat()}."
        )
    event = publish_event(
        db,
        entity_type="quotation",
        entity_id=request.quotation_id,
        event_code=f"quotation.service_change.{request.status}",
        idempotency_key=f"{request.folio}:review:{request.status}",
        body=f"{title}. {body}",
        actor_id=user.id,
        metadata={"exception_folio": request.folio, "status": request.status},
        related_entity_type="service_order",
        related_entity_id=request.service_order_id,
    )
    publish_event(
        db,
        entity_type="service_order",
        entity_id=request.service_order_id,
        event_code=f"quotation.service_change.{request.status}",
        idempotency_key=f"{request.folio}:review:{request.status}:service_order",
        body=f"{title}. {body}",
        actor_id=user.id,
        metadata={"exception_folio": request.folio, "status": request.status},
        related_entity_type="quotation",
        related_entity_id=request.quotation_id,
    )
    _notify(
        db,
        recipient_id=request.requester_id,
        actor_id=user.id,
        notification_type=notification_type,
        title=title,
        body=body,
        quotation=request.quotation,
        event_message_id=event.id,
        exception_folio=request.folio,
    )
    if request.status == "authorized":
        _notify(
            db,
            recipient_id=request.requester_id,
            actor_id=user.id,
            notification_type="quotation_service_change_capability_available",
            title=f"Capacidad disponible: {request.folio}",
            body=(
                f"Puedes aplicar una sola vez {request.requested_service_snapshot['name']} "
                f"en {request.quotation.folio}."
            ),
            quotation=request.quotation,
            event_message_id=event.id,
            exception_folio=request.folio,
        )
        _notify(
            db,
            recipient_id=request.requester_id,
            actor_id=user.id,
            notification_type="quotation_service_change_expiring",
            title=f"Vigencia de {request.folio}",
            body=(
                "La capacidad temporal vencerá el "
                f"{request.expires_at.isoformat()}; después deberá revisarse nuevamente."
            ),
            quotation=request.quotation,
            event_message_id=event.id,
            exception_folio=request.folio,
        )
    write_audit_log(
        db,
        action=f"quotation.service_change_{request.status}",
        entity="quotations",
        entity_id=request.quotation_id,
        user_id=user.id,
        new_values={
            "exception_folio": request.folio,
            "status": request.status,
            "authorized_apply_user_id": request.authorized_apply_user_id,
            "expires_at": request.expires_at.isoformat() if request.expires_at else None,
        },
        comment=request.review_comment,
    )
    db.commit()
    return _resource(db, _get_request(db, request.folio), user)


def _block(
    db: Session,
    request: QuotationServiceChangeRequest,
    user: User,
    detail: str,
) -> None:
    request.status = "blocked"
    request.block_reason = detail
    request.active_scope_key = None
    event = publish_event(
        db,
        entity_type="quotation",
        entity_id=request.quotation_id,
        event_code="quotation.service_change.blocked",
        idempotency_key=f"{request.folio}:blocked",
        body=f"La excepción {request.folio} fue bloqueada. {detail}",
        actor_id=user.id,
        metadata={"exception_folio": request.folio, "reason": detail},
        related_entity_type="service_order",
        related_entity_id=request.service_order_id,
    )
    _notify(
        db,
        recipient_id=request.requester_id,
        actor_id=user.id,
        notification_type="quotation_service_change_blocked",
        title=f"Excepción {request.folio} bloqueada",
        body=detail,
        quotation=request.quotation,
        event_message_id=event.id,
        exception_folio=request.folio,
    )
    db.commit()


def apply_change(
    db: Session, exception_folio: str, user: User
) -> dict:
    _require_all(
        user,
        APPLY_PERMISSION,
        "quotations.read",
        "quotations.update",
        "service_orders.read",
        "activity.create",
    )
    request = _get_request(db, exception_folio, lock=True)
    if request.status == "completed":
        return _resource(db, request, user)
    if request.status != "authorized":
        raise HTTPException(status_code=409, detail="La capacidad no está disponible")
    if request.authorized_apply_user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="La capacidad fue concedida a otro usuario",
        )
    now = _now()
    if request.expires_at is None or _as_utc(request.expires_at) <= now:
        request.status = "expired"
        request.active_scope_key = None
        db.commit()
        raise HTTPException(status_code=409, detail="La capacidad autorizada venció")

    quotation = db.scalar(
        select(Quotation)
        .where(Quotation.id == request.quotation_id)
        .options(selectinload(Quotation.items), selectinload(Quotation.client))
        .with_for_update()
    )
    service_order = db.scalar(
        select(ServiceOrder)
        .where(ServiceOrder.id == request.service_order_id)
        .with_for_update()
    )
    if quotation is None or service_order is None:
        detail = "La cotización o el ETS autorizado ya no está disponible."
        _block(db, request, user, detail)
        raise HTTPException(status_code=409, detail=detail)
    try:
        _validate_base_context(db, quotation, service_order)
    except HTTPException as exc:
        _block(db, request, user, str(exc.detail))
        raise
    quotation_item = next(
        (item for item in quotation.items if item.id == request.quotation_item_id),
        None,
    )
    if (
        quotation_item is None
        or quotation_item.catalog_item_id != request.current_catalog_item_id
    ):
        detail = "El servicio actual ya no coincide con el servicio autorizado."
        _block(db, request, user, detail)
        raise HTTPException(status_code=409, detail=detail)
    if _as_utc(quotation.updated_at) != _as_utc(
        request.quotation_version_at_request
    ):
        detail = "La versión de la cotización cambió después de crear la solicitud."
        _block(db, request, user, detail)
        raise HTTPException(status_code=409, detail=detail)
    try:
        requested = _validate_catalog_item(
            db.get(CatalogItem, request.requested_catalog_item_id)
        )
    except HTTPException as exc:
        _block(db, request, user, str(exc.detail))
        raise
    if _impact(quotation_item, requested).get("commercial_changes_required"):
        detail = "El servicio requiere cambios comerciales no autorizados."
        _block(db, request, user, detail)
        raise HTTPException(status_code=409, detail=detail)

    before = _write_snapshot(
        db,
        quotation,
        reason=f"exception:{request.folio}:approved_before",
        user_id=user.id,
    )
    old_service_name = quotation_item.service_name
    quotation_item.catalog_item_id = requested.id
    quotation_item.service_name = requested.name
    quotation_item.description = requested.description
    quotation_item.unit = (
        requested.custom_internal_unit
        if requested.internal_unit == "other"
        else requested.internal_unit or requested.sat_unit
    )
    quotation_item.sat_key = requested.sat_key
    quotation_item.sat_unit = requested.sat_unit
    quotation_item.internal_unit = requested.internal_unit
    quotation_item.commodity = requested.commodity
    quotation_item.calibration_scope = requested.calibration_scope
    quotation_item.quotation_legend = requested.quotation_legend
    quotation_item.operational_snapshot = _build_operational_snapshot(db, requested)
    db.flush()

    existing_items = db.scalars(
        select(ServiceOrderItem).where(
            ServiceOrderItem.service_order_id == service_order.id,
            ServiceOrderItem.quotation_item_id == quotation_item.id,
        )
    ).all()
    for item in existing_items:
        db.delete(item)
    generated_items, _ = _service_order_items_from_quotation(db, quotation)
    for item in generated_items:
        if item.quotation_item_id == quotation_item.id:
            item.service_order_id = service_order.id
            db.add(item)
    db.flush()

    revision = _write_snapshot(
        db,
        quotation,
        reason=f"exception:{request.folio}:applied",
        user_id=user.id,
    )
    request.snapshot_id = revision.id
    request.status = "completed"
    request.applied_by_id = user.id
    request.applied_at = now
    request.consumed_at = now
    request.active_scope_key = None
    body = (
        f"Se aplicó la excepción {request.folio}. El servicio de "
        f"{quotation.folio} cambió de {old_service_name} a {requested.name}; "
        f"el mismo ETS {service_order.folio} fue sincronizado. "
        f"Snapshot previo #{before.snapshot_number}; revisión "
        f"#{revision.snapshot_number}."
    )
    quotation_event = publish_event(
        db,
        entity_type="quotation",
        entity_id=quotation.id,
        event_code="quotation.service_change.completed",
        idempotency_key=f"{request.folio}:completed:quotation",
        body=body,
        actor_id=user.id,
        metadata={
            "exception_folio": request.folio,
            "service_order_folio": service_order.folio,
            "snapshot_number": revision.snapshot_number,
        },
        related_entity_type="service_order",
        related_entity_id=service_order.id,
    )
    publish_event(
        db,
        entity_type="service_order",
        entity_id=service_order.id,
        event_code="quotation.service_change.completed",
        idempotency_key=f"{request.folio}:completed:service_order",
        body=body,
        actor_id=user.id,
        metadata={
            "exception_folio": request.folio,
            "quotation_folio": quotation.folio,
        },
        related_entity_type="quotation",
        related_entity_id=quotation.id,
    )
    _notify(
        db,
        recipient_id=request.requester_id,
        actor_id=user.id,
        notification_type="quotation_service_change_completed",
        title=f"Excepción {request.folio} completada",
        body=f"{quotation.folio} y {service_order.folio} ya muestran {requested.name}.",
        quotation=quotation,
        event_message_id=quotation_event.id,
        exception_folio=request.folio,
    )
    write_audit_log(
        db,
        action="quotation.service_change_completed",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user.id,
        previous_values={
            "service": request.current_service_snapshot,
            "service_order_folio": service_order.folio,
        },
        new_values={
            "service": request.requested_service_snapshot,
            "exception_folio": request.folio,
            "snapshot_number": revision.snapshot_number,
        },
    )
    db.commit()
    return _resource(db, _get_request(db, request.folio), user)
