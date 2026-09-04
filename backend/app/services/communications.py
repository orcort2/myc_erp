from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
import re

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased, joinedload, selectinload

from app.models.client import Client
from app.models.communication import (
    CommunicationConversation,
    CommunicationMessage,
    CommunicationMessageMention,
    CommunicationMessageReceipt,
    communication_participants,
)
from app.models.notification import Notification
from app.models.lab_work_order import LabWorkOrder
from app.models.operational_ticket import OperationalTicket
from app.models.user import User
from app.schemas.communication import (
    CommunicationActorRead,
    CommunicationClientRead,
    CommunicationConversationDetail,
    CommunicationConversationRead,
    CommunicationMentionInboxItem,
    CommunicationMessagePage,
    CommunicationMessageRead,
    CommunicationWorkOrderMentionRead,
    CommunicationWorkOrderSuggestionRead,
    CommunicationReceiptBatchRead,
    CommunicationSyncRead,
)
from app.services.auth import user_has_permission
from app.services.push_notifications import queue_notification_for_delivery


MASS_MENTION_ROLES = {"administrador", "desarrollador", "calidad"}
_NOT_PROVIDED = object()
_WORK_ORDER_MARKER = re.compile(r"\n?\[\[work_order:(\d+)\]\]")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _message_options():
    return (
        joinedload(CommunicationMessage.sender),
        selectinload(CommunicationMessage.receipts),
        selectinload(CommunicationMessage.mentions),
    )


def _message_read(message: CommunicationMessage) -> CommunicationMessageRead:
    payload = CommunicationMessageRead.model_validate(message)
    ids = [int(value) for value in _WORK_ORDER_MARKER.findall(payload.body)]
    payload.body = _WORK_ORDER_MARKER.sub("", payload.body).rstrip()
    payload.work_order_mentions = [
        CommunicationWorkOrderMentionRead(work_order_id=value)
        for value in dict.fromkeys(ids)
    ]
    return payload


def _can_read_lab_work_orders(user: User) -> bool:
    return user.account_type == "internal" and any(
        user_has_permission(user, permission)
        for permission in (
            "lab_work_orders.use",
            "work_orders.read_organization",
            "work_orders.read",
        )
    )


def search_work_order_mentions(
    db: Session, current_user: User, query: str, *, limit: int = 10
) -> list[CommunicationWorkOrderSuggestionRead]:
    if not _can_read_lab_work_orders(current_user):
        raise HTTPException(status_code=403, detail="No tienes permiso para consultar OTs")
    normalized = query.strip()
    statement = select(LabWorkOrder)
    if normalized:
        folio_query = normalized.upper().removeprefix("OT-")
        criteria = [LabWorkOrder.client_name.ilike(f"%{normalized}%")]
        if folio_query.isdigit():
            criteria.append(LabWorkOrder.folio == int(folio_query))
        statement = statement.where(or_(*criteria))
    orders = list(
        db.scalars(statement.order_by(LabWorkOrder.folio.desc()).limit(limit)).all()
    )
    return [
        CommunicationWorkOrderSuggestionRead(
            work_order_id=item.id,
            folio=item.folio,
            client_name=item.client_name,
            status=item.status,
            label=f"OT-{item.folio} · {item.client_name} · {item.status}",
        )
        for item in orders
    ]


def _client_read(client: Client | None) -> CommunicationClientRead | None:
    if client is None:
        return None
    return CommunicationClientRead(
        id=client.id,
        name=client.commercial_name or client.legal_name,
        email=client.email,
    )


def _title(conversation: CommunicationConversation, current_user_id: int) -> str:
    if conversation.conversation_type == "client":
        return conversation.title or (
            _client_read(conversation.client).name if conversation.client else "Cliente"
        )
    others = [
        participant.full_name
        for participant in conversation.participants
        if participant.id != current_user_id
    ]
    return conversation.title or ", ".join(others) or "Conversación interna"


def _access_filter(conversation_id: int, user_id: int):
    participant_ids = select(communication_participants.c.conversation_id).where(
        communication_participants.c.user_id == user_id
    )
    return and_(
        CommunicationConversation.id == conversation_id,
        CommunicationConversation.archived_at.is_(None),
        or_(
            CommunicationConversation.id.in_(participant_ids),
            CommunicationConversation.created_by_user_id == user_id,
        ),
    )


def _conversation_query():
    return select(CommunicationConversation).options(
        selectinload(CommunicationConversation.participants),
        joinedload(CommunicationConversation.client),
    )


def get_conversation(
    db: Session, conversation_id: int, current_user_id: int, *, for_update: bool = False
) -> CommunicationConversation | None:
    query = _conversation_query().where(_access_filter(conversation_id, current_user_id))
    if for_update:
        query = query.with_for_update(of=CommunicationConversation)
    return db.scalar(query)


def _participant_ids(conversation: CommunicationConversation) -> set[int]:
    return {participant.id for participant in conversation.participants}


def _read_sequence(db: Session, conversation_id: int, user_id: int) -> int:
    last_read_id = db.scalar(
        select(communication_participants.c.last_read_message_id).where(
            communication_participants.c.conversation_id == conversation_id,
            communication_participants.c.user_id == user_id,
        )
    )
    if last_read_id is None:
        return 0
    return db.scalar(
        select(CommunicationMessage.sequence).where(
            CommunicationMessage.id == last_read_id,
            CommunicationMessage.conversation_id == conversation_id,
        )
    ) or 0


def _participant_cursor(
    db: Session, conversation_id: int, user_id: int, column
) -> tuple[int | None, int]:
    message_id = db.scalar(
        select(column).where(
            communication_participants.c.conversation_id == conversation_id,
            communication_participants.c.user_id == user_id,
        )
    )
    if message_id is None:
        return None, 0
    sequence = db.scalar(
        select(CommunicationMessage.sequence).where(
            CommunicationMessage.id == message_id,
            CommunicationMessage.conversation_id == conversation_id,
        )
    )
    return message_id, sequence or 0


def _unread_count(db: Session, conversation_id: int, user_id: int) -> int:
    read_sequence = _read_sequence(db, conversation_id, user_id)
    return int(
        db.scalar(
            select(func.count(CommunicationMessage.id)).where(
                CommunicationMessage.conversation_id == conversation_id,
                CommunicationMessage.sequence > read_sequence,
                CommunicationMessage.sender_user_id != user_id,
            )
        )
        or 0
    )


def _latest_message(
    db: Session, conversation_id: int
) -> CommunicationMessage | None:
    return db.scalar(
        select(CommunicationMessage)
        .where(CommunicationMessage.conversation_id == conversation_id)
        .options(*_message_options())
        .order_by(CommunicationMessage.sequence.desc())
        .limit(1)
    )


def _conversation_read(
    db: Session,
    conversation: CommunicationConversation,
    current_user_id: int,
    *,
    detail: bool = False,
    messages: list[CommunicationMessage] | None = None,
    next_before_sequence: int | None = None,
    last_message: CommunicationMessage | None | object = _NOT_PROVIDED,
    unread_count: int | None = None,
):
    last = (
        _latest_message(db, conversation.id)
        if last_message is _NOT_PROVIDED
        else last_message
    )
    payload = dict(
        id=conversation.id,
        conversation_type=conversation.conversation_type,
        title=_title(conversation, current_user_id),
        client=_client_read(conversation.client),
        ticket_id=conversation.ticket_id,
        participants=[
            CommunicationActorRead.model_validate(participant)
            for participant in conversation.participants
        ],
        last_message=_message_read(last) if last else None,
        last_message_at=conversation.last_message_at,
        latest_sequence=max(conversation.next_message_sequence - 1, 0),
        unread_count=(
            _unread_count(db, conversation.id, current_user_id)
            if unread_count is None
            else unread_count
        ),
        created_at=conversation.created_at,
    )
    if detail:
        payload["messages"] = [_message_read(item) for item in messages or []]
        payload["next_before_sequence"] = next_before_sequence
        return CommunicationConversationDetail(**payload)
    return CommunicationConversationRead(**payload)


def can_use_mass_mentions(user: User) -> bool:
    return any(
        role.is_active and role.name.casefold() in MASS_MENTION_ROLES
        for role in user.roles
    )


def list_directory(db: Session, current_user: User):
    users = list(
        db.scalars(
            select(User)
            .where(
                User.id != current_user.id,
                User.deleted_at.is_(None),
                User.account_type == "internal",
                User.status == "active",
                User.is_active.is_(True),
            )
            .options(selectinload(User.roles))
            .order_by(User.full_name)
        ).all()
    )
    clients = list(
        db.scalars(
            select(Client)
            .where(Client.deleted_at.is_(None))
            .order_by(Client.commercial_name, Client.legal_name)
        ).all()
    )
    groups: list[dict[str, str]] = []
    if can_use_mass_mentions(current_user):
        groups.append({"key": "all", "label": "Todos los participantes"})
        role_names = sorted(
            {
                role.name
                for user in users
                for role in user.roles
                if role.is_active
            }
        )
        groups.extend(
            {"key": f"role:{role_name}", "label": role_name}
            for role_name in role_names
        )
    return {
        "users": [CommunicationActorRead.model_validate(user) for user in users],
        "clients": [_client_read(client) for client in clients],
        "mention_groups": groups,
    }


def list_conversations(
    db: Session, current_user_id: int, conversation_type: str | None = None
) -> list[CommunicationConversationRead]:
    participant_ids = select(communication_participants.c.conversation_id).where(
        communication_participants.c.user_id == current_user_id
    )
    query = _conversation_query().where(
        CommunicationConversation.archived_at.is_(None),
        or_(
            CommunicationConversation.id.in_(participant_ids),
            CommunicationConversation.created_by_user_id == current_user_id,
        ),
    )
    if conversation_type:
        query = query.where(CommunicationConversation.conversation_type == conversation_type)
    rows = list(
        db.scalars(
            query.order_by(
                CommunicationConversation.last_message_at.desc().nullslast(),
                CommunicationConversation.created_at.desc(),
            )
        )
        .unique()
        .all()
    )
    if not rows:
        return []
    conversation_ids = [row.id for row in rows]
    latest_sequences = (
        select(
            CommunicationMessage.conversation_id,
            func.max(CommunicationMessage.sequence).label("sequence"),
        )
        .where(CommunicationMessage.conversation_id.in_(conversation_ids))
        .group_by(CommunicationMessage.conversation_id)
        .subquery()
    )
    latest_messages = list(
        db.scalars(
            select(CommunicationMessage)
            .join(
                latest_sequences,
                and_(
                    latest_sequences.c.conversation_id
                    == CommunicationMessage.conversation_id,
                    latest_sequences.c.sequence == CommunicationMessage.sequence,
                ),
            )
            .options(*_message_options())
        )
        .unique()
        .all()
    )
    last_by_conversation = {
        message.conversation_id: message for message in latest_messages
    }
    participant = communication_participants.alias("current_participant")
    read_message = aliased(CommunicationMessage, name="last_read_message")
    unread_rows = db.execute(
        select(
            CommunicationMessage.conversation_id,
            func.count(CommunicationMessage.id),
        )
        .join(
            participant,
            and_(
                participant.c.conversation_id
                == CommunicationMessage.conversation_id,
                participant.c.user_id == current_user_id,
            ),
        )
        .outerjoin(
            read_message,
            read_message.id == participant.c.last_read_message_id,
        )
        .where(
            CommunicationMessage.conversation_id.in_(conversation_ids),
            CommunicationMessage.sender_user_id != current_user_id,
            CommunicationMessage.sequence > func.coalesce(read_message.sequence, 0),
        )
        .group_by(CommunicationMessage.conversation_id)
    ).all()
    unread_by_conversation = {
        conversation_id: int(count) for conversation_id, count in unread_rows
    }
    return [
        _conversation_read(
            db,
            row,
            current_user_id,
            last_message=last_by_conversation.get(row.id),
            unread_count=unread_by_conversation.get(row.id, 0),
        )
        for row in rows
    ]


def _validate_ticket_access(db: Session, ticket_id: int | None, user: User) -> None:
    if ticket_id is None:
        return
    ticket = db.get(OperationalTicket, ticket_id)
    if ticket is None:
        raise ValueError("Ticket relacionado no encontrado")
    allowed = ticket.requested_by_user_id == user.id or user_has_permission(
        user, "tickets.view_all"
    )
    if not allowed:
        raise ValueError("Ticket relacionado no disponible")


def _active_internal_users(db: Session, user_ids: set[int]) -> list[User]:
    if not user_ids:
        return []
    return list(
        db.scalars(
            select(User).where(
                User.id.in_(user_ids),
                User.deleted_at.is_(None),
                User.account_type == "internal",
                User.status == "active",
                User.is_active.is_(True),
            )
        ).all()
    )


def create_conversation(db: Session, current_user: User, payload):
    _validate_ticket_access(db, payload.ticket_id, current_user)
    if payload.conversation_type == "internal":
        target = db.get(User, payload.participant_user_id)
        if (
            not target
            or target.deleted_at is not None
            or target.account_type != "internal"
            or target.status != "active"
            or not target.is_active
            or target.id == current_user.id
        ):
            raise ValueError("Usuario de destino inválido")
        direct_key = ":".join(map(str, sorted((current_user.id, target.id))))
        existing = db.scalar(
            _conversation_query().where(
                CommunicationConversation.direct_key == direct_key,
                CommunicationConversation.archived_at.is_(None),
            )
        )
        if existing:
            return existing, None, []
        conversation = CommunicationConversation(
            conversation_type="internal",
            direct_key=direct_key,
            ticket_id=payload.ticket_id,
            created_by_user_id=current_user.id,
            created_at=_now(),
            updated_at=_now(),
        )
        conversation.participants = [current_user, target]
    elif payload.conversation_type == "group":
        requested_ids = set(payload.participant_user_ids)
        if current_user.id in requested_ids:
            requested_ids.remove(current_user.id)
        targets = _active_internal_users(db, requested_ids)
        if len(targets) != len(requested_ids) or len(targets) < 2:
            raise ValueError("Uno o más participantes no están disponibles")
        conversation = CommunicationConversation(
            conversation_type="group",
            title=payload.title.strip(),
            ticket_id=payload.ticket_id,
            created_by_user_id=current_user.id,
            created_at=_now(),
            updated_at=_now(),
        )
        conversation.participants = [current_user, *targets]
    else:
        client = db.get(Client, payload.client_id)
        if not client or client.deleted_at is not None:
            raise ValueError("Cliente de destino inválido")
        existing = db.scalar(
            _conversation_query()
            .where(
                CommunicationConversation.conversation_type == "client",
                CommunicationConversation.client_id == client.id,
                CommunicationConversation.created_by_user_id == current_user.id,
                CommunicationConversation.archived_at.is_(None),
            )
            .limit(1)
        )
        if existing:
            return existing, None, []
        conversation = CommunicationConversation(
            conversation_type="client",
            client_id=client.id,
            ticket_id=payload.ticket_id,
            title=payload.title or client.commercial_name or client.legal_name,
            created_by_user_id=current_user.id,
            created_at=_now(),
            updated_at=_now(),
        )
        conversation.participants = [current_user]

    db.add(conversation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if payload.conversation_type != "internal":
            raise
        existing = db.scalar(
            _conversation_query().where(
                CommunicationConversation.direct_key == direct_key,
                CommunicationConversation.archived_at.is_(None),
            )
        )
        if existing is None:
            raise
        return existing, None, []
    conversation = get_conversation(db, conversation.id, current_user.id)
    if payload.initial_message and payload.initial_message.strip():
        message, recipients, notification_ids, _created = add_message(
            db,
            conversation.id,
            current_user,
            payload.initial_message,
            payload.initial_client_message_id,
            [],
        )
        return get_conversation(db, conversation.id, current_user.id), message, notification_ids
    return conversation, None, []


def _resolve_mentions(
    db: Session, conversation: CommunicationConversation, current_user: User, mentions
) -> tuple[dict[int, tuple[str, str | None]], list[int]]:
    participants = {participant.id: participant for participant in conversation.participants}
    resolved: dict[int, tuple[str, str | None]] = {}
    work_order_ids: list[int] = []
    for mention in mentions:
        if mention.kind == "work_order":
            if not _can_read_lab_work_orders(current_user):
                raise HTTPException(status_code=403, detail="No tienes permiso para mencionar OTs")
            exists = db.scalar(
                select(LabWorkOrder.id).where(LabWorkOrder.id == mention.work_order_id)
            )
            if exists is None:
                raise HTTPException(status_code=422, detail="La OT mencionada no existe")
            work_order_ids.append(mention.work_order_id)
            continue
        if mention.kind == "user":
            if mention.user_id not in participants:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="La mención individual no pertenece a la conversación",
                )
            if mention.user_id != current_user.id:
                resolved[mention.user_id] = ("user", None)
            continue
        if not can_use_mass_mentions(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permiso insuficiente para mención masiva",
            )
        if mention.kind == "all":
            for user_id in participants:
                if user_id != current_user.id:
                    resolved[user_id] = ("all", "all")
            continue
        requested_role = (mention.key or "").removeprefix("role:").casefold()
        matched = False
        for participant in conversation.participants:
            if participant.id == current_user.id:
                continue
            if any(
                role.is_active and role.name.casefold() == requested_role
                for role in participant.roles
            ):
                resolved[participant.id] = ("role", mention.key)
                matched = True
        if not matched:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="El grupo mencionado no tiene participantes autorizados",
            )
    return resolved, work_order_ids


def _create_message_notifications(
    db: Session,
    *,
    conversation: CommunicationConversation,
    message: CommunicationMessage,
    sender: User,
    mentioned_user_ids: set[int],
) -> list[int]:
    notification_ids: list[int] = []
    for participant_id in _participant_ids(conversation) - {sender.id}:
        is_mention = participant_id in mentioned_user_ids
        notification = Notification(
            recipient_user_id=participant_id,
            actor_user_id=sender.id,
            notification_type=(
                "communication.mention_received"
                if is_mention
                else "communication.message_received"
            ),
            event_key=f"communication:message:{message.id}:user:{participant_id}",
            title=(
                "Te mencionaron en Comunicaciones"
                if is_mention
                else "Nuevo mensaje en Comunicaciones"
            ),
            body=f"Conversación: {_title(conversation, participant_id)}",
            entity_type="communication",
            entity_id=conversation.id,
            priority="normal",
            metadata_json={
                "conversation_id": conversation.id,
                "message_id": message.id,
                "sequence": message.sequence,
                "mobile_path": "/(technician)/communications",
            },
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(notification)
        queue_notification_for_delivery(db, notification)
    db.flush()
    notification_ids.extend(db.info.pop("push_notification_ids", []))
    return notification_ids


def add_message(
    db: Session,
    conversation_id: int,
    current_user: User,
    body: str,
    client_message_id: str | None,
    mentions,
):
    # Endurecimiento anti-spoofing: [[work_order:N]] es sintaxis de control
    # interna (ver _message_read) -- el remitente nunca la escribe legítimamente
    # a mano. Si un usuario la teclea, se retira ANTES de guardar, para que el
    # único origen posible de ese patrón en el body persistido sea el append
    # controlado de más abajo, construido a partir de mentions ya autorizadas
    # por _resolve_mentions (permiso LAB + existencia de la OT). Así, leer el
    # marcador de vuelta nunca puede fabricar una mención que el emisor no
    # tenía autoridad real para crear.
    normalized_body = _WORK_ORDER_MARKER.sub("", body).strip()
    if not normalized_body:
        raise HTTPException(status_code=422, detail="El mensaje no puede estar vacío")
    client_id = client_message_id or f"server-{uuid4()}"
    existing = db.scalar(
        select(CommunicationMessage)
        .where(
            CommunicationMessage.conversation_id == conversation_id,
            CommunicationMessage.sender_user_id == current_user.id,
            CommunicationMessage.client_message_id == client_id,
        )
        .options(*_message_options())
    )
    if existing:
        return existing, _participant_ids(existing.conversation), [], False

    conversation = get_conversation(
        db, conversation_id, current_user.id, for_update=True
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    # La consulta optimista anterior evita bloquear en el caso habitual. Esta
    # segunda lectura ocurre después de serializar escritores de la conversación
    # y cubre dos reintentos concurrentes con el mismo identificador del cliente.
    existing = db.scalar(
        select(CommunicationMessage)
        .where(
            CommunicationMessage.conversation_id == conversation_id,
            CommunicationMessage.sender_user_id == current_user.id,
            CommunicationMessage.client_message_id == client_id,
        )
        .options(*_message_options())
    )
    if existing:
        return existing, _participant_ids(existing.conversation), [], False
    resolved_mentions, work_order_mentions = _resolve_mentions(
        db, conversation, current_user, mentions
    )
    now = _now()
    message = CommunicationMessage(
        conversation_id=conversation.id,
        sender_user_id=current_user.id,
        client_message_id=client_id,
        sequence=conversation.next_message_sequence,
        body=normalized_body + "".join(
            f"\n[[work_order:{work_order_id}]]"
            for work_order_id in dict.fromkeys(work_order_mentions)
        ),
        delivered_at=now,
        created_at=now,
        updated_at=now,
    )
    conversation.next_message_sequence += 1
    conversation.last_message_at = now
    conversation.updated_at = now
    db.add(message)
    db.flush()
    for participant_id in _participant_ids(conversation):
        own_message = participant_id == current_user.id
        db.add(
            CommunicationMessageReceipt(
                message_id=message.id,
                user_id=participant_id,
                delivered_at=now if own_message else None,
                read_at=now if own_message else None,
            )
        )
    for mentioned_user_id, (kind, key) in resolved_mentions.items():
        db.add(
            CommunicationMessageMention(
                message_id=message.id,
                mentioned_user_id=mentioned_user_id,
                mention_kind=kind,
                mention_key=key,
            )
        )
    notification_ids = _create_message_notifications(
        db,
        conversation=conversation,
        message=message,
        sender=current_user,
        mentioned_user_ids=set(resolved_mentions),
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(CommunicationMessage)
            .where(
                CommunicationMessage.conversation_id == conversation_id,
                CommunicationMessage.sender_user_id == current_user.id,
                CommunicationMessage.client_message_id == client_id,
            )
            .options(*_message_options())
        )
        if existing is None:
            raise
        return existing, _participant_ids(conversation), [], False
    persisted = db.scalar(
        select(CommunicationMessage)
        .where(CommunicationMessage.id == message.id)
        .options(*_message_options())
    )
    return persisted, _participant_ids(conversation), notification_ids, True


def get_message_page(
    db: Session,
    conversation_id: int,
    current_user_id: int,
    *,
    before_sequence: int | None = None,
    limit: int = 50,
) -> CommunicationMessagePage:
    conversation = get_conversation(db, conversation_id, current_user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    query = select(CommunicationMessage).where(
        CommunicationMessage.conversation_id == conversation_id
    )
    if before_sequence is not None:
        query = query.where(CommunicationMessage.sequence < before_sequence)
    rows = list(
        db.scalars(
            query.options(*_message_options())
            .order_by(CommunicationMessage.sequence.desc())
            .limit(limit + 1)
        )
        .unique()
        .all()
    )
    has_more = len(rows) > limit
    selected = list(reversed(rows[:limit]))
    return CommunicationMessagePage(
        items=[_message_read(item) for item in selected],
        next_before_sequence=(selected[0].sequence if has_more and selected else None),
        latest_sequence=max(conversation.next_message_sequence - 1, 0),
        unread_count=_unread_count(db, conversation_id, current_user_id),
    )


def get_conversation_detail(
    db: Session, conversation_id: int, current_user_id: int, *, limit: int = 50
):
    conversation = get_conversation(db, conversation_id, current_user_id)
    if conversation is None:
        return None
    page = get_message_page(db, conversation_id, current_user_id, limit=limit)
    message_ids = [item.id for item in page.items]
    messages = (
        list(
            db.scalars(
                select(CommunicationMessage)
                .where(CommunicationMessage.id.in_(message_ids))
                .options(*_message_options())
                .order_by(CommunicationMessage.sequence)
            )
            .unique()
            .all()
        )
        if message_ids
        else []
    )
    return _conversation_read(
        db,
        conversation,
        current_user_id,
        detail=True,
        messages=messages,
        next_before_sequence=page.next_before_sequence,
    )


def sync_messages(
    db: Session,
    conversation_id: int,
    current_user_id: int,
    *,
    after_sequence: int,
    limit: int = 100,
) -> CommunicationSyncRead:
    conversation = get_conversation(db, conversation_id, current_user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    rows = list(
        db.scalars(
            select(CommunicationMessage)
            .where(
                CommunicationMessage.conversation_id == conversation_id,
                CommunicationMessage.sequence > after_sequence,
            )
            .options(*_message_options())
            .order_by(CommunicationMessage.sequence)
            .limit(limit + 1)
        )
        .unique()
        .all()
    )
    return CommunicationSyncRead(
        items=[_message_read(item) for item in rows[:limit]],
        latest_sequence=max(conversation.next_message_sequence - 1, 0),
        unread_count=_unread_count(db, conversation_id, current_user_id),
        has_more=len(rows) > limit,
    )


def update_receipts(
    db: Session,
    conversation_id: int,
    current_user_id: int,
    payload,
) -> tuple[CommunicationReceiptBatchRead, set[int]]:
    conversation = get_conversation(
        db, conversation_id, current_user_id, for_update=True
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    requested_ids = set(payload.message_ids)
    messages = list(
        db.scalars(
            select(CommunicationMessage).where(
                CommunicationMessage.conversation_id == conversation_id,
                CommunicationMessage.id.in_(requested_ids),
            )
        ).all()
    )
    if len(messages) != len(requested_ids):
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    now = _now()
    for message in messages:
        receipt = db.get(
            CommunicationMessageReceipt, (message.id, current_user_id)
        )
        if receipt is None:
            receipt = CommunicationMessageReceipt(
                message_id=message.id, user_id=current_user_id
            )
            db.add(receipt)
        if receipt.delivered_at is None:
            receipt.delivered_at = now
        if payload.state == "read" and receipt.read_at is None:
            receipt.read_at = now
            mention = db.get(
                CommunicationMessageMention, (message.id, current_user_id)
            )
            if mention is not None and mention.read_at is None:
                mention.read_at = now
    latest = max(messages, key=lambda item: item.sequence)
    delivered_id, delivered_sequence = _participant_cursor(
        db,
        conversation_id,
        current_user_id,
        communication_participants.c.last_delivered_message_id,
    )
    values = {
        "last_delivered_message_id": (
            latest.id if latest.sequence > delivered_sequence else delivered_id
        )
    }
    if payload.state == "read":
        read_id, read_sequence = _participant_cursor(
            db,
            conversation_id,
            current_user_id,
            communication_participants.c.last_read_message_id,
        )
        values.update(
            last_read_message_id=(
                latest.id if latest.sequence > read_sequence else read_id
            ),
            last_read_at=now,
        )
    db.execute(
        update(communication_participants)
        .where(
            communication_participants.c.conversation_id == conversation_id,
            communication_participants.c.user_id == current_user_id,
        )
        .values(**values)
    )
    db.commit()
    return (
        CommunicationReceiptBatchRead(
            conversation_id=conversation_id,
            state=payload.state,
            message_ids=sorted(requested_ids),
            user_id=current_user_id,
            occurred_at=now,
        ),
        _participant_ids(conversation),
    )


def list_mentions(
    db: Session, current_user_id: int, *, unread_only: bool, limit: int
) -> list[CommunicationMentionInboxItem]:
    query = (
        select(CommunicationMessageMention, CommunicationMessage, CommunicationConversation)
        .join(
            CommunicationMessage,
            CommunicationMessage.id == CommunicationMessageMention.message_id,
        )
        .join(
            CommunicationConversation,
            CommunicationConversation.id == CommunicationMessage.conversation_id,
        )
        .where(
            CommunicationMessageMention.mentioned_user_id == current_user_id,
            CommunicationConversation.archived_at.is_(None),
        )
        .options(*_message_options())
        .order_by(CommunicationMessage.created_at.desc(), CommunicationMessage.id.desc())
        .limit(limit)
    )
    if unread_only:
        query = query.where(CommunicationMessageMention.read_at.is_(None))
    rows = db.execute(query).unique().all()
    return [
        CommunicationMentionInboxItem(
            message=_message_read(message),
            conversation_title=_title(conversation, current_user_id),
            read_at=mention.read_at,
        )
        for mention, message, conversation in rows
    ]


def deliver_communication_notifications(notification_ids: list[int]) -> None:
    if not notification_ids:
        return
    from app.core.db import SessionLocal
    from app.services.push_notifications import deliver_notification_ids

    with SessionLocal() as db:
        deliver_notification_ids(db, notification_ids)
