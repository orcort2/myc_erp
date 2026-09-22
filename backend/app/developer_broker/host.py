"""DEV-1B: MYC Developer Broker process host.

    python -m app.developer_broker.host

A separate process, independent of the ERP: no FastAPI, no SQLAlchemy, no
Mobile auth, no DeveloperSession/JWT, no biometrics, no ``app.realtime`` and
no ``app.core.config``. It reads ONLY its own minimal configuration from the
process environment -- never the backend ``.env`` file, so the ERP's
database URL, JWT secret, Facturama or SMTP credentials are never loaded
into the Broker:

    DEVELOPER_BROKER_PIPE_NAME           logical pipe name (e.g. MYCDeveloperBroker)
    DEVELOPER_BROKER_SECRET              HMAC secret shared with the ERP (>= 32 bytes)
    DEVELOPER_BROKER_CLIENT_SID          SID of the ERP/FastAPI identity (S-1-...)
    DEVELOPER_BROKER_SERVICE_SID         SID of this Broker's own identity (S-1-...)
    DEVELOPER_BROKER_IO_TIMEOUT_SECONDS  per-connection I/O budget (default 5)
    DEVELOPER_BROKER_MAX_CONNECTIONS     concurrent connections, 1..16 (default 4)

Lifecycle: validate configuration and identities -> refuse to run as any
identity other than DEVELOPER_BROKER_SERVICE_SID -> create the FIRST pipe
instance (fails if the name already exists) -> accept connections, one
request/response each -> clean shutdown on Ctrl+C / Ctrl+Break.

No daemonization, no Windows service installation (a later deployment phase
wraps this process as ``MYCDeveloperBroker``). Only ``broker.health`` exists.
Exit codes: 0 clean stop, 2 configuration/identity error, 1 runtime failure.
Failures are logged as fixed reason codes only.
"""

import logging
import os
import signal
import sys
from collections.abc import Mapping
from dataclasses import dataclass

from app.developer_broker.pipe_name import validate_pipe_name
from app.developer_broker.protocol import BrokerConfigurationError, BrokerError, BrokerSecret
from app.developer_broker.server import BrokerServer
from app.developer_broker.windows_pipe import (
    NamedPipeBrokerListener,
    Win32Api,
    load_win32_api,
    loggable_reason,
    validate_identity_sids,
)


logger = logging.getLogger("app.developer_broker.host")

ENVIRONMENT_KEYS = (
    "DEVELOPER_BROKER_PIPE_NAME",
    "DEVELOPER_BROKER_SECRET",
    "DEVELOPER_BROKER_CLIENT_SID",
    "DEVELOPER_BROKER_SERVICE_SID",
    "DEVELOPER_BROKER_IO_TIMEOUT_SECONDS",
    "DEVELOPER_BROKER_MAX_CONNECTIONS",
)

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_CONFIGURATION_ERROR = 2


@dataclass(frozen=True)
class BrokerHostConfig:
    pipe_name: str
    secret: BrokerSecret
    client_sid: str
    service_sid: str
    io_timeout_seconds: float = 5.0
    max_connections: int = 4

    def __repr__(self) -> str:
        return "BrokerHostConfig(<redacted>)"

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> "BrokerHostConfig":
        """Reads exactly ``ENVIRONMENT_KEYS``; anything else in the
        environment is ignored."""
        try:
            io_timeout = float(environ.get("DEVELOPER_BROKER_IO_TIMEOUT_SECONDS", "5"))
        except ValueError:
            raise BrokerConfigurationError("io_timeout_invalid") from None
        if not 0 < io_timeout <= 60:
            raise BrokerConfigurationError("io_timeout_invalid")
        try:
            max_connections = int(environ.get("DEVELOPER_BROKER_MAX_CONNECTIONS", "4"))
        except ValueError:
            raise BrokerConfigurationError("max_connections_invalid") from None
        if not 1 <= max_connections <= 16:
            raise BrokerConfigurationError("max_connections_invalid")
        client_sid = environ.get("DEVELOPER_BROKER_CLIENT_SID", "").strip()
        service_sid = environ.get("DEVELOPER_BROKER_SERVICE_SID", "").strip()
        if not client_sid:
            raise BrokerConfigurationError("client_sid_missing")
        if not service_sid:
            raise BrokerConfigurationError("service_sid_missing")
        return cls(
            pipe_name=validate_pipe_name(environ.get("DEVELOPER_BROKER_PIPE_NAME")),
            secret=BrokerSecret.from_text(environ.get("DEVELOPER_BROKER_SECRET")),
            client_sid=client_sid,
            service_sid=service_sid,
            io_timeout_seconds=io_timeout,
            max_connections=max_connections,
        )


def build_listener(config: BrokerHostConfig, api: Win32Api) -> NamedPipeBrokerListener:
    client_sid, service_sid = validate_identity_sids(api, config.client_sid, config.service_sid)
    listener = NamedPipeBrokerListener(
        BrokerServer(config.secret),
        config.pipe_name,
        client_sid=client_sid,
        service_sid=service_sid,
        io_timeout_seconds=config.io_timeout_seconds,
        max_connections=config.max_connections,
        api=api,
    )
    listener.open()  # identity check + FIRST pipe instance
    return listener


def _install_stop_handlers(stop) -> None:
    def handler(signum, frame) -> None:
        stop()

    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), handler)


def main(environ: Mapping[str, str] | None = None, api: Win32Api | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        config = BrokerHostConfig.from_environ(os.environ if environ is None else environ)
        listener = build_listener(config, api if api is not None else load_win32_api())
    except BrokerConfigurationError as exc:
        logger.error("Developer Broker no inició: code=%s", loggable_reason(exc))
        return EXIT_CONFIGURATION_ERROR
    except BrokerError as exc:
        logger.error("Developer Broker no inició: code=%s", loggable_reason(exc))
        return EXIT_RUNTIME_ERROR

    _install_stop_handlers(listener.shutdown)
    logger.info("Developer Broker escuchando (broker.health)")
    try:
        listener.serve_forever()
    except KeyboardInterrupt:
        listener.shutdown()
    except Exception:  # noqa: BLE001 -- fixed code only, no traceback content
        logger.error("Developer Broker se detuvo: code=runtime_error")
        return EXIT_RUNTIME_ERROR
    logger.info("Developer Broker detenido")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
