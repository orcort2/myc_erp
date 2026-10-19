from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.catalog_item import CatalogItem
from app.models.notification import Notification
from app.models.quotation import Quotation, QuotationSnapshot
from app.models.quotation_acceptance import QuotationAcceptance
from app.models.quotation_service_change import QuotationServiceChangeRequest
from app.models.service_order import ServiceOrder
from app.models.user import User
from app.schemas.quotation_service_change import (
    QuotationServiceChangeCreate,
    QuotationServiceChangeReview,
    QuotationUnlockApply,
)
from app.services.activity import publish_event
from app.services.audit_logs import write_audit_log
from app.services.auth import user_has_permission
from app.services.quotation_signing_authority import invalidate_document_links
from app.services.service_order_archives import archive_service_order
from app.services.service_order_rebuilds import can_physically_rebuild_service_order


REQUEST_PERMISSION = "quotations.exceptions.request_unlock"
AUTHORIZE_PERMISSION = "quotations.exceptions.authorize_unlock"
APPLY_PERMISSION = "quotations.exceptions.apply_unlock"
INSPECT_PERMISSION = "quotations.exceptions.inspect"
REBUILD_PERMISSION = "quotations.exceptions.rebuild_empty_service_order"
SELF_AUTHORIZE_PERMISSION = "quotations.exceptions.self_authorize_unlock"
CAPABILITY = "quotation.controlled_unlock"
DEFAULT_UNLOCK_VALIDITY_HOURS = 72
ACTIVE_STATUSES = {"pending_review", "information_required", "authorized"}
STATUS_LABELS = {
    "pending_review": "Pendiente de revisión",
    "information_required": "Información requerida",
    "authorized": "Desbloqueo disponible",
    "completed": "Completada",
    "rejected": "Rechazada",
    "blocked": "Bloqueada por dependencias",
    "expired": "Vencida",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _require(user: User, permission: str) -> None:
    if not user_has_permission(user, permission):
        raise HTTPException(status_code=403, detail=f"Falta el permiso {permission}")


def _client_name(quotation: Quotation) -> str:
    return (
        getattr(quotation.client, "commercial_name", None)
        or getattr(quotation.client, "legal_name", None)
        or "Cliente sin nombre"
    )


def _request_options():
    return (
        selectinload(QuotationServiceChangeRequest.quotation).selectinload(Quotation.client),
        selectinload(QuotationServiceChangeRequest.quotation).selectinload(Quotation.items),
        selectinload(QuotationServiceChangeRequest.service_order),
        selectinload(QuotationServiceChangeRequest.requester),
        selectinload(QuotationServiceChangeRequest.reviewer),
        selectinload(QuotationServiceChangeRequest.authorized_apply_user),
    )


def _load_quotation(
    db: Session, quotation_folio: str, *, lock: bool = False
) -> Quotation:
    query = (
        select(Quotation)
        .where(Quotation.folio == quotation_folio, Quotation.is_active.is_(True))
        .options(selectinload(Quotation.items), selectinload(Quotation.client))
    )
    if lock:
        query = query.with_for_update()
    quotation = db.scalar(query)
    if quotation is None:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return quotation


def _related_service_order(
    db: Session, quotation: Quotation, *, lock: bool = False
) -> ServiceOrder:
    query = select(ServiceOrder).where(
        ServiceOrder.quotation_id == quotation.id,
        ServiceOrder.is_active.is_(True),
    )
    if lock:
        query = query.with_for_update()
    order = db.scalar(query)
    if order is None:
        raise HTTPException(
            status_code=409,
            detail=f"La cotización {quotation.folio} no tiene un ETS relacionado",
        )
    return order


def _latest_snapshot(db: Session, quotation_id: int) -> QuotationSnapshot:
    snapshot = db.scalar(
        select(QuotationSnapshot)
        .where(QuotationSnapshot.quotation_id == quotation_id)
        .order_by(QuotationSnapshot.snapshot_number.desc())
        .limit(1)
    )
    if snapshot is None:
        raise HTTPException(status_code=409, detail="La cotización no tiene revisión base")
    return snapshot


def _validate_base(
    db: Session, quotation: Quotation, order: ServiceOrder
) -> dict:
    if quotation.status != "accepted":
        raise HTTPException(status_code=409, detail="La cotización debe estar aprobada")
    if order.quotation_id != quotation.id:
        raise HTTPException(status_code=409, detail="El ETS ya no pertenece a la cotización")
    validation = can_physically_rebuild_service_order(db, order)
    if not validation.allowed:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"El ETS {order.folio} ya contiene información operativa",
                **validation.to_dict(),
            },
        )
    return validation.to_dict()


def _next_folio(db: Session, moment: datetime) -> str:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"quotation-unlock:{moment.year}"},
        )
    prefix = f"EXV-{moment:%Y}-"
    last = db.scalar(
        select(QuotationServiceChangeRequest.folio)
        .where(QuotationServiceChangeRequest.folio.like(f"{prefix}%"))
        .order_by(QuotationServiceChangeRequest.folio.desc())
        .limit(1)
    )
    return f"{prefix}{(1 if not last else int(last.rsplit('-', 1)[-1]) + 1):05d}"


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


def _notify(
    db: Session,
    *,
    request: QuotationServiceChangeRequest,
    recipient_id: int,
    actor_id: int | None,
    kind: str,
    title: str,
    body: str,
    event_id: int,
) -> None:
    if db.scalar(
        select(Notification.id).where(
            Notification.recipient_user_id == recipient_id,
            Notification.notification_type == kind,
            Notification.activity_message_id == event_id,
        )
    ):
        return
    db.add(
        Notification(
            recipient_user_id=recipient_id,
            actor_user_id=actor_id,
            notification_type=kind,
            title=title,
            body=body,
            entity_type="quotation",
            entity_id=request.quotation_id,
            activity_message_id=event_id,
            priority="high",
            metadata_json={
                "exception_folio": request.folio,
                "quotation_folio": request.quotation.folio,
                "frontend_path": (
                    f"/dashboard?quotation_folio={request.quotation.folio}"
                    f"&exception_folio={request.folio}#cotizaciones"
                ),
            },
        )
    )


def _reviewer_ids(db: Session, requester_id: int) -> list[int]:
    users = db.scalars(
        select(User).where(User.is_active.is_(True)).options(selectinload(User.roles))
    ).all()
    return [
        item.id
        for item in users
        if item.id != requester_id and user_has_permission(item, AUTHORIZE_PERMISSION)
    ]


def _resource(
    db: Session, request: QuotationServiceChangeRequest, user: User
) -> dict:
    expired = bool(
        request.status == "authorized"
        and request.expires_at
        and _as_utc(request.expires_at) <= _now()
    )
    status = "expired" if expired else request.status
    order = request.service_order
    dependencies: list[dict] = []
    if order is not None:
        dependencies = can_physically_rebuild_service_order(
            db, order
        ).to_dict()["dependencies"]
    return {
        "folio": request.folio,
        "status": status,
        "status_label": STATUS_LABELS.get(status, status),
        "capability": request.capability,
        "quotation_folio": request.quotation.folio,
        "service_order_folio": request.service_order_folio_snapshot,
        "client_name": _client_name(request.quotation),
        "requester_name": request.requester.full_name,
        "reviewer_name": request.reviewer.full_name if request.reviewer else None,
        "authorized_apply_user_name": (
            request.authorized_apply_user.full_name
            if request.authorized_apply_user
            else None
        ),
        "service_order_status": order.status if order else "archivada",
        "reason": request.reason,
        "observation": request.observation,
        "review_comment": request.review_comment,
        "block_reason": request.block_reason,
        "base_snapshot_number": (
            request.snapshot.snapshot_number if request.snapshot else 0
        ),
        "impact": request.delta_snapshot or request.impact_snapshot or {},
        "dependencies": dependencies,
        "requested_at": request.requested_at,
        "reviewed_at": request.reviewed_at,
        "expires_at": request.expires_at,
        "applied_at": request.applied_at,
        "can_apply": (
            status == "authorized"
            and request.capability == CAPABILITY
            and request.authorized_apply_user_id == user.id
            and user_has_permission(user, APPLY_PERMISSION)
            and user_has_permission(user, REBUILD_PERMISSION)
        ),
        "can_review": user_has_permission(user, AUTHORIZE_PERMISSION),
        "can_request": user_has_permission(user, REQUEST_PERMISSION),
    }


def quotation_context(db: Session, quotation_folio: str, user: User) -> dict:
    _require(user, "quotations.read")
    quotation = _load_quotation(db, quotation_folio)
    order = db.scalar(
        select(ServiceOrder).where(
            ServiceOrder.quotation_id == quotation.id,
            ServiceOrder.is_active.is_(True),
        )
    )
    reasons: list[str] = []
    can_request = all(
        user_has_permission(user, permission)
        for permission in (
            REQUEST_PERMISSION,
            "quotations.update",
            "service_orders.read",
            "activity.create",
        )
    )
    if not can_request:
        reasons.append("No tienes permiso para solicitar el desbloqueo.")
    if quotation.status != "accepted":
        reasons.append("La cotización no está aprobada.")
    validation = None
    if order is None:
        reasons.append("La cotización no tiene un ETS relacionado.")
    else:
        validation = can_physically_rebuild_service_order(db, order).to_dict()
        reasons.extend(validation["blockers"])
    active = db.scalar(
        select(QuotationServiceChangeRequest)
        .where(
            QuotationServiceChangeRequest.quotation_id == quotation.id,
            QuotationServiceChangeRequest.capability == CAPABILITY,
            QuotationServiceChangeRequest.status.in_(ACTIVE_STATUSES),
        )
        .options(*_request_options())
        .order_by(QuotationServiceChangeRequest.requested_at.desc())
    )
    return {
        "quotation_folio": quotation.folio,
        "service_order_folio": order.folio if order else None,
        "service_order_status": order.status if order else None,
        "eligible": not reasons,
        "reason": " ".join(reasons) if reasons else None,
        "dependencies": validation["dependencies"] if validation else [],
        "can_request": can_request,
        "can_review": user_has_permission(user, AUTHORIZE_PERMISSION),
        "can_apply": user_has_permission(user, APPLY_PERMISSION),
        "active_request": _resource(db, active, user) if active else None,
    }


def list_requests(
    db: Session, user: User, *, quotation_folio: str | None = None
) -> list[dict]:
    _require(user, INSPECT_PERMISSION)
    query = (
        select(QuotationServiceChangeRequest)
        .options(*_request_options())
        .order_by(QuotationServiceChangeRequest.requested_at.desc())
    )
    if quotation_folio:
        query = query.join(Quotation).where(Quotation.folio == quotation_folio)
    return [_resource(db, item, user) for item in db.scalars(query).unique().all()]


def request_change(
    db: Session,
    quotation_folio: str,
    payload: QuotationServiceChangeCreate,
    user: User,
) -> dict:
    for permission in (
        REQUEST_PERMISSION,
        "quotations.read",
        "quotations.update",
        "service_orders.read",
        "activity.create",
    ):
        _require(user, permission)
    quotation = _load_quotation(db, quotation_folio, lock=True)
    order = _related_service_order(db, quotation, lock=True)
    validation = _validate_base(db, quotation, order)
    snapshot = _latest_snapshot(db, quotation.id)
    existing = db.scalar(
        select(QuotationServiceChangeRequest)
        .where(
            QuotationServiceChangeRequest.quotation_id == quotation.id,
            QuotationServiceChangeRequest.status.in_(ACTIVE_STATUSES),
        )
        .options(*_request_options())
    )
    if existing is not None:
        return _resource(db, existing, user)
    moment = _now()
    auto_authorize = all(
        user_has_permission(user, permission)
        for permission in (
            AUTHORIZE_PERMISSION,
            APPLY_PERMISSION,
            REBUILD_PERMISSION,
            INSPECT_PERMISSION,
            SELF_AUTHORIZE_PERMISSION,
        )
    )
    request = QuotationServiceChangeRequest(
        folio=_next_folio(db, moment),
        quotation_id=quotation.id,
        service_order_id=order.id,
        requester_id=user.id,
        snapshot_id=snapshot.id,
        status="authorized" if auto_authorize else "pending_review",
        capability=CAPABILITY,
        active_scope_key=f"{quotation.id}:{user.id}",
        reason=payload.reason.strip(),
        observation=payload.observation.strip() if payload.observation else None,
        current_service_snapshot={"items": snapshot.snapshot_data.get("items", [])},
        requested_service_snapshot={},
        impact_snapshot={"rebuild_validation": validation},
        service_order_folio_snapshot=order.folio,
        base_quotation_snapshot=snapshot.snapshot_data,
        quotation_version_at_request=quotation.updated_at,
        requested_at=moment,
        reviewer_id=user.id if auto_authorize else None,
        reviewed_at=moment if auto_authorize else None,
        review_comment=(
            "Autoautorización administrativa registrada por autoridad explícita."
            if auto_authorize
            else None
        ),
        authorized_apply_user_id=user.id if auto_authorize else None,
        expires_at=(
            moment + timedelta(hours=DEFAULT_UNLOCK_VALIDITY_HOURS)
            if auto_authorize
            else None
        ),
    )
    db.add(request)
    db.flush()
    body = (
        f"{user.full_name} solicitó desbloquear la cotización {quotation.folio}. "
        f"El ETS relacionado es {order.folio}."
    )
    event = publish_event(
        db,
        entity_type="quotation",
        entity_id=quotation.id,
        event_code="quotation.unlock.requested",
        idempotency_key=f"{request.folio}:requested",
        body=body,
        actor_id=user.id,
        metadata={"exception_folio": request.folio, "service_order_folio": order.folio},
    )
    if auto_authorize:
        authorized_event = publish_event(
            db,
            entity_type="quotation",
            entity_id=quotation.id,
            event_code="quotation.unlock.authorized",
            idempotency_key=f"{request.folio}:review:authorized",
            body=(
                f"{user.full_name} registró el motivo y desbloqueó directamente "
                f"la cotización {quotation.folio} con autoridad administrativa."
            ),
            actor_id=user.id,
            metadata={
                "exception_folio": request.folio,
                "status": request.status,
                "self_authorized": True,
            },
        )
        _notify(
            db,
            request=request,
            recipient_id=user.id,
            actor_id=user.id,
            kind="quotation_unlock_authorized",
            title=f"Cotización desbloqueada mediante {request.folio}",
            body=f"{quotation.folio} · {order.folio}",
            event_id=authorized_event.id,
        )
    else:
        for reviewer_id in _reviewer_ids(db, user.id):
            _notify(
                db,
                request=request,
                recipient_id=reviewer_id,
                actor_id=user.id,
                kind="quotation_unlock_requested",
                title=f"Revisar desbloqueo {request.folio}",
                body=f"{quotation.folio} · {order.folio}",
                event_id=event.id,
            )
    write_audit_log(
        db,
        action="quotation.unlock_requested",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user.id,
        new_values={
            "exception_folio": request.folio,
            "quotation_folio": quotation.folio,
            "service_order_folio": order.folio,
            "base_snapshot_number": snapshot.snapshot_number,
        },
    )
    if auto_authorize:
        write_audit_log(
            db,
            action="quotation.unlock_self_authorized",
            entity="quotations",
            entity_id=quotation.id,
            user_id=user.id,
            new_values={
                "exception_folio": request.folio,
                "quotation_folio": quotation.folio,
                "service_order_folio": order.folio,
                "validity_hours": DEFAULT_UNLOCK_VALIDITY_HOURS,
                "authority": SELF_AUTHORIZE_PERMISSION,
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
    for permission in (
        AUTHORIZE_PERMISSION,
        INSPECT_PERMISSION,
        "quotations.read",
        "service_orders.read",
        "activity.create",
    ):
        _require(user, permission)
    request = _get_request(db, exception_folio, lock=True)
    if request.status not in {"pending_review", "information_required"}:
        raise HTTPException(status_code=409, detail="La solicitud ya fue revisada")
    if (
        request.requester_id == user.id
        and not user_has_permission(user, SELF_AUTHORIZE_PERMISSION)
    ):
        raise HTTPException(status_code=403, detail="No puedes autorizar tu propia solicitud")
    request.reviewer_id = user.id
    request.reviewed_at = _now()
    request.review_comment = payload.comment.strip() if payload.comment else None
    if payload.decision == "request_information":
        request.status = "information_required"
        title = f"Información requerida para {request.folio}"
    elif payload.decision == "reject":
        request.status = "rejected"
        request.active_scope_key = None
        title = f"Desbloqueo {request.folio} rechazado"
    else:
        order = _related_service_order(db, request.quotation, lock=True)
        _validate_base(db, request.quotation, order)
        if _latest_snapshot(db, request.quotation_id).id != request.snapshot_id:
            raise HTTPException(status_code=409, detail="La revisión base de la cotización cambió")
        applicant = db.get(User, request.requester_id)
        if applicant is None or not user_has_permission(applicant, APPLY_PERMISSION):
            raise HTTPException(status_code=422, detail="El aplicador no tiene permiso")
        request.status = "authorized"
        request.authorized_apply_user_id = request.requester_id
        request.expires_at = _now() + timedelta(hours=payload.validity_hours)
        title = f"Cotización desbloqueada mediante {request.folio}"
    event = publish_event(
        db,
        entity_type="quotation",
        entity_id=request.quotation_id,
        event_code=f"quotation.unlock.{request.status}",
        idempotency_key=f"{request.folio}:review:{request.status}",
        body=title,
        actor_id=user.id,
        metadata={"exception_folio": request.folio, "status": request.status},
    )
    _notify(
        db,
        request=request,
        recipient_id=request.requester_id,
        actor_id=user.id,
        kind=f"quotation_unlock_{request.status}",
        title=title,
        body=request.review_comment or title,
        event_id=event.id,
    )
    db.commit()
    return _resource(db, _get_request(db, request.folio), user)


def preview_change(db: Session, exception_folio: str, user: User) -> dict:
    """Qué ocurrirá al aplicar: sólo lectura; no propone partidas nuevas."""
    _require(user, APPLY_PERMISSION)
    request = _get_request(db, exception_folio)
    if request.status != "authorized" or request.authorized_apply_user_id != user.id:
        raise HTTPException(status_code=409, detail="El desbloqueo no está disponible para este usuario")
    return {
        "exception_folio": request.folio,
        "quotation_folio": request.quotation.folio,
        "service_order_folio": request.service_order_folio_snapshot,
        "outcome": {
            "next_status": "in_revision",
            "archives_service_order": True,
            "creates_service_order": False,
            "invalidates_current_acceptance": True,
        },
        "rebuild": (
            can_physically_rebuild_service_order(db, request.service_order).to_dict()
            if request.service_order
            else {"allowed": False, "blockers": ["El ETS relacionado cambió"], "dependencies": []}
        ),
    }


def apply_change(
    db: Session,
    exception_folio: str,
    payload: QuotationUnlockApply,
    user: User,
) -> dict:
    """Desbloqueo autorizado: archiva y elimina la ETS no intervenida.

    La cotización pasa a ``in_revision``. No se crea ninguna ETS de reemplazo:
    se generará al aceptarse la nueva versión comercial.
    """
    for permission in (
        APPLY_PERMISSION,
        REBUILD_PERMISSION,
        "quotations.update",
        "service_orders.read",
        "activity.create",
    ):
        _require(user, permission)
    # 1. Bloqueo de la solicitud, la cotización y la ETS.
    request = _get_request(db, exception_folio, lock=True)
    # 2. Revalidación de la autorización EXV.
    if request.status != "authorized":
        raise HTTPException(status_code=409, detail="El desbloqueo no está autorizado")
    if request.capability != CAPABILITY:
        raise HTTPException(
            status_code=409,
            detail="La solicitud pertenece al diseño anterior y debe cerrarse sin aplicar",
        )
    if request.authorized_apply_user_id != user.id:
        raise HTTPException(status_code=403, detail="El desbloqueo pertenece a otro usuario")
    if request.expires_at is None or _as_utc(request.expires_at) <= _now():
        request.status = "expired"
        request.active_scope_key = None
        db.commit()
        raise HTTPException(status_code=409, detail="El desbloqueo venció")

    quotation = _load_quotation(db, request.quotation.folio, lock=True)
    if quotation.status != "accepted":
        raise HTTPException(status_code=409, detail="La cotización debe estar aprobada")
    order = _related_service_order(db, quotation, lock=True)
    if order.id != request.service_order_id or order.folio != request.service_order_folio_snapshot:
        raise HTTPException(status_code=409, detail="El ETS relacionado cambió")
    # 3. Revalidación de la versión base.
    latest = _latest_snapshot(db, quotation.id)
    if latest.id != request.snapshot_id or latest.snapshot_number != payload.expected_snapshot_number:
        raise HTTPException(status_code=409, detail="La revisión base cambió")
    # 4. Única autoridad de dependencias.
    validation = can_physically_rebuild_service_order(db, order)
    if not validation.allowed:
        request.block_reason = "; ".join(validation.blockers)
        event = publish_event(
            db,
            entity_type="quotation",
            entity_id=quotation.id,
            event_code="quotation.unlock.blocked",
            idempotency_key=f"{request.folio}:blocked:{latest.snapshot_number}",
            body=f"El ETS {order.folio} no puede eliminarse: {request.block_reason}.",
            actor_id=user.id,
            metadata={"dependencies": validation.to_dict()["dependencies"]},
        )
        _notify(
            db,
            request=request,
            recipient_id=user.id,
            actor_id=user.id,
            kind="quotation_unlock_blocked",
            title=f"Desbloqueo bloqueado: {order.folio}",
            body=request.block_reason,
            event_id=event.id,
        )
        db.commit()
        raise HTTPException(status_code=409, detail=validation.to_dict())

    moment = _now()
    order_folio = order.folio
    previous_order_id = order.id
    acceptances = list(
        db.scalars(
            select(QuotationAcceptance)
            .where(
                QuotationAcceptance.quotation_id == quotation.id,
                QuotationAcceptance.invalidated_at.is_(None),
            )
            .with_for_update()
        ).all()
    )

    # 5-6. Snapshot histórico persistido y verificado antes de borrar nada.
    archive = archive_service_order(
        db,
        order=order,
        quotation=quotation,
        snapshot=latest,
        acceptance=acceptances[0] if acceptances else None,
        request=request,
        user_id=user.id,
        reason=request.reason,
        deleted_at=moment,
    )

    # 7-8. Desvincular referencias administrativas y eliminar la ETS operativa.
    request.service_order_id = None
    db.flush()
    from app.services.sale_execution import delete_pristine_sale_execution

    delete_pristine_sale_execution(db, order.id)
    db.delete(order)
    db.flush()

    # 10-11. La cotización entra en revisión; la aceptación deja de ser vigente
    # pero su evidencia (PDF, huella, firmante, folio) permanece intacta.
    quotation.status = "in_revision"
    for acceptance in acceptances:
        acceptance.invalidated_at = moment
        acceptance.invalidated_by_id = user.id
        acceptance.invalidation_reason = f"controlled_unlock:{request.folio}"
    invalidate_document_links(db, quotation_id=quotation.id)

    request.rebuild_audit_snapshot = {
        "service_order_folio": order_folio,
        "archived_service_order_id": previous_order_id,
        "archive_id": archive.id,
        "archive_integrity_hash": archive.integrity_hash,
        "creates_service_order": False,
        "validation": validation.to_dict(),
        "invalidated_acceptance_ids": [a.id for a in acceptances],
    }
    request.status = "completed"
    request.applied_by_id = user.id
    request.applied_at = moment
    request.consumed_at = moment
    request.active_scope_key = None
    request.block_reason = None

    # 12. Actividad y auditoría.
    confirmation_folios = [a.confirmation_folio for a in acceptances if a.confirmation_folio]
    body = (
        f"La cotización {quotation.folio} entró en revisión mediante {request.folio}. "
        f"La ETS {order_folio} no tenía intervención: se archivó y se eliminó de la operación activa. "
        "Se generará una nueva ETS cuando la nueva versión comercial sea aceptada."
    )
    event = publish_event(
        db,
        entity_type="quotation",
        entity_id=quotation.id,
        event_code="quotation.unlock.completed",
        idempotency_key=f"{request.folio}:completed",
        body=body,
        actor_id=user.id,
        metadata={
            "exception_folio": request.folio,
            "service_order_folio": order_folio,
            "archive_id": archive.id,
            "confirmation_folios": confirmation_folios,
        },
    )
    publish_event(
        db,
        entity_type="quotation",
        entity_id=quotation.id,
        event_code="quotation.service_order_archived",
        idempotency_key=f"{request.folio}:service-order-archived",
        body=f"ETS {order_folio} archivada y eliminada (archivo #{archive.id}).",
        actor_id=user.id,
        metadata={
            "archive_id": archive.id,
            "service_order_folio": order_folio,
            "integrity_hash": archive.integrity_hash,
            "schema_version": archive.schema_version,
        },
    )
    publish_event(
        db,
        entity_type="quotation",
        entity_id=quotation.id,
        event_code="quotation.in_revision",
        idempotency_key=f"{request.folio}:in-revision",
        body=f"{quotation.folio} está en revisión; la aceptación anterior dejó de ser vigente.",
        actor_id=user.id,
        metadata={
            "previous_status": "accepted",
            "status": "in_revision",
            "invalidated_acceptance_ids": [a.id for a in acceptances],
        },
    )
    _notify(
        db,
        request=request,
        recipient_id=user.id,
        actor_id=user.id,
        kind="quotation_unlock_completed",
        title=f"Cotización {quotation.folio} en revisión",
        body=f"La ETS {order_folio} fue archivada; edita y reenvía la nueva versión.",
        event_id=event.id,
    )
    write_audit_log(
        db,
        action="quotation.unlock_completed",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user.id,
        previous_values={
            "status": "accepted",
            "snapshot_number": latest.snapshot_number,
            "service_order_folio": order_folio,
            "service_order_id": previous_order_id,
        },
        new_values={
            "status": "in_revision",
            "archive_id": archive.id,
            "invalidated_acceptance_ids": [a.id for a in acceptances],
        },
    )
    # 13. Una sola transacción.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No fue posible archivar y eliminar atómicamente el ETS; no se aplicó ningún cambio",
        )
    return _resource(db, _get_request(db, request.folio), user)
