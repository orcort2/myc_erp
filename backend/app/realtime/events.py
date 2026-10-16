from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.realtime.contracts import build_realtime_envelope
from app.realtime.runtime import realtime_hub


async def publish_to_users(
    user_ids: Iterable[int], event: str, data: dict[str, Any]
) -> None:
    envelope = build_realtime_envelope(event, data)
    for user_id in sorted(set(user_ids)):
        await realtime_hub.publish_to_user(user_id, envelope)


def eligible_communication_recipients(
    conversation_id: int,
    proposed_user_ids: set[int],
) -> set[int]:
    """Revalida destinatarios contra el estado actual de la conversación."""
    from sqlalchemy import exists, or_, select

    from app.core.db import SessionLocal
    from app.models.communication import (
        CommunicationConversation,
        communication_participants,
    )
    from app.models.user import User

    if not proposed_user_ids:
        return set()

    participant = exists().where(
        communication_participants.c.conversation_id
        == CommunicationConversation.id,
        communication_participants.c.user_id == User.id,
    )

    with SessionLocal() as db:
        rows = db.scalars(
            select(User.id)
            .select_from(User)
            .join(
                CommunicationConversation,
                or_(
                    CommunicationConversation.created_by_user_id == User.id,
                    exists().where(
                        communication_participants.c.conversation_id
                        == CommunicationConversation.id,
                        communication_participants.c.user_id == User.id,
                    ),
                ),
            )
            .where(
                CommunicationConversation.id == conversation_id,
                User.id.in_(proposed_user_ids),
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                User.status == "active",
                CommunicationConversation.archived_at.is_(None),
                or_(
                    participant,
                    CommunicationConversation.created_by_user_id == User.id,
                ),
            )
        ).all()

    return set(rows)


async def publish_communication_to_users(
    user_ids: Iterable[int],
    event: str,
    data: dict[str, Any],
    *,
    conversation_id: int,
) -> None:
    """Revalida acceso antes de distribuir eventos de una conversación."""
    import asyncio

    recipients = await asyncio.to_thread(
        eligible_communication_recipients,
        conversation_id,
        set(user_ids),
    )

    if not recipients:
        return

    scoped_data = {
        **data,
        "conversation_id": conversation_id,
    }
    await publish_to_users(recipients, event, scoped_data)
