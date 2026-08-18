from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict
from uuid import uuid4


REALTIME_CONTRACT_VERSION = 1


class RealtimeEnvelope(TypedDict):
    version: int
    event: str
    event_id: str
    occurred_at: str
    data: dict[str, Any]


def build_realtime_envelope(
    event: str,
    data: dict[str, Any] | None = None,
    *,
    event_id: str | None = None,
    occurred_at: datetime | None = None,
) -> RealtimeEnvelope:
    """Construye el único envelope público de realtime versión 1."""

    timestamp = occurred_at or datetime.now(timezone.utc)
    return {
        "version": REALTIME_CONTRACT_VERSION,
        "event": event,
        "event_id": event_id or str(uuid4()),
        "occurred_at": timestamp.isoformat(),
        "data": data or {},
    }
