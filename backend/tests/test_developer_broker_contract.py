"""DEV-1A: Developer Broker contract -- canonical serialization, HMAC
authentication, anti-replay, versioning, ``broker.health``, fail-closed
client/configuration and the structural guarantees of the boundary (no ERP
imports, no process execution). No Windows, no network, no subprocess: the
Broker is reached through the in-memory transport only."""
import ast
import json
import logging
import secrets
import sys
import uuid
from pathlib import Path

import pytest

from app.core.config import settings
from app.developer_broker.client import BrokerClient, _health_from_result
from app.developer_broker.protocol import (
    ERROR_INVALID_PAYLOAD,
    ERROR_MALFORMED,
    ERROR_UNAUTHENTICATED,
    ERROR_UNAVAILABLE,
    ERROR_UNKNOWN_OPERATION,
    ERROR_UNSUPPORTED_VERSION,
    MAX_FRAME_BYTES,
    OP_BROKER_HEALTH,
    PROTOCOL,
    STATUS_ERROR,
    STATUS_OK,
    BrokerConfigurationError,
    BrokerRejectedError,
    BrokerRequest,
    BrokerResponseError,
    BrokerSecret,
    BrokerUnavailableError,
    canonical_bytes,
    decode_frame,
    encode_frame,
    verify_signature,
)
from app.developer_broker.replay import InMemoryReplayGuard
from app.developer_broker.server import BrokerOperation, BrokerServer
from app.developer_broker.transport import InMemoryBrokerTransport
from app.services.developer_broker import build_developer_broker_client, get_developer_broker_client

BACKEND = Path(__file__).resolve().parents[1]
BROKER_PACKAGE = BACKEND / "app" / "developer_broker"
NOW_MS = 1_790_000_000_000


class FixedClock:
    def __init__(self, now_ms: int = NOW_MS) -> None:
        self.now_ms = now_ms

    def __call__(self) -> int:
        return self.now_ms


def new_secret_text() -> str:
    # Generated per test run; never a real secret, never committed.
    return secrets.token_urlsafe(48)


@pytest.fixture
def secret_text():
    return new_secret_text()


@pytest.fixture
def secret(secret_text):
    return BrokerSecret.from_text(secret_text)


@pytest.fixture
def clock():
    return FixedClock()


@pytest.fixture
def server(secret, clock):
    return BrokerServer(secret, clock=clock, instance_id="a" * 32)


def request_fields(**overrides):
    fields = BrokerRequest(
        request_id=uuid.uuid4().hex,
        timestamp_ms=NOW_MS,
        nonce=secrets.token_hex(16),
        operation=OP_BROKER_HEALTH,
        payload={},
    ).unsigned()
    fields.update(overrides)
    return fields


def signed(secret, **overrides) -> bytes:
    return encode_frame(request_fields(**overrides), secret)


def reply(server, frame: bytes, secret) -> dict:
    """Sends ``frame`` and returns the decoded response after checking the
    Broker signed it."""
    message = decode_frame(server.handle_frame(frame))
    verify_signature(message, secret)
    return message


def error_code(server, frame, secret):
    message = reply(server, frame, secret)
    assert message["status"] == STATUS_ERROR
    assert message["result"] is None
    return message["error"]["code"]


def rejection_reasons(caplog):
    return [record.getMessage() for record in caplog.records if "rechazó" in record.getMessage()]


# --- A. canonical serialization ------------------------------------------------

def test_canonical_serialization_is_stable_and_unambiguous():
    first = {"b": 1, "a": {"y": [1, "x"], "x": None}, "c": "ñ"}
    second = {"c": "ñ", "a": {"x": None, "y": [1, "x"]}, "b": 1}
    assert canonical_bytes(first) == canonical_bytes(second)
    assert canonical_bytes(first) == b'{"a":{"x":null,"y":[1,"x"]},"b":1,"c":"\\u00f1"}'
    # JSON, never concatenation: these two would collide under naive joining.
    assert canonical_bytes({"operation": "a.b", "nonce": "c"}) != canonical_bytes(
        {"operation": "a", "nonce": "b.c"}
    )
    with pytest.raises(Exception):
        canonical_bytes({"n": float("nan")})


def test_signature_does_not_depend_on_wire_key_order_or_whitespace(server, secret):
    frame = signed(secret)
    reordered = json.dumps(dict(reversed(list(json.loads(frame).items()))), indent=2).encode()
    assert reply(server, reordered, secret)["status"] == STATUS_OK


# --- B. valid request ------------------------------------------------------------

def test_valid_signed_request_is_accepted(server, secret):
    message = reply(server, signed(secret), secret)
    assert message["status"] == STATUS_OK
    assert message["kind"] == "response"
    assert message["protocol"] == PROTOCOL and message["version"] == 1
    assert message["error"] is None


def test_timestamp_window_is_half_open(server, secret, caplog):
    """(now - max_age, now + max_future_skew]: the old edge is exclusive,
    the future edge inclusive."""
    assert reply(server, signed(secret, timestamp=NOW_MS - 29_999), secret)["status"] == STATUS_OK
    assert reply(server, signed(secret, timestamp=NOW_MS + 5_000), secret)["status"] == STATUS_OK
    with caplog.at_level(logging.WARNING, logger="app.developer_broker"):
        assert error_code(server, signed(secret, timestamp=NOW_MS - 30_000), secret) == ERROR_UNAUTHENTICATED
        assert error_code(server, signed(secret, timestamp=NOW_MS + 5_001), secret) == ERROR_UNAUTHENTICATED
    reasons = rejection_reasons(caplog)
    assert "reason=timestamp_expired" in reasons[0]
    assert "reason=timestamp_in_future" in reasons[1]


def test_frame_accepted_with_max_future_skew_cannot_be_replayed_after_its_replay_entry_expires(secret, caplog):
    """P1 regression: the replay entry lives exactly max_age + max_future_skew
    from acceptance. A frame accepted with the maximum future skew must be
    stale at the very instant that entry is purged -- never replayable."""
    clock = FixedClock()
    guard = InMemoryReplayGuard(retention_ms=35_000)
    server = BrokerServer(secret, clock=clock, replay_guard=guard)
    frame = signed(secret, timestamp=NOW_MS + 5_000)  # maximum accepted future skew
    assert reply(server, frame, secret)["status"] == STATUS_OK

    with caplog.at_level(logging.WARNING, logger="app.developer_broker"):
        clock.now_ms = NOW_MS + 34_999  # entry still stored
        assert error_code(server, frame, secret) == ERROR_UNAUTHENTICATED
        clock.now_ms = NOW_MS + 35_000  # entry expires (expires <= now) ...
        assert error_code(server, frame, secret) == ERROR_UNAUTHENTICATED  # ... and the frame is already stale
    reasons = rejection_reasons(caplog)
    assert "reason=nonce_replay" in reasons[0]
    assert "reason=timestamp_expired" in reasons[1]

    # The entry really is gone: a fresh request purges it and only its own
    # two keys (nonce + request_id) remain.
    assert reply(server, signed(secret, timestamp=clock.now_ms), secret)["status"] == STATUS_OK
    assert len(guard) == 2
    assert error_code(server, frame, secret) == ERROR_UNAUTHENTICATED


# --- C / D. signature --------------------------------------------------------------

def test_wrong_secret_is_rejected(server, secret, caplog):
    other = BrokerSecret.from_text(new_secret_text())
    with caplog.at_level(logging.WARNING, logger="app.developer_broker"):
        assert error_code(server, signed(other), secret) == ERROR_UNAUTHENTICATED
    assert "reason=signature_mismatch" in rejection_reasons(caplog)[0]


@pytest.mark.parametrize(
    "field, value",
    [
        ("payload", {"extra": True}),
        ("operation", "broker.other"),
        ("timestamp", NOW_MS - 1),
        ("nonce", "f" * 32),
        ("request_id", "e" * 32),
    ],
)
def test_message_altered_after_signing_is_rejected(server, secret, field, value):
    message = json.loads(signed(secret))
    message[field] = value
    assert error_code(server, json.dumps(message).encode(), secret) == ERROR_UNAUTHENTICATED


def test_missing_or_malformed_signature_is_rejected(server, secret):
    message = json.loads(signed(secret))
    message["signature"] = "Z" * 64
    assert error_code(server, json.dumps(message).encode(), secret) == ERROR_MALFORMED
    del message["signature"]
    assert error_code(server, json.dumps(message).encode(), secret) == ERROR_MALFORMED


def test_signed_response_cannot_be_replayed_as_a_request(server, secret):
    response = server.handle_frame(signed(secret))
    assert error_code(server, response, secret) == ERROR_MALFORMED


# --- E / F. timestamp window ---------------------------------------------------------

def test_old_timestamp_is_rejected(server, secret, caplog):
    with caplog.at_level(logging.WARNING, logger="app.developer_broker"):
        assert error_code(server, signed(secret, timestamp=NOW_MS - 30_001), secret) == ERROR_UNAUTHENTICATED
    assert "reason=timestamp_expired" in rejection_reasons(caplog)[0]


def test_future_timestamp_beyond_tolerance_is_rejected(server, secret, caplog):
    with caplog.at_level(logging.WARNING, logger="app.developer_broker"):
        assert error_code(server, signed(secret, timestamp=NOW_MS + 5_001), secret) == ERROR_UNAUTHENTICATED
    assert "reason=timestamp_in_future" in rejection_reasons(caplog)[0]


# --- G. replay -----------------------------------------------------------------------

def test_replayed_frame_is_rejected(server, secret, caplog):
    frame = signed(secret)
    assert reply(server, frame, secret)["status"] == STATUS_OK
    with caplog.at_level(logging.WARNING, logger="app.developer_broker"):
        assert error_code(server, frame, secret) == ERROR_UNAUTHENTICATED
    assert "reason=nonce_replay" in rejection_reasons(caplog)[0]


def test_repeated_request_id_with_fresh_nonce_is_rejected(server, secret, caplog):
    request_id = uuid.uuid4().hex
    assert reply(server, signed(secret, request_id=request_id), secret)["status"] == STATUS_OK
    with caplog.at_level(logging.WARNING, logger="app.developer_broker"):
        assert error_code(server, signed(secret, request_id=request_id), secret) == ERROR_UNAUTHENTICATED
    assert "reason=request_id_replay" in rejection_reasons(caplog)[0]


def test_unauthenticated_frames_never_consume_anti_replay_state(secret, clock):
    guard = InMemoryReplayGuard(retention_ms=35_000, max_entries=4)
    server = BrokerServer(secret, clock=clock, replay_guard=guard)
    other = BrokerSecret.from_text(new_secret_text())
    for _ in range(10):
        assert error_code(server, signed(other), secret) == ERROR_UNAUTHENTICATED
        assert error_code(server, signed(secret, timestamp=NOW_MS - 60_000), secret) == ERROR_UNAUTHENTICATED
    assert len(guard) == 0


def test_replay_guard_expires_entries_and_is_bounded():
    guard = InMemoryReplayGuard(retention_ms=1_000, max_entries=4)
    guard.remember(nonce="n1", request_id="r1", now_ms=0)
    guard.remember(nonce="n2", request_id="r2", now_ms=10)
    with pytest.raises(Exception) as full:
        guard.remember(nonce="n3", request_id="r3", now_ms=20)
    assert full.value.code == ERROR_UNAVAILABLE  # fails closed, never evicts live entries
    assert len(guard) == 4
    # After the retention window the old entries are purged and space is back.
    guard.remember(nonce="n3", request_id="r3", now_ms=1_000)
    assert len(guard) == 4  # n1/r1 purged
    guard.remember(nonce="n1", request_id="r1", now_ms=1_011)  # n2/r2 purged too
    assert len(guard) == 4


def test_replay_guard_full_makes_broker_fail_closed(secret, clock):
    server = BrokerServer(secret, clock=clock, replay_guard=InMemoryReplayGuard(retention_ms=35_000, max_entries=2))
    assert reply(server, signed(secret), secret)["status"] == STATUS_OK
    assert error_code(server, signed(secret), secret) == ERROR_UNAVAILABLE


def test_broker_restart_loses_replay_state_but_window_still_bounds_it(secret):
    clock = FixedClock()
    frame = signed(secret)
    assert reply(BrokerServer(secret, clock=clock), frame, secret)["status"] == STATUS_OK
    restarted = BrokerServer(secret, clock=clock)
    clock.now_ms += 30_001  # the captured frame is already outside the window
    assert error_code(restarted, frame, secret) == ERROR_UNAUTHENTICATED


# --- H. version ------------------------------------------------------------------------

def test_unknown_version_is_rejected(server, secret):
    assert error_code(server, signed(secret, version=2), secret) == ERROR_UNSUPPORTED_VERSION
    assert error_code(server, signed(secret, version="1"), secret) == ERROR_MALFORMED
    assert error_code(server, signed(secret, version=True), secret) == ERROR_MALFORMED
    assert error_code(server, signed(secret, protocol="other"), secret) == ERROR_MALFORMED


# --- I. operation --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "operation",
    ["broker.nope", "shell.create", "shell.stdin", "database.query", "git.status", "alembic.upgrade", "services.restart", "logs.tail"],
)
def test_unknown_and_reserved_operations_are_rejected(server, secret, operation):
    assert error_code(server, signed(secret, operation=operation), secret) == ERROR_UNKNOWN_OPERATION


def test_only_health_is_registered(server):
    assert server.operations == (OP_BROKER_HEALTH,)


@pytest.mark.parametrize("operation", ["powershell", "BROKER.HEALTH", "broker.health; rm", "a" * 70 + ".b"])
def test_operation_names_are_not_free_text(server, secret, operation):
    assert error_code(server, signed(secret, operation=operation), secret) == ERROR_MALFORMED


# --- J. malformed ----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "frame",
    [
        b"",
        b"not json",
        b"\xff\xfe",
        b"[]",
        b'{"a":1,"a":2}',
        b'{"n": NaN}',
        b"[" * 60_000,
        b" " * (MAX_FRAME_BYTES + 1),
    ],
)
def test_undecodable_frames_are_rejected(server, secret, frame):
    assert error_code(server, frame, secret) == ERROR_MALFORMED


def test_structurally_invalid_requests_are_rejected(server, secret):
    for bad in (
        request_fields(payload=[]),
        request_fields(payload="{}"),
        request_fields(kind="response"),
        request_fields(request_id="not-hex"),
        request_fields(nonce="short"),
        request_fields(timestamp=-1),
        request_fields(timestamp=1.5),
        request_fields(extra="field"),
    ):
        assert error_code(server, encode_frame(bad, secret), secret) == ERROR_MALFORMED
    missing = request_fields()
    del missing["nonce"]
    assert error_code(server, encode_frame(missing, secret), secret) == ERROR_MALFORMED


def test_invalid_payload_for_operation_is_rejected(server, secret):
    assert error_code(server, signed(secret, payload={"command": "anything"}), secret) == ERROR_INVALID_PAYLOAD


def test_handler_failure_never_leaks_a_traceback(server, secret, monkeypatch):
    def boom(payload):
        raise RuntimeError("internal detail /secret/path")

    monkeypatch.setitem(server._operations, OP_BROKER_HEALTH, BrokerOperation(OP_BROKER_HEALTH, lambda payload: None, boom))
    message = reply(server, signed(secret), secret)
    assert message["error"]["code"] == "internal_error"
    assert "secret/path" not in json.dumps(message)


# --- K. broker.health ------------------------------------------------------------------------

def test_broker_health_through_client(server, secret, clock):
    client = BrokerClient(InMemoryBrokerTransport(server), secret, clock=clock)
    health = client.health()
    assert health.status == "ok"
    assert health.protocol == PROTOCOL
    assert health.protocol_version == 1
    assert health.supported_versions == (1,)
    assert health.instance_id == "a" * 32
    assert health.timestamp_ms == NOW_MS
    assert health.operations == (OP_BROKER_HEALTH,)
    assert set(health.features) == {"hmac-sha256", "anti-replay", "signed-responses"}
    # Consecutive calls use fresh request_id/nonce (no self-inflicted replay).
    assert client.health().status == "ok"


def test_health_result_exposes_no_host_or_configuration_details(server, secret):
    result = reply(server, signed(secret), secret)["result"]
    assert set(result) == {
        "status", "protocol", "protocol_version", "supported_versions",
        "instance_id", "timestamp", "operations", "features",
    }


# --- L. broker unavailable / not configured / untrusted response ------------------------------

class DownTransport:
    def __init__(self, error):
        self.error = error

    def exchange(self, frame, *, timeout_seconds):
        raise self.error


@pytest.mark.parametrize("error", [BrokerUnavailableError(), OSError("pipe busy"), TimeoutError()])
def test_unreachable_broker_fails_closed(secret, error):
    with pytest.raises(BrokerUnavailableError):
        BrokerClient(DownTransport(error), secret).health()


def test_client_rejects_response_signed_with_another_secret(server, secret):
    client = BrokerClient(InMemoryBrokerTransport(server), BrokerSecret.from_text(new_secret_text()), clock=server._clock)
    with pytest.raises(BrokerResponseError):
        client.health()


def test_response_is_authenticated_before_it_is_interpreted(secret, clock, monkeypatch):
    """A frame that looks like a perfect ``ok`` health response but is signed
    with another key is rejected by authentication; ``parse_response`` never
    even sees it."""
    import app.developer_broker.client as client_module

    impostor = BrokerSecret.from_text(new_secret_text())
    interpreted = []
    real_parse = client_module.parse_response
    monkeypatch.setattr(client_module, "parse_response", lambda message: interpreted.append(message) or real_parse(message))

    client = BrokerClient(ForgedTransport(impostor, clock), secret, clock=clock)
    with pytest.raises(BrokerResponseError) as rejected:
        client.health()
    assert rejected.value.reason == "signature_mismatch"
    assert interpreted == []

    class UnsignedTransport:
        def exchange(self, frame, *, timeout_seconds):
            message = json.loads(ForgedTransport(secret, clock).exchange(frame, timeout_seconds=timeout_seconds))
            del message["signature"]
            return json.dumps(message).encode()

    with pytest.raises(BrokerResponseError) as unsigned:
        BrokerClient(UnsignedTransport(), secret, clock=clock).health()
    assert unsigned.value.reason == "signature_malformed"
    assert interpreted == []

    # Correctly signed: now (and only now) it is interpreted.
    assert BrokerClient(ForgedTransport(secret, clock), secret, clock=clock).health().status == "ok"
    assert len(interpreted) == 1


VALID_HEALTH_RESULT = {
    "status": "ok",
    "protocol": PROTOCOL,
    "protocol_version": 1,
    "supported_versions": [1],
    "instance_id": "0123456789abcdef0123456789abcdef",
    "timestamp": NOW_MS,
    "operations": [OP_BROKER_HEALTH],
    "features": ["hmac-sha256"],
}


def _without(key):
    return {k: v for k, v in VALID_HEALTH_RESULT.items() if k != key}


@pytest.mark.parametrize(
    "result",
    [
        pytest.param({**VALID_HEALTH_RESULT, "hostname": "srv"}, id="extra-field"),
        pytest.param(_without("features"), id="missing-field"),
        pytest.param(_without("instance_id"), id="missing-instance-id"),
        pytest.param({**VALID_HEALTH_RESULT, "protocol_version": True}, id="protocol_version-bool"),
        pytest.param({**VALID_HEALTH_RESULT, "protocol_version": "1"}, id="protocol_version-str"),
        pytest.param({**VALID_HEALTH_RESULT, "timestamp": False}, id="timestamp-bool"),
        pytest.param({**VALID_HEALTH_RESULT, "timestamp": 0}, id="timestamp-zero"),
        pytest.param({**VALID_HEALTH_RESULT, "timestamp": 1.5}, id="timestamp-float"),
        pytest.param({**VALID_HEALTH_RESULT, "supported_versions": [True]}, id="supported_versions-bool"),
        pytest.param({**VALID_HEALTH_RESULT, "supported_versions": []}, id="supported_versions-empty"),
        pytest.param({**VALID_HEALTH_RESULT, "supported_versions": 1}, id="supported_versions-not-list"),
        pytest.param({**VALID_HEALTH_RESULT, "status": "degraded"}, id="status-not-ok"),
        pytest.param({**VALID_HEALTH_RESULT, "protocol": "other"}, id="protocol-other"),
        pytest.param({**VALID_HEALTH_RESULT, "instance_id": "not-a-uuid"}, id="instance_id-malformed"),
        pytest.param({**VALID_HEALTH_RESULT, "instance_id": "0123456789ABCDEF0123456789ABCDEF"}, id="instance_id-uppercase"),
        pytest.param({**VALID_HEALTH_RESULT, "instance_id": "01234567-89ab-cdef-0123-456789abcdef"}, id="instance_id-dashed"),
        pytest.param({**VALID_HEALTH_RESULT, "instance_id": ""}, id="instance_id-empty"),
        pytest.param({**VALID_HEALTH_RESULT, "operations": ["ok", 1]}, id="operations-not-str"),
        pytest.param({**VALID_HEALTH_RESULT, "features": "hmac-sha256"}, id="features-not-list"),
    ],
)
def test_health_result_contract_is_exact(result):
    with pytest.raises(BrokerResponseError) as rejected:
        _health_from_result(result)
    assert rejected.value.reason == "invalid_health_result"


def test_valid_health_result_is_accepted_without_coercion():
    health = _health_from_result(dict(VALID_HEALTH_RESULT))
    assert health.protocol_version == 1 and type(health.protocol_version) is int
    assert health.supported_versions == (1,)
    assert health.instance_id == VALID_HEALTH_RESULT["instance_id"]


def test_client_rejects_authentic_response_with_invalid_health_result(secret, clock):
    """Authenticated but out of contract (e.g. a leaked extra field) is still rejected."""

    class ExtraFieldTransport:
        def exchange(self, frame, *, timeout_seconds):
            request = json.loads(frame)
            return encode_frame(
                {
                    "protocol": PROTOCOL, "version": 1, "kind": "response",
                    "request_id": request["request_id"], "timestamp": clock(),
                    "status": STATUS_OK, "result": {**VALID_HEALTH_RESULT, "env": {"PATH": "x"}}, "error": None,
                },
                secret,
            )

    with pytest.raises(BrokerResponseError):
        BrokerClient(ExtraFieldTransport(), secret, clock=clock).health()


class ForgedTransport:
    """Answers with a correctly signed response that is bound to another
    request, or is stale."""

    def __init__(self, secret, clock, *, request_id=None, timestamp=None):
        self.secret, self.clock, self.request_id, self.timestamp = secret, clock, request_id, timestamp

    def exchange(self, frame, *, timeout_seconds):
        request = json.loads(frame)
        result = BrokerServer(self.secret, clock=self.clock).process(frame).result
        return encode_frame(
            {
                "protocol": PROTOCOL, "version": 1, "kind": "response",
                "request_id": self.request_id or request["request_id"],
                "timestamp": self.timestamp or self.clock(),
                "status": STATUS_OK, "result": result, "error": None,
            },
            self.secret,
        )


def test_client_rejects_response_for_another_request(secret, clock):
    client = BrokerClient(ForgedTransport(secret, clock, request_id="b" * 32), secret, clock=clock)
    with pytest.raises(BrokerResponseError):
        client.health()


def test_client_rejects_stale_response(secret, clock):
    client = BrokerClient(ForgedTransport(secret, clock, timestamp=NOW_MS - 60_000), secret, clock=clock)
    with pytest.raises(BrokerResponseError):
        client.health()


def test_client_surfaces_authenticated_broker_rejection(secret):
    # Broker clock far ahead of the client: the Broker rejects the request as stale.
    broker_clock = FixedClock(NOW_MS + 60_000)
    server = BrokerServer(secret, clock=broker_clock)
    client = BrokerClient(InMemoryBrokerTransport(server), secret, clock=FixedClock(), max_future_skew_ms=120_000)
    with pytest.raises(BrokerRejectedError) as rejected:
        client.health()
    assert rejected.value.code == ERROR_UNAUTHENTICATED


@pytest.mark.parametrize(
    "update, reason",
    [
        ({}, "disabled"),
        ({"developer_broker_enabled": True}, "secret_missing_or_too_short"),
        ({"developer_broker_enabled": True, "developer_broker_secret": "short"}, "secret_missing_or_too_short"),
        ({"developer_broker_enabled": True, "developer_broker_secret": "x" * 40}, "pipe_name_missing"),
        (
            {"developer_broker_enabled": True, "developer_broker_secret": "x" * 40, "developer_broker_pipe_name": "myc/test"},
            "pipe_name_invalid",
        ),
        (
            {"developer_broker_enabled": True, "developer_broker_secret": "x" * 40, "developer_broker_pipe_name": "myc-test"},
            "service_sid_missing",
        ),
        pytest.param(
            {
                "developer_broker_enabled": True, "developer_broker_secret": "x" * 40,
                "developer_broker_pipe_name": "myc-test", "developer_broker_service_sid": "S-1-5-21-1-2-3-1001",
            },
            "platform_unsupported",
            marks=pytest.mark.skipif(sys.platform == "win32", reason="fail-closed off Windows only"),
        ),
    ],
)
def test_control_plane_configuration_fails_closed(update, reason):
    from pydantic import SecretStr

    if "developer_broker_secret" in update:
        update = {**update, "developer_broker_secret": SecretStr(update["developer_broker_secret"])}
    config = settings.model_copy(update=update)
    with pytest.raises(BrokerConfigurationError) as denied:
        build_developer_broker_client(config)
    assert denied.value.reason == reason
    assert "x" * 40 not in str(denied.value)


def test_broker_is_optional_and_disabled_by_default():
    assert settings.developer_broker_enabled is False
    assert get_developer_broker_client() is None


def test_secret_must_have_minimum_length():
    with pytest.raises(BrokerConfigurationError):
        BrokerSecret.from_text("")
    with pytest.raises(BrokerConfigurationError):
        BrokerSecret.from_text("x" * 31)
    assert BrokerSecret.from_text("x" * 32)


# --- N. the secret never leaks ------------------------------------------------------------------

def test_secret_never_appears_in_frames_errors_repr_or_logs(secret_text, secret, clock, caplog):
    server = BrokerServer(secret, clock=clock)
    client = BrokerClient(InMemoryBrokerTransport(server), secret, clock=clock)
    outputs = [repr(secret), str(secret), repr(client.__dict__)]
    with caplog.at_level(logging.DEBUG):
        client.health()
        for frame in (signed(secret), b"garbage", signed(BrokerSecret.from_text(new_secret_text()))):
            outputs.append(server.handle_frame(frame).decode())
        server.handle_frame(signed(secret, version=9))
        for error in (BrokerConfigurationError("secret_missing_or_too_short"),):
            outputs.append(str(error))
    outputs.extend(record.getMessage() for record in caplog.records)
    everything = "\n".join(outputs)
    assert secret_text not in everything
    assert secret_text.encode().hex() not in everything
    assert "<redacted>" in repr(secret)


def test_logs_never_contain_signatures_or_payloads(server, secret, caplog):
    frame = signed(secret, payload={"marker": "payload-marker"})
    signature = json.loads(frame)["signature"]
    with caplog.at_level(logging.DEBUG, logger="app.developer_broker"):
        server.handle_frame(frame)
        server.handle_frame(signed(secret))
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert signature not in text
    assert "payload-marker" not in text


# --- O / P. structural guarantees of the boundary ------------------------------------------------

def _python_files():
    return sorted(BROKER_PACKAGE.glob("*.py"))


def _imports(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
    return names


def test_broker_package_is_decoupled_from_erp_frameworks_and_authorities():
    forbidden = (
        "sqlalchemy", "fastapi", "starlette", "pydantic",
        "app.core", "app.models", "app.services", "app.routers", "app.realtime", "app.schemas",
    )
    assert _python_files()
    for path in _python_files():
        for name in _imports(path):
            assert not name.startswith(forbidden), f"{path.name} imports {name}"
            if name.startswith("app."):
                assert name.startswith("app.developer_broker"), f"{path.name} imports {name}"


# Files introduced or touched by DEV-1A (implementation, not docs/tests).
DEV_1A_IMPLEMENTATION = [
    *_python_files(),
    BACKEND / "app/services/developer_broker.py",
    BACKEND / "app/routers/mobile_developer.py",
    BACKEND / "app/schemas/mobile_developer.py",
]

FORBIDDEN_MODULES = {"subprocess", "pty", "multiprocessing", "asyncio.subprocess", "pexpect", "ctypes", "socket"}
FORBIDDEN_OS_CALLS = {"system", "popen", "execv", "execve", "execl", "execlp", "execvp", "spawnl", "spawnv", "startfile", "fork", "posix_spawn"}
FORBIDDEN_TEXT = ("powershell", "pwsh", "cmd.exe")


@pytest.mark.parametrize("path", DEV_1A_IMPLEMENTATION, ids=lambda path: path.name)
def test_dev_1a_implementation_executes_no_processes(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for name in _imports(path):
        assert name.split(".")[0] not in FORBIDDEN_MODULES and name not in FORBIDDEN_MODULES, name
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "os":
            assert node.attr not in FORBIDDEN_OS_CALLS, f"os.{node.attr} in {path.name}"
        if isinstance(node, ast.keyword):
            assert node.arg != "shell", path.name
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert not any(term in node.value.lower() for term in FORBIDDEN_TEXT), path.name
