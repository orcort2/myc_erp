"""DEV-1A: the Broker transport port.

The contract (``protocol``) is transport-independent: a transport only
moves one opaque request frame to the Broker and one response frame back.
It never interprets, signs or verifies frames -- authentication is end to
end between ``BrokerClient`` and ``BrokerServer``.

Adapters:

- ``InMemoryBrokerTransport`` -- IMPLEMENTED. Hands the frame to a
  ``BrokerServer`` in the same process. For tests and local development of
  the contract only; it is NOT a production transport and FastAPI's
  configuration cannot select it.
- Windows Named Pipe -- TARGET, NOT IMPLEMENTED (DEV-1B). Local-only IPC
  protected by the pipe's OS ACL (only the ERP service identity may
  connect) plus the HMAC authentication of the contract. It cannot be
  validated from macOS, so it is deliberately not simulated here. There is
  no TCP/loopback fallback: a port is never opened as a substitute.
"""

from typing import Protocol

from app.developer_broker.protocol import BrokerUnavailableError


class BrokerTransport(Protocol):
    def exchange(self, frame: bytes, *, timeout_seconds: float) -> bytes:
        """Sends one request frame and returns the Broker's response frame.
        Must raise ``BrokerUnavailableError`` (never a raw OS error) when
        the Broker cannot be reached or does not answer in time."""


class FrameHandler(Protocol):
    def handle_frame(self, frame: bytes) -> bytes: ...


class InMemoryBrokerTransport:
    def __init__(self, server: FrameHandler) -> None:
        self._server = server

    def exchange(self, frame: bytes, *, timeout_seconds: float) -> bytes:
        if timeout_seconds <= 0:
            raise BrokerUnavailableError("timeout")
        return self._server.handle_frame(bytes(frame))
