from datetime import timedelta
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 - registra todos los modelos en Base
from app.core.db import Base
from app.models.activity import (
    ActivityAttentionRequest,
    ActivityMessage,
    ActivityMessageRevision,
    ActivityThread,
    ActivityThreadRead,
)
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.notification import Notification
from app.models.user import Role, User
from app.schemas.activity import (
    ActivityAttentionCreate,
    ActivityAttentionResolve,
    ActivityMessageCreate,
    ActivityMessageUpdate,
    ActivityMessageWithdraw,
)
from app.services import activity as activity_service


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()


def _user(db: Session, role_name: str, suffix: str) -> User:
    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        role = Role(name=role_name, description=role_name)
        db.add(role)
        db.flush()
    user = User(
        email=f"{suffix}@example.test",
        full_name=f"Usuario {suffix}",
        hashed_password="not-used",
        role_id=role.id,
        roles=[role],
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def context(db: Session):
    author = _user(db, "Comercial", "author")
    peer = _user(db, "Comercial", "peer")
    quality = _user(db, "Calidad", "quality")
    administrator = _user(db, "Administrador", "administrator")
    auditor = _user(db, "Auditor", "auditor")
    client = Client(legal_name="Cliente Activity", notes="Nota histórica")
    other_client = Client(legal_name="Cliente aislado")
    db.add_all([client, other_client])
    db.commit()
    return SimpleNamespace(
        author=author,
        peer=peer,
        quality=quality,
        administrator=administrator,
        auditor=auditor,
        client=client,
        other_client=other_client,
    )


def _create_message(db: Session, context, *, mentions=None):
    return activity_service.create_message(
        db,
        "client",
        context.client.id,
        ActivityMessageCreate(
            body="Seguimiento institucional",
            mentioned_user_ids=mentions or [],
        ),
        context.author,
    )


def test_create_list_mentions_unread_and_explicit_read(db: Session, context):
    message = _create_message(db, context, mentions=[context.peer.id])

    activity = activity_service.get_activity(
        db, "client", context.client.id, context.peer
    )
    assert activity["thread"].id == message.thread_id
    assert activity["unread_count"] == 1
    assert activity["messages"][0].mentions[0].mentioned_user_id == context.peer.id
    assert db.scalar(select(func.count(Notification.id))) == 1

    assert (
        activity_service.mark_thread_read(
            db, "client", context.client.id, context.peer
        )
        == 0
    )
    assert activity_service.get_activity(
        db, "client", context.client.id, context.peer
    )["unread_count"] == 0
    receipt = db.scalar(select(ActivityThreadRead))
    assert receipt.last_read_message_id == message.id


def test_entity_permission_and_thread_isolation(db: Session, context):
    _create_message(db, context)
    isolated = activity_service.get_activity(
        db, "client", context.other_client.id, context.author
    )
    assert isolated["thread"] is None
    assert isolated["messages"] == []

    with pytest.raises(HTTPException) as forbidden:
        activity_service.get_activity(
            db, "client", context.client.id, context.auditor
        )
    assert forbidden.value.status_code == 403


def test_edit_keeps_revision_and_rejects_other_author(db: Session, context):
    message = _create_message(db, context)
    updated = activity_service.update_message(
        db,
        message.id,
        ActivityMessageUpdate(
            body="Seguimiento corregido",
            reason="Precisión",
        ),
        context.author,
    )
    assert updated.body == "Seguimiento corregido"
    revision = db.scalar(select(ActivityMessageRevision))
    assert revision.previous_body == "Seguimiento institucional"
    assert revision.reason == "Precisión"

    with pytest.raises(HTTPException) as forbidden:
        activity_service.update_message(
            db,
            message.id,
            ActivityMessageUpdate(body="Cambio ajeno"),
            context.peer,
        )
    assert forbidden.value.status_code == 403

    message.created_at = message.created_at - timedelta(minutes=31)
    db.commit()
    with pytest.raises(HTTPException) as expired:
        activity_service.update_message(
            db,
            message.id,
            ActivityMessageUpdate(body="Cambio tardío"),
            context.author,
        )
    assert expired.value.status_code == 409


def test_soft_withdraw_preserves_audit_history(db: Session, context):
    message = _create_message(db, context, mentions=[context.peer.id])
    withdrawn = activity_service.withdraw_message(
        db,
        message.id,
        ActivityMessageWithdraw(reason="Duplicado", note="Se aclaró después"),
        context.author,
    )
    assert withdrawn.withdrawn_at is not None
    assert db.get(ActivityMessage, message.id) is not None
    assert withdrawn.mentions[0].revoked_at is not None
    actions = set(db.scalars(select(AuditLog.action)).all())
    assert "activity.message_created" in actions
    assert "activity.message_withdrawn" in actions


def test_attachment_checks_declared_type_and_signature(
    db: Session, context, monkeypatch
):
    message = _create_message(db, context)

    mismatched = UploadFile(
        filename="evidencia.png",
        file=BytesIO(b"%PDF-1.7"),
        headers={"content-type": "application/pdf"},
    )
    with pytest.raises(HTTPException) as invalid_type:
        activity_service.add_attachment(
            db, message.id, mismatched, context.author
        )
    assert invalid_type.value.status_code == 415

    invalid_signature = UploadFile(
        filename="evidencia.png",
        file=BytesIO(b"not-an-image"),
        headers={"content-type": "image/png"},
    )
    with pytest.raises(HTTPException) as invalid_content:
        activity_service.add_attachment(
            db, message.id, invalid_signature, context.author
        )
    assert invalid_content.value.status_code == 415

    monkeypatch.setattr(
        activity_service,
        "save_upload",
        lambda *args, **kwargs: SimpleNamespace(
            relative_path="activity/client/1/evidencia.png"
        ),
    )
    valid = UploadFile(
        filename="evidencia.png",
        file=BytesIO(b"\x89PNG\r\n\x1a\nvalid"),
        headers={"content-type": "image/png"},
    )
    attachment = activity_service.add_attachment(
        db, message.id, valid, context.author
    )
    assert attachment.content_type == "image/png"
    assert attachment.size_bytes == 13


def test_attention_assignment_notification_and_resolution(db: Session, context):
    message = _create_message(db, context)
    attention = activity_service.request_attention(
        db,
        message.id,
        ActivityAttentionCreate(
            assigned_user_id=context.administrator.id,
            priority="high",
        ),
        context.author,
    )
    assert attention.status == "pending"
    assert attention.assigned_user_id == context.administrator.id
    assert db.scalar(select(func.count(Notification.id))) == 1

    resolved = activity_service.resolve_attention(
        db,
        attention.id,
        ActivityAttentionResolve(note="Atendido"),
        context.administrator,
    )
    assert resolved.status == "resolved"
    assert resolved.resolved_by_id == context.administrator.id
    assert resolved.resolution_note == "Atendido"


def test_system_event_is_idempotent_immutable_and_unread(db: Session, context):
    first = activity_service.publish_event(
        db,
        entity_type="client",
        entity_id=context.client.id,
        event_code="client.reviewed",
        idempotency_key=f"client:{context.client.id}:reviewed:v1",
        body="Cliente revisado",
        metadata={"source": "test"},
    )
    second = activity_service.publish_event(
        db,
        entity_type="client",
        entity_id=context.client.id,
        event_code="client.reviewed",
        idempotency_key=f"client:{context.client.id}:reviewed:v1",
        body="No debe duplicarse",
    )
    db.commit()
    assert first.id == second.id
    assert db.scalar(select(func.count(ActivityMessage.id))) == 1
    assert activity_service.get_activity(
        db, "client", context.client.id, context.author
    )["unread_count"] == 1

    with pytest.raises(HTTPException) as immutable:
        activity_service.withdraw_message(
            db,
            first.id,
            ActivityMessageWithdraw(reason="No aplica"),
        context.administrator,
        )
    assert immutable.value.status_code == 409


def test_inbox_filters_by_entity_access(db: Session, context):
    _create_message(db, context)
    inbox = activity_service.list_inbox(db, context.peer)
    assert inbox["total"] == 1
    assert inbox["items"][0]["entity"]["entity_id"] == context.client.id
    assert inbox["unread_count"] == 1

    auditor_inbox = activity_service.list_inbox(db, context.auditor)
    assert auditor_inbox["total"] == 0
