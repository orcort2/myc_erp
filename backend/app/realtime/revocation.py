"""Revalidación de conexiones WebSocket tras cambios de autoridad."""

from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

from app.core.db import SessionLocal
from app.realtime.authentication import (
    RealtimeAuthenticationError,
    authenticate_websocket,
)

logger = logging.getLogger(__name__)


def connection_is_authorized(websocket: WebSocket, identity=None) -> bool:
    """Revalida token y, cuando existe, identidad original."""

    if identity is None:
        return False

    try:
        with SessionLocal() as db:
            current = authenticate_websocket(db, websocket)

        if identity.user_id != current.user_id:
            return False

        if identity.actor_type != current.actor_type:
            return False

        if identity.client_id != current.client_id:
            return False

        if identity.membership_id != current.membership_id:
            return False

        return True

    except RealtimeAuthenticationError:
        return False


async def revoke_invalid_connections(hub) -> int:
    """Cierra conexiones revocadas y renueva identidades vigentes.

    4401: token o cuenta revocados; el cliente no reconecta.
    1012: autoridad potencialmente modificada; el cliente reconecta.
    """
    connections = await hub.active_connections()
    closed = 0

    for connection in connections:
        try:
            authorized = await asyncio.to_thread(
                connection_is_authorized,
                connection.websocket,
                getattr(connection, "identity", None),
            )
        except Exception:
            logger.exception(
                "Realtime authority verification failed user_id=%s",
                connection.user_id,
            )
            continue

        code = 1012 if authorized else 4401
        reason = (
            "authority_refresh"
            if authorized
            else "session_revoked"
        )

        # Retirar del hub antes de cerrar impide nuevas entregas.
        await hub.disconnect(connection)

        try:
            async with connection.send_lock:
                await connection.websocket.close(
                    code=code,
                    reason=reason,
                )
        except (RuntimeError, OSError):
            logger.debug(
                "Realtime socket already closed user_id=%s",
                connection.user_id,
            )

        closed += 1

    return closed
