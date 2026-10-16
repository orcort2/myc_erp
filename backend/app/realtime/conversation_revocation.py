"""Revocacion proactiva de suscripciones a conversaciones."""

from __future__ import annotations

import asyncio
import logging

from app.realtime.delivery_authorization import can_deliver_conversation

logger = logging.getLogger(__name__)


async def revoke_invalid_conversation_rooms(hub) -> int:
    connections = await hub.active_connections()

    subscriptions = [
        (connection, room)
        for connection in connections
        for room in tuple(connection.rooms)
        if room.startswith("conversation:")
    ]

    removed = 0

    for connection, room in subscriptions:
        try:
            conversation_id = int(room.split(":", 1)[1])

            authorized = await asyncio.to_thread(
                can_deliver_conversation,
                connection,
                conversation_id,
            )
        except Exception:
            logger.exception(
                "Conversation revocation verification failed "
                "user_id=%s room=%s",
                connection.user_id,
                room,
            )
            continue

        if not authorized:
            await hub.leave(connection, room)
            removed += 1

    return removed
