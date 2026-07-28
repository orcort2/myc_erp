from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.activity import (
    ActivityAttachmentRead,
    ActivityMessageCreate,
    ActivityMessageRead,
    ActivityMessageUpdate,
    ActivityMessageWithdraw,
    ActivityThreadRead,
)
from app.services.activity import (
    add_attachment,
    attachment_path,
    create_message,
    list_messages,
    update_message,
    withdraw_message,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/{entity_type}/{entity_id}", response_model=ActivityThreadRead)
def get_activity(entity_type: str, entity_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    thread, messages = list_messages(db, entity_type, entity_id, current_user)
    return ActivityThreadRead(
        id=thread.id,
        entity_type=thread.entity_type,
        entity_id=thread.entity_id,
        created_at=thread.created_at,
        messages=messages,
    )


@router.post("/{entity_type}/{entity_id}/messages", response_model=ActivityMessageRead, status_code=status.HTTP_201_CREATED)
def post_message(entity_type: str, entity_id: int, payload: ActivityMessageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return create_message(db, entity_type, entity_id, payload, current_user)


@router.patch("/messages/{message_id}", response_model=ActivityMessageRead)
def patch_message(message_id: int, payload: ActivityMessageUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return update_message(db, message_id, payload, current_user)


@router.post("/messages/{message_id}/withdraw", response_model=ActivityMessageRead)
def post_withdraw(message_id: int, payload: ActivityMessageWithdraw, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return withdraw_message(db, message_id, payload, current_user)


@router.post("/messages/{message_id}/attachments", response_model=ActivityAttachmentRead, status_code=status.HTTP_201_CREATED)
def post_attachment(message_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return add_attachment(db, message_id, file, current_user)


@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attachment, path = attachment_path(db, attachment_id, current_user)
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)
