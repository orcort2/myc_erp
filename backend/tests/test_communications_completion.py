from __future__ import annotations

import asyncio
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base
from app.core.db import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.communication import (
    CommunicationMessage,
    CommunicationMessageMention,
    CommunicationMessageReceipt,
    communication_participants,
)
from app.models.notification import Notification
from app.models.user import Role, User
from app.realtime.contracts import build_realtime_envelope
from app.realtime.hub import InMemoryRealtimeHub
from app.realtime.authentication import REALTIME_PROTOCOL
from app.routers.realtime import get_realtime_session_factory
from app.schemas.communication import (
    CommunicationConversationCreate,
    CommunicationMentionCreate,
    CommunicationMessageCreate,
    CommunicationReceiptUpdate,
)
from app.services.communications import (
    add_message,
    create_conversation,
    get_conversation,
    list_conversations,
    sync_messages,
    update_receipts,
)


@pytest.fixture()
def communication_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        technician = Role(name="Tecnico", description="Técnico")
        administrator = Role(name="Administrador", description="Administrador")
        db.add_all([technician, administrator])
        db.flush()
        users = {}
        for index, (key, role) in enumerate(
            (
                ("sender", technician),
                ("recipient", technician),
                ("third", technician),
                ("admin", administrator),
                ("attacker", technician),
            ),
            start=1,
        ):
            user = User(
                username=f"communication-{index}",
                email=f"communication-{index}@example.test",
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
        db.commit()
        yield db, users


def _direct(db, sender, recipient):
    payload = CommunicationConversationCreate(
        conversation_type="internal", participant_user_id=recipient.id
    )
    conversation, _message, _notifications = create_conversation(db, sender, payload)
    return conversation


def _message_payload(client_id: str, body: str = "Mensaje de prueba"):
    return CommunicationMessageCreate(body=body, client_message_id=client_id)


def test_direct_conversation_and_message_are_idempotent(communication_db):
    db, users = communication_db
    first = _direct(db, users["sender"], users["recipient"])
    second = _direct(db, users["recipient"], users["sender"])
    assert first.id == second.id

    payload = _message_payload("mobile-client-message-1")
    message, recipients, notification_ids, created = add_message(
        db,
        first.id,
        users["sender"],
        payload.body,
        payload.client_message_id,
        payload.mentions,
    )
    repeated, repeated_recipients, repeated_notifications, repeated_created = add_message(
        db,
        first.id,
        users["sender"],
        payload.body,
        payload.client_message_id,
        payload.mentions,
    )

    assert repeated.id == message.id
    assert message.sequence == 1
    assert recipients == repeated_recipients == {
        users["sender"].id,
        users["recipient"].id,
    }
    assert notification_ids
    assert created is True
    assert repeated_notifications == []
    assert repeated_created is False
    assert db.scalar(select(func.count(CommunicationMessage.id))) == 1
    assert db.scalar(select(func.count(Notification.id))) == 1
    notification = db.scalar(select(Notification))
    assert payload.body not in (notification.body or "")


def test_sync_recovers_gap_and_receipts_never_regress(communication_db):
    db, users = communication_db
    conversation = _direct(db, users["sender"], users["recipient"])
    messages = []
    for index in range(1, 4):
        message, _recipients, _notifications, _created = add_message(
            db,
            conversation.id,
            users["sender"],
            f"Mensaje {index}",
            f"mobile-client-message-{index}",
            [],
        )
        messages.append(message)

    recovered = sync_messages(
        db,
        conversation.id,
        users["recipient"].id,
        after_sequence=1,
    )
    assert [item.sequence for item in recovered.items] == [2, 3]
    assert recovered.latest_sequence == 3
    assert recovered.unread_count == 3

    update_receipts(
        db,
        conversation.id,
        users["recipient"].id,
        CommunicationReceiptUpdate(state="read", message_ids=[messages[2].id]),
    )
    update_receipts(
        db,
        conversation.id,
        users["recipient"].id,
        CommunicationReceiptUpdate(state="read", message_ids=[messages[0].id]),
    )
    participant = db.execute(
        select(communication_participants).where(
            communication_participants.c.conversation_id == conversation.id,
            communication_participants.c.user_id == users["recipient"].id,
        )
    ).mappings().one()
    assert participant["last_read_message_id"] == messages[2].id
    assert list_conversations(db, users["recipient"].id)[0].unread_count == 0
    receipt = db.get(
        CommunicationMessageReceipt,
        (messages[2].id, users["recipient"].id),
    )
    assert receipt.delivered_at is not None
    assert receipt.read_at is not None


def test_group_mentions_are_structured_and_mass_mentions_are_authorized(
    communication_db,
):
    db, users = communication_db
    payload = CommunicationConversationCreate(
        conversation_type="group",
        title="Laboratorio",
        participant_user_ids=[users["recipient"].id, users["third"].id],
    )
    conversation, _message, _notifications = create_conversation(
        db, users["sender"], payload
    )
    with pytest.raises(HTTPException) as denied:
        add_message(
            db,
            conversation.id,
            users["sender"],
            "@todos aviso",
            "mobile-mass-denied",
            [CommunicationMentionCreate(kind="all")],
        )
    assert denied.value.status_code == 403

    admin_group = CommunicationConversationCreate(
        conversation_type="group",
        title="Administración",
        participant_user_ids=[users["recipient"].id, users["third"].id],
    )
    admin_conversation, _message, _notifications = create_conversation(
        db, users["admin"], admin_group
    )
    message, _recipients, _notification_ids, _created = add_message(
        db,
        admin_conversation.id,
        users["admin"],
        "@todos aviso",
        "mobile-mass-allowed",
        [CommunicationMentionCreate(kind="all")],
    )
    mentions = list(
        db.scalars(
            select(CommunicationMessageMention).where(
                CommunicationMessageMention.message_id == message.id
            )
        ).all()
    )
    assert {item.mentioned_user_id for item in mentions} == {
        users["recipient"].id,
        users["third"].id,
    }
    assert {item.mention_kind for item in mentions} == {"all"}


def test_conversation_ownership_blocks_idor(communication_db):
    db, users = communication_db
    conversation = _direct(db, users["sender"], users["recipient"])
    assert get_conversation(db, conversation.id, users["attacker"].id) is None
    with pytest.raises(HTTPException) as denied:
        sync_messages(
            db,
            conversation.id,
            users["attacker"].id,
            after_sequence=0,
        )
    assert denied.value.status_code == 404


def test_user_room_reaches_multiple_devices_without_cross_user_delivery():
    class Socket:
        def __init__(self):
            self.sent = []

        async def send_json(self, payload):
            self.sent.append(payload)

    async def scenario():
        hub = InMemoryRealtimeHub()
        first_device = Socket()
        second_device = Socket()
        attacker_device = Socket()
        first = await hub.connect(first_device, 10)
        second = await hub.connect(second_device, 10)
        attacker = await hub.connect(attacker_device, 20)
        event = build_realtime_envelope("message.created", {"id": 1})
        delivered = await hub.publish_to_user(10, event)
        assert delivered == 2
        assert first_device.sent == second_device.sent == [event]
        assert attacker_device.sent == []
        await hub.disconnect(first)
        await hub.disconnect(second)
        await hub.disconnect(attacker)

    asyncio.run(scenario())


def test_persisted_rest_message_is_received_realtime_without_refresh(
    communication_db, monkeypatch
):
    db, users = communication_db
    conversation = _direct(db, users["sender"], users["recipient"])
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)

    def override_db():
        with factory() as session:
            yield session

    monkeypatch.setattr(
        "app.routers.communications.deliver_communication_notifications",
        lambda _ids: None,
    )
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_realtime_session_factory] = lambda: factory
    sender_token = create_access_token(
        str(users["sender"].id),
        extra_claims={"roles": ["Tecnico"], "auth_context": "internal"},
    )
    recipient_token = create_access_token(
        str(users["recipient"].id),
        extra_claims={"roles": ["Tecnico"], "auth_context": "internal"},
    )
    client = TestClient(app)
    try:
        with client.websocket_connect(
            "/api/realtime/ws",
            subprotocols=[REALTIME_PROTOCOL, f"auth.{recipient_token}"],
        ) as websocket:
            websocket.receive_json()
            websocket.send_json(
                {
                    "event": "conversation.subscribe",
                    "data": {"conversation_id": conversation.id},
                }
            )
            websocket.receive_json()
            payload = {
                "body": "Entrega REST a realtime",
                "client_message_id": "e2e-mobile-message-1",
            }
            response = client.post(
                f"/api/communications/conversations/{conversation.id}/messages",
                headers={"Authorization": f"Bearer {sender_token}"},
                json=payload,
            )
            assert response.status_code == 201, response.text
            realtime_message = websocket.receive_json()
            realtime_notification = websocket.receive_json()
            assert realtime_message["event"] == "message.created"
            assert realtime_message["data"]["client_message_id"] == payload["client_message_id"]
            assert realtime_notification["event"] == "notification.created"
            repeated = client.post(
                f"/api/communications/conversations/{conversation.id}/messages",
                headers={"Authorization": f"Bearer {sender_token}"},
                json=payload,
            )
            assert repeated.status_code == 201
            assert repeated.json()["id"] == response.json()["id"]
        with factory() as verification:
            assert verification.scalar(
                select(func.count(CommunicationMessage.id)).where(
                    CommunicationMessage.conversation_id == conversation.id
                )
            ) == 1
    finally:
        app.dependency_overrides.clear()
