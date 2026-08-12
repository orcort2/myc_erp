"""Servicio institucional de comunicación interna y eventos operativos."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.activity import (
    ActivityAttachment,
    ActivityAttentionRequest,
    ActivityMention,
    ActivityMessage,
    ActivityMessageRevision,
    ActivityThread,
    ActivityThreadRead,
)
from app.models.user import User
from app.schemas.activity import (
    ActivityAttentionCreate,
    ActivityAttentionResolve,
    ActivityMessageCreate,
    ActivityMessageUpdate,
    ActivityMessageWithdraw,
)
from app.services.activity_entities import (
    ACTIVITY_ENTITY_DEFINITIONS,
    entity_resource,
    get_activity_entity_definition,
    resolve_activity_entity,
)
from app.services.audit_logs import write_audit_log
from app.services.auth import user_has_permission
from app.services.notifications import (
    create_activity_attention_notification,
    create_activity_mention_notification,
    resolve_activity_attention_notification,
    revoke_activity_mention_notifications,
)
from app.services.storage_service import (
    resolve_storage_path,
    safe_filename,
    save_validated_content,
)
from app.services.file_security import validate_upload


ALLOWED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".webp", ".txt", ".md", ".csv",
    ".zip", ".docx", ".xlsx", ".pptx",
}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg", "image/png", "image/webp",
    "text/plain", "text/markdown", "text/csv",
    "application/zip", "application/x-zip-compressed",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
GENERIC_CONTENT_TYPES = {"", "application/octet-stream"}
IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
CONTENT_TYPES_BY_EXTENSION = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
    ".txt": {"text/plain"},
    ".md": {"text/plain", "text/markdown"},
    ".csv": {"text/plain", "text/csv"},
    ".zip": {"application/zip", "application/x-zip-compressed"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    },
    ".pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    },
}
MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024
MAX_ATTACHMENTS_PER_MESSAGE = 10
EDIT_WINDOW = timedelta(minutes=30)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_permission(user: User, permission: str) -> None:
    if not user_has_permission(user, permission):
        raise HTTPException(
            status_code=403,
            detail=f"Falta el permiso {permission}",
        )


def activity_capabilities(user: User) -> dict[str, bool]:
    return {
        "can_read": user_has_permission(user, "activity.read"),
        "can_create": user_has_permission(user, "activity.create"),
        "can_edit_own": user_has_permission(user, "activity.edit_own"),
        "can_delete_own": user_has_permission(user, "activity.delete_own"),
        "can_moderate": user_has_permission(user, "activity.moderate"),
        "can_attach_files": user_has_permission(user, "activity.attach_files"),
        "can_mention": user_has_permission(user, "activity.mention"),
        "can_request_attention": user_has_permission(
            user, "activity.request_attention"
        ),
        "can_resolve_attention": user_has_permission(
            user, "activity.resolve_attention"
        ),
        "can_view_audit": user_has_permission(user, "activity.view_audit"),
    }


def ensure_entity_access(
    db: Session,
    user: User,
    entity_type: str,
    entity_id: int,
):
    return resolve_activity_entity(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
    )


def _message_options():
    return (
        selectinload(ActivityMessage.thread),
        selectinload(ActivityMessage.author),
        selectinload(ActivityMessage.revisions),
        selectinload(ActivityMessage.attachments),
        selectinload(ActivityMessage.mentions).selectinload(
            ActivityMention.mentioned_user
        ),
        selectinload(ActivityMessage.attention_requests).selectinload(
            ActivityAttentionRequest.requested_by
        ),
        selectinload(ActivityMessage.attention_requests).selectinload(
            ActivityAttentionRequest.assigned_user
        ),
        selectinload(ActivityMessage.attention_requests).selectinload(
            ActivityAttentionRequest.resolved_by
        ),
    )


def _find_thread(
    db: Session,
    entity_type: str,
    entity_id: int,
) -> ActivityThread | None:
    return db.scalar(
        select(ActivityThread).where(
            ActivityThread.entity_type == entity_type,
            ActivityThread.entity_id == entity_id,
        )
    )


def _get_or_create_thread(
    db: Session,
    entity_type: str,
    entity_id: int,
    *,
    created_by_id: int | None,
) -> ActivityThread:
    thread = _find_thread(db, entity_type, entity_id)
    if thread is not None:
        return thread
    thread = ActivityThread(
        entity_type=entity_type,
        entity_id=entity_id,
        created_by_id=created_by_id,
    )
    try:
        with db.begin_nested():
            db.add(thread)
            db.flush()
    except IntegrityError:
        thread = _find_thread(db, entity_type, entity_id)
        if thread is None:
            raise
    return thread


def get_activity(
    db: Session,
    entity_type: str,
    entity_id: int,
    user: User,
) -> dict:
    definition, entity = ensure_entity_access(
        db, user, entity_type, entity_id
    )
    thread = _find_thread(db, entity_type, entity_id)
    messages: list[ActivityMessage] = []
    unread_count = 0
    pending_attention_count = 0
    if thread is not None:
        messages = list(
            db.scalars(
                select(ActivityMessage)
                .where(ActivityMessage.thread_id == thread.id)
                .options(*_message_options())
                .order_by(ActivityMessage.created_at.asc(), ActivityMessage.id.asc())
            ).all()
        )
        unread_count = _thread_unread_count(db, thread.id, user.id)
        pending_attention_count = int(
            db.scalar(
                select(func.count(ActivityAttentionRequest.id)).where(
                    ActivityAttentionRequest.thread_id == thread.id,
                    ActivityAttentionRequest.status == "pending",
                )
            )
            or 0
        )
    return {
        "thread": thread,
        "messages": messages,
        "entity": entity_resource(definition, entity),
        "capabilities": activity_capabilities(user),
        "unread_count": unread_count,
        "pending_attention_count": pending_attention_count,
    }


def _thread_unread_count(db: Session, thread_id: int, user_id: int) -> int:
    receipt = db.scalar(
        select(ActivityThreadRead).where(
            ActivityThreadRead.thread_id == thread_id,
            ActivityThreadRead.user_id == user_id,
        )
    )
    query = select(func.count(ActivityMessage.id)).where(
        ActivityMessage.thread_id == thread_id,
        or_(
            ActivityMessage.author_id.is_(None),
            ActivityMessage.author_id != user_id,
        ),
    )
    if receipt and receipt.last_read_message_id:
        query = query.where(
            ActivityMessage.id > receipt.last_read_message_id
        )
    return int(db.scalar(query) or 0)


def mark_thread_read(
    db: Session,
    entity_type: str,
    entity_id: int,
    user: User,
) -> int:
    ensure_entity_access(db, user, entity_type, entity_id)
    thread = _find_thread(db, entity_type, entity_id)
    if thread is None:
        return 0
    last_message_id = db.scalar(
        select(func.max(ActivityMessage.id)).where(
            ActivityMessage.thread_id == thread.id
        )
    )
    receipt = db.scalar(
        select(ActivityThreadRead).where(
            ActivityThreadRead.thread_id == thread.id,
            ActivityThreadRead.user_id == user.id,
        )
    )
    if receipt is None:
        receipt = ActivityThreadRead(thread_id=thread.id, user_id=user.id)
        db.add(receipt)
    receipt.last_read_message_id = last_message_id
    receipt.last_visited_at = _now()
    db.commit()
    return 0


def create_message(
    db: Session,
    entity_type: str,
    entity_id: int,
    payload: ActivityMessageCreate,
    user: User,
) -> ActivityMessage:
    _require_permission(user, "activity.create")
    ensure_entity_access(db, user, entity_type, entity_id)
    if payload.mentioned_user_ids:
        _require_permission(user, "activity.mention")
    thread = _get_or_create_thread(
        db, entity_type, entity_id, created_by_id=user.id
    )
    message = ActivityMessage(
        thread_id=thread.id,
        author_id=user.id,
        body=payload.body.strip(),
        message_type="comment",
        metadata_json={},
    )
    db.add(message)
    db.flush()
    thread.updated_at = _now()
    _sync_mentions(db, message, payload.mentioned_user_ids, user)
    # `#tarea` es sólo un atajo de captura; la tarea conserva identidad propia
    # y el mensaje origen garantiza idempotencia.
    from app.services.service_execution import task_from_activity_message

    task_from_activity_message(db, message)
    write_audit_log(
        db,
        action="activity.message_created",
        entity=entity_type,
        entity_id=entity_id,
        user_id=user.id,
        new_values={"message_id": message.id, "message_type": "comment"},
    )
    db.commit()
    return get_message(db, message.id)


def publish_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    event_code: str,
    idempotency_key: str,
    body: str,
    actor_id: int | None = None,
    metadata: dict | None = None,
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
) -> ActivityMessage:
    """Publica un evento operativo idempotente; nunca ejecuta commit."""

    definition = get_activity_entity_definition(entity_type)
    entity = db.get(definition.model, entity_id)
    if entity is None:
        raise ValueError(f"Entidad de Activity inexistente: {entity_type}:{entity_id}")
    existing = db.scalar(
        select(ActivityMessage).where(
            ActivityMessage.idempotency_key == idempotency_key
        ).options(*_message_options())
    )
    if existing is not None:
        return existing
    thread = _get_or_create_thread(
        db, entity_type, entity_id, created_by_id=actor_id
    )
    message = ActivityMessage(
        thread_id=thread.id,
        author_id=actor_id,
        message_type="event",
        body=body.strip(),
        is_system=True,
        is_formal=True,
        event_code=event_code,
        idempotency_key=idempotency_key,
        metadata_json=metadata or {},
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    try:
        with db.begin_nested():
            db.add(message)
            db.flush()
    except IntegrityError:
        existing = db.scalar(
            select(ActivityMessage)
            .where(ActivityMessage.idempotency_key == idempotency_key)
            .options(*_message_options())
        )
        if existing is None:
            raise
        return existing
    thread.updated_at = _now()
    return message


def get_message(db: Session, message_id: int) -> ActivityMessage:
    message = db.scalar(
        select(ActivityMessage)
        .where(ActivityMessage.id == message_id)
        .options(*_message_options())
    )
    if message is None:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    return message


def update_message(
    db: Session,
    message_id: int,
    payload: ActivityMessageUpdate,
    user: User,
) -> ActivityMessage:
    _require_permission(user, "activity.edit_own")
    message = get_message(db, message_id)
    ensure_entity_access(
        db, user, message.thread.entity_type, message.thread.entity_id
    )
    if message.author_id != user.id:
        raise HTTPException(
            status_code=403, detail="Sólo el autor puede editar este mensaje"
        )
    if message.is_system or message.is_formal or message.withdrawn_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Este mensaje es inmutable; publica una aclaración",
        )
    created_at = message.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if _now() - created_at > EDIT_WINDOW:
        raise HTTPException(
            status_code=409,
            detail="El plazo institucional de edición de 30 minutos terminó",
        )
    if payload.mentioned_user_ids:
        _require_permission(user, "activity.mention")
    new_body = payload.body.strip()
    if new_body != message.body:
        db.add(
            ActivityMessageRevision(
                message_id=message.id,
                previous_body=message.body,
                new_body=new_body,
                edited_by_id=user.id,
                reason=payload.reason,
                created_at=_now(),
            )
        )
        message.body = new_body
        message.edited_at = _now()
    _sync_mentions(db, message, payload.mentioned_user_ids, user)
    write_audit_log(
        db,
        action="activity.message_edited",
        entity=message.thread.entity_type,
        entity_id=message.thread.entity_id,
        user_id=user.id,
        new_values={"message_id": message.id},
    )
    db.commit()
    return get_message(db, message.id)


def withdraw_message(
    db: Session,
    message_id: int,
    payload: ActivityMessageWithdraw,
    user: User,
) -> ActivityMessage:
    message = get_message(db, message_id)
    ensure_entity_access(
        db, user, message.thread.entity_type, message.thread.entity_id
    )
    own = message.author_id == user.id
    if own:
        _require_permission(user, "activity.delete_own")
    elif not user_has_permission(user, "activity.moderate"):
        raise HTTPException(status_code=403, detail="No puedes retirar este mensaje")
    if message.is_system or message.is_formal:
        raise HTTPException(
            status_code=409,
            detail="Los eventos y decisiones formales no pueden retirarse",
        )
    if message.withdrawn_at is None:
        message.withdrawn_at = _now()
        message.withdrawn_by_id = user.id
        message.withdrawal_reason = payload.reason
        message.withdrawal_note = payload.note
        for attachment in message.attachments:
            if not attachment.is_official_evidence:
                attachment.hidden_with_message = True
        revoked = {
            mention.mentioned_user_id
            for mention in message.mentions
            if mention.revoked_at is None
        }
        for mention in message.mentions:
            if mention.revoked_at is None:
                mention.revoked_at = message.withdrawn_at
        revoke_activity_mention_notifications(
            db, message_id=message.id, recipient_user_ids=revoked
        )
        write_audit_log(
            db,
            action="activity.message_withdrawn",
            entity=message.thread.entity_type,
            entity_id=message.thread.entity_id,
            user_id=user.id,
            new_values={
                "message_id": message.id,
                "reason": payload.reason,
            },
        )
        db.commit()
    return get_message(db, message.id)


def _sync_mentions(
    db: Session,
    message: ActivityMessage,
    user_ids: list[int],
    actor: User,
) -> None:
    requested = set(user_ids)
    existing_users = set()
    if requested:
        existing_users = set(
            db.scalars(
                select(User.id).where(
                    User.id.in_(requested), User.is_active.is_(True)
                )
            ).all()
        )
    missing = requested - existing_users
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Usuarios mencionados no encontrados",
                "user_ids": sorted(missing),
            },
        )
    current = {
        mention.mentioned_user_id: mention for mention in message.mentions
    }
    revoked: set[int] = set()
    for user_id, mention in current.items():
        if user_id not in requested and mention.revoked_at is None:
            mention.revoked_at = _now()
            revoked.add(user_id)
    if revoked:
        revoke_activity_mention_notifications(
            db, message_id=message.id, recipient_user_ids=revoked
        )
    for user_id in requested:
        mention = current.get(user_id)
        if mention is None:
            mention = ActivityMention(
                message=message, mentioned_user_id=user_id
            )
            db.add(mention)
        else:
            mention.revoked_at = None
        create_activity_mention_notification(
            db,
            message=message,
            recipient_user_id=user_id,
            actor=actor,
        )


def add_attachment(
    db: Session,
    message_id: int,
    upload: UploadFile,
    user: User,
) -> ActivityAttachment:
    _require_permission(user, "activity.attach_files")
    message = get_message(db, message_id)
    ensure_entity_access(
        db, user, message.thread.entity_type, message.thread.entity_id
    )
    if (
        message.author_id != user.id
        or message.withdrawn_at is not None
        or message.is_system
    ):
        raise HTTPException(
            status_code=409,
            detail="No se pueden adjuntar archivos a este mensaje",
        )
    if len(message.attachments) >= MAX_ATTACHMENTS_PER_MESSAGE:
        raise HTTPException(
            status_code=409,
            detail="Cada mensaje admite como máximo 10 archivos",
        )
    original_name = upload.filename or "archivo"
    validated = validate_upload(upload, "activity_attachment")
    content_type = validated.declared_mime
    stored_name = (
        f"{uuid4().hex}_"
        f"{safe_filename(original_name, fallback='archivo')}"
    )
    saved = save_validated_content(
        directory=(
            f"activity/{message.thread.entity_type}/"
            f"{message.thread.entity_id}/{message.id}"
        ),
        filename=stored_name,
        content=validated.content,
        original_filename=validated.original_filename,
    )
    attachment = ActivityAttachment(
        message_id=message.id,
        original_name=original_name,
        stored_path=saved.relative_path,
        content_type=content_type,
        size_bytes=len(validated.content),
        uploaded_by_id=user.id,
    )
    db.add(attachment)
    write_audit_log(
        db,
        action="activity.attachment_added",
        entity=message.thread.entity_type,
        entity_id=message.thread.entity_id,
        user_id=user.id,
        new_values={
            "message_id": message.id,
            "filename": original_name,
            "size_bytes": len(validated.content),
            "checksum_sha256": validated.checksum_sha256,
        },
    )
    db.commit()
    db.refresh(attachment)
    return attachment


def attachment_path(
    db: Session,
    attachment_id: int,
    user: User,
) -> tuple[ActivityAttachment, Path]:
    attachment = db.get(ActivityAttachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    message = get_message(db, attachment.message_id)
    ensure_entity_access(
        db, user, message.thread.entity_type, message.thread.entity_id
    )
    if (
        attachment.hidden_with_message
        and not user_has_permission(user, "activity.view_audit")
    ):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    path = resolve_storage_path(attachment.stored_path)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no disponible")
    return attachment, path


def request_attention(
    db: Session,
    message_id: int,
    payload: ActivityAttentionCreate,
    user: User,
) -> ActivityAttentionRequest:
    _require_permission(user, "activity.request_attention")
    message = get_message(db, message_id)
    ensure_entity_access(
        db, user, message.thread.entity_type, message.thread.entity_id
    )
    if message.withdrawn_at is not None or message.is_system:
        raise HTTPException(
            status_code=409,
            detail="La atención debe ligarse a un mensaje humano vigente",
        )
    assigned_user = None
    if payload.assigned_user_id is not None:
        assigned_user = db.scalar(
            select(User).where(
                User.id == payload.assigned_user_id,
                User.is_active.is_(True),
            )
        )
        if assigned_user is None:
            raise HTTPException(
                status_code=422, detail="Usuario responsable no encontrado"
            )
    duplicate = db.scalar(
        select(ActivityAttentionRequest).where(
            ActivityAttentionRequest.message_id == message.id,
            ActivityAttentionRequest.assigned_user_id
            == payload.assigned_user_id,
            ActivityAttentionRequest.assigned_area
            == (
                payload.assigned_area.strip()
                if payload.assigned_area
                else None
            ),
            ActivityAttentionRequest.status == "pending",
        )
    )
    if duplicate is not None:
        return duplicate
    attention = ActivityAttentionRequest(
        thread_id=message.thread_id,
        message_id=message.id,
        requested_by_id=user.id,
        assigned_user_id=payload.assigned_user_id,
        assigned_area=(
            payload.assigned_area.strip() if payload.assigned_area else None
        ),
        priority=payload.priority,
        status="pending",
    )
    db.add(attention)
    db.flush()
    message.thread.updated_at = _now()
    attention.message = message
    create_activity_attention_notification(db, attention=attention, actor=user)
    write_audit_log(
        db,
        action="activity.attention_requested",
        entity=message.thread.entity_type,
        entity_id=message.thread.entity_id,
        user_id=user.id,
        new_values={
            "attention_id": attention.id,
            "assigned_user_id": attention.assigned_user_id,
            "assigned_area": attention.assigned_area,
            "priority": attention.priority,
        },
    )
    db.commit()
    return get_attention(db, attention.id)


def get_attention(
    db: Session,
    attention_id: int,
) -> ActivityAttentionRequest:
    attention = db.scalar(
        select(ActivityAttentionRequest)
        .where(ActivityAttentionRequest.id == attention_id)
        .options(
            selectinload(ActivityAttentionRequest.message).selectinload(
                ActivityMessage.thread
            ),
            selectinload(ActivityAttentionRequest.requested_by),
            selectinload(ActivityAttentionRequest.assigned_user),
            selectinload(ActivityAttentionRequest.resolved_by),
        )
    )
    if attention is None:
        raise HTTPException(
            status_code=404, detail="Solicitud de atención no encontrada"
        )
    return attention


def resolve_attention(
    db: Session,
    attention_id: int,
    payload: ActivityAttentionResolve,
    user: User,
) -> ActivityAttentionRequest:
    _require_permission(user, "activity.resolve_attention")
    attention = get_attention(db, attention_id)
    message = attention.message
    ensure_entity_access(
        db, user, message.thread.entity_type, message.thread.entity_id
    )
    if (
        attention.assigned_user_id is not None
        and attention.assigned_user_id != user.id
        and not user_has_permission(user, "activity.moderate")
    ):
        raise HTTPException(
            status_code=403,
            detail="La solicitud está asignada a otro usuario",
        )
    if attention.status == "pending":
        attention.status = "resolved"
        attention.resolved_at = _now()
        attention.resolved_by_id = user.id
        attention.resolution_note = payload.note
        message.thread.updated_at = _now()
        resolve_activity_attention_notification(db, attention=attention)
        write_audit_log(
            db,
            action="activity.attention_resolved",
            entity=message.thread.entity_type,
            entity_id=message.thread.entity_id,
            user_id=user.id,
            new_values={"attention_id": attention.id},
        )
        db.commit()
    return get_attention(db, attention.id)


def list_inbox(
    db: Session,
    user: User,
    *,
    unread_only: bool = False,
    attention_only: bool = False,
    limit: int = 50,
) -> dict:
    _require_permission(user, "activity.read")
    threads = list(
        db.scalars(
            select(ActivityThread)
            .order_by(ActivityThread.updated_at.desc(), ActivityThread.id.desc())
            .limit(min(max(limit * 3, 50), 300))
        ).all()
    )
    items = []
    total_unread = 0
    total_attention = 0
    for thread in threads:
        try:
            definition, entity = ensure_entity_access(
                db, user, thread.entity_type, thread.entity_id
            )
        except HTTPException:
            continue
        last_message = db.scalar(
            select(ActivityMessage)
            .where(ActivityMessage.thread_id == thread.id)
            .options(*_message_options())
            .order_by(ActivityMessage.id.desc())
            .limit(1)
        )
        if last_message is None:
            continue
        unread = _thread_unread_count(db, thread.id, user.id)
        attention_filters = [
            ActivityAttentionRequest.thread_id == thread.id,
            ActivityAttentionRequest.status == "pending",
            or_(
                ActivityAttentionRequest.assigned_user_id == user.id,
                ActivityAttentionRequest.requested_by_id == user.id,
                ActivityAttentionRequest.assigned_user_id.is_(None),
            ),
        ]
        pending = int(
            db.scalar(
                select(func.count(ActivityAttentionRequest.id)).where(
                    *attention_filters
                )
            )
            or 0
        )
        total_unread += unread
        total_attention += pending
        if unread_only and unread == 0:
            continue
        if attention_only and pending == 0:
            continue
        items.append(
            {
                "thread_id": thread.id,
                "entity": entity_resource(definition, entity),
                "last_message": last_message,
                "unread_count": unread,
                "pending_attention_count": pending,
            }
        )
        if len(items) >= limit:
            break
    return {
        "items": items,
        "total": len(items),
        "unread_count": total_unread,
        "pending_attention_count": total_attention,
    }


def list_entity_definitions(user: User) -> list[dict]:
    _require_permission(user, "activity.read")
    return [
        definition.snapshot()
        for definition in ACTIVITY_ENTITY_DEFINITIONS.values()
        if user_has_permission(user, definition.read_permission)
    ]


def list_mentionable_users(db: Session, user: User) -> list[dict]:
    _require_permission(user, "activity.mention")
    users = list(
        db.scalars(
            select(User)
            .where(User.is_active.is_(True))
            .options(selectinload(User.roles))
            .order_by(User.full_name.asc(), User.id.asc())
        ).all()
    )
    return [
        {
            "id": candidate.id,
            "full_name": candidate.full_name,
            "email": candidate.email,
            "role_name": next(
                (role.name for role in candidate.roles if role.is_active),
                None,
            ),
        }
        for candidate in users
        if candidate.id != user.id
    ]
