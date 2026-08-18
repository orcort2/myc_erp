from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

import app.models  # noqa: F401
from app.core.db import Base
from app.core.security import create_access_token
from app.main import app
from app.models.communication import CommunicationConversation
from app.models.user import Role, User
from app.realtime.authentication import REALTIME_PROTOCOL
from app.realtime.contracts import build_realtime_envelope
from app.realtime.hub import InMemoryRealtimeHub
from app.routers.realtime import get_realtime_session_factory, realtime_hub


@pytest.fixture()
def realtime_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        role = Role(name="Tecnico", description="Técnico")
        db.add(role)
        db.flush()
        users = {}
        for key, active in (
            ("a", True),
            ("b", True),
            ("attacker", True),
            ("inactive", False),
        ):
            user = User(
                username=f"realtime-{key}",
                email=f"realtime-{key}@example.test",
                full_name=f"Realtime {key.upper()}",
                hashed_password="unused",
                account_type="internal",
                status="active" if active else "disabled",
                is_active=active,
                role_id=role.id,
                roles=[role],
            )
            db.add(user)
            users[key] = user
        db.flush()
        conversation = CommunicationConversation(
            conversation_type="internal",
            created_by_user_id=users["a"].id,
            participants=[users["a"], users["b"]],
        )
        db.add(conversation)
        db.commit()
        conversation_id = conversation.id

    app.dependency_overrides[get_realtime_session_factory] = lambda: factory
    client = TestClient(app)
    tokens = {
        key: create_access_token(
            str(user.id),
            extra_claims={"roles": ["Administrador"], "auth_context": "internal"},
        )
        for key, user in users.items()
    }
    try:
        yield client, users, tokens, conversation_id
    finally:
        app.dependency_overrides.clear()


def protocols(token: str) -> list[str]:
    return [REALTIME_PROTOCOL, f"auth.{token}"]


def test_authenticated_connection_uses_server_identity(realtime_context):
    client, users, tokens, _conversation_id = realtime_context
    path = f"/api/realtime/ws?user_id={users['b'].id}"
    with client.websocket_connect(path, subprotocols=protocols(tokens["a"])) as websocket:
        envelope = websocket.receive_json()
        assert websocket.accepted_subprotocol == REALTIME_PROTOCOL
        assert envelope["version"] == 1
        assert envelope["event"] == "realtime.connected"
        assert envelope["data"]["user_id"] == users["a"].id
        assert envelope["data"]["user_id"] != users["b"].id
    assert asyncio.run(realtime_hub.connection_count()) == 0


@pytest.mark.parametrize("credential", [None, "invalid.jwt.value"])
def test_realtime_rejects_missing_or_invalid_token(realtime_context, credential):
    client, _users, _tokens, _conversation_id = realtime_context
    offered = [REALTIME_PROTOCOL]
    if credential:
        offered.append(f"auth.{credential}")
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/realtime/ws", subprotocols=offered):
            pass
    assert exc_info.value.code == 4401


def test_realtime_rejects_inactive_and_unknown_users(realtime_context):
    client, _users, tokens, _conversation_id = realtime_context
    unknown = create_access_token(
        "999999",
        extra_claims={"roles": ["Administrador"], "auth_context": "internal"},
    )
    for token in (tokens["inactive"], unknown):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                "/api/realtime/ws", subprotocols=protocols(token)
            ):
                pass
        assert exc_info.value.code == 4401


def test_conversation_subscription_enforces_participant_ownership(realtime_context):
    client, _users, tokens, conversation_id = realtime_context
    with client.websocket_connect(
        "/api/realtime/ws", subprotocols=protocols(tokens["a"])
    ) as authorized:
        authorized.receive_json()
        authorized.send_json(
            {
                "event": "conversation.subscribe",
                "data": {"conversation_id": conversation_id},
            }
        )
        accepted = authorized.receive_json()
        assert accepted["event"] == "conversation.subscribed"
        assert accepted["data"] == {"conversation_id": conversation_id}

    with client.websocket_connect(
        "/api/realtime/ws", subprotocols=protocols(tokens["attacker"])
    ) as attacker:
        attacker.receive_json()
        attacker.send_json(
            {
                "event": "conversation.subscribe",
                "data": {
                    "conversation_id": conversation_id,
                    "user_id": 1,
                },
            }
        )
        denied = attacker.receive_json()
        assert denied["event"] == "realtime.error"
        assert denied["data"]["code"] == "conversation_forbidden"


def test_typing_is_ephemeral_and_requires_an_authorized_subscription(realtime_context):
    client, users, tokens, conversation_id = realtime_context
    with client.websocket_connect(
        "/api/realtime/ws", subprotocols=protocols(tokens["a"])
    ) as websocket:
        websocket.receive_json()
        websocket.send_json(
            {
                "event": "typing.started",
                "data": {"conversation_id": conversation_id},
            }
        )
        denied = websocket.receive_json()
        assert denied["event"] == "realtime.error"
        assert denied["data"]["code"] == "conversation_not_subscribed"
        websocket.send_json(
            {
                "event": "conversation.subscribe",
                "data": {"conversation_id": conversation_id},
            }
        )
        websocket.receive_json()
        websocket.send_json(
            {
                "event": "typing.started",
                "data": {"conversation_id": conversation_id},
            }
        )
        typing = websocket.receive_json()
        assert typing["event"] == "typing.started"
        assert typing["data"] == {
            "conversation_id": conversation_id,
            "user_id": users["a"].id,
            "full_name": users["a"].full_name,
        }


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


def test_hub_isolates_user_rooms_and_cleans_up_connections():
    async def scenario():
        hub = InMemoryRealtimeHub()
        socket_a = FakeWebSocket()
        socket_b = FakeWebSocket()
        connection_a = await hub.connect(socket_a, 11)  # type: ignore[arg-type]
        connection_b = await hub.connect(socket_b, 22)  # type: ignore[arg-type]
        envelope = build_realtime_envelope(
            "realtime.test", {"target": "a"}
        )
        delivered = await hub.publish_to_user(11, envelope)
        assert delivered == 1
        assert socket_a.sent == [envelope]
        assert socket_b.sent == []
        await hub.disconnect(connection_a)
        await hub.disconnect(connection_b)
        assert await hub.connection_count() == 0

    asyncio.run(scenario())


def test_realtime_envelope_has_server_generated_contract_fields():
    occurred_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    envelope = build_realtime_envelope(
        "realtime.test", {"ok": True}, occurred_at=occurred_at
    )
    assert envelope["version"] == 1
    assert envelope["event"] == "realtime.test"
    assert envelope["event_id"]
    assert datetime.fromisoformat(envelope["occurred_at"]) == occurred_at
    assert envelope["data"] == {"ok": True}
