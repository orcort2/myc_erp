from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.communication import (
    CommunicationConversationCreate,
    CommunicationConversationDetail,
    CommunicationConversationRead,
    CommunicationDirectoryRead,
    CommunicationMessageCreate,
    CommunicationMessageRead,
)
from app.services.auth import get_current_user
from app.services.communications import (
    _conversation_read,
    add_message,
    create_conversation,
    get_conversation,
    list_conversations,
    list_directory,
)

router = APIRouter(prefix="/communications", tags=["communications"])

@router.get("/directory", response_model=CommunicationDirectoryRead)
def get_directory(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return list_directory(db, current_user.id)

@router.get("/conversations", response_model=list[CommunicationConversationRead])
def get_conversations(
    conversation_type: str | None = Query(default=None, pattern="^(internal|client)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_conversations(db, current_user.id, conversation_type)

@router.post("/conversations", response_model=CommunicationConversationDetail, status_code=status.HTTP_201_CREATED)
def post_conversation(payload: CommunicationConversationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        conversation = create_conversation(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _conversation_read(conversation, current_user.id, detail=True)

@router.get("/conversations/{conversation_id}", response_model=CommunicationConversationDetail)
def get_conversation_detail(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversation = get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return _conversation_read(conversation, current_user.id, detail=True)

@router.post("/conversations/{conversation_id}/messages", response_model=CommunicationMessageRead, status_code=status.HTTP_201_CREATED)
def post_message(conversation_id: int, payload: CommunicationMessageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversation = get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    if not payload.body.strip():
        raise HTTPException(status_code=422, detail="El mensaje no puede estar vacío")
    return add_message(db, conversation, current_user, payload.body)
