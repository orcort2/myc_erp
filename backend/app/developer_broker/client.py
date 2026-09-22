"""DEV-1A: the FastAPI-side Broker client.

``BrokerClient`` is the only thing the Developer Control Plane talks to: it
builds versioned request DTOs, signs them, sends them through a
``BrokerTransport`` and authenticates the response (signature, request_id
binding, freshness) before trusting a single field. Routers never touch a
transport directly.

It is not an authority. Callers must already have authorized the user with
DEV-0 (``require_developer_session(<capability>)``) before using it.
"""

import re
import secrets
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.developer_broker.protocol import (
    DEFAULT_MAX_AGE_MS,
    DEFAULT_MAX_FUTURE_SKEW_MS,
    OP_BROKER_HEALTH,
    PROTOCOL,
    STATUS_ERROR,
    BrokerError,
    BrokerRejectedError,
    BrokerRequest,
    BrokerResponseError,
    BrokerSecret,
    BrokerUnavailableError,
    decode_frame,
    encode_frame,
    parse_response,
    verify_signature,
    wall_clock_ms,
)
from app.developer_broker.transport import BrokerTransport


@dataclass(frozen=True)
class BrokerHealth:
    status: str
    protocol: str
    protocol_version: int
    supported_versions: tuple[int, ...]
    instance_id: str
    timestamp_ms: int
    operations: tuple[str, ...]
    features: tuple[str, ...]


HEALTH_RESULT_FIELDS = frozenset(
    {"status", "protocol", "protocol_version", "supported_versions", "instance_id", "timestamp", "operations", "features"}
)
# The Broker's instance_id is ``uuid.uuid4().hex``.
_INSTANCE_ID = re.compile(r"[0-9a-f]{32}")


def _invalid_health() -> BrokerResponseError:
    return BrokerResponseError("invalid_health_result")


def _strict_int(value: Any) -> int:
    # bool is a subclass of int: never accepted as a number.
    if not isinstance(value, int) or isinstance(value, bool):
        raise _invalid_health()
    return value


def _str_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise _invalid_health()
    return tuple(value)


def _health_from_result(result: Mapping[str, Any]) -> BrokerHealth:
    """Exact contract of the ``broker.health`` result -- no missing or extra
    fields, no silent coercions."""
    if set(result) != HEALTH_RESULT_FIELDS:
        raise _invalid_health()
    versions = result["supported_versions"]
    if not isinstance(versions, list) or not versions:
        raise _invalid_health()
    timestamp = _strict_int(result["timestamp"])
    instance_id = result["instance_id"]
    if (
        result["status"] != "ok"
        or result["protocol"] != PROTOCOL
        or timestamp <= 0
        or not isinstance(instance_id, str)
        or not _INSTANCE_ID.fullmatch(instance_id)
    ):
        raise _invalid_health()
    return BrokerHealth(
        status=result["status"],
        protocol=result["protocol"],
        protocol_version=_strict_int(result["protocol_version"]),
        supported_versions=tuple(_strict_int(item) for item in versions),
        instance_id=instance_id,
        timestamp_ms=timestamp,
        operations=_str_list(result["operations"]),
        features=_str_list(result["features"]),
    )


class BrokerClient:
    def __init__(
        self,
        transport: BrokerTransport,
        secret: BrokerSecret,
        *,
        timeout_seconds: float = 5.0,
        clock: Callable[[], int] = wall_clock_ms,
        max_age_ms: int = DEFAULT_MAX_AGE_MS,
        max_future_skew_ms: int = DEFAULT_MAX_FUTURE_SKEW_MS,
    ) -> None:
        if not isinstance(secret, BrokerSecret):
            raise TypeError("secret must be a BrokerSecret")
        self._transport = transport
        self._secret = secret
        self._timeout_seconds = timeout_seconds
        self._clock = clock
        self._max_age_ms = max_age_ms
        self._max_future_skew_ms = max_future_skew_ms

    def _call(self, operation: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        request = BrokerRequest(
            request_id=uuid.uuid4().hex,
            timestamp_ms=self._clock(),
            nonce=secrets.token_hex(16),
            operation=operation,
            payload=payload,
        )
        frame = encode_frame(request.unsigned(), self._secret)
        try:
            raw = self._transport.exchange(frame, timeout_seconds=self._timeout_seconds)
        except BrokerError:
            raise
        except (OSError, TimeoutError) as exc:
            raise BrokerUnavailableError("transport_error") from exc

        try:
            # Authenticate BEFORE interpreting: an unsigned/foreign frame is
            # never parsed as a Broker response.
            message = decode_frame(raw)
            verify_signature(message, self._secret)
            response = parse_response(message)
        except BrokerError as exc:
            raise BrokerResponseError(exc.reason) from exc
        if response.request_id is not None and response.request_id != request.request_id:
            raise BrokerResponseError("request_id_mismatch")
        now_ms = self._clock()
        # Same half-open window as the Broker (see BrokerServer._check_freshness).
        if not (now_ms - self._max_age_ms < response.timestamp_ms <= now_ms + self._max_future_skew_ms):
            raise BrokerResponseError("stale_response")
        if response.status == STATUS_ERROR:
            raise BrokerRejectedError(response.error_code or "internal_error")
        if response.request_id is None:
            raise BrokerResponseError("request_id_mismatch")
        return response.result or {}

    def health(self) -> BrokerHealth:
        return _health_from_result(self._call(OP_BROKER_HEALTH, {}))
