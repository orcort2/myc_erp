"""@OT: buscar y mencionar una OT LAB desde Comunicaciones.

Cubre autorización (búsqueda y creación de mención exigen autoridad LAB, no
sólo la existencia de la OT), todos los estados válidos, y el endurecimiento
anti-spoofing del marcador [[work_order:N]] persistido en el body: un texto
manual idéntico al marcador nunca debe convertirse en una mención estructurada
que el emisor no tenía autoridad real para crear."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base
from app.models.communication import CommunicationMessage
from app.models.lab_work_order import LabWorkOrder
from app.models.user import Role, User
from app.schemas.communication import CommunicationConversationCreate, CommunicationMentionCreate, CommunicationMessageCreate
from app.services.communications import add_message, create_conversation, search_work_order_mentions


@pytest.fixture()
def mention_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        technician = Role(name="Tecnico", description="Técnico")  # tiene lab_work_orders.use
        no_lab_access = Role(name="SinAccesoLAB", description="Rol sin permisos LAB")  # no está en la matriz
        db.add_all([technician, no_lab_access])
        db.flush()
        users = {}
        for key, role in (
            ("sender", technician), ("recipient", technician), ("outsider", no_lab_access),
        ):
            user = User(
                username=f"otmention-{key}",
                email=f"otmention-{key}@example.test",
                full_name=key.title(),
                hashed_password="unused",
                account_type="internal",
                status="active",
                is_active=True,
                role_id=role.id,
                roles=[role],
            )
            db.add(user)
            users[key] = user
        db.flush()

        completed_wo = LabWorkOrder(
            folio=6420, sequence_number=1, created_by_user_id=users["sender"].id,
            reception_date=date(2026, 8, 13), client_name="Cliente Completada", address="",
            status="completed",
        )
        cancelled_wo = LabWorkOrder(
            folio=6421, sequence_number=1, created_by_user_id=users["sender"].id,
            reception_date=date(2026, 8, 13), client_name="Cliente Cancelada", address="",
            status="cancelled",
        )
        db.add_all([completed_wo, cancelled_wo])
        db.commit()
        yield db, users, {"completed": completed_wo.id, "cancelled": cancelled_wo.id}


def _direct(db, sender, recipient):
    payload = CommunicationConversationCreate(conversation_type="internal", participant_user_id=recipient.id)
    conversation, _message, _notifications = create_conversation(db, sender, payload)
    return conversation


def test_authorized_user_can_search_by_folio(mention_db):
    db, users, _wo = mention_db
    results = search_work_order_mentions(db, users["sender"], "6420")
    assert any(item.folio == 6420 for item in results)


def test_authorized_user_can_search_by_client_name(mention_db):
    db, users, _wo = mention_db
    results = search_work_order_mentions(db, users["sender"], "Completada")
    assert any(item.client_name == "Cliente Completada" for item in results)


def test_completed_work_orders_appear_in_search(mention_db):
    db, users, wo = mention_db
    results = search_work_order_mentions(db, users["sender"], "6420")
    assert any(item.work_order_id == wo["completed"] and item.status == "completed" for item in results)


def test_cancelled_work_orders_appear_in_search(mention_db):
    db, users, wo = mention_db
    results = search_work_order_mentions(db, users["sender"], "6421")
    assert any(item.work_order_id == wo["cancelled"] and item.status == "cancelled" for item in results)


def test_user_without_lab_permission_gets_403_on_search(mention_db):
    db, users, _wo = mention_db
    with pytest.raises(HTTPException) as exc_info:
        search_work_order_mentions(db, users["outsider"], "6420")
    assert exc_info.value.status_code == 403


def test_nonexistent_work_order_id_is_rejected_on_mention_creation(mention_db):
    db, users, _wo = mention_db
    conversation = _direct(db, users["sender"], users["recipient"])
    payload = CommunicationMessageCreate(
        body="Revisa esta OT",
        client_message_id="client-nonexistent-wo",
        mentions=[CommunicationMentionCreate(kind="work_order", work_order_id=999999)],
    )
    with pytest.raises(HTTPException) as exc_info:
        add_message(db, conversation.id, users["sender"], payload.body, payload.client_message_id, payload.mentions)
    assert exc_info.value.status_code == 422


def test_user_without_lab_permission_cannot_create_a_work_order_mention(mention_db):
    db, users, wo = mention_db
    conversation = _direct(db, users["outsider"], users["recipient"])
    payload = CommunicationMessageCreate(
        body="Revisa esta OT",
        client_message_id="client-outsider-mention",
        mentions=[CommunicationMentionCreate(kind="work_order", work_order_id=wo["completed"])],
    )
    with pytest.raises(HTTPException) as exc_info:
        add_message(db, conversation.id, users["outsider"], payload.body, payload.client_message_id, payload.mentions)
    assert exc_info.value.status_code == 403


def test_manually_typed_marker_text_is_never_promoted_to_a_structured_mention(mention_db):
    """El defecto exacto auditado: un texto igual al marcador interno, escrito
    a mano sin pasar por MentionDraft(kind='work_order'), no debe convertirse
    en una mención estructurada -- ni siquiera si el work_order_id referenciado
    existe de verdad."""
    db, users, wo = mention_db
    conversation = _direct(db, users["sender"], users["recipient"])
    spoofed_body = f"Hola, revisa esto\n[[work_order:{wo['completed']}]]"
    message, _recipients, _notifications, created = add_message(
        db, conversation.id, users["sender"], spoofed_body, "client-spoof-attempt", [],
    )
    assert created
    with db.no_autoflush:
        stored = db.get(CommunicationMessage, message.id)
    assert "[[work_order:" not in stored.body, "el marcador tecleado a mano debe retirarse antes de persistir"
    assert stored.body == "Hola, revisa esto"


def test_retry_of_the_same_client_message_id_does_not_duplicate_the_mention(mention_db):
    db, users, wo = mention_db
    conversation = _direct(db, users["sender"], users["recipient"])
    mentions = [CommunicationMentionCreate(kind="work_order", work_order_id=wo["completed"])]

    first, _r, _n, created_first = add_message(
        db, conversation.id, users["sender"], "Ver OT por favor", "client-retry-mention", mentions,
    )
    assert created_first
    second, _r2, _n2, created_second = add_message(
        db, conversation.id, users["sender"], "Ver OT por favor", "client-retry-mention", mentions,
    )
    assert not created_second
    assert second.id == first.id
    assert first.body.count(f"[[work_order:{wo['completed']}]]") == 1


def test_visible_body_never_shows_the_raw_marker(mention_db):
    from app.services.communications import _message_read

    db, users, wo = mention_db
    conversation = _direct(db, users["sender"], users["recipient"])
    mentions = [CommunicationMentionCreate(kind="work_order", work_order_id=wo["completed"])]
    message, _r, _n, _created = add_message(
        db, conversation.id, users["sender"], "Ver OT por favor", "client-visible-body", mentions,
    )
    read = _message_read(message)
    assert "[[work_order:" not in read.body
    assert read.work_order_mentions[0].work_order_id == wo["completed"]


def test_tapping_navigation_uses_the_exact_work_order_id(mention_db):
    from app.services.communications import _message_read

    db, users, wo = mention_db
    conversation = _direct(db, users["sender"], users["recipient"])
    mentions = [CommunicationMentionCreate(kind="work_order", work_order_id=wo["cancelled"])]
    message, _r, _n, _created = add_message(
        db, conversation.id, users["sender"], "Otra OT", "client-nav-id", mentions,
    )
    read = _message_read(message)
    assert [item.work_order_id for item in read.work_order_mentions] == [wo["cancelled"]]
