"""API genérica de Actividad, sin routers específicos por módulo."""

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.activity import ActivityMessage
from app.models.user import User
from app.schemas.activity import (
    ActivityAttachmentRead,
    ActivityAttentionCreate,
    ActivityAttentionRead,
    ActivityAttentionResolve,
    ActivityEntityRead,
    ActivityEntityDefinitionRead,
    ActivityInboxItemRead,
    ActivityInboxRead,
    ActivityMessageCreate,
    ActivityMessageRead,
    ActivityMentionableUserRead,
    ActivityMessageUpdate,
    ActivityMessageWithdraw,
    ActivityThreadRead,
    ActivityUnreadRead,
)
from app.services.activity import (
    IMAGE_CONTENT_TYPES,
    activity_capabilities,
    add_attachment,
    attachment_path,
    create_message,
    get_activity,
    list_entity_definitions,
    list_inbox,
    list_mentionable_users,
    mark_thread_read,
    request_attention,
    resolve_attention,
    update_message,
    withdraw_message,
)
from app.services.auth import get_current_user, user_has_permission
from app.services.activity_entities import resolve_resolution_activity_target


router = APIRouter(prefix="/activity", tags=["activity"])


def _message_read(
    message: ActivityMessage,
    *,
    can_view_audit: bool,
) -> ActivityMessageRead:
    resource = ActivityMessageRead.model_validate(message)
    attachments = [
        item.model_copy(
            update={
                "preview_available": (
                    item.content_type in IMAGE_CONTENT_TYPES
                    and not message.withdrawn_at
                )
            }
        )
        for item in resource.attachments
    ]
    updates = {"attachments": attachments}
    if message.withdrawn_at is not None and not can_view_audit:
        updates.update(
            {
                "body": "Mensaje retirado.",
                "revisions": [],
                "metadata_json": {},
            }
        )
    elif not can_view_audit:
        updates["revisions"] = []
    return resource.model_copy(update=updates)


@router.get(
    "/entities",
    response_model=list[ActivityEntityDefinitionRead],
)
def get_entities(
    current_user: User = Depends(get_current_user),
):
    return list_entity_definitions(current_user)


@router.get(
    "/mentionable-users",
    response_model=list[ActivityMentionableUserRead],
)
def get_mentionable_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_mentionable_users(db, current_user)


@router.get(
    "/resolution-target/{public_id}",
    response_model=ActivityEntityRead,
)
def get_resolution_target(
    public_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return resolve_resolution_activity_target(
        db,
        public_id=public_id,
        user=current_user,
    )


@router.get("/inbox", response_model=ActivityInboxRead)
def get_inbox(
    unread_only: bool = Query(default=False),
    attention_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = list_inbox(
        db,
        current_user,
        unread_only=unread_only,
        attention_only=attention_only,
        limit=limit,
    )
    can_audit = user_has_permission(current_user, "activity.view_audit")
    return ActivityInboxRead(
        items=[
            ActivityInboxItemRead(
                **{
                    **item,
                    "last_message": _message_read(
                        item["last_message"],
                        can_view_audit=can_audit,
                    ),
                }
            )
            for item in result["items"]
        ],
        total=result["total"],
        unread_count=result["unread_count"],
        pending_attention_count=result["pending_attention_count"],
    )


@router.get(
    "/{entity_type}/{entity_id}",
    response_model=ActivityThreadRead,
)
def get_entity_activity(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = get_activity(db, entity_type, entity_id, current_user)
    thread = result["thread"]
    can_audit = result["capabilities"]["can_view_audit"]
    return ActivityThreadRead(
        id=thread.id if thread else None,
        entity_type=entity_type,
        entity_id=entity_id,
        created_at=thread.created_at if thread else None,
        entity=result["entity"],
        capabilities=result["capabilities"],
        unread_count=result["unread_count"],
        pending_attention_count=result["pending_attention_count"],
        messages=[
            _message_read(message, can_view_audit=can_audit)
            for message in result["messages"]
        ],
    )


@router.post(
    "/{entity_type}/{entity_id}/read",
    response_model=ActivityUnreadRead,
)
def post_entity_read(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ActivityUnreadRead(
        unread_count=mark_thread_read(
            db, entity_type, entity_id, current_user
        )
    )


@router.post(
    "/{entity_type}/{entity_id}/messages",
    response_model=ActivityMessageRead,
    status_code=status.HTTP_201_CREATED,
)
def post_message(
    entity_type: str,
    entity_id: int,
    payload: ActivityMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = create_message(
        db, entity_type, entity_id, payload, current_user
    )
    return _message_read(
        message,
        can_view_audit=user_has_permission(
            current_user, "activity.view_audit"
        ),
    )


@router.patch(
    "/messages/{message_id}",
    response_model=ActivityMessageRead,
)
def patch_message(
    message_id: int,
    payload: ActivityMessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = update_message(db, message_id, payload, current_user)
    return _message_read(
        message,
        can_view_audit=user_has_permission(
            current_user, "activity.view_audit"
        ),
    )


@router.delete(
    "/messages/{message_id}",
    response_model=ActivityMessageRead,
)
def delete_message(
    message_id: int,
    payload: ActivityMessageWithdraw,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = withdraw_message(db, message_id, payload, current_user)
    return _message_read(
        message,
        can_view_audit=user_has_permission(
            current_user, "activity.view_audit"
        ),
    )


@router.post(
    "/messages/{message_id}/withdraw",
    response_model=ActivityMessageRead,
    deprecated=True,
)
def post_withdraw_compatibility(
    message_id: int,
    payload: ActivityMessageWithdraw,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_message(message_id, payload, db, current_user)


@router.post(
    "/messages/{message_id}/attachments",
    response_model=ActivityAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
def post_attachment(
    message_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = add_attachment(db, message_id, file, current_user)
    resource = ActivityAttachmentRead.model_validate(attachment)
    return resource.model_copy(
        update={
            "preview_available": attachment.content_type
            in IMAGE_CONTENT_TYPES
        }
    )


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment, path = attachment_path(db, attachment_id, current_user)
    return FileResponse(
        path,
        media_type=attachment.content_type,
        filename=attachment.original_name,
    )


@router.get("/attachments/{attachment_id}/preview")
def preview_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment, path = attachment_path(db, attachment_id, current_user)
    if attachment.content_type not in IMAGE_CONTENT_TYPES:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=415,
            detail="Este archivo no admite vista previa",
        )
    return FileResponse(path, media_type=attachment.content_type)


@router.post(
    "/messages/{message_id}/attention",
    response_model=ActivityAttentionRead,
    status_code=status.HTTP_201_CREATED,
)
def post_attention(
    message_id: int,
    payload: ActivityAttentionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return request_attention(db, message_id, payload, current_user)


@router.post(
    "/attention/{attention_id}/resolve",
    response_model=ActivityAttentionRead,
)
def post_attention_resolve(
    attention_id: int,
    payload: ActivityAttentionResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return resolve_attention(db, attention_id, payload, current_user)
