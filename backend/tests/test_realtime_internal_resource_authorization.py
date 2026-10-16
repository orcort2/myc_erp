"""Pruebas de seguridad para eventos internos realtime."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.realtime.authentication import (
    RealtimeAuthenticationError,
    RealtimeIdentity,
)
from app.realtime.delivery_authorization import (
    can_deliver_internal_resource,
)
from app.realtime.hub import InMemoryRealtimeHub


def make_identity(user_id=10, actor_type="internal", expired=False):
    delta = timedelta(hours=-1 if expired else 1)
    return RealtimeIdentity(
        user_id=user_id,
        actor_type=actor_type,
        expires_at=datetime.now(timezone.utc) + delta,
    )


def make_connection(identity=None, user_id=10):
    return SimpleNamespace(
        user_id=user_id,
        identity=identity,
        websocket=AsyncMock(),
    )


def test_missing_identity_is_rejected():
    connection = make_connection()

    assert not can_deliver_internal_resource(
        connection, "users"
    )


def test_client_identity_is_rejected():
    connection = make_connection(
        make_identity(actor_type="client")
    )

    assert not can_deliver_internal_resource(
        connection, "users"
    )


def test_mismatched_identity_is_rejected():
    connection = make_connection(
        make_identity(user_id=20),
        user_id=10,
    )

    assert not can_deliver_internal_resource(
        connection, "users"
    )


def test_expired_identity_is_rejected():
    connection = make_connection(
        make_identity(expired=True)
    )

    assert not can_deliver_internal_resource(
        connection, "users"
    )


def test_unknown_resource_is_rejected():
    connection = make_connection(make_identity())

    assert not can_deliver_internal_resource(
        connection, "secrets"
    )


def test_revoked_token_is_rejected():
    connection = make_connection(make_identity())

    with patch(
        "app.realtime.delivery_authorization.SessionLocal"
    ) as session_factory, patch(
        "app.realtime.delivery_authorization.authenticate_websocket",
        side_effect=RealtimeAuthenticationError(
            "session_revoked"
        ),
    ):
        session_factory.return_value.__enter__.return_value = object()

        assert not can_deliver_internal_resource(
            connection, "users"
        )


def test_insufficient_permission_is_rejected():
    connection = make_connection(make_identity())

    with patch(
        "app.realtime.delivery_authorization.SessionLocal"
    ) as session_factory, patch(
        "app.realtime.delivery_authorization.authenticate_websocket",
        return_value=connection.identity,
    ), patch(
        "app.services.auth.user_has_permission",
        return_value=False,
    ):
        db = session_factory.return_value.__enter__.return_value
        db.scalar.return_value = SimpleNamespace(id=10)

        assert not can_deliver_internal_resource(
            connection, "users"
        )


def test_authorized_internal_connection_is_accepted():
    connection = make_connection(make_identity())

    with patch(
        "app.realtime.delivery_authorization.SessionLocal"
    ) as session_factory, patch(
        "app.realtime.delivery_authorization.authenticate_websocket",
        return_value=connection.identity,
    ), patch(
        "app.services.auth.user_has_permission",
        return_value=True,
    ):
        db = session_factory.return_value.__enter__.return_value
        db.scalar.return_value = SimpleNamespace(id=10)

        assert can_deliver_internal_resource(
            connection, "users"
        )


def test_hub_does_not_deliver_internal_event_to_client():
    async def scenario():
        hub = InMemoryRealtimeHub()
        websocket = AsyncMock()

        connection = await hub.connect(
            websocket,
            10,
            identity=make_identity(actor_type="client"),
        )

        delivered = await hub.publish(
            "user:10",
            {
                "event": "resource.changed",
                "data": {"resources": ["users"]},
            },
        )

        assert delivered == 0
        websocket.send_json.assert_not_awaited()
        assert connection.identity.actor_type == "client"

    asyncio.run(scenario())


def test_hub_delivers_internal_event_when_authorized():
    async def scenario():
        hub = InMemoryRealtimeHub()
        websocket = AsyncMock()

        await hub.connect(
            websocket,
            10,
            identity=make_identity(),
        )

        with patch(
            "app.realtime.delivery_authorization."
            "can_deliver_internal_resource",
            return_value=True,
        ):
            delivered = await hub.publish(
                "user:10",
                {
                    "event": "resource.changed",
                    "data": {"resources": ["users"]},
                },
            )

        assert delivered == 1
        websocket.send_json.assert_awaited_once()

    asyncio.run(scenario())
