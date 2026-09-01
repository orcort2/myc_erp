from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import zipfile
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import String, cast, delete, func, select, text, update
from sqlalchemy.orm import Session, selectinload

from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.communication import (
    CommunicationConversation,
    CommunicationMessage,
    CommunicationMessageReceipt,
)
from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.field_sheet import FieldSheet
from app.models.lab_client import LabClient
from app.models.linked_company import LinkedCompany
from app.models.lab_work_order import (
    LabWorkOrder,
    LabWorkOrderEquipment,
    LabWorkOrderGroupRequest,
    LabWorkOrderSignature,
    LabWorkOrderSignatureSession,
)
from app.models.lab_work_order_revision import LabWorkOrderRevision
from app.models.notification import Notification
from app.models.operational_ticket import OperationalTicket
from app.models.user import User
from app.schemas.lab_work_order import (
    LabEquipmentCertificateClientWrite,
    LabEquipmentConfiguredCreate,
    LabEquipmentWrite,
    LabEquipmentServiceWrite,
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
LAB_CERTIFICATE_SEQUENCE_YEAR = 0
LAB_CERTIFICATE_LIMIT = 7999
LAB_CERTIFICATE_STARTS = {"MYCA": 4700, "MYCT": 1640}
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
    "lab_client_id",
)
CRITICAL_GENERAL_FIELDS = {"reception_date", "departure_date", "client_name", "address"}
CRITICAL_EQUIPMENT_FIELDS = {
    "instrument", "brand", "identification", "serial_number", "is_good_condition"
}


def _query_with_relations():
    return select(LabWorkOrder).options(
        selectinload(LabWorkOrder.equipment).selectinload(LabWorkOrderEquipment.field_sheet),
        selectinload(LabWorkOrder.signature_session).selectinload(
            LabWorkOrderSignatureSession.signatures
        ),
    )


def _get(db: Session, work_order_id: int, *, lock: bool = False) -> LabWorkOrder:
    query = (
        _query_with_relations()
        .where(LabWorkOrder.id == work_order_id)
        .execution_options(populate_existing=True)
    )
    if lock:
        query = query.with_for_update()
    work_order = db.scalar(query)
    if work_order is None:
        raise HTTPException(status_code=404, detail="Orden de trabajo LAB no encontrada")
    return work_order


def _root_id(work_order: LabWorkOrder) -> int:
    return work_order.root_work_order_id or work_order.id


def _group(db: Session, work_order: LabWorkOrder, *, lock: bool = False) -> list[LabWorkOrder]:
    query = (
        _query_with_relations()
        .where(LabWorkOrder.root_work_order_id == _root_id(work_order))
        .order_by(LabWorkOrder.sequence_number)
        .execution_options(populate_existing=True)
    )
    if lock:
        query = query.with_for_update()
    return list(db.scalars(query).all())


def _open_group_members(group: list[LabWorkOrder]) -> list[LabWorkOrder]:
    """Return non-final members without changing historical group identity."""
    return [item for item in group if item.status not in {"completed", "partially_closed", "cancelled"}]


def _editable_group_members(group: list[LabWorkOrder]) -> list[LabWorkOrder]:
    """Return only draft members that may still receive ordinary mutations."""
    return [item for item in group if item.status == "draft"]


def _signature_cohort(
    group: list[LabWorkOrder], work_order: LabWorkOrder, *, include_completed: bool = False
) -> list[LabWorkOrder]:
    if work_order.signature_session_id is None:
        return []
    return [
        item
        for item in group
        if item.signature_session_id == work_order.signature_session_id
        and (include_completed or item.status not in {"completed", "partially_closed", "cancelled"})
    ]


def _affected_signature_members(
    group: list[LabWorkOrder], work_order: LabWorkOrder
) -> list[LabWorkOrder]:
    cohort = _signature_cohort(group, work_order)
    return cohort or [work_order]


def _lock_historical_group(
    db: Session, work_order_id: int
) -> tuple[LabWorkOrder, list[LabWorkOrder]]:
    """Serialize closure-session versioning by locking the historical root first."""
    selected = _get(db, work_order_id)
    root_id = _root_id(selected)
    locked_root = db.scalar(
        select(LabWorkOrder).where(LabWorkOrder.id == root_id).with_for_update()
    )
    if locked_root is None:
        raise HTTPException(status_code=404, detail="Orden de trabajo LAB no encontrada")
    group = _group(db, locked_root, lock=True)
    work_order = next((item for item in group if item.id == work_order_id), None)
    if work_order is None:
        raise HTTPException(status_code=404, detail="Orden de trabajo LAB no encontrada")
    return work_order, group


def _ensure_members_editable(members: list[LabWorkOrder]) -> None:
    if not members or any(item.status != "draft" for item in members):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="INVALID_STATE_TRANSITION: la OT no está disponible para edición",
        )
    if any(
        item.signature_session_id is not None
        and not (item.reopen_ticket_id and item.signature_preserved)
        for item in members
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La cohorte ya fue firmada y no admite cambios ordinarios",
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


def _member_signatures_preserved(members: list[LabWorkOrder]) -> bool:
    """True when the members' current signature comes from a preserved reopening
    approved with requested_signature_policy = "preserve".

    ``_ensure_members_editable`` already guarantees that, once a member is
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
        for item in members
    )


def invalidate_member_signatures(
    db: Session, members: list[LabWorkOrder], user: User, *, fields: list[str]
) -> None:
    mutable_members = [item for item in members if item.status != "completed"]
    if not any(item.signature_session_id is not None for item in mutable_members):
        return
    previous_session_ids = sorted(
        {
            item.signature_session_id
            for item in mutable_members
            if item.signature_session_id is not None
        }
    )
    for item in mutable_members:
        item.signature_session_id = None
        item.signature_required = True
        item.signature_preserved = False
    write_audit_log(
        db,
        action="lab_work_order.signatures_invalidated",
        entity="lab_work_orders",
        entity_id=_root_id(mutable_members[0]),
        user_id=user.id,
        previous_values={"signature_session_ids": previous_session_ids},
        new_values={
            "critical_fields": fields,
            "signature_required": True,
            "work_order_ids": [item.id for item in mutable_members],
        },
    )
    ticket_id = next(
        (item.reopen_ticket_id for item in mutable_members if item.reopen_ticket_id), None
    )
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
    by_id = {item.id: item for item in work_order.equipment}
    for projected in result.equipment:
        source = by_id[projected.id]
        projected.field_sheet_id = source.field_sheet.id if source.field_sheet else None
        projected.field_sheet_status = source.field_sheet.status if source.field_sheet else None
    result.signature_scope = _recorded_signature_scope(
        db, work_order.signature_session_id
    )
    result.related_work_orders = [
        LabRelatedWorkOrderRead(**{
            "id": item.id,
            "folio": item.folio,
            "sequence_number": item.sequence_number,
            "status": item.status,
            "signature_session_id": item.signature_session_id,
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
    lab_client_id = values.get("lab_client_id")
    if lab_client_id is not None:
        client = db.scalar(
            select(LabClient).where(
                LabClient.id == lab_client_id,
                LabClient.operator_client_id.is_(None)
                if operator_client_id is None
                else LabClient.operator_client_id == operator_client_id,
                LabClient.is_active.is_(True),
            )
        )
        if client is None:
            raise HTTPException(status_code=404, detail="Cliente LAB no encontrado")
        values.update(
            client_name=client.company,
            address=client.address or values.get("address"),
            contact_name=client.attention or values.get("contact_name"),
        )
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
    lab_client_id = values.get("lab_client_id")
    if lab_client_id is not None:
        client = db.scalar(
            select(LabClient).where(
                LabClient.id == lab_client_id,
                LabClient.operator_client_id.is_(None)
                if operator_client_id is None
                else LabClient.operator_client_id == operator_client_id,
                LabClient.is_active.is_(True),
            )
        )
        if client is None:
            raise HTTPException(status_code=404, detail="Cliente LAB no encontrado")
        values.update(
            client_name=client.company,
            address=client.address or values.get("address"),
            contact_name=client.attention or values.get("contact_name"),
        )
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
        if request.requested_by_user_id == user.id:
            raise HTTPException(status_code=403, detail="TICKET_SELF_APPROVAL_FORBIDDEN")
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
    if request.requested_by_user_id == user.id:
        raise HTTPException(status_code=403, detail="TICKET_SELF_APPROVAL_FORBIDDEN")
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
        query = query.where(
            LabWorkOrder.status.in_(
                ("draft", "received_signed", "in_progress", "ready_for_signatures", "ready_to_close")
            )
        )
    elif work_order_status == "completed":
        query = query.where(
            LabWorkOrder.status.in_(("completed", "partially_closed", "cancelled"))
        )
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
            completed_equipment_count=sum(
                1 for equipment in item.equipment
                if equipment.field_sheet is not None and equipment.field_sheet.status == "completed"
            ),
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
        group_requests: list[LabWorkOrderGroupRequest] = []
        if work_order.id == root_id:
            group_requests = list(
                db.scalars(
                    select(LabWorkOrderGroupRequest)
                    .where(LabWorkOrderGroupRequest.root_work_order_id == root_id)
                    .with_for_update()
                ).all()
            )
            for group_request in group_requests:
                group_request.root_work_order_id = (
                    replacement.id if replacement is not None else None
                )

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
                "reconciled_group_request_ids": [
                    request.id for request in group_requests
                ],
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


def cancel_work_order(
    db: Session, work_order_id: int, user: User, reason: str
) -> LabWorkOrderRead:
    work_order = _get(db, work_order_id, lock=True)
    if work_order.status == "cancelled":
        return _read(db, work_order)
    if work_order.status in {"completed", "partially_closed"}:
        raise HTTPException(status_code=409, detail="Una OT cerrada requiere reapertura antes de cancelar")
    now = datetime.now(timezone.utc)
    previous = work_order.status
    work_order.status = "cancelled"
    work_order.cancelled_at = now
    work_order.cancelled_by_user_id = user.id
    work_order.cancellation_reason = reason.strip()
    write_audit_log(
        db,
        action="lab_work_order.cancelled",
        entity="lab_work_orders",
        entity_id=work_order.id,
        user_id=user.id,
        previous_values={"status": previous},
        new_values={
            "status": "cancelled",
            "cancelled_at": now.isoformat(),
            "cancellation_reason": work_order.cancellation_reason,
        },
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order.id))


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
    _ensure_members_editable([work_order])
    editable_members = _editable_group_members(group)
    updates = payload.model_dump(exclude_unset=True)
    expected_edit_version = updates.pop("expected_edit_version", None)
    if "lab_client_id" in updates:
        client = db.scalar(
            select(LabClient).where(
                LabClient.id == updates["lab_client_id"],
                LabClient.operator_client_id.is_(None)
                if operator_client_id is None
                else LabClient.operator_client_id == operator_client_id,
                LabClient.is_active.is_(True),
            )
        )
        if client is None:
            raise HTTPException(status_code=404, detail="Cliente LAB no encontrado")
        # El catálogo manda cuando tiene dato; si el catálogo está vacío (permitido
        # desde que sólo Empresa es obligatoria), se respeta lo que el propio
        # payload ya traía como snapshot editable de esta OT, o si tampoco lo trae,
        # se deja el valor que ya tenía la OT sin tocar.
        updates["client_name"] = client.company
        updates["address"] = client.address or updates.get("address", work_order.address)
        updates["contact_name"] = client.attention or updates.get("contact_name", work_order.contact_name)
    _check_edit_version(editable_members, expected_edit_version)
    reception = updates.get("reception_date", work_order.reception_date)
    departure = updates.get("departure_date", work_order.departure_date)
    if departure < reception:
        raise HTTPException(status_code=422, detail="La salida no puede ser anterior a la recepción")
    changed_fields = sorted(
        key for key, value in updates.items() if getattr(work_order, key) != value
    )
    if CRITICAL_GENERAL_FIELDS.intersection(changed_fields) and not _member_signatures_preserved(
        editable_members
    ):
        invalidate_member_signatures(db, editable_members, user, fields=changed_fields)
    for item in editable_members:
        for key, value in updates.items():
            setattr(item, key, value)
    if changed_fields:
        _bump_edit_version(editable_members)
    write_audit_log(
        db,
        action="lab_work_order.group_updated",
        entity="lab_work_orders",
        entity_id=_root_id(work_order),
        user_id=user.id,
        new_values={
            "fields": sorted(updates),
            "work_order_ids": [item.id for item in editable_members],
        },
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order.id))


def _add_equipment_core(
    db: Session,
    work_order: LabWorkOrder,
    group: list[LabWorkOrder],
    editable_members: list[LabWorkOrder],
    values: dict,
    user: User,
) -> LabWorkOrderEquipment:
    """Núcleo sin commit de add_equipment: crea la fila y hace flush, pero deja
    la transacción abierta para que un caller (el endpoint público, o Fase 2
    create_configured_equipment) decida cuándo confirmar/hacer rollback."""
    if work_order.reopen_ticket_id:
        invalidate_member_signatures(
            db,
            _affected_signature_members(group, work_order),
            user,
            fields=["equipment.added"],
        )
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
    _bump_edit_version(editable_members)
    write_audit_log(
        db,
        action="lab_work_order.equipment_added",
        entity="lab_work_order_equipment",
        entity_id=equipment.id,
        user_id=user.id,
        new_values={"work_order_id": work_order.id, "position": equipment.position},
    )
    return equipment


def add_equipment(
    db: Session, work_order_id: int, payload: LabEquipmentWrite, user: User
) -> LabWorkOrderRead:
    work_order = _get(db, work_order_id, lock=True)
    group = _group(db, work_order, lock=True)
    _ensure_members_editable([work_order])
    editable_members = _editable_group_members(group)
    values = payload.model_dump()
    expected_edit_version = values.pop("expected_edit_version", None)
    _check_edit_version(editable_members, expected_edit_version)
    _add_equipment_core(db, work_order, group, editable_members, values, user)
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order.id))


def _update_equipment_core(
    db: Session,
    work_order: LabWorkOrder,
    group: list[LabWorkOrder],
    editable_members: list[LabWorkOrder],
    equipment: LabWorkOrderEquipment,
    values: dict,
    user: User,
) -> LabWorkOrderEquipment:
    """Núcleo sin commit de update_equipment: actualiza los datos básicos del
    equipo y hace flush, sin confirmar la transacción -- para que el endpoint
    público y update_configured_equipment (Fase 2 hardening) puedan decidir
    cuándo confirmar/revertir."""
    changed_fields = sorted(
        key for key, value in values.items() if getattr(equipment, key) != value
    )
    affected_signature_members = _affected_signature_members(group, work_order)
    if CRITICAL_EQUIPMENT_FIELDS.intersection(changed_fields) and not _member_signatures_preserved(
        affected_signature_members
    ):
        invalidate_member_signatures(
            db, affected_signature_members, user, fields=changed_fields
        )
    for key, value in values.items():
        setattr(equipment, key, value)
    if changed_fields:
        _bump_edit_version(editable_members)
    write_audit_log(
        db,
        action="lab_work_order.equipment_updated",
        entity="lab_work_order_equipment",
        entity_id=equipment.id,
        user_id=user.id,
        new_values={"work_order_id": work_order.id},
    )
    return equipment


def update_equipment(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: LabEquipmentWrite,
    user: User,
) -> LabWorkOrderRead:
    work_order = _get(db, work_order_id, lock=True)
    group = _group(db, work_order, lock=True)
    _ensure_members_editable([work_order])
    editable_members = _editable_group_members(group)
    values = payload.model_dump()
    expected_edit_version = values.pop("expected_edit_version", None)
    _check_edit_version(editable_members, expected_edit_version)
    equipment = db.scalar(
        select(LabWorkOrderEquipment).where(
            LabWorkOrderEquipment.id == equipment_id,
            LabWorkOrderEquipment.work_order_id == work_order.id,
        )
    )
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")
    _update_equipment_core(db, work_order, group, editable_members, equipment, values, user)
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order.id))


def resolve_equipment_certificate_client(
    equipment: LabWorkOrderEquipment, work_order: LabWorkOrder
) -> dict:
    """Fase 1A: resuelve el cliente documental de un equipo. En modo 'order'
    (default) refleja el snapshot vigente de la OT; en modo 'different' usa
    el snapshot congelado en el propio equipo, que nunca se recalcula desde
    LabClient. Punto único de lectura para que FieldSheet/certificado (fases
    posteriores) no reinventen esta resolución."""
    if equipment.certificate_client_mode == "different":
        return {
            "company": equipment.final_client_company_snapshot,
            "address": equipment.final_client_address_snapshot,
            "attention": equipment.final_client_attention_snapshot,
        }
    return {
        "company": work_order.client_name,
        "address": work_order.address,
        "attention": work_order.contact_name,
    }


def _set_equipment_certificate_client_core(
    db: Session,
    equipment: LabWorkOrderEquipment,
    payload: LabEquipmentCertificateClientWrite,
    user: User,
    *,
    operator_client_id: int | None,
) -> None:
    """Núcleo sin commit de set_equipment_certificate_client. Fase 1A: fija el
    cliente documental de un equipo LAB, independiente del cliente de la OT.
    No crea Client productivo, no crea otro motor de FieldSheets: sólo
    persiste columnas propias de LabWorkOrderEquipment. La FK
    final_lab_client_id es procedencia; el snapshot es la autoridad histórica
    y no se resincroniza si el LabClient de origen cambia después.

    Endurecimiento de seguridad: cuando el payload trae final_lab_client_id,
    el backend es la única autoridad para los snapshots -- se cargan SIEMPRE
    desde el LabClient validado (existe, is_active, mismo operator_client_id),
    nunca desde company/address/attention que Mobile haya podido enviar. Un
    payload manipulado que combine un final_lab_client_id real con snapshots
    falsos no puede persistir el dato falso: se descarta en silencio y se usa
    el LabClient real. Sólo si no hay final_lab_client_id (cliente final sin
    referencia de catálogo) se confía en el snapshot que trae el payload.
    """
    company_snapshot = payload.final_client_company_snapshot
    address_snapshot = payload.final_client_address_snapshot
    attention_snapshot = payload.final_client_attention_snapshot
    if payload.final_lab_client_id is not None:
        origin = db.scalar(
            select(LabClient).where(
                LabClient.id == payload.final_lab_client_id,
                LabClient.operator_client_id.is_(None)
                if operator_client_id is None
                else LabClient.operator_client_id == operator_client_id,
                LabClient.is_active.is_(True),
            )
        )
        if origin is None:
            raise HTTPException(status_code=404, detail="Cliente LAB no encontrado")
        company_snapshot = origin.company
        address_snapshot = origin.address or None
        attention_snapshot = origin.attention or None
    equipment.certificate_client_mode = payload.certificate_client_mode
    equipment.final_lab_client_id = payload.final_lab_client_id
    equipment.final_client_company_snapshot = company_snapshot
    equipment.final_client_address_snapshot = address_snapshot
    equipment.final_client_attention_snapshot = attention_snapshot
    write_audit_log(
        db,
        action="lab_work_order.equipment_certificate_client_set",
        entity="lab_work_order_equipment",
        entity_id=equipment.id,
        user_id=user.id,
        new_values={
            "certificate_client_mode": equipment.certificate_client_mode,
            "final_lab_client_id": equipment.final_lab_client_id,
        },
    )


def set_equipment_certificate_client(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: LabEquipmentCertificateClientWrite,
    user: User,
    *,
    operator_client_id: int | None,
) -> LabWorkOrderRead:
    work_order = _get(db, work_order_id, lock=True)
    _ensure_members_editable([work_order])
    equipment = db.scalar(
        select(LabWorkOrderEquipment).where(
            LabWorkOrderEquipment.id == equipment_id,
            LabWorkOrderEquipment.work_order_id == work_order.id,
        )
    )
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")
    _set_equipment_certificate_client_core(
        db, equipment, payload, user, operator_client_id=operator_client_id
    )
    db.commit()
    return _read(db, _get(db, work_order.id))


def _allocate_lab_certificate_folio(db: Session, prefix: str) -> str:
    if prefix not in LAB_CERTIFICATE_STARTS:
        raise HTTPException(status_code=422, detail="Serie LAB no soportada")
    lock_key = f"lab_certificate:{prefix}"
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": lock_key})
    counter = db.scalar(
        select(InstitutionalFolioSequence)
        .where(
            InstitutionalFolioSequence.document_type == "lab_certificate",
            InstitutionalFolioSequence.prefix == prefix,
            InstitutionalFolioSequence.year == LAB_CERTIFICATE_SEQUENCE_YEAR,
        )
        .with_for_update()
    )
    start = LAB_CERTIFICATE_STARTS[prefix]
    if counter is None:
        counter = InstitutionalFolioSequence(
            document_type="lab_certificate",
            prefix=prefix,
            year=LAB_CERTIFICATE_SEQUENCE_YEAR,
            next_value=start,
        )
        db.add(counter)
        db.flush()
    sequence = max(counter.next_value, start)
    if sequence > LAB_CERTIFICATE_LIMIT:
        raise HTTPException(status_code=409, detail=f"Se agotó la secuencia temporal {prefix}")
    counter.next_value = sequence + 1
    today = date.today()
    db.flush()
    return f"{prefix}-{today:%m}-{today:%y}-{sequence:04d}"


def _assign_equipment_service_core(
    db: Session,
    work_order: LabWorkOrder,
    equipment: LabWorkOrderEquipment,
    payload: LabEquipmentServiceWrite,
    user: User,
    *,
    external: bool,
) -> LabWorkOrderEquipment:
    """Núcleo sin commit de assign_equipment_service.

    Fase 2G: si el equipo YA tiene un folio MYCA/MYCT reservado o autorizado,
    la trazabilidad prohíbe liberarlo/reasignarlo en silencio (no hay política
    existente de invalidar-y-reservar-otro para este flujo). Reconfirmar
    exactamente el mismo servicio es un no-op seguro; cualquier otro cambio se
    bloquea con 409 explícito en vez de reciclar el folio ya emitido.
    """
    if equipment.field_sheet is not None:
        raise HTTPException(status_code=409, detail="La hoja existente congela el tipo de servicio")
    folio_already_secured = (
        equipment.certificate_folio is not None
        or equipment.folio_status in {"reserved", "authorized"}
    )
    if folio_already_secured:
        unchanged = (
            equipment.service_type == payload.service_type
            and equipment.linked_company_id == payload.linked_company_id
        )
        if unchanged:
            return equipment
        raise HTTPException(
            status_code=409,
            detail=(
                "El equipo ya tiene un folio MYCA/MYCT reservado; cambiar el "
                "servicio requiere el flujo de reapertura/ticket existente, no "
                "se libera ni reutiliza el folio en curso"
            ),
        )

    linked = None
    if payload.service_type == "linked":
        if payload.linked_company_id is not None:
            linked = db.scalar(
                select(LinkedCompany).where(
                    LinkedCompany.id == payload.linked_company_id,
                    LinkedCompany.is_active.is_(True),
                )
            )
            if linked is None:
                raise HTTPException(status_code=404, detail="Empresa vinculada no encontrada")
        elif not external:
            raise HTTPException(status_code=422, detail="Selecciona la empresa vinculada")
    elif payload.linked_company_id is not None:
        raise HTTPException(status_code=422, detail="LinkedCompany sólo aplica a Vinculado")

    previous = {
        "service_type": equipment.service_type,
        "certificate_folio": equipment.certificate_folio,
        "folio_status": equipment.folio_status,
    }
    equipment.service_type = payload.service_type
    equipment.linked_company_id = linked.id if linked else None
    equipment.linked_company_name_snapshot = linked.name if linked else None
    equipment.linked_company_prefix_snapshot = linked.default_certificate_prefix if linked else None
    equipment.certificate_folio = None
    equipment.automatic_certificate_folio = None
    equipment.folio_ticket_id = None
    if payload.service_type in {"accredited", "traceable"}:
        prefix = "MYCA" if payload.service_type == "accredited" else "MYCT"
        folio = None
        if external:
            requests = db.scalars(
                select(OperationalTicket)
                .where(
                    OperationalTicket.type == "certificate_folio_block",
                    OperationalTicket.operator_client_id == work_order.operator_client_id,
                    OperationalTicket.status == "resolved",
                )
                .order_by(OperationalTicket.created_at)
                .with_for_update()
            ).all()
            for request in requests:
                snapshot = dict(request.resolution_snapshot or {})
                available = list((snapshot.get("folios") or {}).get(prefix) or [])
                used = dict(snapshot.get("used") or {})
                folio = next((value for value in available if value not in used), None)
                if folio:
                    used[folio] = {"equipment_id": equipment.id, "assigned_at": datetime.now(timezone.utc).isoformat()}
                    request.resolution_snapshot = {**snapshot, "used": used}
                    break
        else:
            folio = _allocate_lab_certificate_folio(db, prefix)
        if folio:
            equipment.certificate_folio = folio
            equipment.automatic_certificate_folio = folio
            equipment.folio_status = "reserved"
            action = "lab_equipment.folio_reserved"
        else:
            equipment.folio_status = "pending"
            action = "lab_equipment.service_assigned"
    else:
        equipment.folio_status = "pending"
        action = "lab_equipment.service_assigned"
    write_audit_log(
        db,
        action=action,
        entity="lab_work_order_equipment",
        entity_id=equipment.id,
        user_id=user.id,
        previous_values=previous,
        new_values={
            "service_type": equipment.service_type,
            "linked_company_id": equipment.linked_company_id,
            "linked_company_name_snapshot": equipment.linked_company_name_snapshot,
            "linked_company_prefix_snapshot": equipment.linked_company_prefix_snapshot,
            "certificate_folio": equipment.certificate_folio,
            "folio_status": equipment.folio_status,
        },
    )
    return equipment


def assign_equipment_service(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: LabEquipmentServiceWrite,
    user: User,
    *,
    external: bool,
) -> LabWorkOrderRead:
    work_order = _get(db, work_order_id, lock=True)
    _ensure_members_editable([work_order])
    equipment = db.scalar(
        select(LabWorkOrderEquipment)
        .where(
            LabWorkOrderEquipment.id == equipment_id,
            LabWorkOrderEquipment.work_order_id == work_order.id,
        )
        .with_for_update()
    )
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")
    _assign_equipment_service_core(db, work_order, equipment, payload, user, external=external)
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order.id))


def create_configured_equipment(
    db: Session,
    work_order_id: int,
    payload: LabEquipmentConfiguredCreate,
    user: User,
    *,
    operator_client_id: int | None,
    external: bool,
) -> LabWorkOrderRead:
    """Fase 2E: alta integrada de equipo — datos del equipo + cliente
    documental + servicio/folio — como una sola operación atómica.

    Reutiliza exactamente las mismas autoridades que los endpoints
    individuales (_add_equipment_core / _set_equipment_certificate_client_core
    / _assign_equipment_service_core) sin duplicar su lógica; sólo mueve el
    límite de commit al final para que un fallo en cualquier paso (p.ej. no
    hay más folios MYCA disponibles) revierta TODO, incluido el equipo recién
    creado — nunca debe quedar un equipo huérfano parcialmente configurado.
    """
    try:
        work_order = _get(db, work_order_id, lock=True)
        group = _group(db, work_order, lock=True)
        _ensure_members_editable([work_order])
        editable_members = _editable_group_members(group)
        equipment_values = payload.equipment.model_dump()
        expected_edit_version = equipment_values.pop("expected_edit_version", None)
        _check_edit_version(editable_members, expected_edit_version)

        equipment = _add_equipment_core(
            db, work_order, group, editable_members, equipment_values, user
        )

        certificate_client = payload.certificate_client
        if certificate_client is not None and certificate_client.certificate_client_mode == "different":
            _set_equipment_certificate_client_core(
                db, equipment, certificate_client, user, operator_client_id=operator_client_id
            )

        _assign_equipment_service_core(
            db, work_order, equipment, payload.service, user, external=external
        )
    except Exception:
        db.rollback()
        raise
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order.id))


def update_configured_equipment(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: LabEquipmentConfiguredCreate,
    user: User,
    *,
    operator_client_id: int | None,
    external: bool,
) -> LabWorkOrderRead:
    """Fase 2 hardening: edición integrada de un equipo ya existente -- datos
    del equipo + cliente documental + servicio/folio como una sola operación
    atómica, análoga a create_configured_equipment. El botón único "Guardar"
    de Mobile debe corresponder a UNA sola transacción backend: si cualquier
    parte falla (p.ej. 409 porque el folio ya está reserved/authorized),
    absolutamente nada de la edición persiste -- ni los datos básicos, ni el
    cliente documental, ni edit_version quedan a medio actualizar.

    Reutiliza exactamente los mismos núcleos sin commit que ya usan
    update_equipment / set_equipment_certificate_client / assign_equipment_service
    (_update_equipment_core, _set_equipment_certificate_client_core,
    _assign_equipment_service_core); no duplica ninguna de sus reglas
    (versión de edición, invalidación de firmas, guard de folio ya
    reservado, autoridad de snapshot de LabClient, scope de LinkedCompany).
    """
    try:
        work_order = _get(db, work_order_id, lock=True)
        group = _group(db, work_order, lock=True)
        _ensure_members_editable([work_order])
        editable_members = _editable_group_members(group)
        equipment = db.scalar(
            select(LabWorkOrderEquipment)
            .where(
                LabWorkOrderEquipment.id == equipment_id,
                LabWorkOrderEquipment.work_order_id == work_order.id,
            )
            .with_for_update()
        )
        if equipment is None:
            raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")

        equipment_values = payload.equipment.model_dump()
        expected_edit_version = equipment_values.pop("expected_edit_version", None)
        _check_edit_version(editable_members, expected_edit_version)

        _update_equipment_core(db, work_order, group, editable_members, equipment, equipment_values, user)

        # A diferencia de create_configured_equipment, aquí SIEMPRE se aplica
        # el cliente documental (incluido el 'order' implícito por omisión):
        # el equipo puede venir de un 'different' previo y el usuario eligió
        # volver a 'order' en el formulario -- omitir la llamada dejaría el
        # 'different' anterior sin revertir.
        certificate_client = payload.certificate_client or LabEquipmentCertificateClientWrite(
            certificate_client_mode="order"
        )
        _set_equipment_certificate_client_core(
            db, equipment, certificate_client, user, operator_client_id=operator_client_id
        )

        _assign_equipment_service_core(
            db, work_order, equipment, payload.service, user, external=external
        )
    except Exception:
        db.rollback()
        raise
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order.id))


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
    _ensure_members_editable([work_order])
    editable_members = _editable_group_members(group)
    _check_edit_version(editable_members, expected_edit_version)
    equipment = db.scalar(
        select(LabWorkOrderEquipment).where(
            LabWorkOrderEquipment.id == equipment_id,
            LabWorkOrderEquipment.work_order_id == work_order.id,
        )
    )
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")
    if work_order.reopen_ticket_id:
        invalidate_member_signatures(
            db,
            _affected_signature_members(group, work_order),
            user,
            fields=["equipment.deleted"],
        )
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
    _bump_edit_version(editable_members)
    write_audit_log(
        db,
        action="lab_work_order.equipment_deleted",
        entity="lab_work_order_equipment",
        entity_id=equipment_id,
        user_id=user.id,
        previous_values={"work_order_id": work_order.id, "position": removed_position},
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order.id))


def create_additional_work_order(db: Session, work_order_id: int, user: User) -> LabWorkOrderRead:
    source = _get(db, work_order_id, lock=True)
    group = _group(db, source, lock=True)
    _ensure_members_editable([source])
    editable_members = _editable_group_members(group)
    if source.reopen_ticket_id:
        invalidate_member_signatures(
            db,
            _affected_signature_members(group, source),
            user,
            fields=["work_order.additional"],
        )
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
    _bump_edit_version([*editable_members, additional])
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


def _create_signature_session(
    db: Session,
    *,
    root_work_order_id: int,
    payload: LabSignatureGroupWrite,
    user: User,
) -> LabWorkOrderSignatureSession:
    _decode_signature(payload.technician.signature_data_url)
    _decode_signature(payload.client.signature_data_url)
    now = datetime.now(timezone.utc)
    latest_version = db.scalar(
        select(func.max(LabWorkOrderSignatureSession.version)).where(
            LabWorkOrderSignatureSession.root_work_order_id == root_work_order_id
        )
    ) or 0
    session = LabWorkOrderSignatureSession(
        root_work_order_id=root_work_order_id,
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
    return session


def _recorded_signature_scope(
    db: Session, signature_session_id: int | None
) -> str | None:
    if signature_session_id is None:
        return None
    audits = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.action.in_(
                (
                    "lab_work_order.individual_signed",
                    "lab_work_order.group_signed",
                )
            )
        )
        .order_by(AuditLog.id.desc())
    )
    for audit in audits:
        values = audit.new_values or {}
        if values.get("signature_session_id") == signature_session_id:
            return values.get("scope") or (
                "individual"
                if audit.action == "lab_work_order.individual_signed"
                else "group"
            )
    return None


def _equipment_reception_gap(equipment: LabWorkOrderEquipment) -> str | None:
    """Fase 3: describe por qué un equipo aún no puede recibirse (firmarse),
    o None si ya está coherente. El cliente documental no se valida aquí --
    'order' siempre hereda client_name (NOT NULL en la OT) y 'different'
    siempre exige un snapshot de empresa no vacío (CHECK constraint de Fase
    1), así que ambos modos son resolubles por construcción."""
    if equipment.service_type is None:
        return "Selecciona el tipo de servicio"
    if equipment.service_type in {"accredited", "traceable"} and equipment.folio_status not in {
        "reserved", "authorized"
    }:
        return "El equipo requiere folio MYCA/MYCT asignado"
    if equipment.service_type == "linked" and equipment.linked_company_id is None:
        return "Selecciona la empresa vinculada"
    return None


def _ensure_reception_prerequisites(members: list[LabWorkOrder]) -> None:
    """Fase 3: antes de firmar la recepción (draft -> received_signed), cada
    equipo de la cohorte debe traer una configuración operacional coherente.
    Vinculado con folio de autorización pendiente SÍ puede firmar recepción
    -- esa autorización sigue siendo un requisito técnico posterior (no se
    reconstruye aquí el flujo de tickets linked_folio)."""
    incomplete = [
        {
            "work_order_id": item.id,
            "work_order_folio": item.folio,
            "equipment_id": equipment.id,
            "equipment_position": equipment.position,
            "equipment": equipment.instrument,
            "reason": reason,
        }
        for item in members
        for equipment in item.equipment
        for reason in [_equipment_reception_gap(equipment)]
        if reason is not None
    ]
    if incomplete:
        raise HTTPException(
            status_code=409,
            detail={"code": "LAB_RECEPTION_INCOMPLETE", "items": incomplete},
        )


def _sign_members(
    db: Session,
    *,
    work_order: LabWorkOrder,
    members: list[LabWorkOrder],
    payload: LabSignatureGroupWrite,
    user: User,
    scope: str,
) -> LabWorkOrderRead:
    """Fase 3: la firma representa CONFORMIDAD DE RECEPCIÓN (equipos y
    condiciones aceptados para ejecutar el servicio), no el cierre técnico.
    Reutiliza exactamente _create_signature_session (misma autoridad de
    firma técnico/cliente que ya existía); sólo cambia el estado resultante
    y el momento del flujo en que se invoca (antes de FieldSheets, no
    después). No se reasignan FieldSheets existentes a esta sesión aquí --
    bajo el nuevo flujo no existen todavía en el caso normal, y en el caso de
    una reapertura que invalidó la firma, unas hojas ya capturadas bajo la
    sesión histórica anterior no deben reescribirse hacia la nueva (ver
    sección 16: no sobrescribir la sesión histórica). Las FieldSheets nuevas
    se vinculan a la sesión vigente en el momento de su propia creación
    (create_lab_field_sheet)."""
    root_work_order_id = _root_id(work_order)
    session = _create_signature_session(
        db,
        root_work_order_id=root_work_order_id,
        payload=payload,
        user=user,
    )
    for item in members:
        item.signature_session_id = session.id
        item.status = "received_signed"
        item.signature_required = False
        item.signature_preserved = False
    write_audit_log(
        db,
        action=(
            "lab_work_order.individual_signed"
            if scope == "individual"
            else "lab_work_order.group_signed"
        ),
        entity="lab_work_orders",
        entity_id=work_order.id if scope == "individual" else root_work_order_id,
        user_id=user.id,
        new_values={
            "root_work_order_id": root_work_order_id,
            "signature_session_id": session.id,
            "work_order_ids": [item.id for item in members],
            "scope": scope,
        },
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order.id))


def _missing_completed_sheets(members: list[LabWorkOrder]) -> list[dict]:
    return [
        {
            "work_order_id": item.id,
            "work_order_folio": item.folio,
            "equipment_id": equipment.id,
            "equipment_position": equipment.position,
            "equipment": equipment.instrument,
            "field_sheet_status": equipment.field_sheet.status if equipment.field_sheet else "missing",
        }
        for item in members
        for equipment in item.equipment
        # Historical OT created before the LAB client/capture contract remain
        # closable. Every OT created by the evolved flow carries lab_client_id
        # and therefore requires a completed sheet for each equipment item.
        if item.lab_client_id is not None
        if equipment.field_sheet is None or equipment.field_sheet.status != "completed"
    ]


def _unresolved_folio_equipment(members: list[LabWorkOrder]) -> list[dict]:
    """Fase 5: frontera de cierre autoritativa para folios. La captura
    externa (Fase 3, _ensure_capture_allowed) puede avanzar con un folio
    Vinculado todavía "pending" -- eso es deliberado, para no bloquear al
    cliente mientras MYC resuelve la autorización. Pero el cierre staff sí
    exige el folio ya resuelto: una FieldSheet completed no implica un folio
    documental resuelto, y sin esto la OT podía cerrar con MYCA/MYCT sin
    reservar o Vinculado sin autorizar. Misma frontera histórica que
    _missing_completed_sheets (item.lab_client_id is not None)."""
    return [
        {
            "work_order_id": item.id,
            "work_order_folio": item.folio,
            "equipment_id": equipment.id,
            "equipment_position": equipment.position,
            "equipment": equipment.instrument,
            "service_type": equipment.service_type,
            "folio_status": equipment.folio_status,
        }
        for item in members
        for equipment in item.equipment
        if item.lab_client_id is not None
        if (
            equipment.service_type in {"accredited", "traceable"}
            and equipment.folio_status not in {"reserved", "authorized"}
        )
        or (equipment.service_type == "linked" and equipment.folio_status != "authorized")
    ]


def _ensure_staff_sheet_prerequisites(members: list[LabWorkOrder]) -> None:
    missing = _missing_completed_sheets(members)
    exempt_ids = {item.id for item in members if item.partial_close_ticket_id is not None}
    blocking = [item for item in missing if item["work_order_id"] not in exempt_ids]
    if blocking:
        raise HTTPException(
            status_code=409,
            detail={"code": "LAB_FIELD_SHEETS_INCOMPLETE", "items": blocking},
        )
    unresolved_folios = _unresolved_folio_equipment(members)
    if unresolved_folios:
        raise HTTPException(
            status_code=409,
            detail={"code": "LAB_FOLIOS_UNRESOLVED", "items": unresolved_folios},
        )


def _closable_status(item: LabWorkOrder) -> bool:
    """Fase 3: el cierre normal exige ready_to_close (trabajo técnico
    completo, ver complete_lab_field_sheet). 'ready_for_signatures' se
    conserva como equivalente legacy -- una OT firmada bajo el flujo anterior
    a esta fase puede seguir cerrando exactamente igual que antes, sin
    fingir que pasó por recepción/ready_to_close. Una OT sin lab_client_id
    (anterior al contrato de cliente LAB/captura) conserva la excepción ya
    existente de _missing_completed_sheets: no requiere FieldSheets
    completas para cerrar, así que basta con que ya esté firmada
    (received_signed/in_progress), sin necesidad de alcanzar ready_to_close.
    Una reapertura 'preserve' vuelve a draft con la firma histórica intacta
    (signature_preserved=True) -- exactamente el mismo camino de cierre que
    ya existía antes de esta fase, sin necesidad de re-pasar por
    received_signed/ready_to_close."""
    if item.status in {"ready_to_close", "ready_for_signatures"}:
        return True
    if item.lab_client_id is None and item.status in {"received_signed", "in_progress"}:
        return True
    return item.status == "draft" and bool(item.reopen_ticket_id) and item.signature_preserved


def sign_group(
    db: Session, work_order_id: int, payload: LabSignatureGroupWrite, user: User,
) -> LabWorkOrderRead:
    work_order, group = _lock_historical_group(db, work_order_id)
    _ensure_members_editable([work_order])
    members = [
        item
        for item in _editable_group_members(group)
        if item.signature_session_id is None or item.signature_required
    ]
    if work_order not in members:
        raise HTTPException(status_code=409, detail="La OT ya conserva una firma válida")
    if any(not item.equipment for item in members):
        raise HTTPException(
            status_code=409,
            detail="Todas las OT abiertas de la cohorte deben tener al menos un equipo",
        )
    _ensure_reception_prerequisites(members)
    return _sign_members(
        db,
        work_order=work_order,
        members=members,
        payload=payload,
        user=user,
        scope="group",
    )


def sign_individual(
    db: Session, work_order_id: int, payload: LabSignatureGroupWrite, user: User,
) -> LabWorkOrderRead:
    work_order, _group_members = _lock_historical_group(db, work_order_id)
    _ensure_members_editable([work_order])
    if work_order.signature_session_id is not None and not work_order.signature_required:
        raise HTTPException(status_code=409, detail="La OT ya conserva una firma válida")
    if not work_order.equipment:
        raise HTTPException(
            status_code=409, detail="La OT debe tener al menos un equipo"
        )
    _ensure_reception_prerequisites([work_order])
    return _sign_members(
        db,
        work_order=work_order,
        members=[work_order],
        payload=payload,
        user=user,
        scope="individual",
    )


def _complete_members(
    db: Session,
    *,
    work_order: LabWorkOrder,
    members: list[LabWorkOrder],
    user: User,
    scope: str,
    require_completed_sheets: bool = True,
) -> LabWorkOrderRead:
    if not members or any(
        item.signature_session_id is None or item.signature_required for item in members
    ):
        raise HTTPException(
            status_code=409, detail="La cohorte requiere las firmas de técnico y cliente"
        )
    if require_completed_sheets:
        # El detalle de hojas faltantes (por equipo) es más informativo que un
        # simple INVALID_STATE_TRANSITION, así que se revisa primero -- para
        # cualquier miembro no exento, si ya está ready_to_close no puede
        # haber hojas faltantes (invariante mantenido por
        # complete_lab_field_sheet), y si aún no llegó, esto explica
        # exactamente qué falta.
        _ensure_staff_sheet_prerequisites(members)
        if any(not _closable_status(item) for item in members):
            raise HTTPException(status_code=409, detail="INVALID_STATE_TRANSITION")
    else:
        # Fase 3 preserva el comportamiento previo a esta fase para actores
        # externos: nunca estuvieron sujetos al requisito de hojas completas
        # (antes se evaluaba, condicionado a actor interno, en el momento de
        # firmar; ahora ese momento es el cierre). Sólo se exige que la
        # recepción ya esté firmada.
        if any(
            not _closable_status(item) and item.status not in {"received_signed", "in_progress"}
            for item in members
        ):
            raise HTTPException(status_code=409, detail="INVALID_STATE_TRANSITION")
    session_ids = {item.signature_session_id for item in members}
    if len(session_ids) != 1:
        raise HTTPException(
            status_code=409, detail="La cohorte no comparte una única sesión de firma"
        )
    signature_session_id = next(iter(session_ids))
    recorded_scope = _recorded_signature_scope(db, signature_session_id) or scope
    completed_at = datetime.now(timezone.utc)
    for item in members:
        pdf, _ = generate_lab_work_order_pdf(item)
        item.final_pdf = pdf
        item.final_pdf_sha256 = hashlib.sha256(pdf).hexdigest()
        item.final_pdf_generated_at = completed_at
        item.completed_at = completed_at
        item.status = "partially_closed" if item.partial_close_ticket_id else "completed"
        if item.partial_close_ticket_id:
            item.partially_closed_at = completed_at
        item.signature_preserved = bool(item.reopen_ticket_id and item.signature_preserved)
    ticket_ids = {item.reopen_ticket_id for item in members if item.reopen_ticket_id}
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
        action=(
            "lab_work_order.individual_completed"
            if recorded_scope == "individual"
            else "lab_work_order.group_completed"
        ),
        entity="lab_work_orders",
        entity_id=(
            work_order.id
            if recorded_scope == "individual"
            else _root_id(work_order)
        ),
        user_id=user.id,
        new_values={
            "root_work_order_id": _root_id(work_order),
            "signature_session_id": signature_session_id,
            "work_order_ids": [item.id for item in members],
            "scope": recorded_scope,
            "completed_at": completed_at.isoformat(),
        },
    )
    commit_and_dispatch_notifications(db)
    return _read(db, _get(db, work_order.id))


def complete_group(
    db: Session, work_order_id: int, user: User, *, require_completed_sheets: bool = True
) -> LabWorkOrderRead:
    work_order, group = _lock_historical_group(db, work_order_id)
    if work_order.status in {"completed", "partially_closed"}:
        return _read(db, work_order)
    if _recorded_signature_scope(db, work_order.signature_session_id) == "individual":
        raise HTTPException(
            status_code=409,
            detail="La sesión es individual y debe completarse con esa modalidad",
        )
    members = _signature_cohort(group, work_order)
    return _complete_members(
        db,
        work_order=work_order,
        members=members,
        user=user,
        scope="group",
        require_completed_sheets=require_completed_sheets,
    )


def complete_individual(
    db: Session, work_order_id: int, user: User, *, require_completed_sheets: bool = True
) -> LabWorkOrderRead:
    work_order, group = _lock_historical_group(db, work_order_id)
    if work_order.status in {"completed", "partially_closed"}:
        return _read(db, work_order)
    if _recorded_signature_scope(db, work_order.signature_session_id) == "group":
        raise HTTPException(
            status_code=409,
            detail="La sesión es grupal y debe completarse como cohorte",
        )
    members = _signature_cohort(group, work_order)
    if [item.id for item in members] != [work_order.id]:
        raise HTTPException(
            status_code=409,
            detail="La sesión pertenece a una cohorte grupal y debe completarse como grupo",
        )
    return _complete_members(
        db,
        work_order=work_order,
        members=members,
        user=user,
        scope="individual",
        require_completed_sheets=require_completed_sheets,
    )


def get_pdf(db: Session, work_order_id: int) -> tuple[bytes, str]:
    work_order = _get(db, work_order_id)
    if work_order.status not in {"completed", "partially_closed"} or not work_order.final_pdf:
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
