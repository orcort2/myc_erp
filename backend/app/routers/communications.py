from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.realtime.events import publish_to_users
from app.schemas.communication import (
    CommunicationConversationCreate,
    CommunicationConversationDetail,
    CommunicationConversationRead,
    CommunicationDirectoryRead,
    CommunicationMentionInboxItem,
    CommunicationMessageCreate,
    CommunicationMessagePage,
    CommunicationMessageRead,
    CommunicationReceiptBatchRead,
    CommunicationReceiptUpdate,
    CommunicationSyncRead,
)
from app.core.mobile.security import get_communications_user
from app.services.communications import (
    _message_read,
    add_message,
    create_conversation,
    deliver_communication_notifications,
    get_conversation_detail,
    get_message_page,
    list_conversations,
    list_directory,
    list_mentions,
    sync_messages,
    update_receipts,
)


router = APIRouter(prefix="/communications", tags=["communications"])


@router.get("/directory", response_model=CommunicationDirectoryRead)
def get_directory(
    db: Session = Depends(get_db), current_user: User = Depends(get_communications_user)
):
    return list_directory(db, current_user)


@router.get("/mentions", response_model=list[CommunicationMentionInboxItem])
def get_mentions(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_communications_user),
):
    return list_mentions(db, current_user.id, unread_only=unread_only, limit=limit)


@router.get("/conversations", response_model=list[CommunicationConversationRead])
def get_conversations(
    conversation_type: str | None = Query(
        default=None, pattern="^(internal|group|client)$"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_communications_user),
):
    return list_conversations(db, current_user.id, conversation_type)


@router.post(
    "/conversations",
    response_model=CommunicationConversationDetail,
    status_code=status.HTTP_201_CREATED,
)
def post_conversation(
    payload: CommunicationConversationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_communications_user),
):
    try:
        conversation, initial_message, notification_ids = create_conversation(
            db, current_user, payload
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if initial_message is not None:
        user_ids = {participant.id for participant in conversation.participants}
        background_tasks.add_task(
            publish_to_users,
            user_ids,
            "message.created",
            _message_read(initial_message).model_dump(mode="json"),
        )
        background_tasks.add_task(
            deliver_communication_notifications, notification_ids
        )
        background_tasks.add_task(
            publish_to_users,
            user_ids - {current_user.id},
            "notification.created",
            {
                "event_type": "communication.message_received",
                "entity_type": "communication",
                "entity_id": conversation.id,
                "conversation_id": conversation.id,
                "message_id": initial_message.id,
            },
        )
    detail = get_conversation_detail(db, conversation.id, current_user.id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return detail


@router.get(
    "/conversations/{conversation_id}",
    response_model=CommunicationConversationDetail,
)
def get_conversation_detail_route(
    conversation_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_communications_user),
):
    conversation = get_conversation_detail(
        db, conversation_id, current_user.id, limit=limit
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return conversation


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=CommunicationMessagePage,
)
def get_messages(
    conversation_id: int,
    before_sequence: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_communications_user),
):
    return get_message_page(
        db,
        conversation_id,
        current_user.id,
        before_sequence=before_sequence,
        limit=limit,
    )


@router.get(
    "/conversations/{conversation_id}/sync", response_model=CommunicationSyncRead
)
def get_message_sync(
    conversation_id: int,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_communications_user),
):
    return sync_messages(
        db,
        conversation_id,
        current_user.id,
        after_sequence=after_sequence,
        limit=limit,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=CommunicationMessageRead,
    status_code=status.HTTP_201_CREATED,
)
def post_message(
    conversation_id: int,
    payload: CommunicationMessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_communications_user),
):
    message, participant_ids, notification_ids, created = add_message(
        db,
        conversation_id,
        current_user,
        payload.body,
        payload.client_message_id,
        payload.mentions,
    )
    message_read = _message_read(message)
    if created:
        background_tasks.add_task(
            publish_to_users,
            participant_ids,
            "message.created",
            message_read.model_dump(mode="json"),
        )
        background_tasks.add_task(
            deliver_communication_notifications, notification_ids
        )
        background_tasks.add_task(
            publish_to_users,
            participant_ids - {current_user.id},
            "notification.created",
            {
                "event_type": "communication.message_received",
                "entity_type": "communication",
                "entity_id": conversation_id,
                "conversation_id": conversation_id,
                "message_id": message.id,
            },
        )
    return message_read


@router.post(
    "/conversations/{conversation_id}/receipts",
    response_model=CommunicationReceiptBatchRead,
)
def post_receipts(
    conversation_id: int,
    payload: CommunicationReceiptUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_communications_user),
):
    receipt, participant_ids = update_receipts(
        db, conversation_id, current_user.id, payload
    )
    background_tasks.add_task(
        publish_to_users,
        participant_ids,
        "message.read" if payload.state == "read" else "message.delivered",
        receipt.model_dump(mode="json"),
    )
    return receipt
