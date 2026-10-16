"""Renovación de sesiones realtime del Portal del Cliente."""

from __future__ import annotations

import asyncio
import logging

from app.realtime.revocation import connection_is_authorized


logger = logging.getLogger(__name__)


async def refresh_portal_connections(hub) -> int:
    """Revalida exclusivamente conexiones de clientes."""

    connections = await hub.active_connections()
    closed = 0

    for connection in connections:
        identity = connection.identity

        if identity is None or identity.actor_type != "client":
            continue

        try:
            authorized = await asyncio.to_thread(
                connection_is_authorized,
                connection.websocket,
                identity,
            )
        except Exception:
            logger.exception(
                "Portal realtime authority verification failed "
                "user_id=%s",
                connection.user_id,
            )
            continue

        code = 1012 if authorized else 4401
        reason = (
            "authority_refresh"
            if authorized
            else "session_revoked"
        )

        await hub.disconnect(connection)

        try:
            async with connection.send_lock:
                await connection.websocket.close(
                    code=code,
                    reason=reason,
                )
        except (RuntimeError, OSError):
            logger.debug(
                "Portal realtime socket already closed "
                "user_id=%s",
                connection.user_id,
            )

        closed += 1

    return closed
