"""DEV-1A: Broker-side anti-replay state.

Anti-replay belongs to the Broker (the party that must refuse a replayed
frame), never to FastAPI. ``InMemoryReplayGuard`` is enough for a single
Broker instance: entries expire after the acceptance window and the store is
hard-bounded. A Broker restart empties it; the residual risk is bounded by
the timestamp window (a captured frame older than ``max_age`` is rejected
regardless). No Redis or other external infrastructure in DEV-1A.

Full store = fail closed (``unavailable``): an unexpired entry is never
evicted to make room, because that would silently re-open replay.
"""

import threading
from collections import OrderedDict
from typing import Protocol

from app.developer_broker.protocol import (
    ERROR_UNAUTHENTICATED,
    ERROR_UNAVAILABLE,
    BrokerProtocolError,
)


class ReplayGuard(Protocol):
    def remember(self, *, nonce: str, request_id: str, now_ms: int) -> None:
        """Atomically records both values or raises ``BrokerProtocolError``
        if either was already seen inside the retention window."""


class InMemoryReplayGuard:
    def __init__(self, *, retention_ms: int, max_entries: int = 10_000) -> None:
        if retention_ms <= 0 or max_entries <= 0:
            raise ValueError("retention_ms and max_entries must be positive")
        self._retention_ms = retention_ms
        self._max_entries = max_entries
        self._expiry: OrderedDict[tuple[str, str], int] = OrderedDict()
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._expiry)

    def _purge(self, now_ms: int) -> None:
        # Insertion order ~ expiry order (monotonic-ish clock); a full sweep
        # covers any out-of-order entry when the store looks full.
        while self._expiry:
            key, expires = next(iter(self._expiry.items()))
            if expires > now_ms:
                break
            self._expiry.popitem(last=False)
        if len(self._expiry) + 2 > self._max_entries:
            for key in [key for key, expires in self._expiry.items() if expires <= now_ms]:
                del self._expiry[key]

    def remember(self, *, nonce: str, request_id: str, now_ms: int) -> None:
        keys = (("nonce", nonce), ("request_id", request_id))
        with self._lock:
            self._purge(now_ms)
            if keys[0] in self._expiry:
                raise BrokerProtocolError(ERROR_UNAUTHENTICATED, "nonce_replay")
            if keys[1] in self._expiry:
                raise BrokerProtocolError(ERROR_UNAUTHENTICATED, "request_id_replay")
            if len(self._expiry) + len(keys) > self._max_entries:
                raise BrokerProtocolError(ERROR_UNAVAILABLE, "replay_store_full")
            expires = now_ms + self._retention_ms
            for key in keys:
                self._expiry[key] = expires
