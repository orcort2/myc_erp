from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.communication import (
    CommunicationConversation,
    communication_participants,
)
from app.models.user import User
from app.realtime.authentication import (
    REALTIME_PROTOCOL,
    RealtimeAuthenticationError,
    authenticate_websocket,
)
from app.realtime.contracts import build_realtime_envelope
from app.realtime.hub import conversation_room
from app.realtime.runtime import realtime_hub


router = APIRouter(tags=["realtime"])
logger = logging.getLogger("app.realtime")
SessionFactory = Callable[[], Session]


def get_realtime_session_factory() -> SessionFactory:
    """Punto de inyección sin mantener una transacción durante todo el socket."""

    return SessionLocal


def _can_access_conversation(
    db: Session, *, conversation_id: int, identity
) -> bool:
    participant = exists().where(
        communication_participants.c.conversation_id == CommunicationConversation.id,
        communication_participants.c.user_id == identity.user_id,
    )
    query = select(CommunicationConversation.id).where(
        CommunicationConversation.id == conversation_id,
        CommunicationConversation.archived_at.is_(None),
        or_(
            participant,
            CommunicationConversation.created_by_user_id == identity.user_id,
        ),
    )
    if identity.actor_type == "client":
        if not {
            "communications.view",
            "communications.create",
        }.intersection(identity.permissions):
            return False
        query = query.where(
            CommunicationConversation.conversation_type == "client",
            CommunicationConversation.client_id == identity.client_id,
        )
    return bool(db.scalar(query))


async def _close_rejected(websocket: WebSocket, *, code: int) -> None:
    try:
        await websocket.close(code=code)
    except RuntimeError:
        pass


async def _handle_command(
    *,
    session_factory: SessionFactory,
    connection: Any,
    command: dict[str, Any],
    identity,
) -> None:
    event = command.get("event")
    data = command.get("data") if isinstance(command.get("data"), dict) else {}
    if event == "connection.ping":
        await realtime_hub.send(
            connection, build_realtime_envelope("connection.pong")
        )
        return
    conversation_events = {
        "conversation.subscribe",
        "conversation.unsubscribe",
        "typing.started",
        "typing.stopped",
    }
    if event not in conversation_events:
        await realtime_hub.send(
            connection,
            build_realtime_envelope(
                "realtime.error", {"code": "unsupported_command"}
            ),
        )
        return
    try:
        conversation_id = int(data.get("conversation_id"))
    except (TypeError, ValueError):
        conversation_id = 0
    with session_factory() as db:
        allowed = conversation_id > 0 and _can_access_conversation(
            db, conversation_id=conversation_id, identity=identity
        )
        actor_name = db.scalar(
            select(User.full_name).where(User.id == connection.user_id)
        )
    if not allowed:
        logger.warning(
            "Realtime conversation authorization denied user_id=%s conversation_id=%s",
            connection.user_id,
            conversation_id or "invalid",
        )
        await realtime_hub.send(
            connection,
            build_realtime_envelope(
                "realtime.error", {"code": "conversation_forbidden"}
            ),
        )
        return
    room = conversation_room(conversation_id)
    if event == "conversation.unsubscribe":
        await realtime_hub.leave(connection, room)
        await realtime_hub.send(
            connection,
            build_realtime_envelope(
                "conversation.unsubscribed", {"conversation_id": conversation_id}
            ),
        )
        return
    if event in {"typing.started", "typing.stopped"}:
        if room not in connection.rooms:
            await realtime_hub.send(
                connection,
                build_realtime_envelope(
                    "realtime.error", {"code": "conversation_not_subscribed"}
                ),
            )
            return
        await realtime_hub.publish(
            room,
            build_realtime_envelope(
                event,
                {
                    "conversation_id": conversation_id,
                    "user_id": connection.user_id,
                    "full_name": actor_name,
                },
            ),
        )
        return
    await realtime_hub.join(connection, room)
    await realtime_hub.send(
        connection,
        build_realtime_envelope(
            "conversation.subscribed", {"conversation_id": conversation_id}
        ),
    )


@router.websocket("/api/realtime/ws")
async def realtime_websocket(
    websocket: WebSocket,
    session_factory: SessionFactory = Depends(get_realtime_session_factory),
) -> None:
    try:
        with session_factory() as db:
            identity = authenticate_websocket(db, websocket)
            identity_user_id = identity.user_id
    except RealtimeAuthenticationError as exc:
        logger.warning("Realtime connection rejected reason=%s", str(exc))
        await _close_rejected(websocket, code=4401)
        return

    await websocket.accept(subprotocol=REALTIME_PROTOCOL)
    connection = await realtime_hub.connect(websocket, identity_user_id)
    logger.info(
        "Realtime connection accepted user_id=%s connection_id=%s",
        identity_user_id,
        connection.id,
    )
    await realtime_hub.send(
        connection,
        build_realtime_envelope(
            "realtime.connected",
            {
                "user_id": identity_user_id,
                "connection_id": connection.id,
                "actor_type": identity.actor_type,
                "client_id": identity.client_id,
            },
        ),
    )
    try:
        while True:
            remaining = (
                identity.expires_at - datetime.now(timezone.utc)
            ).total_seconds()
            if remaining <= 0:
                await websocket.close(code=4401, reason="access_token_expired")
                break
            try:
                command = await asyncio.wait_for(
                    websocket.receive_json(), timeout=remaining
                )
            except TimeoutError:
                await websocket.close(code=4401, reason="access_token_expired")
                break
            if not isinstance(command, dict):
                await realtime_hub.send(
                    connection,
                    build_realtime_envelope(
                        "realtime.error", {"code": "invalid_command"}
                    ),
                )
                continue
            await _handle_command(
                session_factory=session_factory,
                connection=connection,
                command=command,
                identity=identity,
            )
    except WebSocketDisconnect as exc:
        logger.info(
            "Realtime disconnected user_id=%s connection_id=%s code=%s",
            identity_user_id,
            connection.id,
            exc.code,
        )
    except Exception:
        logger.exception(
            "Realtime connection error user_id=%s connection_id=%s",
            identity_user_id,
            connection.id,
        )
    finally:
        await realtime_hub.disconnect(connection)
