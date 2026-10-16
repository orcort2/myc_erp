import asyncio
from unittest.mock import AsyncMock, patch

from app.realtime.conversation_revocation import (
    revoke_invalid_conversation_rooms,
)
from app.realtime.hub import InMemoryRealtimeHub, conversation_room


def test_revoked_participant_leaves_only_conversation_room():
    async def scenario():
        hub = InMemoryRealtimeHub()

        authorized = await hub.connect(AsyncMock(), 10)
        revoked = await hub.connect(AsyncMock(), 20)

        room = conversation_room(7)

        await hub.join(authorized, room)
        await hub.join(revoked, room)

        def eligible(connection, conversation_id):
            assert conversation_id == 7
            return connection.user_id == 10

        with patch(
            "app.realtime.conversation_revocation."
            "can_deliver_conversation",
            side_effect=eligible,
        ):
            removed = await revoke_invalid_conversation_rooms(hub)

        assert removed == 1
        assert room in authorized.rooms
        assert room not in revoked.rooms
        assert await hub.connection_count() == 2
        assert "user:20" in revoked.rooms

    asyncio.run(scenario())


def test_database_failure_preserves_subscriptions():
    async def scenario():
        hub = InMemoryRealtimeHub()
        connection = await hub.connect(AsyncMock(), 30)

        room = conversation_room(7)
        await hub.join(connection, room)

        with patch(
            "app.realtime.conversation_revocation."
            "can_deliver_conversation",
            side_effect=RuntimeError("Database unavailable"),
        ):
            removed = await revoke_invalid_conversation_rooms(hub)

        assert removed == 0
        assert room in connection.rooms
        assert await hub.connection_count() == 1

    asyncio.run(scenario())


def test_no_conversation_subscriptions_requires_no_database():
    async def scenario():
        hub = InMemoryRealtimeHub()
        await hub.connect(AsyncMock(), 40)

        with patch(
            "app.realtime.conversation_revocation."
            "can_deliver_conversation",
        ) as eligible:
            removed = await revoke_invalid_conversation_rooms(hub)

        assert removed == 0
        eligible.assert_not_called()

    asyncio.run(scenario())
