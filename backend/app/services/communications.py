from datetime import datetime, timezone
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.client import Client
from app.models.communication import CommunicationConversation, CommunicationMessage, communication_participants
from app.models.notification import Notification
from app.models.user import User
from app.schemas.communication import (
    CommunicationActorRead,
    CommunicationClientRead,
    CommunicationConversationDetail,
    CommunicationConversationRead,
    CommunicationMessageRead,
)


def _now():
    return datetime.now(timezone.utc)


def _message_read(message):
    return CommunicationMessageRead.model_validate(message)


def _client_read(client):
    if client is None:
        return None
    return CommunicationClientRead(
        id=client.id,
        name=client.commercial_name or client.legal_name,
        email=client.email,
    )


def _title(conversation, current_user_id):
    if conversation.conversation_type == "client":
        return conversation.title or (_client_read(conversation.client).name if conversation.client else "Cliente")
    others = [p.full_name for p in conversation.participants if p.id != current_user_id]
    return conversation.title or ", ".join(others) or "Conversación interna"


def _conversation_read(conversation, current_user_id, detail=False):
    last = conversation.messages[-1] if conversation.messages else None
    payload = dict(
        id=conversation.id,
        conversation_type=conversation.conversation_type,
        title=_title(conversation, current_user_id),
        client=_client_read(conversation.client),
        participants=[CommunicationActorRead.model_validate(p) for p in conversation.participants],
        last_message=_message_read(last) if last else None,
        last_message_at=conversation.last_message_at,
        created_at=conversation.created_at,
    )
    if detail:
        payload["messages"] = [_message_read(item) for item in conversation.messages]
        return CommunicationConversationDetail(**payload)
    return CommunicationConversationRead(**payload)


def list_directory(db: Session, current_user_id: int):
    users = db.scalars(select(User).where(User.id != current_user_id, User.deleted_at.is_(None)).order_by(User.full_name)).all()
    clients = db.scalars(select(Client).where(Client.deleted_at.is_(None)).order_by(Client.commercial_name, Client.legal_name)).all()
    return {
        "users": [CommunicationActorRead.model_validate(user) for user in users],
        "clients": [_client_read(client) for client in clients],
    }


def _base_query():
    return select(CommunicationConversation).options(
        selectinload(CommunicationConversation.participants),
        joinedload(CommunicationConversation.client),
        selectinload(CommunicationConversation.messages).joinedload(CommunicationMessage.sender),
    )


def list_conversations(db: Session, current_user_id: int, conversation_type: str | None = None):
    participant_ids = select(communication_participants.c.conversation_id).where(
        communication_participants.c.user_id == current_user_id
    )
    query = _base_query().where(
        CommunicationConversation.archived_at.is_(None),
        or_(
            CommunicationConversation.id.in_(participant_ids),
            and_(
                CommunicationConversation.conversation_type == "client",
                CommunicationConversation.created_by_user_id == current_user_id,
            ),
        ),
    )
    if conversation_type:
        query = query.where(CommunicationConversation.conversation_type == conversation_type)
    query = query.order_by(CommunicationConversation.last_message_at.desc().nullslast(), CommunicationConversation.created_at.desc())
    rows = db.scalars(query).unique().all()
    return [_conversation_read(row, current_user_id) for row in rows]


def get_conversation(db: Session, conversation_id: int, current_user_id: int):
    conversation = db.scalar(_base_query().where(CommunicationConversation.id == conversation_id))
    if not conversation:
        return None
    allowed = conversation.created_by_user_id == current_user_id or any(p.id == current_user_id for p in conversation.participants)
    if not allowed:
        return None
    return conversation


def create_conversation(db: Session, current_user: User, payload):
    if payload.conversation_type == "internal":
        target = db.get(User, payload.participant_user_id)
        if not target or target.deleted_at is not None or target.id == current_user.id:
            raise ValueError("Usuario de destino inválido")
        existing_ids = db.execute(
            select(communication_participants.c.conversation_id)
            .where(communication_participants.c.user_id.in_([current_user.id, target.id]))
            .group_by(communication_participants.c.conversation_id)
            .having(__import__('sqlalchemy').func.count() == 2)
        ).scalars().all()
        existing = db.scalar(_base_query().where(
            CommunicationConversation.id.in_(existing_ids),
            CommunicationConversation.conversation_type == "internal",
        ).limit(1)) if existing_ids else None
        if existing:
            return existing
        conversation = CommunicationConversation(
            conversation_type="internal",
            created_by_user_id=current_user.id,
            last_message_at=_now() if payload.initial_message else None,
            created_at=_now(), updated_at=_now(),
        )
        conversation.participants = [current_user, target]
    else:
        client = db.get(Client, payload.client_id)
        if not client or client.deleted_at is not None:
            raise ValueError("Cliente de destino inválido")
        existing = db.scalar(_base_query().where(
            CommunicationConversation.conversation_type == "client",
            CommunicationConversation.client_id == client.id,
            CommunicationConversation.created_by_user_id == current_user.id,
        ).limit(1))
        if existing:
            return existing
        conversation = CommunicationConversation(
            conversation_type="client",
            client_id=client.id,
            title=client.commercial_name or client.legal_name,
            created_by_user_id=current_user.id,
            last_message_at=_now() if payload.initial_message else None,
            created_at=_now(), updated_at=_now(),
        )
        conversation.participants = [current_user]
    db.add(conversation)
    db.flush()
    if payload.initial_message and payload.initial_message.strip():
        db.add(CommunicationMessage(
            conversation_id=conversation.id,
            sender_user_id=current_user.id,
            body=payload.initial_message.strip(),
            delivered_at=_now(), created_at=_now(), updated_at=_now(),
        ))
    db.commit()
    return get_conversation(db, conversation.id, current_user.id)


def add_message(db: Session, conversation, current_user: User, body: str):
    now = _now()
    message = CommunicationMessage(
        conversation_id=conversation.id,
        sender_user_id=current_user.id,
        body=body.strip(),
        delivered_at=now,
        created_at=now,
        updated_at=now,
    )
    conversation.last_message_at = now
    conversation.updated_at = now
    db.add(message)
    db.flush()
    if conversation.conversation_type == "internal":
        for participant in conversation.participants:
            if participant.id == current_user.id:
                continue
            db.add(Notification(
                recipient_user_id=participant.id,
                actor_user_id=current_user.id,
                notification_type="communication_message",
                title=f"Nuevo mensaje de {current_user.full_name}",
                body=body.strip()[:500],
                entity_type="communication",
                entity_id=conversation.id,
                priority="normal",
                metadata_json={
                    "frontend_path": f"/communications?conversation_id={conversation.id}",
                    "conversation_id": conversation.id,
                },
                created_at=now,
                updated_at=now,
            ))
    db.commit()
    db.refresh(message)
    return db.scalar(select(CommunicationMessage).options(joinedload(CommunicationMessage.sender)).where(CommunicationMessage.id == message.id))
