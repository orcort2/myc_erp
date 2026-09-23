"""DEV-1B: Windows Named Pipe adapter (client transport + server listener).

Three independent layers, each with its own guarantee:

- DACL (server side, mandatory): WHO may open the pipe. An explicit DACL
  with exactly two ACEs -- the ERP/FastAPI identity and the Broker service
  identity, both configured as canonical SIDs. Never Everyone, Authenticated
  Users, Users, Guests or Administrators; never the default DACL.
- Server identity verification (client side): that FastAPI never hands a
  request to an impostor pipe server. Before writing ANY byte the client
  resolves the server PID (``GetNamedPipeServerProcessId``), opens that
  process with ``PROCESS_QUERY_LIMITED_INFORMATION``, reads ``TokenUser`` and
  compares the SID with the configured Broker service SID. Mismatch or
  failure -> handle closed, nothing written, ``server_identity_mismatch`` /
  ``server_identity_unverifiable``.
- HMAC (DEV-1A, end to end): authenticity/integrity of every protocol
  message, independent of the pipe.

Defence in depth on the server: after reading the (size-bounded) request
frame -- Windows only allows ``ImpersonateNamedPipeClient`` once data has
been read -- the listener impersonates the client at IDENTIFICATION level,
reads its ``TokenUser`` SID, reverts, and drops the connection without
processing anything if it is not the configured client SID. This is the
same identity the DACL already enforces, not a second auth architecture.

Anti-squatting: the first instance is created with
``FILE_FLAG_FIRST_PIPE_INSTANCE`` (if the name exists, the Broker FAILS TO
START: ``pipe_name_in_use``; it never connects to, replaces or renames it),
and the listener always creates the next instance before handing the
current one to a worker, so the name is never left unowned while serving.
Every instance rejects remote clients (``PIPE_REJECT_REMOTE_CLIENTS``).

The client opens the pipe with ``SECURITY_SQOS_PRESENT |
SECURITY_IDENTIFICATION``: the ERP backend runs as LocalSystem today, and
the Broker must be able to IDENTIFY it but never IMPERSONATE it.

The client desired access and the client ACE never include
``FILE_APPEND_DATA``/``GENERIC_WRITE``: on a pipe that bit is
``FILE_CREATE_PIPE_INSTANCE``, which would let the ERP identity create its
own server instances (squatting). Only the Broker service ACE carries it.

pywin32 is imported lazily and only on Windows (``load_win32_api``): this
module imports everywhere, and any use outside Windows fails closed with
``platform_unsupported``. Every Win32 failure is mapped to a fixed reason
identifier; WinError text, paths, PIDs, SIDs and handles never leave this
module (``raise ... from None``) and are never logged: every log line goes
through ``loggable_reason``, which only emits codes from ``LOGGABLE_REASONS``.
"""

import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Protocol

from app.developer_broker.framing import encode_length_prefixed, read_length_prefixed
from app.developer_broker.pipe_name import local_pipe_path
from app.developer_broker.protocol import (
    MAX_FRAME_BYTES,
    BrokerConfigurationError,
    BrokerError,
    BrokerUnavailableError,
)
from app.developer_broker.transport import FrameHandler


logger = logging.getLogger("app.developer_broker.windows_pipe")

# --- Win32 constants (SDK values; kept local so their meaning is explicit) ----
PIPE_ACCESS_DUPLEX = 0x00000003
FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
FILE_FLAG_OVERLAPPED = 0x40000000
PIPE_TYPE_BYTE = 0x00000000
PIPE_READMODE_BYTE = 0x00000000
PIPE_WAIT = 0x00000000
PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
OPEN_EXISTING = 3
SECURITY_SQOS_PRESENT = 0x00100000
SECURITY_IDENTIFICATION = 0x00010000  # SecurityIdentification << 16

FILE_READ_DATA = 0x0001
FILE_WRITE_DATA = 0x0002
FILE_CREATE_PIPE_INSTANCE = 0x0004  # == FILE_APPEND_DATA on files
FILE_READ_EA = 0x0008
FILE_WRITE_EA = 0x0010
FILE_READ_ATTRIBUTES = 0x0080
FILE_WRITE_ATTRIBUTES = 0x0100
DELETE = 0x00010000
READ_CONTROL = 0x00020000
WRITE_DAC = 0x00040000
WRITE_OWNER = 0x00080000
SYNCHRONIZE = 0x00100000
GENERIC_ACCESS_BITS = 0xF0000000  # GENERIC_READ/WRITE/EXECUTE/ALL
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008

WAIT_OBJECT_0 = 0x00000000
ERROR_FILE_NOT_FOUND = 2
ERROR_ACCESS_DENIED = 5
ERROR_BROKEN_PIPE = 109
ERROR_SEM_TIMEOUT = 121
ERROR_PIPE_BUSY = 231
ERROR_NO_DATA = 232
ERROR_PIPE_NOT_CONNECTED = 233
ERROR_PIPE_CONNECTED = 535
ERROR_IO_PENDING = 997
_PEER_GONE = frozenset({ERROR_BROKEN_PIPE, ERROR_NO_DATA, ERROR_PIPE_NOT_CONNECTED})

SERVER_PIPE_MODE = PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS
SERVER_OPEN_MODE = PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED
CLIENT_FLAGS = FILE_FLAG_OVERLAPPED | SECURITY_SQOS_PRESENT | SECURITY_IDENTIFICATION
PIPE_BUFFER_BYTES = MAX_FRAME_BYTES + 4

# Client: read/write data, read attributes (pipe server PID query),
# synchronize -- and NEVER FILE_CREATE_PIPE_INSTANCE (== FILE_APPEND_DATA),
# so the ERP identity can never create a squatting server instance.
CLIENT_PIPE_ACCESS = FILE_READ_DATA | FILE_WRITE_DATA | FILE_READ_ATTRIBUTES | SYNCHRONIZE

# Service: exactly FILE_GENERIC_READ | FILE_GENERIC_WRITE, spelled out as
# specific rights (0x0012019F). This is NOT extra privilege for convenience:
# every additional CreateNamedPipe instance is access-checked against this
# DACL for the rights implied by the PIPE_ACCESS_DUPLEX open mode
# (FILE_GENERIC_READ | FILE_GENERIC_WRITE | SYNCHRONIZE) plus
# FILE_CREATE_PIPE_INSTANCE -- which on a pipe is the FILE_APPEND_DATA bit
# of FILE_GENERIC_WRITE and belongs to the Broker only. Without the EA and
# write-attribute bits, the second instance fails. No WRITE_DAC,
# WRITE_OWNER, DELETE or GENERIC_* bits.
FILE_GENERIC_READ_RIGHTS = READ_CONTROL | FILE_READ_DATA | FILE_READ_ATTRIBUTES | FILE_READ_EA | SYNCHRONIZE
FILE_GENERIC_WRITE_RIGHTS = (
    READ_CONTROL | FILE_WRITE_DATA | FILE_WRITE_ATTRIBUTES | FILE_WRITE_EA | FILE_CREATE_PIPE_INSTANCE | SYNCHRONIZE
)
SERVICE_PIPE_ACCESS = FILE_GENERIC_READ_RIGHTS | FILE_GENERIC_WRITE_RIGHTS

# Broad or shared identities that may never be one of the two pipe identities.
BROAD_SIDS = frozenset({
    "S-1-1-0",        # Everyone
    "S-1-2-0",        # Local
    "S-1-3-0",        # Creator Owner
    "S-1-5-2",        # Network
    "S-1-5-4",        # Interactive
    "S-1-5-6",        # Service (every service)
    "S-1-5-7",        # Anonymous
    "S-1-5-11",       # Authenticated Users
    "S-1-5-113",      # Local account
    "S-1-5-114",      # Local account and member of Administrators
    "S-1-5-32-544",   # Administrators
    "S-1-5-32-545",   # Users
    "S-1-5-32-546",   # Guests
    "S-1-5-32-547",   # Power Users
    "S-1-5-32-555",   # Remote Desktop Users
})
# The Broker needs a DEDICATED least-privilege identity: never LocalSystem,
# and never the shared LocalService/NetworkService accounts.
SHARED_SERVICE_SIDS = frozenset({"S-1-5-18", "S-1-5-19", "S-1-5-20"})


# --- log sanitization ----------------------------------------------------------

# The only reason identifiers this boundary ever writes to a log. Anything
# else (a future reason that might carry WinError text, a path, a PID, a SID
# or a handle) is logged as "unrecognized" instead of verbatim.
LOGGABLE_REASONS = frozenset({
    # transport / connection
    "pipe_not_found", "timeout", "access_denied", "pipe_open_failed",
    "server_identity_mismatch", "server_identity_unverifiable",
    "client_identity_mismatch", "client_identity_unverifiable", "revert_to_self_failed",
    "connection_closed", "frame_empty", "frame_too_large", "io_failed",
    "transport_error", "transport_unavailable", "accept_failed", "pipe_create_failed",
    # configuration / startup
    "platform_unsupported", "win32_unavailable", "pipe_name_missing", "pipe_name_invalid",
    "pipe_name_in_use", "sid_invalid", "service_sid_missing", "service_sid_invalid",
    "service_sid_not_allowed", "client_sid_missing", "client_sid_invalid",
    "client_sid_not_allowed", "sids_not_distinct", "identity_unverifiable",
    "service_identity_mismatch", "secret_missing_or_too_short",
    "io_timeout_invalid", "max_connections_invalid",
    # generic BrokerError codes
    "unavailable", "not_configured", "invalid_response",
})


def loggable_reason(exc: BaseException) -> str:
    """A stable, known code for ``exc`` -- never its raw text."""
    for candidate in (getattr(exc, "reason", None), getattr(exc, "code", None)):
        if isinstance(candidate, str) and candidate in LOGGABLE_REASONS:
            return candidate
    return "unrecognized"


# --- identity policy (pure) ---------------------------------------------------

def pipe_dacl_entries(client_sid: str, service_sid: str) -> tuple[tuple[str, int], ...]:
    """The exact ACEs of the pipe DACL: two access-allowed entries, nothing else."""
    return ((service_sid, SERVICE_PIPE_ACCESS), (client_sid, CLIENT_PIPE_ACCESS))


def _canonical(api: "Win32Api", value: str | None, missing: str, invalid: str) -> str:
    text = (value or "").strip()
    if not text:
        raise BrokerConfigurationError(missing)
    # Only literal SIDs; SDDL aliases ("WD", "SY", ...) are not accepted.
    if not text.upper().startswith("S-1-"):
        raise BrokerConfigurationError(invalid)
    try:
        return api.canonical_sid(text)
    except BrokerConfigurationError:
        raise BrokerConfigurationError(invalid) from None


def validate_service_sid(api: "Win32Api", service_sid: str | None) -> str:
    sid = _canonical(api, service_sid, "service_sid_missing", "service_sid_invalid")
    if sid in BROAD_SIDS or sid in SHARED_SERVICE_SIDS:
        raise BrokerConfigurationError("service_sid_not_allowed")
    return sid


def validate_identity_sids(
    api: "Win32Api", client_sid: str | None, service_sid: str | None, *, require_distinct: bool = True
) -> tuple[str, str]:
    """Deployment policy: two DISTINCT identities (ERP != Broker). The host
    and the FastAPI builder -- the only production entry points -- always
    require it; the listener alone does not, so the adapter can be exercised
    under a single Windows account in integration tests."""
    service = validate_service_sid(api, service_sid)
    client = _canonical(api, client_sid, "client_sid_missing", "client_sid_invalid")
    if client in BROAD_SIDS:
        raise BrokerConfigurationError("client_sid_not_allowed")
    if require_distinct and client == service:
        raise BrokerConfigurationError("sids_not_distinct")
    return client, service


# --- Win32 port -------------------------------------------------------------------

class Win32Api(Protocol):
    """Internal port over the few pywin32 calls the adapter needs. Every
    method raises ``BrokerError`` with a fixed reason, never a raw OS error."""

    def canonical_sid(self, text: str) -> str: ...
    def current_process_user_sid(self) -> str: ...
    def open_client(self, path: str, deadline: float) -> Any: ...
    def server_process_user_sid(self, handle: Any) -> str: ...
    def client_user_sid(self, handle: Any) -> str: ...
    def read_some(self, handle: Any, max_bytes: int, deadline: float) -> bytes: ...
    def write_all(self, handle: Any, data: bytes, deadline: float) -> None: ...
    def create_server(self, path: str, client_sid: str, service_sid: str, *, first: bool, max_instances: int) -> Any: ...
    def wait_for_client(self, handle: Any, stop: threading.Event, poll_seconds: float) -> bool: ...
    def disconnect(self, handle: Any) -> None: ...
    def close(self, handle: Any) -> None: ...


def _remaining_ms(deadline: float) -> int:
    return max(0, int((deadline - time.monotonic()) * 1000))


class _PyWin32Api:
    def __init__(self, modules: Any = None) -> None:
        """``modules`` is only an explicit seam for cross-platform tests (an
        object with ``types, api, event, file, pipe, security``); production
        always imports the real pywin32 modules here."""
        if modules is None:
            import pywintypes
            import win32api
            import win32event
            import win32file
            import win32pipe
            import win32security

            self.types, self.api, self.event = pywintypes, win32api, win32event
            self.file, self.pipe, self.security = win32file, win32pipe, win32security
        else:
            self.types, self.api, self.event = modules.types, modules.api, modules.event
            self.file, self.pipe, self.security = modules.file, modules.pipe, modules.security

    # identities -----------------------------------------------------------
    def canonical_sid(self, text: str) -> str:
        try:
            sid = self.security.ConvertStringSidToSid(text)
            if not sid.IsValid():
                raise BrokerConfigurationError("sid_invalid")
            return self.security.ConvertSidToStringSid(sid)
        except self.types.error:
            raise BrokerConfigurationError("sid_invalid") from None

    def _token_user_sid(self, token: Any) -> str:
        try:
            sid, _attributes = self.security.GetTokenInformation(token, self.security.TokenUser)
            return self.security.ConvertSidToStringSid(sid)
        finally:
            token.Close()

    def current_process_user_sid(self) -> str:
        try:
            return self._token_user_sid(
                self.security.OpenProcessToken(self.api.GetCurrentProcess(), TOKEN_QUERY)
            )
        except self.types.error:
            raise BrokerConfigurationError("identity_unverifiable") from None

    def server_process_user_sid(self, handle: Any) -> str:
        get_server_pid = getattr(self.pipe, "GetNamedPipeServerProcessId", None)
        if get_server_pid is None:
            raise BrokerUnavailableError("server_identity_unverifiable")
        try:
            process = self.api.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, get_server_pid(handle))
            try:
                return self._token_user_sid(self.security.OpenProcessToken(process, TOKEN_QUERY))
            finally:
                process.Close()
        except self.types.error:
            raise BrokerUnavailableError("server_identity_unverifiable") from None

    def client_user_sid(self, handle: Any) -> str:
        """SID of the pipe client, read at IDENTIFICATION level.

        Identity boundary: ANY failure (pywintypes.error or anything else,
        e.g. a wrong pywin32 attribute) becomes ``client_identity_unverifiable``;
        nothing raw escapes. ``ImpersonateNamedPipeClient``, ``OpenThreadToken``,
        ``GetTokenInformation`` and ``RevertToSelf`` all live in
        ``win32security`` (not ``win32pipe``).

        ``RevertToSelf`` runs only if impersonation SUCCEEDED, and then exactly
        once (``finally``), even if the token/SID lookup fails. If it fails the
        caller gets ``revert_to_self_failed`` and must not reuse the thread."""
        try:
            self.security.ImpersonateNamedPipeClient(handle)
        except Exception:  # noqa: BLE001 -- not impersonating: nothing to revert
            raise BrokerUnavailableError("client_identity_unverifiable") from None
        sid: str | None = None
        try:
            sid = self._token_user_sid(
                self.security.OpenThreadToken(self.api.GetCurrentThread(), TOKEN_QUERY, True)
            )
        except Exception:  # noqa: BLE001 -- normalized below, never logged raw
            sid = None
        finally:
            try:
                self.security.RevertToSelf()
            except Exception:  # noqa: BLE001
                raise BrokerUnavailableError("revert_to_self_failed") from None
        if not isinstance(sid, str) or not sid:
            raise BrokerUnavailableError("client_identity_unverifiable")
        return sid

    # client ---------------------------------------------------------------
    def open_client(self, path: str, deadline: float) -> Any:
        while True:
            try:
                return self.file.CreateFile(
                    path, CLIENT_PIPE_ACCESS, 0, None, OPEN_EXISTING, CLIENT_FLAGS, None
                )
            except self.types.error as exc:
                if exc.winerror == ERROR_FILE_NOT_FOUND:
                    raise BrokerUnavailableError("pipe_not_found") from None
                if exc.winerror == ERROR_ACCESS_DENIED:
                    raise BrokerUnavailableError("access_denied") from None
                if exc.winerror != ERROR_PIPE_BUSY:
                    raise BrokerUnavailableError("pipe_open_failed") from None
            remaining = _remaining_ms(deadline)
            if remaining <= 0:
                raise BrokerUnavailableError("timeout")
            try:
                self.pipe.WaitNamedPipe(path, remaining)  # never 0: 0 means "default wait"
            except self.types.error as exc:
                if exc.winerror == ERROR_FILE_NOT_FOUND:
                    raise BrokerUnavailableError("pipe_not_found") from None
                if exc.winerror == ERROR_SEM_TIMEOUT:
                    raise BrokerUnavailableError("timeout") from None
                raise BrokerUnavailableError("pipe_open_failed") from None

    # overlapped I/O with a real deadline ----------------------------------
    def _overlapped(self) -> tuple[Any, Any]:
        overlapped = self.types.OVERLAPPED()
        event = self.event.CreateEvent(None, True, False, None)
        overlapped.hEvent = event
        return overlapped, event

    def _cancel(self, handle: Any, overlapped: Any) -> None:
        try:
            self.file.CancelIo(handle)
            self.file.GetOverlappedResult(handle, overlapped, True)  # wait for the cancellation
        except self.types.error:
            pass

    def _complete(self, handle: Any, overlapped: Any, event: Any, deadline: float) -> int:
        if self.event.WaitForSingleObject(event, _remaining_ms(deadline)) != WAIT_OBJECT_0:
            self._cancel(handle, overlapped)
            raise BrokerUnavailableError("timeout")
        try:
            return self.file.GetOverlappedResult(handle, overlapped, False)
        except self.types.error as exc:
            if exc.winerror in _PEER_GONE:
                return 0
            raise BrokerUnavailableError("io_failed") from None

    def read_some(self, handle: Any, max_bytes: int, deadline: float) -> bytes:
        if not 0 < max_bytes <= MAX_FRAME_BYTES:
            raise BrokerUnavailableError("io_failed")
        overlapped, event = self._overlapped()
        try:
            buffer = self.file.AllocateReadBuffer(max_bytes)
            try:
                self.file.ReadFile(handle, buffer, overlapped)
            except self.types.error as exc:
                if exc.winerror in _PEER_GONE:
                    return b""
                raise BrokerUnavailableError("io_failed") from None
            return bytes(buffer[: self._complete(handle, overlapped, event, deadline)])
        finally:
            event.Close()

    def write_all(self, handle: Any, data: bytes, deadline: float) -> None:
        view = memoryview(data)
        offset = 0
        while offset < len(view):
            overlapped, event = self._overlapped()
            try:
                try:
                    self.file.WriteFile(handle, bytes(view[offset:]), overlapped)
                except self.types.error as exc:
                    if exc.winerror in _PEER_GONE:
                        raise BrokerUnavailableError("connection_closed") from None
                    raise BrokerUnavailableError("io_failed") from None
                written = self._complete(handle, overlapped, event, deadline)
            finally:
                event.Close()
            if written <= 0:
                raise BrokerUnavailableError("connection_closed")
            offset += written

    # server -----------------------------------------------------------------
    def _security_attributes(self, client_sid: str, service_sid: str) -> Any:
        acl = self.security.ACL()
        for sid, access in pipe_dacl_entries(client_sid, service_sid):
            acl.AddAccessAllowedAce(self.security.ACL_REVISION, access, self.security.ConvertStringSidToSid(sid))
        descriptor = self.security.SECURITY_DESCRIPTOR()
        descriptor.SetSecurityDescriptorOwner(self.security.ConvertStringSidToSid(service_sid), False)
        descriptor.SetSecurityDescriptorDacl(True, acl, False)  # explicit DACL, never defaulted
        attributes = self.security.SECURITY_ATTRIBUTES()
        attributes.SECURITY_DESCRIPTOR = descriptor
        attributes.bInheritHandle = False
        return attributes

    def create_server(self, path: str, client_sid: str, service_sid: str, *, first: bool, max_instances: int) -> Any:
        open_mode = SERVER_OPEN_MODE | (FILE_FLAG_FIRST_PIPE_INSTANCE if first else 0)
        try:
            return self.pipe.CreateNamedPipe(
                path, open_mode, SERVER_PIPE_MODE, max_instances,
                PIPE_BUFFER_BYTES, PIPE_BUFFER_BYTES, 0,
                self._security_attributes(client_sid, service_sid),
            )
        except self.types.error as exc:
            if first and exc.winerror in (ERROR_ACCESS_DENIED, ERROR_PIPE_BUSY):
                raise BrokerConfigurationError("pipe_name_in_use") from None
            raise BrokerUnavailableError("pipe_create_failed") from None

    def wait_for_client(self, handle: Any, stop: threading.Event, poll_seconds: float) -> bool:
        overlapped, event = self._overlapped()
        try:
            try:
                result = self.pipe.ConnectNamedPipe(handle, overlapped)
            except self.types.error as exc:
                if exc.winerror == ERROR_PIPE_CONNECTED:
                    return True
                raise BrokerUnavailableError("accept_failed") from None
            if result == ERROR_PIPE_CONNECTED:
                return True
            while not stop.is_set():
                if self.event.WaitForSingleObject(event, int(poll_seconds * 1000)) == WAIT_OBJECT_0:
                    try:
                        self.file.GetOverlappedResult(handle, overlapped, False)
                        return True
                    except self.types.error as exc:
                        if exc.winerror == ERROR_PIPE_CONNECTED:
                            return True
                        raise BrokerUnavailableError("accept_failed") from None
            self._cancel(handle, overlapped)
            return False
        finally:
            event.Close()

    def disconnect(self, handle: Any) -> None:
        try:
            self.pipe.DisconnectNamedPipe(handle)
        except self.types.error:
            pass

    def close(self, handle: Any) -> None:
        try:
            handle.Close()
        except self.types.error:
            pass


def load_win32_api() -> Win32Api:
    """The real pywin32 port -- Windows only; fails closed everywhere else."""
    if sys.platform != "win32":
        raise BrokerConfigurationError("platform_unsupported")
    try:
        return _PyWin32Api()
    except ImportError:
        raise BrokerConfigurationError("win32_unavailable") from None


# --- client transport ----------------------------------------------------------

class WindowsNamedPipeTransport:
    """``BrokerTransport`` over ``\\\\.\\pipe\\<name>``: one connection, one
    request, one response per ``exchange``."""

    def __init__(self, pipe_name: str, *, expected_server_sid: str, api: Win32Api | None = None) -> None:
        self._path = local_pipe_path(pipe_name)
        self._api = api if api is not None else load_win32_api()
        self._expected_server_sid = validate_service_sid(self._api, expected_server_sid)

    def exchange(self, frame: bytes, *, timeout_seconds: float) -> bytes:
        if timeout_seconds <= 0:
            raise BrokerUnavailableError("timeout")
        payload = encode_length_prefixed(frame)  # validated before touching the pipe
        deadline = time.monotonic() + timeout_seconds
        try:
            handle = self._api.open_client(self._path, deadline)
        except BrokerError as exc:
            logger.warning("Developer Broker pipe no disponible: reason=%s", loggable_reason(exc))
            raise
        try:
            # Identity FIRST: not a single request byte reaches an unverified server.
            if self._api.server_process_user_sid(handle) != self._expected_server_sid:
                raise BrokerUnavailableError("server_identity_mismatch")
            self._api.write_all(handle, payload, deadline)
            return read_length_prefixed(lambda size: self._api.read_some(handle, size, deadline))
        except BrokerError as exc:
            logger.warning("Developer Broker pipe falló: reason=%s", loggable_reason(exc))
            raise
        except Exception:  # noqa: BLE001 -- never leak an OS/pywin32 message
            logger.warning("Developer Broker pipe falló: reason=transport_error")
            raise BrokerUnavailableError("transport_error") from None
        finally:
            self._api.close(handle)


# --- server listener -------------------------------------------------------------

class NamedPipeBrokerListener:
    """Accepts one connection at a time per instance; each connection carries
    exactly one request and one response and is then closed. Connections are
    served by a bounded worker pool (``max_connections``) so the listener is
    not structurally single-client, without any multiplexing."""

    def __init__(
        self,
        handler: FrameHandler,
        pipe_name: str,
        *,
        client_sid: str,
        service_sid: str,
        io_timeout_seconds: float = 5.0,
        max_connections: int = 4,
        poll_seconds: float = 0.25,
        api: Win32Api | None = None,
    ) -> None:
        if io_timeout_seconds <= 0 or not 1 <= max_connections <= 16:
            raise ValueError("invalid listener limits")
        self._handler = handler
        self._path = local_pipe_path(pipe_name)
        self._api = api if api is not None else load_win32_api()
        self._client_sid, self._service_sid = validate_identity_sids(
            self._api, client_sid, service_sid, require_distinct=False
        )
        self._io_timeout_seconds = io_timeout_seconds
        self._max_connections = max_connections
        self._poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._slots = threading.BoundedSemaphore(max_connections)
        self._pending: Any = None

    def _create_instance(self, *, first: bool) -> Any:
        return self._api.create_server(
            self._path, self._client_sid, self._service_sid,
            first=first, max_instances=self._max_connections + 1,
        )

    def open(self) -> None:
        """Creates the FIRST instance. Fails (``pipe_name_in_use``) if the name
        already exists, and refuses to run under any identity other than the
        configured Broker service SID."""
        if self._pending is not None:
            return
        if self._api.current_process_user_sid() != self._service_sid:
            raise BrokerConfigurationError("service_identity_mismatch")
        self._pending = self._create_instance(first=True)

    def shutdown(self) -> None:
        self._stop.set()

    def _acquire_slot(self) -> bool:
        while not self._stop.is_set():
            if self._slots.acquire(timeout=self._poll_seconds):
                return True
        return False

    def serve_forever(self) -> None:
        self.open()
        executor = ThreadPoolExecutor(max_workers=self._max_connections, thread_name_prefix="myc-broker-conn")
        try:
            while not self._stop.is_set():
                try:
                    if not self._api.wait_for_client(self._pending, self._stop, self._poll_seconds):
                        continue
                except BrokerError as exc:
                    logger.warning("Developer Broker accept falló: reason=%s", loggable_reason(exc))
                    self._api.disconnect(self._pending)
                    continue
                connection = self._pending
                # Own the name BEFORE serving: never a moment with no instance.
                self._pending = None
                try:
                    self._pending = self._create_instance(first=False)
                except BrokerError as exc:
                    logger.error("Developer Broker no pudo crear instancia: reason=%s", loggable_reason(exc))
                    self._stop.set()
                if not self._acquire_slot():
                    self._release(connection)
                    break
                try:
                    future = executor.submit(self._serve_connection, connection)
                except RuntimeError:
                    self._slots.release()
                    self._release(connection)
                    break
                future.add_done_callback(lambda _future: self._slots.release())
        finally:
            if self._pending is not None:
                self._api.close(self._pending)
                self._pending = None
            executor.shutdown(wait=True)  # workers are bounded by io_timeout_seconds

    def _release(self, handle: Any) -> None:
        self._api.disconnect(handle)
        self._api.close(handle)

    def _await_peer_close(self, handle: Any, deadline: float) -> None:
        """DisconnectNamedPipe discards unread data, so wait (bounded) for the
        client to read the response and close its end."""
        try:
            while self._api.read_some(handle, 1, deadline):
                pass
        except BrokerError:
            pass

    def _serve_connection(self, handle: Any) -> None:
        deadline = time.monotonic() + self._io_timeout_seconds
        try:
            request = read_length_prefixed(lambda size: self._api.read_some(handle, size, deadline))
            if self._api.client_user_sid(handle) != self._client_sid:
                raise BrokerUnavailableError("client_identity_mismatch")
            response = self._handler.handle_frame(request)
            self._api.write_all(handle, encode_length_prefixed(response), deadline)
            self._await_peer_close(handle, deadline)
        except BrokerError as exc:
            logger.warning("Developer Broker conexión rechazada: reason=%s", loggable_reason(exc))
            if exc.reason == "revert_to_self_failed":
                # This worker thread may still be impersonating the client: stop
                # accepting so it never serves another connection (fail closed).
                logger.error("Developer Broker se detiene: reason=revert_to_self_failed")
                self._stop.set()
        except Exception:  # noqa: BLE001 -- one connection never takes the listener down
            logger.error("Developer Broker conexión falló: reason=connection_failed")
        finally:
            self._release(handle)
