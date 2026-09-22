"""DEV-1B (Windows only): the adapter against REAL Windows Named Pipes,
DACLs and Win32 identity APIs through pywin32.

Skipped on every other platform -- a skip here is NOT a pass. The listener
runs in a thread of the test process (no child processes are spawned), so
both pipe identities are the current Windows account; that is why these
tests construct the listener directly (the host/FastAPI "distinct SIDs"
deployment policy is covered by the cross-platform suite). The
"separate process" check is the manual host run described in
docs/architecture/MOBILE_DEVELOPER_BROKER.md."""
import secrets
import sys
import threading
import time
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="requires Windows Named Pipes and pywin32 (Windows only)"
)

from app.developer_broker.client import BrokerClient  # noqa: E402
from app.developer_broker.framing import encode_length_prefixed  # noqa: E402
from app.developer_broker.pipe_name import local_pipe_path  # noqa: E402
from app.developer_broker.protocol import (  # noqa: E402
    BrokerConfigurationError,
    BrokerError,
    BrokerSecret,
    BrokerUnavailableError,
)
from app.developer_broker.server import BrokerServer  # noqa: E402
from app.developer_broker.windows_pipe import (  # noqa: E402
    BROAD_SIDS,
    CLIENT_PIPE_ACCESS,
    SERVICE_PIPE_ACCESS,
    SHARED_SERVICE_SIDS,
    NamedPipeBrokerListener,
    WindowsNamedPipeTransport,
    load_win32_api,
)

# A syntactically valid SID that is not the test account (need not exist).
OTHER_SID = "S-1-5-21-1111111111-2222222222-3333333333-1001"


@pytest.fixture
def win():
    api = load_win32_api()
    me = api.current_process_user_sid()
    if me in SHARED_SERVICE_SIDS or me in BROAD_SIDS:
        pytest.skip("test account is LocalSystem/LocalService/NetworkService; the Broker identity may not be")
    return api, me


@pytest.fixture
def pipe_name():
    return f"MYCBrokerTest{uuid.uuid4().hex[:16]}"


class SpyHandler:
    def __init__(self, inner):
        self.inner = inner
        self.requests = []

    def handle_frame(self, frame):
        self.requests.append(frame)
        return self.inner.handle_frame(frame)


@pytest.fixture
def running_broker(win, pipe_name):
    api, me = win
    secret = BrokerSecret.from_text(secrets.token_urlsafe(48))
    spy = SpyHandler(BrokerServer(secret))
    listener = NamedPipeBrokerListener(
        spy, pipe_name, client_sid=me, service_sid=me, io_timeout_seconds=3, poll_seconds=0.05, api=api
    )
    listener.open()
    worker = threading.Thread(target=listener.serve_forever, daemon=True)
    worker.start()
    yield api, me, pipe_name, secret, spy, listener
    listener.shutdown()
    worker.join(timeout=10)
    assert not worker.is_alive(), "listener did not shut down"


def _client(api, name, expected_sid, secret, timeout=5):
    return BrokerClient(
        WindowsNamedPipeTransport(name, expected_server_sid=expected_sid, api=api), secret, timeout_seconds=timeout
    )


# A / B / J
def test_health_over_a_real_named_pipe(running_broker):
    api, me, name, secret, spy, _ = running_broker
    health = _client(api, name, me, secret).health()
    assert health.status == "ok" and health.operations == ("broker.health",)
    assert len(spy.requests) == 1  # the request really crossed the pipe to the listener
    assert _client(api, name, me, secret).health().status == "ok"  # listener keeps serving
    assert len(spy.requests) == 2


class RecordingApi:
    """Real pywin32 port with every ``create_server`` outcome recorded."""

    def __init__(self, inner):
        self._inner = inner
        self.creates = []

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def create_server(self, path, client_sid, service_sid, *, first, max_instances):
        try:
            handle = self._inner.create_server(path, client_sid, service_sid, first=first, max_instances=max_instances)
        except BrokerError as exc:
            self.creates.append((first, exc.reason))
            raise
        self.creates.append((first, "ok"))
        return handle


def test_subsequent_create_named_pipe_instances_succeed_under_the_explicit_dacl(win, pipe_name):
    """Invariant: subsequent CreateNamedPipe instance succeeds under the
    explicit DACL. Every additional instance is access-checked against the
    pipe DACL for the PIPE_ACCESS_DUPLEX rights + FILE_CREATE_PIPE_INSTANCE,
    so with the pre-audit service mask 0x00120087 (no FILE_READ_EA /
    FILE_WRITE_EA / FILE_WRITE_ATTRIBUTES) the listener cannot create its
    second instance and the second exchange fails. This test must fail if
    that mask is restored."""
    api, me = win
    recording = RecordingApi(api)
    secret = BrokerSecret.from_text(secrets.token_urlsafe(48))
    listener = NamedPipeBrokerListener(
        BrokerServer(secret), pipe_name, client_sid=me, service_sid=me,
        io_timeout_seconds=3, poll_seconds=0.05, api=recording,
    )
    listener.open()
    assert recording.creates == [(True, "ok")]  # first instance, FILE_FLAG_FIRST_PIPE_INSTANCE
    worker = threading.Thread(target=listener.serve_forever, daemon=True)
    worker.start()
    try:
        client = _client(api, pipe_name, me, secret)
        for _ in range(3):  # >= 2 consecutive exchanges, each forcing a new instance
            assert client.health().status == "ok"
        subsequent = [outcome for first, outcome in recording.creates if not first]
        assert len(subsequent) >= 3
        assert all(outcome == "ok" for outcome in subsequent), recording.creates
        # And an extra instance of the same name, created directly by the
        # Broker identity while the listener owns the name, also succeeds.
        extra = api.create_server(local_pipe_path(pipe_name), me, me, first=False, max_instances=5)
        api.close(extra)
    finally:
        listener.shutdown()
        worker.join(timeout=10)
    assert not worker.is_alive()


def test_fastapi_builder_reaches_the_real_pipe(running_broker):
    from pydantic import SecretStr

    from app.core.config import settings
    from app.services.developer_broker import build_developer_broker_client

    api, me, name, secret, _, _ = running_broker
    config = settings.model_copy(update={
        "developer_broker_enabled": True,
        "developer_broker_secret": SecretStr(secret._key.decode()),
        "developer_broker_pipe_name": name,
        "developer_broker_service_sid": me,
    })
    assert build_developer_broker_client(config).health().status == "ok"


# C
def test_wrong_hmac_is_rejected_over_the_pipe(running_broker):
    api, me, name, _, spy, _ = running_broker
    wrong = BrokerSecret.from_text(secrets.token_urlsafe(48))
    with pytest.raises(BrokerError):
        _client(api, name, me, wrong).health()
    assert len(spy.requests) == 1  # it reached the Broker and was rejected there


# D
def test_missing_pipe_fails_fast_and_controlled(win, pipe_name):
    api, me = win
    started = time.monotonic()
    with pytest.raises(BrokerUnavailableError) as rejected:
        _client(api, pipe_name, me, BrokerSecret.from_text(secrets.token_urlsafe(48))).health()
    assert rejected.value.reason == "pipe_not_found"
    assert time.monotonic() - started < 2


def _raw_server(api, me, name, client_sid=None):
    return api.create_server(local_pipe_path(name), client_sid or me, me, first=True, max_instances=1)


# E
def test_real_timeout_when_server_never_answers(win, pipe_name):
    api, me = win
    handle = _raw_server(api, me, pipe_name)
    stop = threading.Event()
    accepted = threading.Thread(target=api.wait_for_client, args=(handle, stop, 0.05), daemon=True)
    accepted.start()
    try:
        started = time.monotonic()
        with pytest.raises(BrokerUnavailableError) as rejected:
            WindowsNamedPipeTransport(pipe_name, expected_server_sid=me, api=api).exchange(b"{}", timeout_seconds=0.5)
        elapsed = time.monotonic() - started
        assert rejected.value.reason == "timeout"
        assert 0.4 <= elapsed < 3
    finally:
        stop.set()
        accepted.join(timeout=5)
        api.close(handle)


# F
@pytest.mark.parametrize(
    "raw", [b"\xff\xff\xff\xff", encode_length_prefixed(b"x" * 100)[:20]], ids=["oversized", "truncated"]
)
def test_bad_frames_are_dropped_and_listener_keeps_serving(running_broker, raw):
    api, me, name, secret, spy, _ = running_broker
    deadline = time.monotonic() + 3
    handle = api.open_client(local_pipe_path(name), deadline)
    try:
        api.write_all(handle, raw, deadline)
        if raw.startswith(b"\xff"):
            assert api.read_some(handle, 1, deadline) == b""  # server closed without a response
    finally:
        api.close(handle)
    assert spy.requests == []
    assert _client(api, name, me, secret).health().status == "ok"


# G
def test_second_first_instance_with_same_name_fails(running_broker):
    api, me, name, _, _, _ = running_broker
    impostor = NamedPipeBrokerListener(
        BrokerServer(BrokerSecret.from_text(secrets.token_urlsafe(48))), name,
        client_sid=me, service_sid=me, api=api,
    )
    with pytest.raises(BrokerConfigurationError) as rejected:
        impostor.open()
    assert rejected.value.reason == "pipe_name_in_use"


# H
@pytest.mark.skip(
    reason=(
        "requires a second Windows host (or an SMB client path) to attempt a REMOTE open; a local "
        "failure to open \\\\localhost\\pipe\\... cannot distinguish PIPE_REJECT_REMOTE_CLIENTS from a "
        "stopped Server service. The flag itself is asserted in test_developer_broker_named_pipe.py."
    )
)
def test_remote_clients_are_rejected():  # pragma: no cover
    raise AssertionError("not executable locally")


# I
def test_pipe_dacl_is_exactly_the_two_configured_identities(win, pipe_name):
    api, me = win
    import win32security

    handle = _raw_server(api, me, pipe_name, client_sid=OTHER_SID)
    try:
        descriptor = win32security.GetSecurityInfo(
            handle, win32security.SE_KERNEL_OBJECT, win32security.DACL_SECURITY_INFORMATION
        )
        dacl = descriptor.GetSecurityDescriptorDacl()
        aces = []
        for index in range(dacl.GetAceCount()):
            (ace_type, _flags), mask, sid = dacl.GetAce(index)
            aces.append((ace_type, win32security.ConvertSidToStringSid(sid), mask))
        assert aces == [
            (win32security.ACCESS_ALLOWED_ACE_TYPE, me, SERVICE_PIPE_ACCESS),
            (win32security.ACCESS_ALLOWED_ACE_TYPE, OTHER_SID, CLIENT_PIPE_ACCESS),
        ]
        assert not {sid for _, sid, _ in aces} & {"S-1-1-0", "S-1-5-11", "S-1-5-32-545", "S-1-5-32-546"}
    finally:
        api.close(handle)


# K
def test_wrong_expected_server_sid_aborts_before_writing(win, pipe_name):
    api, me = win
    handle = _raw_server(api, me, pipe_name)
    received = []
    stop = threading.Event()

    def server_side():
        if api.wait_for_client(handle, stop, 0.05):
            try:
                received.append(api.read_some(handle, 1, time.monotonic() + 3))
            except BrokerError as exc:
                received.append(exc.reason)

    worker = threading.Thread(target=server_side, daemon=True)
    worker.start()
    try:
        with pytest.raises(BrokerUnavailableError) as rejected:
            WindowsNamedPipeTransport(pipe_name, expected_server_sid=OTHER_SID, api=api).exchange(
                b"request-bytes-that-must-not-leave", timeout_seconds=3
            )
        assert rejected.value.reason == "server_identity_mismatch"
        worker.join(timeout=5)
        # The client connected and closed without writing: EOF, zero bytes.
        assert received == [b""]
    finally:
        stop.set()
        worker.join(timeout=5)
        api.close(handle)
