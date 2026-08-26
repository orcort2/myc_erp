from __future__ import annotations

import base64
import asyncio
import hashlib
import io
import json
import zipfile
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import String, cast, delete, func, select, text, update
from sqlalchemy.orm import Session, selectinload

from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.client import Client
from app.models.communication import (
    CommunicationConversation,
    CommunicationMessage,
    CommunicationMessageReceipt,
)
from app.models.lab_work_order import (
    LabWorkOrder,
    LabWorkOrderEquipment,
    LabWorkOrderGroupRequest,
    LabWorkOrderSignature,
    LabWorkOrderSignatureSession,
)
from app.models.operational_ticket import OperationalTicket
from app.models.lab_work_order_revision import LabWorkOrderRevision
from app.models.notification import Notification
from app.models.user import User
from app.schemas.lab_work_order import (
    LabEquipmentWrite,
    LabSignatureGroupWrite,
    LabWorkOrderCreate,
    LabWorkOrderGroupCreate,
    LabWorkOrderGroupRequestRead,
    LabWorkOrderListItem,
    LabWorkOrderRead,
    LabRelatedWorkOrderRead,
    LabWorkOrderUpdate,
)
from app.services.audit_logs import write_audit_log
from app.services.lab_work_order_pdfs import generate_lab_work_order_pdf
from app.services.notification_events import (
    notify_ticket_resolved,
    notify_ticket_signature_required,
)
from app.services.push_notifications import commit_and_dispatch_notifications
from app.services.push_notifications import queue_notification_for_delivery
from app.services.auth import user_has_permission
from app.realtime.events import publish_to_users


LAB_FOLIO_MIN = 6400
LAB_FOLIO_MAX = 6999
LAB_SEQUENCE_YEAR = 0
LAB_SEQUENCE_PREFIX = "LAB"
GENERAL_FIELDS = (
    "reception_date",
    "departure_date",
    "client_name",
    "address",
    "contact_name",
    "contact_phone",
    "contact_email",
    "postal_code",
    "city",
    "state_name",
    "purchase_order",
    "notes",
)
CRITICAL_GENERAL_FIELDS = {"reception_date", "departure_date", "client_name", "address"}
CRITICAL_EQUIPMENT_FIELDS = {
    "instrument", "brand", "identification", "serial_number", "is_good_condition"
}


def _query_with_relations():
    return select(LabWorkOrder).options(
        selectinload(LabWorkOrder.equipment),
        selectinload(LabWorkOrder.signature_session).selectinload(
            LabWorkOrderSignatureSession.signatures
        ),
    )


def _get(db: Session, work_order_id: int, *, lock: bool = False) -> LabWorkOrder:
    query = _query_with_relations().where(LabWorkOrder.id == work_order_id)
    if lock:
        query = query.with_for_update()
    work_order = db.scalar(query)
    if work_order is None:
        raise HTTPException(status_code=404, detail="Orden de trabajo LAB no encontrada")
    return work_order


def _root_id(work_order: LabWorkOrder) -> int:
    return work_order.root_work_order_id or work_order.id


def _group(db: Session, work_order: LabWorkOrder, *, lock: bool = False) -> list[LabWorkOrder]:
    query = _query_with_relations().where(
        LabWorkOrder.root_work_order_id == _root_id(work_order)
    ).order_by(LabWorkOrder.sequence_number)
    if lock:
        query = query.with_for_update()
    return list(db.scalars(query).all())


def _ensure_group_editable(group: list[LabWorkOrder]) -> None:
    if any(item.status != "draft" for item in group):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="INVALID_STATE_TRANSITION: el grupo no está disponible para edición",
        )
    if any(
        item.signature_session_id is not None
        and not (item.reopen_ticket_id and item.signature_preserved)
        for item in group
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El grupo ya fue firmado y no admite nuevas OT ni equipos",
        )


def _check_edit_version(group: list[LabWorkOrder], expected: int | None) -> None:
    if not any(item.reopen_ticket_id for item in group):
        return
    current = max(item.edit_version for item in group)
    if expected is None or expected != current:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "REVISION_CONFLICT", "current_edit_version": current},
        )


def _bump_edit_version(group: list[LabWorkOrder]) -> None:
    next_version = max(item.edit_version for item in group) + 1
    for item in group:
        item.edit_version = next_version


def _group_signatures_preserved(group: list[LabWorkOrder]) -> bool:
    """True when the group's current signature session comes from a reopening
    approved with requested_signature_policy = "preserve".

    ``_ensure_group_editable`` already guarantees that, once a group is
    editable, any item that still carries a ``signature_session_id`` must
    have ``reopen_ticket_id`` and ``signature_preserved`` set (otherwise the
    group would have been rejected as "ya fue firmado"). So the presence of
    a live signature session on an editable group means that session was
    explicitly preserved through a reopening and must not be invalidated by
    ordinary edits to already-existing data (general fields or equipment).
    """
    return any(
        item.signature_session_id is not None
        and item.reopen_ticket_id is not None
        and item.signature_preserved
        for item in group
    )


def invalidate_group_signatures(
    db: Session, group: list[LabWorkOrder], user: User, *, fields: list[str]
) -> None:
    if not any(item.signature_session_id is not None for item in group):
        return
    previous_session_ids = sorted(
        {item.signature_session_id for item in group if item.signature_session_id is not None}
    )
    for item in group:
        item.signature_session_id = None
        item.signature_required = True
        item.signature_preserved = False
    write_audit_log(
        db,
        action="lab_work_order.signatures_invalidated",
        entity="lab_work_orders",
        entity_id=_root_id(group[0]),
        user_id=user.id,
        previous_values={"signature_session_ids": previous_session_ids},
        new_values={"critical_fields": fields, "signature_required": True},
    )
    ticket_id = next((item.reopen_ticket_id for item in group if item.reopen_ticket_id), None)
    if ticket_id is not None:
        ticket = db.scalar(select(OperationalTicket).where(OperationalTicket.id == ticket_id))
        if ticket is not None:
            notify_ticket_signature_required(db, ticket, user)


def _allocate_folio_block(db: Session, quantity: int) -> list[int]:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": "lab_work_order:LAB:0"})
    counter = db.scalar(
        select(InstitutionalFolioSequence)
        .where(
            InstitutionalFolioSequence.document_type == "lab_work_order",
            InstitutionalFolioSequence.prefix == LAB_SEQUENCE_PREFIX,
            InstitutionalFolioSequence.year == LAB_SEQUENCE_YEAR,
        )
        .with_for_update()
    )
    existing_max = db.scalar(select(func.max(LabWorkOrder.folio)))
    candidate = max(LAB_FOLIO_MIN, (existing_max + 1) if existing_max is not None else LAB_FOLIO_MIN)
    if counter is None:
        counter = InstitutionalFolioSequence(
            document_type="lab_work_order",
            prefix=LAB_SEQUENCE_PREFIX,
            year=LAB_SEQUENCE_YEAR,
            next_value=candidate,
        )
        db.add(counter)
        db.flush()
    folio = max(counter.next_value, candidate)
    if folio + quantity - 1 > LAB_FOLIO_MAX:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Se agotó el rango de folios LAB 6400–6999",
        )
    counter.next_value = folio + quantity
    db.flush()
    return list(range(folio, folio + quantity))


def _allocate_folio(db: Session) -> int:
    return _allocate_folio_block(db, 1)[0]


def _read(db: Session, work_order: LabWorkOrder) -> LabWorkOrderRead:
    group = _group(db, work_order)
    result = LabWorkOrderRead.model_validate(work_order)
    result.related_work_orders = [
        LabRelatedWorkOrderRead(**{
            "id": item.id,
            "folio": item.folio,
            "sequence_number": item.sequence_number,
            "status": item.status,
            "equipment_count": len(item.equipment),
        })
        for item in group
    ]
    return result


def _append_request_system_message(
    db: Session, conversation: CommunicationConversation, actor: User, body: str, event_key: str
) -> None:
    now = datetime.now(timezone.utc)
    message = CommunicationMessage(
        conversation_id=conversation.id,
        sender_user_id=actor.id,
        client_message_id=f"group-request:{event_key}",
        sequence=conversation.next_message_sequence,
        body=body,
        message_type="system",
        delivered_at=now,
        created_at=now,
        updated_at=now,
    )
    conversation.next_message_sequence += 1
    conversation.last_message_at = now
    db.add(message)
    db.flush()
    for participant in conversation.participants:
        own = participant.id == actor.id
        db.add(CommunicationMessageReceipt(
            message_id=message.id,
            user_id=participant.id,
            delivered_at=now if own else None,
            read_at=now if own else None,
        ))


def _request_read(db: Session, request: LabWorkOrderGroupRequest) -> LabWorkOrderGroupRequestRead:
    operator = db.get(Client, request.operator_client_id)
    requester = db.get(User, request.requested_by_user_id)
    handler = db.get(User, request.handled_by_user_id) if request.handled_by_user_id else None
    folios: list[int] = []
    if request.root_work_order_id:
        folios = list(db.scalars(
            select(LabWorkOrder.folio)
            .where(LabWorkOrder.root_work_order_id == request.root_work_order_id)
            .order_by(LabWorkOrder.sequence_number)
        ).all())
    return LabWorkOrderGroupRequestRead(
        **{
            field: getattr(request, field)
            for field in LabWorkOrderGroupRequestRead.model_fields
            if hasattr(request, field)
        },
        operator_client_name=(operator.commercial_name or operator.legal_name) if operator else "Organización no disponible",
        requested_by_name=requester.full_name if requester else "Usuario no disponible",
        handled_by_name=handler.full_name if handler else None,
        folios=folios,
    )


def _ensure_request_conversation(
    db: Session,
    request: LabWorkOrderGroupRequest,
    requester: User,
    handler: User,
) -> CommunicationConversation:
    conversation = db.get(CommunicationConversation, request.conversation_id) if request.conversation_id else None
    if conversation is not None:
        for participant in (requester, handler):
            if all(item.id != participant.id for item in conversation.participants):
                conversation.participants.append(participant)
        return conversation
    conversation = CommunicationConversation(
        conversation_type="client",
        client_id=request.operator_client_id,
        title=f"Solicitud de grupo OT LAB #{request.id}",
        created_by_user_id=requester.id,
        participants=[requester, handler],
    )
    db.add(conversation)
    db.flush()
    request.conversation_id = conversation.id
    _append_request_system_message(
        db,
        conversation,
        requester,
        f"{requester.full_name} solicitó un grupo de {request.quantity} órdenes de trabajo.",
        f"{request.id}:created",
    )
    return conversation


def _notify_request_user(
    db: Session, request: LabWorkOrderGroupRequest, actor: User, event: str, title: str, body: str
) -> None:
    notification = Notification(
        recipient_user_id=request.requested_by_user_id,
        actor_user_id=actor.id,
        notification_type=event,
        event_key=f"lab-group-request:{request.id}:{event}",
        title=title,
        body=body,
        entity_type="work_order_group_request",
        entity_id=request.id,
        priority="normal",
        metadata_json={
            "request_id": request.id,
            "frontend_path": f"/lab-work-order-groups?request_id={request.id}",
            "mobile_path": "/(technician)/work-orders",
        },
    )
    db.add(notification)
    queue_notification_for_delivery(db, notification)


def _publish_request_event(request: LabWorkOrderGroupRequest, event: str) -> None:
    recipients = {request.requested_by_user_id}
    if request.handled_by_user_id:
        recipients.add(request.handled_by_user_id)
    try:
        asyncio.run(publish_to_users(recipients, event, {
            "entity_type": "work_order_group_request",
            "entity_id": request.id,
            "request_id": request.id,
            "status": request.status,
            "operator_client_id": request.operator_client_id,
            "root_work_order_id": request.root_work_order_id,
            "conversation_id": request.conversation_id,
        }))
    except Exception:
        # Realtime is a post-commit projection; it can never invalidate the
        # already durable decision or cause a client retry to duplicate work.
        return


def create_work_order(
    db: Session,
    payload: LabWorkOrderCreate,
    user: User,
    *,
    operator_client_id: int | None = None,
) -> LabWorkOrderRead:
    values = payload.model_dump()
    work_order = LabWorkOrder(
        folio=_allocate_folio(db),
        sequence_number=1,
        created_by_user_id=user.id,
        operator_client_id=operator_client_id,
        **values,
    )
    db.add(work_order)
    db.flush()
    work_order.root_work_order_id = work_order.id
    write_audit_log(
        db,
        action="lab_work_order.created",
        entity="lab_work_orders",
        entity_id=work_order.id,
        user_id=user.id,
        new_values={"folio": work_order.folio, "root_work_order_id": work_order.id},
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order.id))


def _materialize_group(
    db: Session,
    payload: LabWorkOrderGroupCreate,
    user: User,
    *,
    operator_client_id: int | None,
    origin: str,
) -> LabWorkOrder:
    """Create an anticipated LAB group atomically; caller owns the commit."""
    values = payload.model_dump(exclude={"quantity"})
    folios = _allocate_folio_block(db, payload.quantity)
    root: LabWorkOrder | None = None
    previous: LabWorkOrder | None = None
    for sequence_number, folio in enumerate(folios, start=1):
        item = LabWorkOrder(
            folio=folio,
            root_work_order_id=root.id if root else None,
            previous_work_order_id=previous.id if previous else None,
            sequence_number=sequence_number,
            created_by_user_id=user.id,
            operator_client_id=operator_client_id,
            **values,
        )
        db.add(item)
        db.flush()
        if root is None:
            root = item
            item.root_work_order_id = item.id
        previous = item
    assert root is not None
    write_audit_log(
        db,
        action="lab_work_order.group_materialized",
        entity="lab_work_orders",
        entity_id=root.id,
        user_id=user.id,
        new_values={
            "origin": origin,
            "quantity": payload.quantity,
            "folios": folios,
            "operator_client_id": operator_client_id,
        },
    )
    return root


def create_work_order_group(
    db: Session,
    payload: LabWorkOrderGroupCreate,
    user: User,
    *,
    operator_client_id: int | None,
) -> LabWorkOrderRead:
    try:
        root = _materialize_group(
            db, payload, user, operator_client_id=operator_client_id, origin="staff_direct"
        )
        commit_and_dispatch_notifications(db)
        return _read(db, _get(db, root.id))
    except Exception:
        db.rollback()
        raise


def create_group_request(
    db: Session,
    payload: LabWorkOrderGroupCreate,
    user: User,
    *,
    operator_client_id: int,
) -> LabWorkOrderGroupRequestRead:
    request = LabWorkOrderGroupRequest(
        operator_client_id=operator_client_id,
        requested_by_user_id=user.id,
        quantity=payload.quantity,
        **payload.model_dump(exclude={"quantity"}),
    )
    db.add(request)
    db.flush()
    for staff in db.scalars(select(User).where(User.is_active.is_(True))).all():
        if staff.id == user.id or not user_has_permission(staff, "lab_work_order_groups.requests.read"):
            continue
        notification = Notification(
            recipient_user_id=staff.id,
            actor_user_id=user.id,
            notification_type="lab_work_order_group.requested",
            event_key=f"lab-group-request:{request.id}:staff:{staff.id}",
            title="Nueva solicitud de grupo OT LAB",
            body=f"{request.quantity} OT para {request.client_name}",
            entity_type="work_order_group_request",
            entity_id=request.id,
            priority="normal",
            metadata_json={
                "request_id": request.id,
                "frontend_path": f"/lab-work-order-groups?request_id={request.id}",
                "mobile_path": "/(technician)/tickets",
            },
        )
        db.add(notification)
        queue_notification_for_delivery(db, notification)
    write_audit_log(
        db,
        action="lab_work_order.group_requested",
        entity="lab_work_order_group_requests",
        entity_id=request.id,
        user_id=user.id,
        new_values={"quantity": request.quantity, "operator_client_id": operator_client_id},
    )
    commit_and_dispatch_notifications(db)
    db.refresh(request)
    _publish_request_event(request, "lab_work_order_group.requested")
    return _request_read(db, request)


def list_group_requests(
    db: Session, *, operator_client_id: int | None = None, requester_user_id: int | None = None
) -> list[LabWorkOrderGroupRequestRead]:
    query = select(LabWorkOrderGroupRequest)
    if operator_client_id is not None:
        query = query.where(LabWorkOrderGroupRequest.operator_client_id == operator_client_id)
    if requester_user_id is not None:
        query = query.where(LabWorkOrderGroupRequest.requested_by_user_id == requester_user_id)
    rows = db.scalars(query.order_by(LabWorkOrderGroupRequest.created_at.desc())).all()
    return [_request_read(db, item) for item in rows]


def claim_group_request(db: Session, request_id: int, user: User) -> LabWorkOrderGroupRequestRead:
    request = db.scalar(
        select(LabWorkOrderGroupRequest)
        .where(LabWorkOrderGroupRequest.id == request_id)
        .with_for_update()
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if request.status == "in_review" and request.handled_by_user_id == user.id:
        return _request_read(db, request)
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="La solicitud ya fue tomada o resuelta")
    request.status = "in_review"
    request.handled_by_user_id = user.id
    request.claimed_at = datetime.now(timezone.utc)
    requester = db.get(User, request.requested_by_user_id)
    if requester is None:
        raise HTTPException(status_code=409, detail="El solicitante ya no está disponible")
    conversation = _ensure_request_conversation(db, request, requester, user)
    _append_request_system_message(db, conversation, user, f"{user.full_name} está atendiendo la solicitud.", f"{request.id}:claimed")
    _notify_request_user(db, request, user, "lab_work_order_group.in_review", "Solicitud OT LAB en revisión", "Un administrador tomó tu solicitud.")
    commit_and_dispatch_notifications(db)
    db.refresh(request)
    _publish_request_event(request, "lab_work_order_group.in_review")
    return _request_read(db, request)


def approve_group_request(db: Session, request_id: int, user: User) -> LabWorkOrderGroupRequestRead:
    try:
        request = db.scalar(
            select(LabWorkOrderGroupRequest)
            .where(LabWorkOrderGroupRequest.id == request_id)
            .with_for_update()
        )
        if request is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        if request.status == "approved" and request.root_work_order_id is not None:
            return _request_read(db, request)
        if request.status != "in_review" or request.handled_by_user_id != user.id:
            raise HTTPException(status_code=409, detail="La solicitud debe estar tomada por el aprobador")
        payload = LabWorkOrderGroupCreate(
            quantity=request.quantity,
            **{field: getattr(request, field) for field in GENERAL_FIELDS},
        )
        root = _materialize_group(
            db,
            payload,
            user,
            operator_client_id=request.operator_client_id,
            origin="external_request",
        )
        request.root_work_order_id = root.id
        request.status = "approved"
        request.decided_at = datetime.now(timezone.utc)
        conversation = db.get(CommunicationConversation, request.conversation_id)
        if conversation is not None:
            folios = list(range(root.folio, root.folio + request.quantity))
            _append_request_system_message(db, conversation, user, f"{user.full_name} aprobó la solicitud. Folios asignados: {', '.join(map(str, folios))}.", f"{request.id}:approved")
        _notify_request_user(db, request, user, "lab_work_order_group.approved", "Grupo OT LAB aprobado", f"Se materializaron {request.quantity} órdenes.")
        commit_and_dispatch_notifications(db)
        db.refresh(request)
        _publish_request_event(request, "lab_work_order_group.approved")
        return _request_read(db, request)
    except Exception:
        db.rollback()
        raise


def reject_group_request(
    db: Session, request_id: int, user: User, reason: str | None
) -> LabWorkOrderGroupRequestRead:
    if not reason or not reason.strip():
        raise HTTPException(status_code=422, detail="El motivo de rechazo es obligatorio")
    request = db.scalar(
        select(LabWorkOrderGroupRequest)
        .where(LabWorkOrderGroupRequest.id == request_id)
        .with_for_update()
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if request.status != "in_review" or request.handled_by_user_id != user.id:
        raise HTTPException(status_code=409, detail="La solicitud debe estar tomada por quien decide")
    request.status = "rejected"
    request.decision_reason = reason.strip()
    request.decided_at = datetime.now(timezone.utc)
    conversation = db.get(CommunicationConversation, request.conversation_id)
    if conversation is not None:
        _append_request_system_message(db, conversation, user, f"{user.full_name} rechazó la solicitud. Motivo: {reason.strip()}", f"{request.id}:rejected")
    _notify_request_user(db, request, user, "lab_work_order_group.rejected", "Solicitud OT LAB rechazada", reason.strip())
    commit_and_dispatch_notifications(db)
    db.refresh(request)
    _publish_request_event(request, "lab_work_order_group.rejected")
    return _request_read(db, request)


def list_work_orders(
    db: Session,
    *,
    folio: str | None = None,
    client: str | None = None,
    work_order_status: str | None = None,
    offset: int = 0,
    limit: int = 25,
    operator_client_id: int | None = None,
) -> list[LabWorkOrderListItem]:
    query = _query_with_relations()
    if operator_client_id is not None:
        query = query.where(LabWorkOrder.operator_client_id == operator_client_id)
    if folio and folio.strip():
        query = query.where(cast(LabWorkOrder.folio, String).contains(folio.strip()))
    if client and client.strip():
        query = query.where(LabWorkOrder.client_name.ilike(f"%{client.strip()}%"))
    if work_order_status == "open":
        query = query.where(LabWorkOrder.status.in_(("draft", "ready_for_signatures")))
    elif work_order_status == "completed":
        query = query.where(LabWorkOrder.status == "completed")
    items = list(
        db.scalars(
            query.order_by(LabWorkOrder.folio.desc()).offset(offset).limit(limit)
        ).all()
    )
    return [
        LabWorkOrderListItem(
            id=item.id,
            folio=item.folio,
            root_work_order_id=item.root_work_order_id,
            sequence_number=item.sequence_number,
            client_name=item.client_name,
            reception_date=item.reception_date,
            status=item.status,
            equipment_count=len(item.equipment),
            created_at=item.created_at,
            revision_number=item.revision_number,
            signature_required=item.signature_required,
        )
        for item in items
    ]


def get_work_order(db: Session, work_order_id: int) -> LabWorkOrderRead:
    return _read(db, _get(db, work_order_id))


def delete_work_order(db: Session, work_order_id: int, user: User) -> None:
    """Delete one LAB work order while preserving valid group-owned resources."""
    try:
        work_order = _get(db, work_order_id, lock=True)
        group = _group(db, work_order, lock=True)
        survivors = [item for item in group if item.id != work_order.id]
        survivor_ids = {item.id for item in survivors}
        root_id = _root_id(work_order)
        deleted_folio = work_order.folio

        revisions = list(
            db.scalars(
                select(LabWorkOrderRevision)
                .where(LabWorkOrderRevision.work_order_id == work_order.id)
                .with_for_update()
            ).all()
        )
        for revision in revisions:
            db.delete(revision)

        tickets = list(
            db.scalars(
                select(OperationalTicket)
                .where(OperationalTicket.work_order_id == work_order.id)
                .with_for_update()
            ).all()
        )
        ticket_ids = {ticket.id for ticket in tickets}
        shared_ticket_ids: set[int] = {
            item.reopen_ticket_id
            for item in survivors
            if item.reopen_ticket_id in ticket_ids
        }
        if survivor_ids and ticket_ids:
            shared_ticket_ids.update(
                db.scalars(
                    select(LabWorkOrderRevision.reopen_ticket_id).where(
                        LabWorkOrderRevision.work_order_id.in_(survivor_ids),
                        LabWorkOrderRevision.reopen_ticket_id.in_(ticket_ids),
                    )
                ).all()
            )

        replacement = survivors[0] if survivors else None
        orphan_sessions: list[LabWorkOrderSignatureSession] = []
        if replacement is not None and work_order.id == root_id:
            sessions = list(
                db.scalars(
                    select(LabWorkOrderSignatureSession)
                    .where(LabWorkOrderSignatureSession.root_work_order_id == root_id)
                    .with_for_update()
                ).all()
            )
            for session in sessions:
                session.root_work_order_id = replacement.id
        elif replacement is None:
            orphan_sessions = list(
                db.scalars(
                    select(LabWorkOrderSignatureSession)
                    .where(LabWorkOrderSignatureSession.root_work_order_id == root_id)
                    .with_for_update()
                ).all()
            )

        work_order.signature_session_id = None
        work_order.reopen_ticket_id = None
        work_order.previous_work_order_id = None
        work_order.root_work_order_id = None
        db.flush()

        for ticket in tickets:
            if replacement is not None and ticket.id in shared_ticket_ids:
                ticket.work_order_id = replacement.id
                notifications = list(
                    db.scalars(
                        select(Notification).where(
                            Notification.entity_type == "ticket",
                            Notification.entity_id == ticket.id,
                        )
                    ).all()
                )
                for notification in notifications:
                    notification.metadata_json = {
                        **notification.metadata_json,
                        "work_order_id": replacement.id,
                        "work_order_folio": replacement.folio,
                    }
                continue
            db.execute(
                delete(Notification).where(
                    Notification.entity_type == "ticket",
                    Notification.entity_id == ticket.id,
                )
            )
            db.delete(ticket)

        previous_id: int | None = None
        if replacement is not None:
            for survivor in survivors:
                survivor.root_work_order_id = replacement.id
                survivor.previous_work_order_id = previous_id
                previous_id = survivor.id
        else:
            for session in orphan_sessions:
                db.delete(session)
        db.flush()

        db.delete(work_order)
        db.flush()

        for sequence, survivor in enumerate(survivors, start=1):
            survivor.sequence_number = sequence

        write_audit_log(
            db,
            action="lab_work_order.deleted",
            entity="lab_work_orders",
            entity_id=work_order_id,
            user_id=user.id,
            previous_values={
                "folio": deleted_folio,
                "root_work_order_id": root_id,
            },
            new_values={
                "surviving_work_order_ids": [item.id for item in survivors],
            },
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No fue posible eliminar la orden de trabajo LAB de forma segura",
        ) from exc


def update_work_order(
    db: Session,
    work_order_id: int,
    payload: LabWorkOrderUpdate,
    user: User,
    *,
    operator_client_id: int | None = None,
) -> LabWorkOrderRead:
    work_order = _get(db, work_order_id, lock=True)
    group = _group(db, work_order, lock=True)
    _ensure_group_editable(group)
    updates = payload.model_dump(exclude_unset=True)
    expected_edit_version = updates.pop("expected_edit_version", None)
    _check_edit_version(group, expected_edit_version)
    reception = updates.get("reception_date", work_order.reception_date)
    departure = updates.get("departure_date", work_order.departure_date)
    if departure < reception:
        raise HTTPException(status_code=422, detail="La salida no puede ser anterior a la recepción")
    changed_fields = sorted(
        key for key, value in updates.items() if getattr(work_order, key) != value
    )
    if CRITICAL_GENERAL_FIELDS.intersection(changed_fields) and not _group_signatures_preserved(
        group
    ):
        invalidate_group_signatures(db, group, user, fields=changed_fields)
    for item in group:
        for key, value in updates.items():
            setattr(item, key, value)
    if changed_fields:
        _bump_edit_version(group)
    write_audit_log(
        db,
        action="lab_work_order.group_updated",
        entity="lab_work_orders",
        entity_id=_root_id(work_order),
        user_id=user.id,
        new_values={"fields": sorted(updates), "group_size": len(group)},
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order_id))


def add_equipment(
    db: Session, work_order_id: int, payload: LabEquipmentWrite, user: User
) -> LabWorkOrderRead:
    work_order = _get(db, work_order_id, lock=True)
    group = _group(db, work_order, lock=True)
    _ensure_group_editable(group)
    values = payload.model_dump()
    expected_edit_version = values.pop("expected_edit_version", None)
    _check_edit_version(group, expected_edit_version)
    if any(item.reopen_ticket_id for item in group):
        invalidate_group_signatures(db, group, user, fields=["equipment.added"])
    count = db.scalar(
        select(func.count(LabWorkOrderEquipment.id)).where(
            LabWorkOrderEquipment.work_order_id == work_order.id
        )
    ) or 0
    if count >= 10:
        raise HTTPException(status_code=409, detail="La OT ya contiene el máximo de 10 equipos")
    equipment = LabWorkOrderEquipment(
        work_order_id=work_order.id, position=count + 1, **values
    )
    db.add(equipment)
    db.flush()
    _bump_edit_version(group)
    write_audit_log(
        db,
        action="lab_work_order.equipment_added",
        entity="lab_work_order_equipment",
        entity_id=equipment.id,
        user_id=user.id,
        new_values={"work_order_id": work_order.id, "position": equipment.position},
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order_id))


def update_equipment(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: LabEquipmentWrite,
    user: User,
) -> LabWorkOrderRead:
    work_order = _get(db, work_order_id, lock=True)
    group = _group(db, work_order, lock=True)
    _ensure_group_editable(group)
    values = payload.model_dump()
    expected_edit_version = values.pop("expected_edit_version", None)
    _check_edit_version(group, expected_edit_version)
    equipment = db.scalar(
        select(LabWorkOrderEquipment).where(
            LabWorkOrderEquipment.id == equipment_id,
            LabWorkOrderEquipment.work_order_id == work_order.id,
        )
    )
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")
    changed_fields = sorted(
        key for key, value in values.items() if getattr(equipment, key) != value
    )
    if CRITICAL_EQUIPMENT_FIELDS.intersection(changed_fields) and not _group_signatures_preserved(
        group
    ):
        invalidate_group_signatures(db, group, user, fields=changed_fields)
    for key, value in values.items():
        setattr(equipment, key, value)
    if changed_fields:
        _bump_edit_version(group)
    write_audit_log(
        db,
        action="lab_work_order.equipment_updated",
        entity="lab_work_order_equipment",
        entity_id=equipment.id,
        user_id=user.id,
        new_values={"work_order_id": work_order.id},
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order_id))


def delete_equipment(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    user: User,
    *,
    expected_edit_version: int | None = None,
) -> LabWorkOrderRead:
    work_order = _get(db, work_order_id, lock=True)
    group = _group(db, work_order, lock=True)
    _ensure_group_editable(group)
    _check_edit_version(group, expected_edit_version)
    equipment = db.scalar(
        select(LabWorkOrderEquipment).where(
            LabWorkOrderEquipment.id == equipment_id,
            LabWorkOrderEquipment.work_order_id == work_order.id,
        )
    )
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")
    if any(item.reopen_ticket_id for item in group):
        invalidate_group_signatures(db, group, user, fields=["equipment.deleted"])
    removed_position = equipment.position
    work_order.equipment.remove(equipment)
    db.flush()
    db.execute(
        update(LabWorkOrderEquipment)
        .where(
            LabWorkOrderEquipment.work_order_id == work_order.id,
            LabWorkOrderEquipment.position > removed_position,
        )
        .values(position=LabWorkOrderEquipment.position - 1)
    )
    db.expire(work_order, ["equipment"])
    _bump_edit_version(group)
    write_audit_log(
        db,
        action="lab_work_order.equipment_deleted",
        entity="lab_work_order_equipment",
        entity_id=equipment_id,
        user_id=user.id,
        previous_values={"work_order_id": work_order.id, "position": removed_position},
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order_id))


def create_additional_work_order(db: Session, work_order_id: int, user: User) -> LabWorkOrderRead:
    source = _get(db, work_order_id, lock=True)
    group = _group(db, source, lock=True)
    _ensure_group_editable(group)
    if any(item.reopen_ticket_id for item in group):
        invalidate_group_signatures(db, group, user, fields=["work_order.additional"])
    latest = group[-1]
    if latest.id != source.id:
        raise HTTPException(status_code=409, detail="Sólo la última OT del grupo puede generar una adicional")
    if len(source.equipment) != 10:
        raise HTTPException(status_code=409, detail="La OT debe tener 10 equipos para asignar una OT extra")
    values = {field: getattr(source, field) for field in GENERAL_FIELDS}
    additional = LabWorkOrder(
        folio=_allocate_folio(db),
        root_work_order_id=_root_id(source),
        previous_work_order_id=source.id,
        sequence_number=source.sequence_number + 1,
        created_by_user_id=user.id,
        operator_client_id=source.operator_client_id,
        revision_number=source.revision_number,
        edit_version=source.edit_version,
        reopened_at=source.reopened_at,
        reopened_by_user_id=source.reopened_by_user_id,
        reopen_ticket_id=source.reopen_ticket_id,
        signature_required=source.signature_required,
        signature_preserved=False,
        **values,
    )
    db.add(additional)
    db.flush()
    _bump_edit_version([*group, additional])
    write_audit_log(
        db,
        action="lab_work_order.additional_created",
        entity="lab_work_orders",
        entity_id=additional.id,
        user_id=user.id,
        new_values={
            "folio": additional.folio,
            "root_work_order_id": additional.root_work_order_id,
            "previous_work_order_id": source.id,
            "sequence_number": additional.sequence_number,
        },
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, additional.id))


def _decode_signature(value: str) -> bytes:
    try:
        binary = base64.b64decode(value.split(",", 1)[1], validate=True)
    except (IndexError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Firma PNG inválida") from exc
    if not binary.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=422, detail="Firma PNG inválida")
    return binary


def sign_group(
    db: Session, work_order_id: int, payload: LabSignatureGroupWrite, user: User
) -> LabWorkOrderRead:
    work_order = _get(db, work_order_id, lock=True)
    group = _group(db, work_order, lock=True)
    _ensure_group_editable(group)
    if all(item.signature_session_id is not None for item in group) and not any(
        item.signature_required for item in group
    ):
        raise HTTPException(status_code=409, detail="El grupo ya conserva una firma válida")
    if any(not item.equipment for item in group):
        raise HTTPException(status_code=409, detail="Todas las OT del grupo deben tener al menos un equipo")
    _decode_signature(payload.technician.signature_data_url)
    _decode_signature(payload.client.signature_data_url)
    now = datetime.now(timezone.utc)
    latest_version = db.scalar(
        select(func.max(LabWorkOrderSignatureSession.version)).where(
            LabWorkOrderSignatureSession.root_work_order_id == _root_id(work_order)
        )
    ) or 0
    session = LabWorkOrderSignatureSession(
        root_work_order_id=_root_id(work_order),
        signed_by_user_id=user.id,
        signed_at=now,
        version=latest_version + 1,
        signatures=[
            LabWorkOrderSignature(signature_type="technician", **payload.technician.model_dump()),
            LabWorkOrderSignature(signature_type="client", **payload.client.model_dump()),
        ],
    )
    db.add(session)
    db.flush()
    for item in group:
        item.signature_session_id = session.id
        item.status = "ready_for_signatures"
        item.signature_required = False
        item.signature_preserved = False
    write_audit_log(
        db,
        action="lab_work_order.group_signed",
        entity="lab_work_orders",
        entity_id=_root_id(work_order),
        user_id=user.id,
        new_values={"signature_session_id": session.id, "work_order_ids": [item.id for item in group]},
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order_id))


def complete_group(db: Session, work_order_id: int, user: User) -> LabWorkOrderRead:
    work_order = _get(db, work_order_id, lock=True)
    group = _group(db, work_order, lock=True)
    if all(item.status == "completed" for item in group):
        return _read(db, work_order)
    if any(item.signature_session_id is None or item.signature_required for item in group):
        raise HTTPException(status_code=409, detail="El grupo requiere las firmas de técnico y cliente")
    if any(item.status not in {"draft", "ready_for_signatures"} for item in group):
        raise HTTPException(status_code=409, detail="INVALID_STATE_TRANSITION")
    session_ids = {item.signature_session_id for item in group}
    if len(session_ids) != 1:
        raise HTTPException(status_code=409, detail="El grupo no comparte una única sesión de firma")
    completed_at = datetime.now(timezone.utc)
    for item in group:
        pdf, _ = generate_lab_work_order_pdf(item)
        item.final_pdf = pdf
        item.final_pdf_sha256 = hashlib.sha256(pdf).hexdigest()
        item.final_pdf_generated_at = completed_at
        item.completed_at = completed_at
        item.status = "completed"
        item.signature_preserved = bool(item.reopen_ticket_id and item.signature_preserved)
    ticket_ids = {item.reopen_ticket_id for item in group if item.reopen_ticket_id}
    if ticket_ids:
        tickets = list(
            db.scalars(
                select(OperationalTicket).where(OperationalTicket.id.in_(ticket_ids)).with_for_update()
            )
        )
        for ticket in tickets:
            ticket.status = "resolved"
            ticket.resolved_at = completed_at
            notify_ticket_resolved(db, ticket, user)
    write_audit_log(
        db,
        action="lab_work_order.group_completed",
        entity="lab_work_orders",
        entity_id=_root_id(work_order),
        user_id=user.id,
        new_values={"work_order_ids": [item.id for item in group], "completed_at": completed_at.isoformat()},
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order_id))


def get_pdf(db: Session, work_order_id: int) -> tuple[bytes, str]:
    work_order = _get(db, work_order_id)
    if work_order.status != "completed" or not work_order.final_pdf:
        raise HTTPException(status_code=409, detail="La OT LAB aún no tiene PDF final")
    return (
        work_order.final_pdf,
        f"OT-{work_order.folio}-r{work_order.revision_number}.pdf",
    )


def export_all(db: Session) -> tuple[bytes, str]:
    work_orders = list(db.scalars(_query_with_relations().order_by(LabWorkOrder.folio)).all())
    equipment_count = sum(len(item.equipment) for item in work_orders)
    manifest = {
        "format_version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "work_order_count": len(work_orders),
        "equipment_count": equipment_count,
        "folios": [item.folio for item in work_orders],
        "files": [],
    }
    work_order_rows = []
    equipment_rows = []
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in work_orders:
            work_order_rows.append({
                "id": item.id,
                "folio": item.folio,
                "root_work_order_id": item.root_work_order_id,
                "previous_work_order_id": item.previous_work_order_id,
                "sequence_number": item.sequence_number,
                "created_by_user_id": item.created_by_user_id,
                "status": item.status,
                "general_data": {field: str(getattr(item, field) or "") for field in GENERAL_FIELDS},
                "signature_session_id": item.signature_session_id,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            })
            for equipment in item.equipment:
                equipment_rows.append({
                    "id": equipment.id,
                    "work_order_id": item.id,
                    "folio": item.folio,
                    "position": equipment.position,
                    "instrument": equipment.instrument,
                    "brand": equipment.brand,
                    "identification": equipment.identification,
                    "serial_number": equipment.serial_number,
                    "report_number": equipment.report_number,
                    "is_good_condition": equipment.is_good_condition,
                })
            if item.final_pdf:
                path = f"pdf/OT-{item.folio}.pdf"
                archive.writestr(path, item.final_pdf)
                manifest["files"].append({"path": path, "sha256": hashlib.sha256(item.final_pdf).hexdigest()})
        sessions = {
            item.signature_session.id: item.signature_session
            for item in work_orders
            if item.signature_session is not None
        }
        for session in sessions.values():
            metadata = {
                "id": session.id,
                "root_work_order_id": session.root_work_order_id,
                "signed_by_user_id": session.signed_by_user_id,
                "signed_at": session.signed_at.isoformat(),
                "version": session.version,
                "signatures": [],
            }
            for signature in session.signatures:
                path = f"signatures/session-{session.id}-{signature.signature_type}.png"
                binary = _decode_signature(signature.signature_data_url)
                archive.writestr(path, binary)
                sha256 = hashlib.sha256(binary).hexdigest()
                metadata["signatures"].append({
                    "type": signature.signature_type,
                    "signer_name": signature.signer_name,
                    "signed_at": signature.signed_at.isoformat(),
                    "version": signature.version,
                    "path": path,
                    "sha256": sha256,
                })
                manifest["files"].append({"path": path, "sha256": sha256})
            archive.writestr(
                f"signatures/session-{session.id}.json",
                json.dumps(metadata, ensure_ascii=False, indent=2),
            )
        archive.writestr("work_orders.json", json.dumps(work_order_rows, ensure_ascii=False, indent=2))
        archive.writestr("equipment.json", json.dumps(equipment_rows, ensure_ascii=False, indent=2))
        if len(work_order_rows) != manifest["work_order_count"] or len(equipment_rows) != equipment_count:
            raise RuntimeError("La exportación LAB no coincide con los registros persistidos")
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return archive_buffer.getvalue(), f"export_lab_ot_{date.today().isoformat()}.zip"
