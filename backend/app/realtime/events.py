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
