import asyncio
from unittest.mock import AsyncMock, patch

from app.realtime.hub import InMemoryRealtimeHub
from app.realtime.authentication import RealtimeIdentity
from datetime import datetime, timedelta, timezone


def authenticated_identity(user_id):
    return RealtimeIdentity(
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        actor_type="internal",
    )



def test_authorized_participant_receives_event():
    async def scenario():
        hub = InMemoryRealtimeHub()
        socket = AsyncMock()

        connection = await hub.connect(socket, 10)
        connection.identity = authenticated_identity(10)
        await hub.join(connection, "conversation:7")

        with patch(
            "app.realtime.delivery_authorization.can_deliver_conversation",
            return_value=True,
        ):
            delivered = await hub.publish(
                "conversation:7",
                {"event": "typing.started", "data": {"conversation_id": 7}},
            )

        assert delivered == 1
        socket.send_json.assert_awaited_once()
        assert "conversation:7" in connection.rooms

    asyncio.run(scenario())


def test_revoked_participant_is_removed_from_room():
    async def scenario():
        hub = InMemoryRealtimeHub()
        socket = AsyncMock()

        connection = await hub.connect(socket, 20)
        connection.identity = authenticated_identity(20)
        await hub.join(connection, "conversation:7")

        with patch(
            "app.realtime.delivery_authorization.can_deliver_conversation",
            return_value=False,
        ):
            delivered = await hub.publish(
                "conversation:7",
                {"event": "typing.started", "data": {"conversation_id": 7}},
            )

        assert delivered == 0
        socket.send_json.assert_not_awaited()
        assert "conversation:7" not in connection.rooms
        assert await hub.connection_count() == 1

    asyncio.run(scenario())


def test_database_failure_does_not_deliver_event():
    async def scenario():
        hub = InMemoryRealtimeHub()
        socket = AsyncMock()

        connection = await hub.connect(socket, 30)
        connection.identity = authenticated_identity(30)
        await hub.join(connection, "conversation:7")

        with patch(
            "app.realtime.delivery_authorization.can_deliver_conversation",
            side_effect=RuntimeError("Database unavailable"),
        ):
            delivered = await hub.publish(
                "conversation:7",
                {"event": "typing.started", "data": {"conversation_id": 7}},
            )

        assert delivered == 0
        socket.send_json.assert_not_awaited()

        # Un fallo de BD no debe interpretarse como revocacion.
        assert await hub.connection_count() == 1
        assert "conversation:7" in connection.rooms

    asyncio.run(scenario())
