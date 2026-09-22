"""DEV-1B: transport framing for stream IPC (Windows Named Pipe).

A stream never guarantees that one read returns one message, so every
Broker frame crosses the pipe as::

    4-byte unsigned big-endian length  +  exactly that many payload bytes

Invariants: ``0 < length <= MAX_FRAME_BYTES``; the length is validated
BEFORE any buffer for the payload is requested; reads are exact; a premature
EOF/broken pipe is ``connection_closed``. Exactly one request and one
response per connection in DEV-1B.

Framing belongs to the transport, not to the Broker protocol: the payload is
the unchanged DEV-1A JSON/HMAC frame, which this module never inspects.
"""

import struct
from collections.abc import Callable

from app.developer_broker.protocol import MAX_FRAME_BYTES, BrokerUnavailableError


LENGTH_PREFIX = struct.Struct(">I")
# Upper bound for a single low-level read request (never larger than a frame).
MAX_READ_CHUNK = MAX_FRAME_BYTES


class FramingError(BrokerUnavailableError):
    """A frame could not be moved across the transport. ``reason`` is always
    one of the fixed identifiers below -- never OS text."""


FRAME_EMPTY = "frame_empty"
FRAME_TOO_LARGE = "frame_too_large"
CONNECTION_CLOSED = "connection_closed"


def encode_length_prefixed(payload: bytes) -> bytes:
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    if not payload:
        raise FramingError(FRAME_EMPTY)
    if len(payload) > MAX_FRAME_BYTES:
        raise FramingError(FRAME_TOO_LARGE)
    return LENGTH_PREFIX.pack(len(payload)) + bytes(payload)


def read_exact(read_some: Callable[[int], bytes], size: int) -> bytes:
    """Reads exactly ``size`` bytes with ``read_some(max_bytes)``, which may
    return fewer bytes than asked and returns ``b""`` on EOF."""
    if size <= 0 or size > MAX_FRAME_BYTES:
        raise FramingError(FRAME_TOO_LARGE if size > 0 else FRAME_EMPTY)
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = read_some(min(remaining, MAX_READ_CHUNK))
        if not chunk:
            raise FramingError(CONNECTION_CLOSED)
        if len(chunk) > remaining:
            # A reader must never hand back more than it was asked for.
            raise FramingError(CONNECTION_CLOSED)
        chunks.append(bytes(chunk))
        remaining -= len(chunk)
    return b"".join(chunks)


def read_length_prefixed(read_some: Callable[[int], bytes]) -> bytes:
    (length,) = LENGTH_PREFIX.unpack(read_exact(read_some, LENGTH_PREFIX.size))
    # Validated before a single payload byte is requested.
    if length == 0:
        raise FramingError(FRAME_EMPTY)
    if length > MAX_FRAME_BYTES:
        raise FramingError(FRAME_TOO_LARGE)
    return read_exact(read_some, length)
