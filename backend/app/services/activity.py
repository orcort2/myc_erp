from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.activity import (
    ActivityAttachment,
    ActivityMention,
    ActivityMessage,
    ActivityMessageRevision,
    ActivityThread,
)
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.service_order import ServiceOrder
from app.models.user import User
from app.schemas.activity import ActivityMessageCreate, ActivityMessageUpdate, ActivityMessageWithdraw
from app.services.auth import user_has_permission
from app.services.storage_service import resolve_storage_path, safe_filename, save_upload

ENTITY_RULES = {
    "client": (Client, "clients.read", "clients.update"),
    "service_order": (ServiceOrder, "service_orders.read", "service_orders.update"),
    "invoice": (Invoice, "invoices.read", "invoices.manage"),
}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024


def _entity_rule(entity_type: str):
    rule = ENTITY_RULES.get(entity_type)
    if not rule:
        raise HTTPException(status_code=422, detail="Tipo de entidad no compatible con Actividad")
    return rule


def ensure_entity_access(db: Session, user: User, entity_type: str, entity_id: int, *, write: bool = False):
    model, read_permission, write_permission = _entity_rule(entity_type)
    if not user_has_permission(user, write_permission if write else read_permission):
        raise HTTPException(status_code=403, detail="No tienes permiso para acceder a la actividad de esta entidad")
    entity = db.get(model, entity_id)
    if entity is None or getattr(entity, "is_active", True) is False:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")
    return entity


def _message_options():
    return (
        selectinload(ActivityMessage.thread),
        selectinload(ActivityMessage.author),
        selectinload(ActivityMessage.revisions),
        selectinload(ActivityMessage.attachments),
        selectinload(ActivityMessage.mentions).selectinload(ActivityMention.mentioned_user),
    )


def get_or_create_thread(db: Session, entity_type: str, entity_id: int, user: User) -> ActivityThread:
    ensure_entity_access(db, user, entity_type, entity_id)
    thread = db.scalar(
        select(ActivityThread).where(
            ActivityThread.entity_type == entity_type,
            ActivityThread.entity_id == entity_id,
        )
    )
    if thread is None:
        thread = ActivityThread(entity_type=entity_type, entity_id=entity_id, created_by_id=user.id)
        db.add(thread)
        db.commit()
        db.refresh(thread)
    return thread


def list_messages(db: Session, entity_type: str, entity_id: int, user: User) -> tuple[ActivityThread, list[ActivityMessage]]:
    thread = get_or_create_thread(db, entity_type, entity_id, user)
    messages = list(
        db.scalars(
            select(ActivityMessage)
            .where(ActivityMessage.thread_id == thread.id)
            .options(*_message_options())
            .order_by(ActivityMessage.created_at.asc(), ActivityMessage.id.asc())
        ).all()
    )
    return thread, messages


def _sync_mentions(db: Session, message: ActivityMessage, user_ids: list[int]) -> None:
    requested = set(user_ids)
    if requested:
        existing_users = set(db.scalars(select(User.id).where(User.id.in_(requested), User.is_active.is_(True))).all())
        missing = requested - existing_users
        if missing:
            raise HTTPException(status_code=422, detail={"message": "Usuarios mencionados no encontrados", "user_ids": sorted(missing)})
    current = {mention.mentioned_user_id: mention for mention in message.mentions}
    now = datetime.now(timezone.utc)
    for user_id, mention in current.items():
        if user_id not in requested and mention.revoked_at is None:
            mention.revoked_at = now
    for user_id in requested:
        mention = current.get(user_id)
        if mention:
            mention.revoked_at = None
        else:
            db.add(ActivityMention(message=message, mentioned_user_id=user_id))


def create_message(db: Session, entity_type: str, entity_id: int, payload: ActivityMessageCreate, user: User) -> ActivityMessage:
    ensure_entity_access(db, user, entity_type, entity_id, write=True)
    thread = get_or_create_thread(db, entity_type, entity_id, user)
    message = ActivityMessage(thread_id=thread.id, author_id=user.id, body=payload.body.strip())
    db.add(message)
    db.flush()
    _sync_mentions(db, message, payload.mentioned_user_ids)
    db.commit()
    return get_message(db, message.id)


def get_message(db: Session, message_id: int) -> ActivityMessage:
    message = db.scalar(select(ActivityMessage).where(ActivityMessage.id == message_id).options(*_message_options()))
    if message is None:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    return message


def update_message(db: Session, message_id: int, payload: ActivityMessageUpdate, user: User) -> ActivityMessage:
    message = get_message(db, message_id)
    ensure_entity_access(db, user, message.thread.entity_type, message.thread.entity_id, write=True)
    if message.author_id != user.id:
        raise HTTPException(status_code=403, detail="Sólo el autor puede editar este mensaje")
    if message.is_system or message.is_formal or message.withdrawn_at is not None:
        raise HTTPException(status_code=409, detail="Este mensaje es inmutable; publica una aclaración")
    new_body = payload.body.strip()
    if new_body != message.body:
        db.add(ActivityMessageRevision(
            message_id=message.id,
            previous_body=message.body,
            new_body=new_body,
            edited_by_id=user.id,
            reason=payload.reason,
            created_at=datetime.now(timezone.utc),
        ))
        message.body = new_body
        message.edited_at = datetime.now(timezone.utc)
    _sync_mentions(db, message, payload.mentioned_user_ids)
    db.commit()
    return get_message(db, message.id)


def withdraw_message(db: Session, message_id: int, payload: ActivityMessageWithdraw, user: User) -> ActivityMessage:
    message = get_message(db, message_id)
    ensure_entity_access(db, user, message.thread.entity_type, message.thread.entity_id, write=True)
    if message.author_id != user.id and not user_has_permission(user, "activity.moderate"):
        raise HTTPException(status_code=403, detail="No puedes retirar este mensaje")
    if message.is_system or message.is_formal:
        raise HTTPException(status_code=409, detail="Los eventos y decisiones formales no pueden retirarse")
    if message.withdrawn_at is None:
        message.withdrawn_at = datetime.now(timezone.utc)
        message.withdrawn_by_id = user.id
        message.withdrawal_reason = payload.reason
        message.withdrawal_note = payload.note
        for attachment in message.attachments:
            if not attachment.is_official_evidence:
                attachment.hidden_with_message = True
        for mention in message.mentions:
            if mention.revoked_at is None:
                mention.revoked_at = message.withdrawn_at
        db.commit()
    return get_message(db, message.id)


def add_attachment(db: Session, message_id: int, upload: UploadFile, user: User) -> ActivityAttachment:
    message = get_message(db, message_id)
    ensure_entity_access(db, user, message.thread.entity_type, message.thread.entity_id, write=True)
    if message.author_id != user.id or message.withdrawn_at is not None or message.is_system:
        raise HTTPException(status_code=409, detail="No se pueden adjuntar archivos a este mensaje")
    content_type = upload.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Tipo de archivo no permitido")
    raw = upload.file.read(MAX_ATTACHMENT_BYTES + 1)
    if len(raw) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 15 MB")
    upload.file.seek(0)
    stored_name = safe_filename(upload.filename or "archivo")
    saved = save_upload(
        upload,
        directory=f"activity/{message.thread.entity_type}/{message.thread.entity_id}/{message.id}",
        filename=stored_name,
    )
    attachment = ActivityAttachment(
        message_id=message.id,
        original_name=upload.filename or Path(saved.relative_path).name,
        stored_path=saved.relative_path,
        content_type=content_type,
        size_bytes=len(raw),
        uploaded_by_id=user.id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def attachment_path(db: Session, attachment_id: int, user: User) -> tuple[ActivityAttachment, Path]:
    attachment = db.get(ActivityAttachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    message = get_message(db, attachment.message_id)
    ensure_entity_access(db, user, message.thread.entity_type, message.thread.entity_id)
    if attachment.hidden_with_message and not user_has_permission(user, "activity.audit"):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    path = resolve_storage_path(attachment.stored_path)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no disponible")
    return attachment, path
