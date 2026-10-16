"""Garantias de identidad durante el registro de conexiones realtime."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.realtime.authentication import RealtimeIdentity
from app.realtime.hub import InMemoryRealtimeHub


def identity(user_id: int) -> RealtimeIdentity:
    return RealtimeIdentity(
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        actor_type="internal",
    )


def test_connection_is_registered_with_identity():
    async def scenario():
        hub = InMemoryRealtimeHub()
        socket = AsyncMock()
        authenticated = identity(10)

        connection = await hub.connect(
            socket,
            10,
            identity=authenticated,
        )

        assert connection.identity is authenticated
        assert connection.user_id == 10
        assert "user:10" in connection.rooms
        assert await hub.active_connections() == (connection,)

    asyncio.run(scenario())


def test_mismatched_identity_is_rejected_before_registration():
    async def scenario():
        hub = InMemoryRealtimeHub()
        socket = AsyncMock()

        with pytest.raises(
            ValueError,
            match="La identidad no corresponde al usuario",
        ):
            await hub.connect(
                socket,
                10,
                identity=identity(20),
            )

        assert await hub.connection_count() == 0
        assert await hub.active_connections() == ()

    asyncio.run(scenario())


def test_connection_without_identity_cannot_receive_conversation_event():
    async def scenario():
        hub = InMemoryRealtimeHub()
        socket = AsyncMock()

        connection = await hub.connect(socket, 10)
        await hub.join(connection, "conversation:7")

        with patch(
            "app.realtime.delivery_authorization.can_deliver_conversation",
            wraps=None,
        ) as authorize:
            authorize.return_value = False

            delivered = await hub.publish(
                "conversation:7",
                {
                    "event": "typing.started",
                    "data": {"conversation_id": 7},
                },
            )

        assert delivered == 0
        socket.send_json.assert_not_awaited()
        assert "conversation:7" not in connection.rooms
        assert "user:10" in connection.rooms

    asyncio.run(scenario())
