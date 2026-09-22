"""DEV-1A: the MYC Developer Broker request pipeline (transport-agnostic).

``BrokerServer.handle_frame`` takes one request frame and always returns one
signed response frame; it never raises and never returns a traceback. The
pipeline, in order:

1. decode (size limit, strict JSON, no duplicate keys)          -> malformed
2. protocol / version / exact field set / field formats        -> malformed | unsupported_version
3. HMAC signature (constant time)                              -> unauthenticated
4. timestamp inside (now - max_age, now + max_future_skew]     -> unauthenticated
5. nonce and request_id never seen inside the window           -> unauthenticated
6. operation registered                                        -> unknown_operation
7. operation payload contract                                  -> invalid_payload
8. handler

Anti-replay state is only written after the signature and the timestamp are
valid, so an unauthenticated caller can never fill it.

The Broker authenticates the calling *process*; it does NOT authorize the
*user*. It never sees a JWT, a role, a DeveloperSession or a biometric
credential -- FastAPI's Developer authority (DEV-0) has already decided that
before a request reaches this boundary.

DEV-1A registers exactly one operation, ``broker.health``, which executes
nothing. The Windows service host that will own a ``BrokerServer`` (Named
Pipe listener, dedicated least-privilege identity) is DEV-1B.
"""

import logging
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.developer_broker.protocol import (
    DEFAULT_MAX_AGE_MS,
    DEFAULT_MAX_FUTURE_SKEW_MS,
    ERROR_INTERNAL,
    ERROR_INVALID_PAYLOAD,
    ERROR_UNAUTHENTICATED,
    ERROR_UNKNOWN_OPERATION,
    OP_BROKER_HEALTH,
    PROTOCOL,
    PROTOCOL_VERSION,
    SIGNATURE_ALGORITHM,
    STATUS_ERROR,
    STATUS_OK,
    SUPPORTED_VERSIONS,
    BrokerProtocolError,
    BrokerResponse,
    BrokerSecret,
    decode_frame,
    encode_frame,
    is_request_id,
    parse_request,
    verify_signature,
    wall_clock_ms,
)
from app.developer_broker.replay import InMemoryReplayGuard, ReplayGuard


logger = logging.getLogger("app.developer_broker.server")

FEATURES = (SIGNATURE_ALGORITHM, "anti-replay", "signed-responses")


@dataclass(frozen=True)
class BrokerOperation:
    name: str
    validate_payload: Callable[[Mapping[str, Any]], None]
    handle: Callable[[Mapping[str, Any]], dict[str, Any]]


def _require_empty_payload(payload: Mapping[str, Any]) -> None:
    if payload:
        raise BrokerProtocolError(ERROR_INVALID_PAYLOAD, "payload_must_be_empty")


class BrokerServer:
    def __init__(
        self,
        secret: BrokerSecret,
        *,
        replay_guard: ReplayGuard | None = None,
        clock: Callable[[], int] = wall_clock_ms,
        instance_id: str | None = None,
        max_age_ms: int = DEFAULT_MAX_AGE_MS,
        max_future_skew_ms: int = DEFAULT_MAX_FUTURE_SKEW_MS,
    ) -> None:
        if not isinstance(secret, BrokerSecret):
            raise TypeError("secret must be a BrokerSecret")
        self._secret = secret
        self._clock = clock
        self._max_age_ms = max_age_ms
        self._max_future_skew_ms = max_future_skew_ms
        # ``is None``, not ``or``: an empty guard is falsy (``__len__``).
        self._replay_guard = (
            replay_guard
            if replay_guard is not None
            else InMemoryReplayGuard(retention_ms=max_age_ms + max_future_skew_ms)
        )
        # Random per Broker process: identifies an instance (restarts are
        # visible) without revealing hostname, paths or configuration.
        self.instance_id = instance_id or uuid.uuid4().hex
        self._operations: dict[str, BrokerOperation] = {
            OP_BROKER_HEALTH: BrokerOperation(OP_BROKER_HEALTH, _require_empty_payload, self._health),
        }

    @property
    def operations(self) -> tuple[str, ...]:
        return tuple(sorted(self._operations))

    def _health(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "status": "ok",
            "protocol": PROTOCOL,
            "protocol_version": PROTOCOL_VERSION,
            "supported_versions": sorted(SUPPORTED_VERSIONS),
            "instance_id": self.instance_id,
            "timestamp": self._clock(),
            "operations": list(self.operations),
            "features": list(FEATURES),
        }

    def _check_freshness(self, timestamp_ms: int, now_ms: int) -> None:
        # Half-open window (now - max_age, now + max_future_skew]. The lower
        # bound is exclusive so a request is stale at exactly the instant its
        # replay entry (``now_accepted + max_age + max_future_skew``, purged
        # when ``expires <= now``) can disappear: even a frame accepted with
        # the maximum future skew is never valid again once forgotten.
        if timestamp_ms <= now_ms - self._max_age_ms:
            raise BrokerProtocolError(ERROR_UNAUTHENTICATED, "timestamp_expired")
        if timestamp_ms > now_ms + self._max_future_skew_ms:
            raise BrokerProtocolError(ERROR_UNAUTHENTICATED, "timestamp_in_future")

    def process(self, frame: bytes) -> BrokerResponse:
        """Runs the pipeline and returns the (unsigned) response. Rejections
        are logged with their internal reason -- never the frame, payload,
        signature or secret."""
        request_id: str | None = None
        operation: str | None = None
        try:
            message = decode_frame(frame)
            if is_request_id(message.get("request_id")):
                request_id = message["request_id"]
            request = parse_request(message)
            verify_signature(message, self._secret)
            now_ms = self._clock()
            self._check_freshness(request.timestamp_ms, now_ms)
            self._replay_guard.remember(nonce=request.nonce, request_id=request.request_id, now_ms=now_ms)
            handler = self._operations.get(request.operation)
            if handler is None:
                raise BrokerProtocolError(ERROR_UNKNOWN_OPERATION, "unknown_operation")
            operation = handler.name
            handler.validate_payload(request.payload)
            result = handler.handle(request.payload)
        except BrokerProtocolError as exc:
            logger.warning(
                "Developer Broker rechazó una solicitud: code=%s reason=%s request_id=%s operation=%s",
                exc.code, exc.reason, request_id, operation,
            )
            return BrokerResponse(request_id, self._clock(), STATUS_ERROR, error_code=exc.code)
        except Exception:  # noqa: BLE001 -- the boundary never leaks a traceback
            logger.error(
                "Developer Broker falló al procesar: request_id=%s operation=%s", request_id, operation
            )
            return BrokerResponse(request_id, self._clock(), STATUS_ERROR, error_code=ERROR_INTERNAL)
        logger.info("Developer Broker atendió: request_id=%s operation=%s", request_id, operation)
        return BrokerResponse(request_id, self._clock(), STATUS_OK, result=result)

    def handle_frame(self, frame: bytes) -> bytes:
        return encode_frame(self.process(frame).unsigned(), self._secret)
