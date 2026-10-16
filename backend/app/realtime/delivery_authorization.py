"""Autorización vigente de entregas WebSocket por conexión."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.db import SessionLocal
from app.realtime.authentication import (
    RealtimeAuthenticationError,
    authenticate_websocket,
)


def can_deliver_conversation(connection, conversation_id: int) -> bool:
    """Revalida token, identidad y acceso a una conversación."""

    if conversation_id <= 0:
        return False

    identity = connection.identity

    if identity is None:
        return False

    if identity.user_id != connection.user_id:
        return False

    if identity.expires_at <= datetime.now(timezone.utc):
        return False

    try:
        with SessionLocal() as db:
            current = authenticate_websocket(db, connection.websocket)

            if current.user_id != identity.user_id:
                return False

            if current.actor_type != identity.actor_type:
                return False

            if current.client_id != identity.client_id:
                return False

            if current.membership_id != identity.membership_id:
                return False

            from app.routers.realtime import _can_access_conversation

            return _can_access_conversation(
                db,
                conversation_id=conversation_id,
                identity=current,
            )

    except RealtimeAuthenticationError:
        return False



def can_deliver_internal_resource(connection, resource: str) -> bool:
    """Revalida identidad interna y permiso vigente antes de entregar."""

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.user import User
    from app.realtime.resource_changes import RESOURCE_READ_PERMISSIONS
    from app.services.auth import user_has_permission

    permission = RESOURCE_READ_PERMISSIONS.get(resource)
    identity = connection.identity

    if permission is None or identity is None:
        return False

    if identity.actor_type != "internal":
        return False

    if identity.user_id != connection.user_id:
        return False

    if identity.expires_at <= datetime.now(timezone.utc):
        return False

    try:
        with SessionLocal() as db:
            current = authenticate_websocket(
                db,
                connection.websocket,
            )

            if (
                current.user_id != identity.user_id
                or current.actor_type != "internal"
                or current.client_id != identity.client_id
                or current.membership_id != identity.membership_id
            ):
                return False

            user = db.scalar(
                select(User)
                .where(
                    User.id == connection.user_id,
                    User.is_active.is_(True),
                    User.status == "active",
                    User.account_type == "internal",
                )
                .options(selectinload(User.roles))
            )

            return (
                user is not None
                and user_has_permission(user, permission)
            )

    except RealtimeAuthenticationError:
        return False
