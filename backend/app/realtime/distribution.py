"""Distribución de invalidaciones hacia sesiones WebSocket autorizadas."""

from __future__ import annotations

from app.realtime.contracts import build_realtime_envelope
from app.realtime.hub import RealtimeHub
from app.realtime.invalidation import ResourceInvalidation


async def distribute_invalidation(
    hub: RealtimeHub,
    invalidation: ResourceInvalidation,
) -> int:
    """Entrega avisos mínimos a los usuarios destinatarios."""

    envelope = build_realtime_envelope(
        "resource.changed",
        {
            "resources": list(invalidation.resources),
        },
        event_id=invalidation.event_id,
    )

    delivered = 0

    for user_id in sorted(set(invalidation.user_ids)):
        delivered += await hub.publish_to_user(
            user_id,
            envelope,
        )

    return delivered
