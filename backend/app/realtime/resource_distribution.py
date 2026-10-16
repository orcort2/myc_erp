"""Distribución autorizada de cambios de recursos PostgreSQL."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.db import SessionLocal
from app.models.user import User
from app.realtime.contracts import build_realtime_envelope
from app.realtime.resource_changes import (
    RESOURCE_READ_PERMISSIONS,
    ResourceChange,
)
from app.services.auth import user_has_permission


def eligible_user_ids(resource: str, connected_user_ids: tuple[int, ...]) -> list[int]:
    permission = RESOURCE_READ_PERMISSIONS.get(resource)

    if permission is None or not connected_user_ids:
        return []

    with SessionLocal() as db:
        users = db.scalars(
            select(User)
            .where(
                User.is_active.is_(True),
                User.status == "active",
                User.account_type == "internal",
                User.id.in_(connected_user_ids),
            )
            .options(selectinload(User.roles))
        ).all()

        return [
            user.id
            for user in users
            if user_has_permission(user, permission)
        ]


async def distribute_resource_change(hub, change: ResourceChange) -> int:
    """Notifica solamente a usuarios internos activos y autorizados."""

    connections = await hub.active_connections()
    connected_user_ids = tuple(sorted({
        connection.user_id for connection in connections
    }))

    if not connected_user_ids:
        return 0

    recipients = await asyncio.to_thread(
        eligible_user_ids,
        change.resource,
        connected_user_ids,
    )

    if not recipients:
        return 0

    envelope = build_realtime_envelope(
        "resource.changed",
        {"resources": [change.resource]},
        event_id=str(uuid4()),
    )

    delivered = 0

    for user_id in recipients:
        delivered += await hub.publish_to_user(user_id, envelope)

    return delivered
