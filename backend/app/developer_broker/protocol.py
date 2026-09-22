"""DEV-1A: versioned Developer Broker wire contract and message authentication.

Every frame is one JSON object. The signature is HMAC-SHA256 (stdlib
``hmac``/``hashlib``) over the *canonical* JSON of every other field of the
envelope -- keys sorted, no insignificant whitespace, ASCII only, no NaN --
so the signed bytes are unambiguous (no field concatenation) and any change
to any field after signing invalidates it. Duplicate JSON keys are rejected
on decode, so a frame can never mean two different things to two parsers.

Requests and responses are both signed with the dedicated ERP<->Broker
secret. ``kind`` is part of the signed bytes, so a signed response can never
be replayed as a request (or vice versa). The secret is never logged, never
echoed in errors and never part of ``repr``.

Wire error codes are deliberately coarse: every authentication failure
(bad signature, stale/future timestamp, replayed nonce/request_id) is
``unauthenticated`` on the wire; the precise ``reason`` stays inside the
Broker (logs/tests) and is never sent to an untrusted caller.
"""

import hashlib
import hmac
import json
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


PROTOCOL = "myc.developer-broker"
PROTOCOL_VERSION = 1
SUPPORTED_VERSIONS = frozenset({PROTOCOL_VERSION})
SIGNATURE_ALGORITHM = "hmac-sha256"

KIND_REQUEST = "request"
KIND_RESPONSE = "response"
STATUS_OK = "ok"
STATUS_ERROR = "error"

MAX_FRAME_BYTES = 64 * 1024
# Acceptance window for message timestamps (both directions). Both processes
# run on the same host, so a tight window is realistic.
DEFAULT_MAX_AGE_MS = 30_000
DEFAULT_MAX_FUTURE_SKEW_MS = 5_000
MIN_SECRET_BYTES = 32

# The only operation implemented in DEV-1A. Nothing here executes anything.
OP_BROKER_HEALTH = "broker.health"

# Reserved for DEV-1B+ -- documented, NOT implemented: any operation in these
# namespaces is rejected as ``unknown_operation`` until a handler exists.
RESERVED_NAMESPACES = ("shell.", "database.", "git.", "alembic.", "services.", "logs.")

# Wire error codes.
ERROR_MALFORMED = "malformed"
ERROR_UNSUPPORTED_VERSION = "unsupported_version"
ERROR_UNAUTHENTICATED = "unauthenticated"
ERROR_UNKNOWN_OPERATION = "unknown_operation"
ERROR_INVALID_PAYLOAD = "invalid_payload"
ERROR_UNAVAILABLE = "unavailable"
ERROR_INTERNAL = "internal_error"
# Client-side only (never on the wire).
ERROR_NOT_CONFIGURED = "not_configured"
ERROR_INVALID_RESPONSE = "invalid_response"

WIRE_ERROR_MESSAGES = {
    ERROR_MALFORMED: "Mensaje Broker malformado",
    ERROR_UNSUPPORTED_VERSION: "Versión de protocolo Broker no soportada",
    ERROR_UNAUTHENTICATED: "Mensaje Broker no autenticado",
    ERROR_UNKNOWN_OPERATION: "Operación Broker desconocida",
    ERROR_INVALID_PAYLOAD: "Payload Broker inválido",
    ERROR_UNAVAILABLE: "Broker no disponible",
    ERROR_INTERNAL: "Error interno del Broker",
}

REQUEST_FIELDS = frozenset(
    {"protocol", "version", "kind", "request_id", "timestamp", "nonce", "operation", "payload", "signature"}
)
RESPONSE_FIELDS = frozenset(
    {"protocol", "version", "kind", "request_id", "timestamp", "status", "result", "error", "signature"}
)

_REQUEST_ID = re.compile(r"[0-9a-f]{32}")
_NONCE = re.compile(r"[0-9a-f]{32,64}")
_SIGNATURE = re.compile(r"[0-9a-f]{64}")
_OPERATION = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+")
_MAX_OPERATION_LENGTH = 64


def wall_clock_ms() -> int:
    return time.time_ns() // 1_000_000


class BrokerError(Exception):
    """Base error. ``code`` is safe to show; ``reason`` is Broker-internal
    detail for logs/tests and is never sent to an untrusted caller. Neither
    ever contains secret material."""

    def __init__(self, code: str, reason: str | None = None) -> None:
        super().__init__(code if reason is None else f"{code}: {reason}")
        self.code = code
        self.reason = reason or code


class BrokerProtocolError(BrokerError):
    """A frame was rejected by the contract (either side)."""


class BrokerConfigurationError(BrokerError):
    def __init__(self, reason: str) -> None:
        super().__init__(ERROR_NOT_CONFIGURED, reason)


class BrokerUnavailableError(BrokerError):
    def __init__(self, reason: str = "transport_unavailable") -> None:
        super().__init__(ERROR_UNAVAILABLE, reason)


class BrokerRejectedError(BrokerError):
    """The Broker answered with an authenticated error response."""


class BrokerResponseError(BrokerError):
    """The response itself could not be trusted (unsigned, stale, foreign)."""

    def __init__(self, reason: str) -> None:
        super().__init__(ERROR_INVALID_RESPONSE, reason)


@dataclass(frozen=True, eq=False)
class BrokerSecret:
    """The dedicated ERP<->Broker HMAC key. Loaded from external secret
    material only; ``repr``/``str`` never reveal it. No ``__eq__``: keys are
    never compared outside ``hmac.compare_digest``."""

    _key: bytes = field(repr=False)

    @classmethod
    def from_text(cls, value: str | None) -> "BrokerSecret":
        key = (value or "").encode("utf-8")
        if len(key) < MIN_SECRET_BYTES:
            raise BrokerConfigurationError("secret_missing_or_too_short")
        return cls(key)

    def __repr__(self) -> str:
        return "BrokerSecret(<redacted>)"

    __str__ = __repr__

    def sign(self, message: bytes) -> str:
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()

    def verify(self, message: bytes, signature: str) -> bool:
        return hmac.compare_digest(self.sign(message).encode("ascii"), signature.encode("utf-8"))


def canonical_bytes(fields: Mapping[str, Any]) -> bytes:
    """The exact bytes that are signed: stable across key order and
    whitespace, unambiguous (JSON, never concatenation)."""
    try:
        return json.dumps(
            fields, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise BrokerProtocolError(ERROR_MALFORMED, "not_canonicalizable") from exc


def encode_frame(fields: Mapping[str, Any], secret: BrokerSecret) -> bytes:
    """Signs ``fields`` (which must not contain ``signature``) and returns the frame."""
    if "signature" in fields:
        raise ValueError("fields must not already carry a signature")
    return canonical_bytes({**fields, "signature": secret.sign(canonical_bytes(fields))})


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BrokerProtocolError(ERROR_MALFORMED, "duplicate_key")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise BrokerProtocolError(ERROR_MALFORMED, "non_finite_number")


def decode_frame(frame: bytes) -> dict[str, Any]:
    if not isinstance(frame, (bytes, bytearray)):
        raise BrokerProtocolError(ERROR_MALFORMED, "not_bytes")
    if len(frame) > MAX_FRAME_BYTES:
        raise BrokerProtocolError(ERROR_MALFORMED, "frame_too_large")
    try:
        decoded = json.loads(
            bytes(frame).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise BrokerProtocolError(ERROR_MALFORMED, "invalid_json") from exc
    if not isinstance(decoded, dict):
        raise BrokerProtocolError(ERROR_MALFORMED, "not_an_object")
    return decoded


def unsigned_fields(message: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in message.items() if key != "signature"}


def verify_signature(message: Mapping[str, Any], secret: BrokerSecret) -> None:
    """Constant-time check of ``message['signature']`` over the canonical
    bytes of every other field."""
    signature = message.get("signature")
    if not isinstance(signature, str) or not _SIGNATURE.fullmatch(signature):
        raise BrokerProtocolError(ERROR_UNAUTHENTICATED, "signature_malformed")
    if not secret.verify(canonical_bytes(unsigned_fields(message)), signature):
        raise BrokerProtocolError(ERROR_UNAUTHENTICATED, "signature_mismatch")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_header(message: Mapping[str, Any], expected_kind: str, expected_fields: frozenset[str]) -> None:
    if message.get("protocol") != PROTOCOL:
        raise BrokerProtocolError(ERROR_MALFORMED, "unknown_protocol")
    version = message.get("version")
    if not _is_int(version):
        raise BrokerProtocolError(ERROR_MALFORMED, "version_not_integer")
    if version not in SUPPORTED_VERSIONS:
        raise BrokerProtocolError(ERROR_UNSUPPORTED_VERSION, "unsupported_version")
    if set(message) != expected_fields:
        raise BrokerProtocolError(ERROR_MALFORMED, "unexpected_fields")
    if message["kind"] != expected_kind:
        raise BrokerProtocolError(ERROR_MALFORMED, "unexpected_kind")
    if not _is_int(message["timestamp"]) or message["timestamp"] <= 0:
        raise BrokerProtocolError(ERROR_MALFORMED, "invalid_timestamp")
    if not isinstance(message["signature"], str) or not _SIGNATURE.fullmatch(message["signature"]):
        raise BrokerProtocolError(ERROR_MALFORMED, "invalid_signature_format")


def is_request_id(value: Any) -> bool:
    return isinstance(value, str) and _REQUEST_ID.fullmatch(value) is not None


@dataclass(frozen=True)
class BrokerRequest:
    request_id: str
    timestamp_ms: int
    nonce: str
    operation: str
    payload: Mapping[str, Any]
    version: int = PROTOCOL_VERSION

    def unsigned(self) -> dict[str, Any]:
        return {
            "protocol": PROTOCOL,
            "version": self.version,
            "kind": KIND_REQUEST,
            "request_id": self.request_id,
            "timestamp": self.timestamp_ms,
            "nonce": self.nonce,
            "operation": self.operation,
            "payload": dict(self.payload),
        }


def parse_request(message: Mapping[str, Any]) -> BrokerRequest:
    """Structural validation only; authentication is ``verify_signature``."""
    _check_header(message, KIND_REQUEST, REQUEST_FIELDS)
    if not is_request_id(message["request_id"]):
        raise BrokerProtocolError(ERROR_MALFORMED, "invalid_request_id")
    if not isinstance(message["nonce"], str) or not _NONCE.fullmatch(message["nonce"]):
        raise BrokerProtocolError(ERROR_MALFORMED, "invalid_nonce")
    operation = message["operation"]
    if (
        not isinstance(operation, str)
        or len(operation) > _MAX_OPERATION_LENGTH
        or not _OPERATION.fullmatch(operation)
    ):
        raise BrokerProtocolError(ERROR_MALFORMED, "invalid_operation_name")
    if not isinstance(message["payload"], dict):
        raise BrokerProtocolError(ERROR_MALFORMED, "payload_not_object")
    return BrokerRequest(
        request_id=message["request_id"],
        timestamp_ms=message["timestamp"],
        nonce=message["nonce"],
        operation=operation,
        payload=message["payload"],
        version=message["version"],
    )


@dataclass(frozen=True)
class BrokerResponse:
    request_id: str | None
    timestamp_ms: int
    status: str
    result: Mapping[str, Any] | None = None
    error_code: str | None = None
    version: int = PROTOCOL_VERSION

    def unsigned(self) -> dict[str, Any]:
        error = None
        if self.error_code is not None:
            error = {"code": self.error_code, "message": WIRE_ERROR_MESSAGES[self.error_code]}
        return {
            "protocol": PROTOCOL,
            "version": self.version,
            "kind": KIND_RESPONSE,
            "request_id": self.request_id,
            "timestamp": self.timestamp_ms,
            "status": self.status,
            "result": None if self.result is None else dict(self.result),
            "error": error,
        }


def parse_response(message: Mapping[str, Any]) -> BrokerResponse:
    _check_header(message, KIND_RESPONSE, RESPONSE_FIELDS)
    request_id, status = message["request_id"], message["status"]
    if request_id is not None and not is_request_id(request_id):
        raise BrokerProtocolError(ERROR_MALFORMED, "invalid_request_id")
    if status == STATUS_OK:
        if not isinstance(message["result"], dict) or message["error"] is not None or request_id is None:
            raise BrokerProtocolError(ERROR_MALFORMED, "inconsistent_ok_response")
        return BrokerResponse(request_id, message["timestamp"], status, result=message["result"])
    if status == STATUS_ERROR:
        error = message["error"]
        if (
            message["result"] is not None
            or not isinstance(error, dict)
            or set(error) != {"code", "message"}
            or error["code"] not in WIRE_ERROR_MESSAGES
        ):
            raise BrokerProtocolError(ERROR_MALFORMED, "inconsistent_error_response")
        return BrokerResponse(request_id, message["timestamp"], status, error_code=error["code"])
    raise BrokerProtocolError(ERROR_MALFORMED, "unknown_status")
