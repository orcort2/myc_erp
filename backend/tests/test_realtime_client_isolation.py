import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.realtime.authentication import RealtimeIdentity
from app.realtime.hub import InMemoryRealtimeHub


def _identity(user_id, client_id, membership_id):
    return RealtimeIdentity(
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        actor_type="client",
        client_id=client_id,
        membership_id=membership_id,
        permissions=frozenset({"communications.view"}),
    )


def test_foreign_client_connection_cannot_receive_conversation_event():
    async def scenario():
        hub = InMemoryRealtimeHub()

        socket = MagicMock()
        socket.headers = {
            "sec-websocket-protocol": "myc.realtime.v1, auth.test-token"
        }
        socket.send_json = AsyncMock()
        socket.close = AsyncMock()

        connection = await hub.connect(socket, 25)

        connection.identity = _identity(
            user_id=25,
            client_id=999,
            membership_id=80,
        )

        envelope = {
            "version": 1,
            "event": "message.created",
            "event_id": "test-client-isolation",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "data": {
                "conversation_id": 7,
                "body": "Mensaje confidencial",
            },
        }

        with patch(
            "app.realtime.events.eligible_communication_recipients",
            return_value={25},
        ):
            delivered = await hub.publish_to_user(25, envelope)

        assert delivered == 0
        socket.send_json.assert_not_awaited()

    asyncio.run(scenario())
