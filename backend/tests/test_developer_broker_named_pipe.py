"""DEV-1B (cross-platform): pipe-name validation, length-prefixed framing,
platform guard, configuration, the Windows adapter's control flow and the
Broker host -- WITHOUT Windows.

The adapter talks to Win32 only through its internal ``Win32Api`` port;
here that port is ``FakeWin32Api``, passed explicitly (no global win32
mocks, nothing patched into ``sys.modules``). These tests prove the
adapter's LOGIC (ordering, fail-closed paths, no write before identity
verification, handles always closed, no OS detail leaks). They do NOT prove
anything about real Windows Named Pipes, DACL enforcement or Win32 identity
APIs -- that is ``test_developer_broker_windows.py``, which only runs on
Windows."""
import ast
import logging
import secrets
import struct
import sys
import threading
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.developer_broker import host as broker_host
from app.developer_broker.client import BrokerClient
from app.developer_broker.framing import (
    CONNECTION_CLOSED,
    FRAME_EMPTY,
    FRAME_TOO_LARGE,
    FramingError,
    encode_length_prefixed,
    read_length_prefixed,
)
from app.developer_broker.pipe_name import PIPE_NAME_MAX_LENGTH, local_pipe_path, validate_pipe_name
from app.developer_broker.protocol import (
    MAX_FRAME_BYTES,
    BrokerConfigurationError,
    BrokerSecret,
    BrokerUnavailableError,
)
from app.developer_broker.server import BrokerServer
from app.developer_broker.windows_pipe import (
    CLIENT_FLAGS,
    CLIENT_PIPE_ACCESS,
    FILE_CREATE_PIPE_INSTANCE,
    FILE_FLAG_FIRST_PIPE_INSTANCE,
    PIPE_REJECT_REMOTE_CLIENTS,
    SECURITY_IDENTIFICATION,
    SECURITY_SQOS_PRESENT,
    SERVER_OPEN_MODE,
    SERVER_PIPE_MODE,
    SERVICE_PIPE_ACCESS,
    NamedPipeBrokerListener,
    WindowsNamedPipeTransport,
    LOGGABLE_REASONS,
    load_win32_api,
    loggable_reason,
    pipe_dacl_entries,
    validate_identity_sids,
)
from app.services.developer_broker import build_developer_broker_client

BACKEND = Path(__file__).resolve().parents[1]
BROKER_PACKAGE = BACKEND / "app" / "developer_broker"
SERVICE_SID = "S-1-5-80-1111111111-2222222222-3333333333-4444444444-555555555"
CLIENT_SID = "S-1-5-21-1000000000-2000000000-3000000000-1001"
IMPOSTOR_SID = "S-1-5-21-1000000000-2000000000-3000000000-1002"
SENSITIVE = "C:\\very\\sensitive\\windows\\path WinError 5 pid=4242"
PIPE = "MYCDeveloperBroker"


# --- fake Win32 port ------------------------------------------------------------------

class FakeHandle:
    def __init__(self, name, inbound=b"", chunk=None):
        self.name = name
        self.inbound = bytearray(inbound)
        self.chunk = chunk
        self.outbound = bytearray()
        self.closed = False
        self.disconnected = False


class FakeWin32Api:
    """Scriptable stand-in for the adapter's Win32 port -- no Windows involved."""

    def __init__(self, *, process_sid=CLIENT_SID, server_sid=SERVICE_SID, client_sid=CLIENT_SID):
        self.process_sid = process_sid
        self.server_sid = server_sid
        self.client_sid = client_sid
        self.events: list[tuple] = []
        self.handles: list[FakeHandle] = []
        self.next_inbound = b""
        self.fail = {}

    def _maybe_fail(self, step):
        if step in self.fail:
            raise self.fail[step]

    def canonical_sid(self, text):
        parts = text.upper().split("-")
        if len(parts) < 3 or parts[0] != "S" or not all(part.isdigit() for part in parts[1:]):
            raise BrokerConfigurationError("sid_invalid")
        return "-".join(parts)

    def current_process_user_sid(self):
        return self.process_sid

    def open_client(self, path, deadline):
        self.events.append(("open", path))
        self._maybe_fail("open")
        handle = FakeHandle("client", self.next_inbound)
        self.handles.append(handle)
        return handle

    def server_process_user_sid(self, handle):
        self.events.append(("server_sid",))
        self._maybe_fail("server_sid")
        return self.server_sid

    def client_user_sid(self, handle):
        self.events.append(("client_sid",))
        return self.client_sid

    def read_some(self, handle, max_bytes, deadline):
        self.events.append(("read", max_bytes))
        self._maybe_fail("read")
        size = min(max_bytes, handle.chunk or max_bytes, len(handle.inbound))
        data = bytes(handle.inbound[:size])
        del handle.inbound[:size]
        return data

    def write_all(self, handle, data, deadline):
        self.events.append(("write", len(data)))
        self._maybe_fail("write")
        handle.outbound.extend(data)

    def create_server(self, path, client_sid, service_sid, *, first, max_instances):
        self.events.append(("create", first))
        self._maybe_fail("create_first" if first else "create_next")
        handle = FakeHandle(f"server-{len(self.handles)}")
        self.handles.append(handle)
        return handle

    def wait_for_client(self, handle, stop, poll_seconds):
        self.events.append(("wait",))
        return True

    def disconnect(self, handle):
        handle.disconnected = True

    def close(self, handle):
        self.events.append(("close", handle.name))
        handle.closed = True


class LoopbackApi(FakeWin32Api):
    """Fake pipe whose far end is a real ``BrokerServer`` (in memory): proves
    the framing + transport + client wiring end to end, not a Named Pipe."""

    def __init__(self, server, **kwargs):
        super().__init__(**kwargs)
        self.server = server

    def write_all(self, handle, data, deadline):
        super().write_all(handle, data, deadline)
        request = read_length_prefixed(_reader(bytes(data)))
        handle.inbound.extend(encode_length_prefixed(self.server.handle_frame(request)))


def _reader(data: bytes, chunk: int | None = None, requested: list | None = None):
    buffer = bytearray(data)

    def read_some(size):
        if requested is not None:
            requested.append(size)
        take = min(size, chunk or size, len(buffer))
        out = bytes(buffer[:take])
        del buffer[:take]
        return out

    return read_some


def framed(payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + payload


# --- pipe name ----------------------------------------------------------------------

@pytest.mark.parametrize("name", ["MYCDeveloperBroker", "myc-dev_broker-2", "Abc", "A" * PIPE_NAME_MAX_LENGTH])
def test_valid_logical_pipe_names(name):
    assert validate_pipe_name(name) == name
    assert local_pipe_path(name) == "\\\\.\\pipe\\" + name


@pytest.mark.parametrize(
    "name, reason",
    [
        ("", "pipe_name_missing"),
        ("   ", "pipe_name_missing"),
        (None, "pipe_name_missing"),
        ("a/b/c", "pipe_name_invalid"),
        ("a\\b", "pipe_name_invalid"),
        ("..", "pipe_name_invalid"),
        ("abc..def", "pipe_name_invalid"),
        ("a.b.c", "pipe_name_invalid"),
        ("abc:def", "pipe_name_invalid"),
        ("NUL", "pipe_name_invalid"),
        ("con", "pipe_name_invalid"),
        ("Aux", "pipe_name_invalid"),
        ("COM1", "pipe_name_invalid"),
        ("lpt9", "pipe_name_invalid"),
        ("\\\\.\\pipe\\MYCDeveloperBroker", "pipe_name_invalid"),
        ("\\\\server\\pipe\\MYCDeveloperBroker", "pipe_name_invalid"),
        ("//server/pipe/x", "pipe_name_invalid"),
        ("Global\\MYCDeveloperBroker", "pipe_name_invalid"),
        ("LOCAL\\MYCDeveloperBroker", "pipe_name_invalid"),
        ("A" * (PIPE_NAME_MAX_LENGTH + 1), "pipe_name_invalid"),
        ("ab", "pipe_name_invalid"),
        ("1abc", "pipe_name_invalid"),
        ("-abc", "pipe_name_invalid"),
        ("has space", "pipe_name_invalid"),
        ("abc\x00def", "pipe_name_invalid"),
        ("abc\ndef", "pipe_name_invalid"),
        ("ñandú", "pipe_name_invalid"),
    ],
)
def test_invalid_pipe_names_are_rejected_not_cleaned(name, reason):
    with pytest.raises(BrokerConfigurationError) as rejected:
        validate_pipe_name(name)
    assert rejected.value.reason == reason


# --- framing ---------------------------------------------------------------------------

@pytest.mark.parametrize("chunk", [None, 1, 3, 7])
def test_framing_round_trip_independent_of_read_boundaries(chunk):
    payload = secrets.token_bytes(5000)
    encoded = encode_length_prefixed(payload)
    assert encoded[:4] == struct.pack(">I", 5000)
    assert read_length_prefixed(_reader(encoded, chunk)) == payload


def test_framing_accepts_max_frame():
    payload = b"x" * MAX_FRAME_BYTES
    assert read_length_prefixed(_reader(encode_length_prefixed(payload), 4096)) == payload


@pytest.mark.parametrize("length", [MAX_FRAME_BYTES + 1, 0xFFFFFFFF])
def test_oversized_prefix_is_rejected_before_reading_payload(length):
    requested = []
    with pytest.raises(FramingError) as rejected:
        read_length_prefixed(_reader(struct.pack(">I", length) + b"x" * 10, requested=requested))
    assert rejected.value.reason == FRAME_TOO_LARGE
    # Only the 4-byte header was ever requested: no buffer sized by the prefix.
    assert sum(requested) == 4


def test_zero_length_prefix_is_rejected():
    with pytest.raises(FramingError) as rejected:
        read_length_prefixed(_reader(struct.pack(">I", 0)))
    assert rejected.value.reason == FRAME_EMPTY


@pytest.mark.parametrize("data", [b"", b"\x00", b"\x00\x00\x01"])
def test_truncated_prefix_is_connection_closed(data):
    with pytest.raises(FramingError) as rejected:
        read_length_prefixed(_reader(data))
    assert rejected.value.reason == CONNECTION_CLOSED


def test_truncated_payload_is_connection_closed():
    with pytest.raises(FramingError) as rejected:
        read_length_prefixed(_reader(struct.pack(">I", 100) + b"x" * 99, chunk=10))
    assert rejected.value.reason == CONNECTION_CLOSED


def test_reader_returning_more_than_requested_is_rejected():
    with pytest.raises(FramingError):
        read_length_prefixed(lambda size: b"\x00" * (size + 1))


def test_encoding_rejects_empty_and_oversized_frames():
    with pytest.raises(FramingError) as empty:
        encode_length_prefixed(b"")
    assert empty.value.reason == FRAME_EMPTY
    with pytest.raises(FramingError) as large:
        encode_length_prefixed(b"x" * (MAX_FRAME_BYTES + 1))
    assert large.value.reason == FRAME_TOO_LARGE
    assert isinstance(large.value, BrokerUnavailableError)


# --- Win32 flags / DACL policy (values, not Windows behaviour) -------------------------

def test_pipe_flags_carry_the_required_protections():
    assert SERVER_PIPE_MODE & PIPE_REJECT_REMOTE_CLIENTS
    assert PIPE_REJECT_REMOTE_CLIENTS == 0x00000008
    assert FILE_FLAG_FIRST_PIPE_INSTANCE == 0x00080000
    # FIRST_PIPE_INSTANCE is added only for the first instance (see create_server).
    assert not SERVER_OPEN_MODE & FILE_FLAG_FIRST_PIPE_INSTANCE
    # The client lets the Broker IDENTIFY it (LocalSystem today), never impersonate it.
    assert CLIENT_FLAGS & SECURITY_SQOS_PRESENT and CLIENT_FLAGS & SECURITY_IDENTIFICATION


def test_dacl_is_exactly_two_minimal_aces():
    assert pipe_dacl_entries(CLIENT_SID, SERVICE_SID) == (
        (SERVICE_SID, SERVICE_PIPE_ACCESS),
        (CLIENT_SID, CLIENT_PIPE_ACCESS),
    )


def test_service_mask_is_exactly_the_duplex_rights_plus_create_instance():
    """P1 regression: every additional CreateNamedPipe instance is access-
    checked for the rights implied by PIPE_ACCESS_DUPLEX (FILE_GENERIC_READ |
    FILE_GENERIC_WRITE | SYNCHRONIZE) plus FILE_CREATE_PIPE_INSTANCE. The old
    0x00120087 lacked FILE_READ_EA, FILE_WRITE_EA and FILE_WRITE_ATTRIBUTES,
    so the second instance would fail. Not extra privilege for convenience."""
    required = {
        "FILE_READ_DATA": 0x0001,
        "FILE_WRITE_DATA": 0x0002,
        "FILE_CREATE_PIPE_INSTANCE": 0x0004,
        "FILE_READ_EA": 0x0008,
        "FILE_WRITE_EA": 0x0010,
        "FILE_READ_ATTRIBUTES": 0x0080,
        "FILE_WRITE_ATTRIBUTES": 0x0100,
        "READ_CONTROL": 0x00020000,
        "SYNCHRONIZE": 0x00100000,
    }
    for name, bit in required.items():
        assert SERVICE_PIPE_ACCESS & bit == bit, name
    assert SERVICE_PIPE_ACCESS == sum(required.values()) == 0x0012019F
    # SDK definitions: FILE_GENERIC_READ 0x00120089, FILE_GENERIC_WRITE 0x00120116.
    assert SERVICE_PIPE_ACCESS == 0x00120089 | 0x00120116
    assert SERVICE_PIPE_ACCESS != 0x00120087  # the insufficient pre-audit mask
    forbidden = {"DELETE": 0x00010000, "WRITE_DAC": 0x00040000, "WRITE_OWNER": 0x00080000, "GENERIC_*": 0xF0000000}
    for name, bits in forbidden.items():
        assert not SERVICE_PIPE_ACCESS & bits, name


def test_client_mask_never_gains_create_pipe_instance():
    # FILE_CREATE_PIPE_INSTANCE shares bit 0x0004 with FILE_APPEND_DATA: it
    # belongs to the Broker only (anti-squatting).
    assert CLIENT_PIPE_ACCESS == 0x00100083
    assert not CLIENT_PIPE_ACCESS & FILE_CREATE_PIPE_INSTANCE
    assert not CLIENT_PIPE_ACCESS & (0xF0000000 | 0x00010000 | 0x00040000 | 0x00080000 | 0x0010 | 0x0100)


# --- identity validation ----------------------------------------------------------

@pytest.mark.parametrize(
    "client, service, reason",
    [
        (CLIENT_SID, "", "service_sid_missing"),
        ("", SERVICE_SID, "client_sid_missing"),
        (CLIENT_SID, "SY", "service_sid_invalid"),          # SDDL alias, not a literal SID
        ("WD", SERVICE_SID, "client_sid_invalid"),
        (CLIENT_SID, "S-1-garbage", "service_sid_invalid"),
        (CLIENT_SID, "S-1-5-18", "service_sid_not_allowed"),  # LocalSystem
        (CLIENT_SID, "S-1-5-19", "service_sid_not_allowed"),  # LocalService (shared)
        (CLIENT_SID, "S-1-5-20", "service_sid_not_allowed"),  # NetworkService (shared)
        (CLIENT_SID, "S-1-1-0", "service_sid_not_allowed"),   # Everyone
        ("S-1-1-0", SERVICE_SID, "client_sid_not_allowed"),
        ("S-1-5-11", SERVICE_SID, "client_sid_not_allowed"),  # Authenticated Users
        ("S-1-5-32-545", SERVICE_SID, "client_sid_not_allowed"),  # Users
        ("S-1-5-32-546", SERVICE_SID, "client_sid_not_allowed"),  # Guests
        ("S-1-5-32-544", SERVICE_SID, "client_sid_not_allowed"),  # Administrators
        (SERVICE_SID, SERVICE_SID, "sids_not_distinct"),
    ],
)
def test_identity_sids_policy(client, service, reason):
    with pytest.raises(BrokerConfigurationError) as rejected:
        validate_identity_sids(FakeWin32Api(), client, service)
    assert rejected.value.reason == reason


def test_localsystem_is_allowed_only_as_the_erp_client_identity():
    """MYCBackend runs as LocalSystem today: it may be the CLIENT SID, never the Broker's."""
    assert validate_identity_sids(FakeWin32Api(), "S-1-5-18", SERVICE_SID) == ("S-1-5-18", SERVICE_SID)


# --- platform guard -----------------------------------------------------------------

@pytest.mark.skipif(sys.platform == "win32", reason="guard for non-Windows platforms")
def test_windows_adapter_fails_closed_off_windows():
    for build in (
        load_win32_api,
        lambda: WindowsNamedPipeTransport(PIPE, expected_server_sid=SERVICE_SID),
        lambda: NamedPipeBrokerListener(object(), PIPE, client_sid=CLIENT_SID, service_sid=SERVICE_SID),
    ):
        with pytest.raises(BrokerConfigurationError) as rejected:
            build()
        assert rejected.value.reason == "platform_unsupported"
    assert "win32pipe" not in sys.modules and "pywintypes" not in sys.modules


# --- FastAPI builder ---------------------------------------------------------------

def _broker_config(**overrides):
    values = {
        "developer_broker_enabled": True,
        "developer_broker_secret": SecretStr(secrets.token_urlsafe(48)),
        "developer_broker_pipe_name": PIPE,
        "developer_broker_service_sid": SERVICE_SID,
        "developer_broker_client_sid": "",
        **overrides,
    }
    return settings.model_copy(update=values)


def test_builder_creates_the_named_pipe_transport_and_nothing_else():
    client = build_developer_broker_client(_broker_config(), api=FakeWin32Api())
    assert isinstance(client, BrokerClient)
    assert isinstance(client._transport, WindowsNamedPipeTransport)  # no TCP/in-memory fallback


@pytest.mark.skipif(sys.platform == "win32", reason="guard for non-Windows platforms")
def test_builder_fails_closed_off_windows_even_when_enabled():
    with pytest.raises(BrokerConfigurationError) as rejected:
        build_developer_broker_client(_broker_config())
    assert rejected.value.reason == "platform_unsupported"


@pytest.mark.parametrize(
    "overrides, reason",
    [
        ({"developer_broker_pipe_name": "\\\\evil\\pipe\\x"}, "pipe_name_invalid"),
        ({"developer_broker_service_sid": ""}, "service_sid_missing"),
        ({"developer_broker_service_sid": "S-1-5-18"}, "service_sid_not_allowed"),
        ({"developer_broker_client_sid": SERVICE_SID}, "sids_not_distinct"),
        ({"developer_broker_client_sid": IMPOSTOR_SID}, "client_identity_mismatch"),
    ],
)
def test_builder_configuration_fails_closed(overrides, reason):
    with pytest.raises(BrokerConfigurationError) as rejected:
        build_developer_broker_client(_broker_config(**overrides), api=FakeWin32Api(process_sid=CLIENT_SID))
    assert rejected.value.reason == reason


def test_builder_accepts_matching_client_identity():
    config = _broker_config(developer_broker_client_sid=CLIENT_SID)
    assert build_developer_broker_client(config, api=FakeWin32Api(process_sid=CLIENT_SID))


# --- client transport (fake port) --------------------------------------------------

def _transport(api):
    return WindowsNamedPipeTransport(PIPE, expected_server_sid=SERVICE_SID, api=api)


def test_transport_verifies_identity_before_writing_then_frames_the_exchange():
    api = FakeWin32Api()
    api.next_inbound = framed(b'{"response":true}')
    assert _transport(api).exchange(b'{"request":true}', timeout_seconds=5) == b'{"response":true}'
    kinds = [event[0] for event in api.events]
    assert kinds.index("server_sid") < kinds.index("write")
    assert kinds[0] == "open" and kinds[-1] == "close"
    assert api.events[0] == ("open", "\\\\.\\pipe\\" + PIPE)
    [handle] = api.handles
    assert bytes(handle.outbound) == framed(b'{"request":true}')
    assert handle.closed


def test_server_identity_mismatch_aborts_before_any_request_byte(caplog):
    api = FakeWin32Api(server_sid=IMPOSTOR_SID)
    with caplog.at_level(logging.DEBUG), pytest.raises(BrokerUnavailableError) as rejected:
        _transport(api).exchange(b"secret-request-bytes", timeout_seconds=5)
    assert rejected.value.reason == "server_identity_mismatch"
    assert not any(event[0] == "write" for event in api.events)
    [handle] = api.handles
    assert handle.outbound == bytearray() and handle.closed
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert IMPOSTOR_SID not in logs and SERVICE_SID not in logs and "reason=server_identity_mismatch" in logs


def test_unverifiable_server_identity_aborts_before_writing():
    api = FakeWin32Api()
    api.fail["server_sid"] = BrokerUnavailableError("server_identity_unverifiable")
    with pytest.raises(BrokerUnavailableError) as rejected:
        _transport(api).exchange(b"x", timeout_seconds=5)
    assert rejected.value.reason == "server_identity_unverifiable"
    assert not any(event[0] == "write" for event in api.events)
    assert api.handles[0].closed


@pytest.mark.parametrize("reason", ["pipe_not_found", "timeout", "access_denied", "pipe_open_failed"])
def test_open_failures_propagate_as_stable_reasons(reason):
    api = FakeWin32Api()
    api.fail["open"] = BrokerUnavailableError(reason)
    with pytest.raises(BrokerUnavailableError) as rejected:
        _transport(api).exchange(b"x", timeout_seconds=5)
    assert rejected.value.reason == reason
    assert api.handles == []


@pytest.mark.parametrize(
    "step, error, reason",
    [
        ("read", BrokerUnavailableError("timeout"), "timeout"),
        ("write", BrokerUnavailableError("connection_closed"), "connection_closed"),
        ("read", OSError(SENSITIVE), "transport_error"),
        ("write", RuntimeError(SENSITIVE), "transport_error"),
    ],
)
def test_io_failures_close_the_handle_and_never_leak_os_detail(step, error, reason, caplog):
    api = FakeWin32Api()
    api.next_inbound = framed(b"{}")
    api.fail[step] = error
    with caplog.at_level(logging.DEBUG), pytest.raises(BrokerUnavailableError) as rejected:
        _transport(api).exchange(b"x", timeout_seconds=5)
    assert rejected.value.reason == reason
    assert api.handles[0].closed
    assert rejected.value.__cause__ is None or SENSITIVE not in str(rejected.value.__cause__)
    assert SENSITIVE not in str(rejected.value)
    assert SENSITIVE not in "\n".join(record.getMessage() for record in caplog.records)


def test_oversized_or_truncated_response_is_rejected_and_handle_closed():
    for inbound, reason in ((struct.pack(">I", MAX_FRAME_BYTES + 1), FRAME_TOO_LARGE), (framed(b"abc")[:-1], CONNECTION_CLOSED)):
        api = FakeWin32Api()
        api.next_inbound = inbound
        with pytest.raises(BrokerUnavailableError) as rejected:
            _transport(api).exchange(b"x", timeout_seconds=5)
        assert rejected.value.reason == reason
        assert api.handles[0].closed


def test_invalid_request_or_timeout_never_touches_the_pipe():
    api = FakeWin32Api()
    with pytest.raises(BrokerUnavailableError):
        _transport(api).exchange(b"x" * (MAX_FRAME_BYTES + 1), timeout_seconds=5)
    with pytest.raises(BrokerUnavailableError):
        _transport(api).exchange(b"x", timeout_seconds=0)
    assert api.events == []


def test_health_end_to_end_through_the_adapter_over_a_fake_pipe():
    secret = BrokerSecret.from_text(secrets.token_urlsafe(48))
    api = LoopbackApi(BrokerServer(secret))
    health = BrokerClient(_transport(api), secret).health()
    assert health.status == "ok" and health.operations == ("broker.health",)
    assert api.handles[0].closed


# --- listener (fake port) --------------------------------------------------------------

def _listener(api, handler=None, **kwargs):
    handler = handler or BrokerServer(BrokerSecret.from_text(secrets.token_urlsafe(48)))
    return NamedPipeBrokerListener(
        handler, PIPE, client_sid=CLIENT_SID, service_sid=SERVICE_SID, api=api, poll_seconds=0.01, **kwargs
    )


class OneShotApi(FakeWin32Api):
    """Delivers exactly one client connection, then asks the listener to stop."""

    def __init__(self, request_bytes, listener_ref, **kwargs):
        super().__init__(process_sid=SERVICE_SID, **kwargs)
        self.request_bytes = request_bytes
        self.listener_ref = listener_ref
        self.served = False

    def wait_for_client(self, handle, stop, poll_seconds):
        self.events.append(("wait",))
        if self.served:
            self.listener_ref[0].shutdown()
            return False
        self.served = True
        handle.inbound.extend(self.request_bytes)
        return True


class RecordingHandler:
    def __init__(self, response=b'{"ok":true}', error=None):
        self.requests = []
        self.response, self.error = response, error

    def handle_frame(self, frame):
        self.requests.append(frame)
        if self.error:
            raise self.error
        return self.response


def _serve_once(request_bytes, handler, **api_kwargs):
    ref = []
    api = OneShotApi(request_bytes, ref, **api_kwargs)
    listener = _listener(api, handler)
    ref.append(listener)
    worker = threading.Thread(target=listener.serve_forever)
    worker.start()
    worker.join(timeout=5)
    assert not worker.is_alive(), "listener did not shut down deterministically"
    return api


def test_listener_refuses_to_run_as_another_identity():
    with pytest.raises(BrokerConfigurationError) as rejected:
        _listener(FakeWin32Api(process_sid=CLIENT_SID)).open()
    assert rejected.value.reason == "service_identity_mismatch"


def test_listener_fails_to_start_when_pipe_name_is_taken():
    api = FakeWin32Api(process_sid=SERVICE_SID)
    api.fail["create_first"] = BrokerConfigurationError("pipe_name_in_use")
    with pytest.raises(BrokerConfigurationError) as rejected:
        _listener(api).open()
    assert rejected.value.reason == "pipe_name_in_use"
    assert api.events == [("create", True)]  # never retried, never renamed


def test_listener_serves_one_request_and_keeps_the_name_owned():
    handler = RecordingHandler()
    api = _serve_once(framed(b'{"req":1}'), handler)
    assert handler.requests == [b'{"req":1}']
    creates = [event for event in api.events if event[0] == "create"]
    assert creates[0] == ("create", True) and creates[1] == ("create", False)
    # The next instance exists BEFORE the connection is served.
    kinds = [event[0] for event in api.events]
    assert kinds.index("create", 1) < kinds.index("client_sid")
    served = api.handles[0]
    assert bytes(served.outbound) == framed(b'{"ok":true}')
    assert served.disconnected and served.closed
    assert all(handle.closed for handle in api.handles)  # pending instance closed at shutdown


def test_listener_drops_unauthorized_client_without_processing():
    handler = RecordingHandler()
    api = _serve_once(framed(b'{"req":1}'), handler, client_sid=IMPOSTOR_SID)
    assert handler.requests == []
    assert api.handles[0].outbound == bytearray() and api.handles[0].closed


@pytest.mark.parametrize(
    "request_bytes",
    [struct.pack(">I", 0xFFFFFFFF), struct.pack(">I", 50) + b"short", b"\x00\x00"],
    ids=["oversized", "truncated-payload", "truncated-prefix"],
)
def test_listener_rejects_bad_frames_and_keeps_running(request_bytes):
    handler = RecordingHandler()
    api = _serve_once(request_bytes, handler)
    assert handler.requests == []
    assert api.handles[0].outbound == bytearray() and api.handles[0].closed


def test_listener_isolates_handler_failures():
    api = _serve_once(framed(b"{}"), RecordingHandler(error=RuntimeError(SENSITIVE)))
    assert api.handles[0].closed and api.handles[0].outbound == bytearray()


# --- Broker host -------------------------------------------------------------------------

HOST_ENV = {
    "DEVELOPER_BROKER_PIPE_NAME": PIPE,
    "DEVELOPER_BROKER_CLIENT_SID": CLIENT_SID,
    "DEVELOPER_BROKER_SERVICE_SID": SERVICE_SID,
}


def test_host_config_reads_only_its_own_keys(monkeypatch):
    secret_text = secrets.token_urlsafe(48)
    environ = {
        **HOST_ENV,
        "DEVELOPER_BROKER_SECRET": secret_text,
        "DATABASE_URL": "postgresql://should-not-be-read",
        "SECRET_KEY": "erp-jwt-secret",
        "FACTURAMA_PASSWORD": "nope",
    }
    config = broker_host.BrokerHostConfig.from_environ(environ)
    assert config.pipe_name == PIPE and config.io_timeout_seconds == 5 and config.max_connections == 4
    assert secret_text not in repr(config)
    assert set(broker_host.ENVIRONMENT_KEYS) == {
        "DEVELOPER_BROKER_PIPE_NAME", "DEVELOPER_BROKER_SECRET", "DEVELOPER_BROKER_CLIENT_SID",
        "DEVELOPER_BROKER_SERVICE_SID", "DEVELOPER_BROKER_IO_TIMEOUT_SECONDS", "DEVELOPER_BROKER_MAX_CONNECTIONS",
    }


@pytest.mark.parametrize(
    "overrides, code",
    [
        ({"DEVELOPER_BROKER_SECRET": ""}, "secret_missing_or_too_short"),
        ({"DEVELOPER_BROKER_PIPE_NAME": "..\\evil"}, "pipe_name_invalid"),
        ({"DEVELOPER_BROKER_CLIENT_SID": ""}, "client_sid_missing"),
        ({"DEVELOPER_BROKER_SERVICE_SID": ""}, "service_sid_missing"),
        ({"DEVELOPER_BROKER_IO_TIMEOUT_SECONDS": "abc"}, "io_timeout_invalid"),
        ({"DEVELOPER_BROKER_IO_TIMEOUT_SECONDS": "0"}, "io_timeout_invalid"),
        ({"DEVELOPER_BROKER_MAX_CONNECTIONS": "99"}, "max_connections_invalid"),
    ],
)
def test_host_invalid_configuration_exits_2_with_code_only(overrides, code, caplog):
    secret_text = secrets.token_urlsafe(48)
    environ = {**HOST_ENV, "DEVELOPER_BROKER_SECRET": secret_text, **overrides}
    with caplog.at_level(logging.DEBUG):
        assert broker_host.main(environ, api=FakeWin32Api(process_sid=SERVICE_SID)) == broker_host.EXIT_CONFIGURATION_ERROR
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert f"code={code}" in logs and secret_text not in logs


@pytest.mark.parametrize(
    "api_kwargs, fail, code",
    [
        ({"process_sid": CLIENT_SID}, None, "service_identity_mismatch"),
        ({"process_sid": SERVICE_SID}, BrokerConfigurationError("pipe_name_in_use"), "pipe_name_in_use"),
    ],
)
def test_host_refuses_to_start(api_kwargs, fail, code, caplog):
    api = FakeWin32Api(**api_kwargs)
    if fail:
        api.fail["create_first"] = fail
    environ = {**HOST_ENV, "DEVELOPER_BROKER_SECRET": secrets.token_urlsafe(48)}
    with caplog.at_level(logging.DEBUG):
        assert broker_host.main(environ, api=api) == broker_host.EXIT_CONFIGURATION_ERROR
    assert f"code={code}" in "\n".join(record.getMessage() for record in caplog.records)


def test_host_rejects_same_identity_for_erp_and_broker():
    environ = {**HOST_ENV, "DEVELOPER_BROKER_CLIENT_SID": SERVICE_SID, "DEVELOPER_BROKER_SECRET": secrets.token_urlsafe(48)}
    assert broker_host.main(environ, api=FakeWin32Api(process_sid=SERVICE_SID)) == broker_host.EXIT_CONFIGURATION_ERROR


@pytest.mark.skipif(sys.platform == "win32", reason="guard for non-Windows platforms")
def test_host_fails_closed_off_windows(caplog):
    environ = {**HOST_ENV, "DEVELOPER_BROKER_SECRET": secrets.token_urlsafe(48)}
    with caplog.at_level(logging.DEBUG):
        assert broker_host.main(environ) == broker_host.EXIT_CONFIGURATION_ERROR
    assert "code=platform_unsupported" in "\n".join(record.getMessage() for record in caplog.records)


def test_host_builds_a_listener_with_validated_identities():
    config = broker_host.BrokerHostConfig.from_environ({**HOST_ENV, "DEVELOPER_BROKER_SECRET": secrets.token_urlsafe(48)})
    api = FakeWin32Api(process_sid=SERVICE_SID)
    listener = broker_host.build_listener(config, api)
    assert isinstance(listener, NamedPipeBrokerListener)
    assert api.events == [("create", True)]


# --- log sanitization -----------------------------------------------------------

SENSITIVE_REASON = "C:\\sensitive\\path WinError 5"


@pytest.mark.parametrize("step", ["open", "server_sid", "read", "write"])
def test_transport_logs_never_carry_a_raw_reason(step, caplog):
    api = FakeWin32Api()
    api.next_inbound = framed(b"{}")
    api.fail[step] = BrokerUnavailableError(SENSITIVE_REASON)
    with caplog.at_level(logging.DEBUG), pytest.raises(BrokerUnavailableError):
        _transport(api).exchange(b"x", timeout_seconds=5)
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert SENSITIVE_REASON not in logs and "sensitive" not in logs and "WinError" not in logs
    assert "reason=unavailable" in logs  # falls back to the stable code


def test_listener_and_host_logs_never_carry_a_raw_reason(caplog):
    class LeakyApi(OneShotApi):
        def client_user_sid(self, handle):
            raise BrokerUnavailableError(SENSITIVE_REASON)

    ref = []
    api = LeakyApi(framed(b"{}"), ref)
    listener = _listener(api, RecordingHandler())
    ref.append(listener)
    with caplog.at_level(logging.DEBUG):
        worker = threading.Thread(target=listener.serve_forever)
        worker.start()
        worker.join(timeout=5)
        startup = FakeWin32Api(process_sid=SERVICE_SID)
        startup.fail["create_first"] = BrokerConfigurationError(SENSITIVE_REASON)
        environ = {**HOST_ENV, "DEVELOPER_BROKER_SECRET": secrets.token_urlsafe(48)}
        assert broker_host.main(environ, api=startup) == broker_host.EXIT_CONFIGURATION_ERROR
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert SENSITIVE_REASON not in logs and "WinError" not in logs
    assert "reason=unavailable" in logs and "code=not_configured" in logs


def test_unknown_reason_and_code_log_as_unrecognized():
    from app.developer_broker.protocol import BrokerError

    assert loggable_reason(BrokerError(SENSITIVE_REASON, SENSITIVE_REASON)) == "unrecognized"
    assert loggable_reason(OSError(SENSITIVE_REASON)) == "unrecognized"
    assert loggable_reason(BrokerUnavailableError("timeout")) == "timeout"


def test_every_reason_the_package_raises_is_loggable():
    """Keeps LOGGABLE_REASONS in sync with the codes actually raised, so real
    diagnostics never degrade to 'unrecognized'."""
    raised = set()
    constants = {}
    for path in BROKER_PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = node.value.value
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"BrokerUnavailableError", "BrokerConfigurationError", "FramingError", "BrokerResponseError"}
                and node.args
            ):
                argument = node.args[0]
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    raised.add(argument.value)
                elif isinstance(argument, ast.Name) and argument.id in constants:
                    raised.add(constants[argument.id])
    transport_and_config = {code for code in raised if code not in {"invalid_health_result", "request_id_mismatch", "stale_response"}}
    assert transport_and_config, "scan found nothing"
    assert transport_and_config <= LOGGABLE_REASONS, transport_and_config - LOGGABLE_REASONS


# --- pywin32 module ownership (Windows-found regression) ------------------------

# Where each pywin32 name ACTUALLY lives (pywin32 sources: win32pipe.i,
# win32security.i, win32file.i, win32event.i, win32api.i, pywintypes).
# Found on real Windows: ImpersonateNamedPipeClient was called through
# win32pipe (AttributeError) instead of win32security. Every name the
# adapter uses must be listed here with its owner module.
PYWIN32_OWNERSHIP = {
    "security": {
        "ImpersonateNamedPipeClient", "RevertToSelf", "OpenThreadToken", "OpenProcessToken",
        "GetTokenInformation", "TokenUser", "ConvertStringSidToSid", "ConvertSidToStringSid",
        "ACL", "ACL_REVISION", "SECURITY_DESCRIPTOR", "SECURITY_ATTRIBUTES",
    },
    "pipe": {"CreateNamedPipe", "ConnectNamedPipe", "DisconnectNamedPipe", "WaitNamedPipe", "GetNamedPipeServerProcessId"},
    "file": {"CreateFile", "ReadFile", "WriteFile", "GetOverlappedResult", "CancelIo", "AllocateReadBuffer"},
    "event": {"CreateEvent", "WaitForSingleObject"},
    "api": {"OpenProcess", "GetCurrentProcess", "GetCurrentThread"},
    "types": {"error", "OVERLAPPED"},
}


def _pywin32_uses():
    tree = ast.parse((BROKER_PACKAGE / "windows_pipe.py").read_text(encoding="utf-8"))
    [port] = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == "_PyWin32Api"]
    uses = set()
    for node in ast.walk(port):
        # self.<module>.<Name>
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "self"
            and node.value.attr in PYWIN32_OWNERSHIP
        ):
            uses.add((node.value.attr, node.attr))
        # getattr(self.<module>, "<Name>", ...)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and isinstance(node.args[0], ast.Attribute)
            and isinstance(node.args[0].value, ast.Name)
            and node.args[0].value.id == "self"
            and isinstance(node.args[1], ast.Constant)
        ):
            uses.add((node.args[0].attr, node.args[1].value))
    return uses


def test_impersonate_named_pipe_client_is_resolved_from_win32security():
    uses = _pywin32_uses()
    assert ("security", "ImpersonateNamedPipeClient") in uses
    assert ("pipe", "ImpersonateNamedPipeClient") not in uses
    assert {("security", "RevertToSelf"), ("security", "OpenThreadToken"), ("security", "GetTokenInformation")} <= uses


def test_every_pywin32_name_is_used_through_its_owner_module():
    uses = _pywin32_uses()
    assert uses, "scan found no pywin32 usage"
    owner = {name: module for module, names in PYWIN32_OWNERSHIP.items() for name in names}
    wrong = {(module, name) for module, name in uses if name in owner and owner[name] != module}
    unknown = {(module, name) for module, name in uses if name not in owner and not name.startswith("_")}
    assert not wrong, f"pywin32 names used through the wrong module: {wrong}"
    assert not unknown, f"new pywin32 names need an explicit owner in PYWIN32_OWNERSHIP: {unknown}"


# --- client identity normalization (real _PyWin32Api logic, fake modules) ------------

import traceback  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from app.developer_broker.windows_pipe import _PyWin32Api  # noqa: E402


class FakeWinError(Exception):
    """Stand-in for pywintypes.error (passed explicitly, never via sys.modules)."""


class FakeToken:
    def __init__(self):
        self.closed = False

    def Close(self):
        self.closed = True


class FakeSecurity:
    TokenUser = 1

    def __init__(self, fail=None, error=None):
        self.fail, self.error = fail, error
        self.calls = []
        self.token = FakeToken()

    def _step(self, name):
        self.calls.append(name)
        if self.fail == name:
            raise self.error

    def ImpersonateNamedPipeClient(self, handle):
        self._step("impersonate")

    def OpenThreadToken(self, thread, access, open_as_self):
        self._step("open_thread_token")
        assert open_as_self is True
        return self.token

    def GetTokenInformation(self, token, kind):
        self._step("get_token_information")
        return ("PySID", 0)

    def ConvertSidToStringSid(self, sid):
        self._step("convert_sid")
        return CLIENT_SID

    def RevertToSelf(self):
        self._step("revert")


def _port(security):
    modules = SimpleNamespace(
        types=SimpleNamespace(error=FakeWinError),
        api=SimpleNamespace(GetCurrentThread=lambda: -2),
        event=None, file=None, pipe=SimpleNamespace(), security=security,
    )
    return _PyWin32Api(modules)


def _assert_no_leak(exc):
    assert SENSITIVE not in str(exc) and SENSITIVE not in repr(exc)
    assert exc.__cause__ is None
    assert exc.__context__ is None or exc.__suppress_context__
    assert SENSITIVE not in "".join(traceback.format_exception(exc))


def test_client_identity_success_reverts_exactly_once():
    security = FakeSecurity()
    assert _port(security).client_user_sid(object()) == CLIENT_SID
    assert security.calls == ["impersonate", "open_thread_token", "get_token_information", "convert_sid", "revert"]
    assert security.token.closed


def test_win32pipe_has_no_say_in_client_identity():
    # The port's win32pipe stand-in has NO ImpersonateNamedPipeClient (as on
    # real Windows); the lookup must still work because it goes to win32security.
    assert _port(FakeSecurity()).client_user_sid(object()) == CLIENT_SID


@pytest.mark.parametrize(
    "fail, error",
    [
        ("impersonate", FakeWinError(5, "ImpersonateNamedPipeClient", SENSITIVE)),
        ("impersonate", AttributeError(SENSITIVE)),
        ("impersonate", RuntimeError(SENSITIVE)),
    ],
    ids=["winerror", "attributeerror", "unexpected"],
)
def test_impersonation_failure_is_normalized_and_never_reverts(fail, error):
    """Not impersonating -> nothing to revert: RevertToSelf is called ZERO times."""
    security = FakeSecurity(fail=fail, error=error)
    with pytest.raises(BrokerUnavailableError) as rejected:
        _port(security).client_user_sid(object())
    assert rejected.value.reason == "client_identity_unverifiable"
    _assert_no_leak(rejected.value)
    assert security.calls == ["impersonate"]
    assert security.calls.count("revert") == 0


@pytest.mark.parametrize(
    "fail, error",
    [
        ("open_thread_token", FakeWinError(1346, "OpenThreadToken", SENSITIVE)),
        ("open_thread_token", RuntimeError(SENSITIVE)),
        ("get_token_information", FakeWinError(87, "GetTokenInformation", SENSITIVE)),
        ("get_token_information", RuntimeError(SENSITIVE)),
        ("convert_sid", FakeWinError(1337, "ConvertSidToStringSid", SENSITIVE)),
        ("convert_sid", TypeError(SENSITIVE)),
    ],
    ids=["winerror-token", "unexpected-token", "winerror-tokeninfo", "unexpected-tokeninfo", "winerror-convert", "unexpected-convert"],
)
def test_lookup_failure_after_impersonation_reverts_exactly_once(fail, error):
    security = FakeSecurity(fail=fail, error=error)
    with pytest.raises(BrokerUnavailableError) as rejected:
        _port(security).client_user_sid(object())
    assert rejected.value.reason == "client_identity_unverifiable"
    _assert_no_leak(rejected.value)
    assert security.calls[0] == "impersonate"
    assert security.calls.count("revert") == 1 and security.calls[-1] == "revert"
    if fail != "open_thread_token":
        assert security.token.closed  # token cleanup even when the lookup fails


@pytest.mark.parametrize("error", [FakeWinError(1, "RevertToSelf", SENSITIVE), RuntimeError(SENSITIVE)])
def test_revert_to_self_failure_is_its_own_code(error):
    security = FakeSecurity(fail="revert", error=error)
    with pytest.raises(BrokerUnavailableError) as rejected:
        _port(security).client_user_sid(object())
    assert rejected.value.reason == "revert_to_self_failed"
    _assert_no_leak(rejected.value)
    assert security.calls == ["impersonate", "open_thread_token", "get_token_information", "convert_sid", "revert"]


def test_revert_failure_wins_over_lookup_failure_with_a_single_attempt():
    class DoubleFailure(FakeSecurity):
        def GetTokenInformation(self, token, kind):
            self.calls.append("get_token_information")
            raise RuntimeError(SENSITIVE)

    security = DoubleFailure(fail="revert", error=FakeWinError(1, "RevertToSelf", SENSITIVE))
    with pytest.raises(BrokerUnavailableError) as rejected:
        _port(security).client_user_sid(object())
    assert rejected.value.reason == "revert_to_self_failed"
    _assert_no_leak(rejected.value)
    assert security.calls.count("revert") == 1
    assert security.token.closed


class IdentityPortApi(OneShotApi):
    """Listener fake whose client identity lookup runs the REAL
    _PyWin32Api.client_user_sid logic over fake security primitives."""

    def __init__(self, request_bytes, ref, security):
        super().__init__(request_bytes, ref)
        self.identity_port = _port(security)

    def client_user_sid(self, handle):
        self.events.append(("client_sid",))
        return self.identity_port.client_user_sid(handle)


def _serve_with_identity(security, caplog):
    ref = []
    api = IdentityPortApi(framed(b'{"req":1}'), ref, security)
    handler = RecordingHandler()
    listener = _listener(api, handler)
    ref.append(listener)
    with caplog.at_level(logging.DEBUG):
        worker = threading.Thread(target=listener.serve_forever)
        worker.start()
        worker.join(timeout=5)
    assert not worker.is_alive()
    return api, handler, listener, "\n".join(record.getMessage() for record in caplog.records)


def test_unexpected_identity_error_is_controlled_through_the_listener(caplog):
    api, handler, listener, logs = _serve_with_identity(
        FakeSecurity(fail="get_token_information", error=RuntimeError(SENSITIVE)), caplog
    )
    assert handler.requests == []
    assert api.handles[0].outbound == bytearray() and api.handles[0].closed
    assert "reason=client_identity_unverifiable" in logs
    assert "connection_failed" not in logs  # no longer falls into the generic handler
    assert SENSITIVE not in logs


def test_revert_failure_stops_the_listener_fail_closed(caplog):
    api, handler, listener, logs = _serve_with_identity(
        FakeSecurity(fail="revert", error=FakeWinError(1, "RevertToSelf", SENSITIVE)), caplog
    )
    assert handler.requests == []
    assert listener._stop.is_set()
    assert "reason=revert_to_self_failed" in logs and SENSITIVE not in logs


def test_controlled_identity_error_from_the_port_stays_controlled(caplog):
    class ControlledApi(OneShotApi):
        def client_user_sid(self, handle):
            raise BrokerUnavailableError("client_identity_unverifiable")

    ref = []
    api = ControlledApi(framed(b"{}"), ref)
    handler = RecordingHandler()
    listener = _listener(api, handler)
    ref.append(listener)
    with caplog.at_level(logging.DEBUG):
        worker = threading.Thread(target=listener.serve_forever)
        worker.start()
        worker.join(timeout=5)
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert handler.requests == [] and "reason=client_identity_unverifiable" in logs
    # A normal identity rejection never triggers the fail-closed stop of a failed revert.
    assert "revert_to_self_failed" not in logs and "se detiene" not in logs


# --- structural scans ---------------------------------------------------------------------

def _module_imports(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
    return names


def _transitive_app_imports(module: str, seen=None) -> set[str]:
    seen = set() if seen is None else seen
    if module in seen:
        return seen
    seen.add(module)
    path = BACKEND / (module.replace(".", "/") + ".py")
    if not path.exists():
        path = BACKEND / module.replace(".", "/") / "__init__.py"
    for name in _module_imports(path):
        if name.startswith("app"):
            _transitive_app_imports(name, seen)
    return seen


def test_host_import_closure_is_broker_only():
    closure = _transitive_app_imports("app.developer_broker.host")
    assert closure and all(name == "app" or name.startswith("app.developer_broker") for name in closure), closure
    third_party = set()
    for module in closure:
        path = BACKEND / (module.replace(".", "/") + ".py")
        if path.exists():
            third_party |= {name for name in _module_imports(path) if not name.startswith("app")}
    forbidden = {"sqlalchemy", "fastapi", "starlette", "pydantic", "pydantic_settings", "dotenv", "jose", "passlib"}
    assert not {name.split(".")[0] for name in third_party} & forbidden
    # pywin32 is only touched lazily inside the adapter's port.
    assert {name for name in third_party if name.startswith(("win32", "pywintypes"))} <= {
        "win32api", "win32event", "win32file", "win32pipe", "win32security", "pywintypes",
    }


NETWORK_MODULES = {"socket", "socketserver", "http", "ssl", "selectors", "asyncio", "urllib", "xmlrpc", "ftplib", "smtplib", "multiprocessing"}
NETWORK_TEXT = ("127.0.0.1", "localhost", "0.0.0.0", "tcp://", "http://", "https://", "::1")


@pytest.mark.parametrize("path", sorted(BROKER_PACKAGE.glob("*.py")), ids=lambda path: path.name)
def test_broker_package_opens_no_network_listener_or_tcp_fallback(path):
    for name in _module_imports(path):
        assert name.split(".")[0] not in NETWORK_MODULES, f"{path.name} imports {name}"
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert not any(term in node.value.lower() for term in NETWORK_TEXT), path.name
