import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.realtime.hub import InMemoryRealtimeHub, conversation_room
from app.routers.realtime import _handle_command


def test_unsubscribe_after_revocation_does_not_query_database():
    async def scenario():
        hub = InMemoryRealtimeHub()
        websocket = AsyncMock()
        connection = await hub.connect(websocket, 42)

        room = conversation_room(7)
        await hub.join(connection, room)

        session_factory = Mock(
            side_effect=AssertionError(
                "Unsubscribe no debe consultar PostgreSQL"
            )
        )

        with patch(
            "app.routers.realtime.realtime_hub",
            hub,
        ):
            await _handle_command(
                session_factory=session_factory,
                connection=connection,
                command={
                    "event": "conversation.unsubscribe",
                    "data": {"conversation_id": 7},
                },
                identity=SimpleNamespace(user_id=42),
            )

        assert room not in connection.rooms
        assert await hub.connection_count() == 1

        session_factory.assert_not_called()
        websocket.send_json.assert_awaited_once()

        envelope = websocket.send_json.await_args.args[0]

        assert envelope["event"] == "conversation.unsubscribed"
        assert envelope["data"]["conversation_id"] == 7

    asyncio.run(scenario())
