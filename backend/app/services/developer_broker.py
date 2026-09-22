"""DEV-1A/1B: Developer Control Plane side of the Broker boundary.

Builds the ``BrokerClient`` from configuration and runs Broker operations on
behalf of a request that the DEV-0 Developer authority has ALREADY
authorized (live DeveloperSession + explicit granular capability). This
module never authorizes anything itself, and routers never see a transport.

The Broker is optional in this phase: missing/invalid configuration never
breaks ERP startup; it only makes Broker routes fail closed with a generic
503. Configuration problems are logged by code only -- never the secret.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.developer_broker.client import BrokerClient
from app.developer_broker.pipe_name import validate_pipe_name
from app.developer_broker.protocol import BrokerConfigurationError, BrokerError, BrokerSecret
from app.developer_broker.windows_pipe import (
    WindowsNamedPipeTransport,
    Win32Api,
    load_win32_api,
    validate_identity_sids,
)
from app.models.developer_session import DeveloperSession
from app.services.audit_logs import write_audit_log


logger = logging.getLogger("app.developer_broker.control_plane")

BROKER_UNAVAILABLE_DETAIL = "Developer Broker no disponible"
# Stable, non-sensitive configuration codes this module raises itself. Any
# other ``reason`` is never logged verbatim (it could carry transport or
# host detail once the Windows adapter exists).
CONFIGURATION_CODES = frozenset({
    "disabled",
    "secret_missing_or_too_short",
    "unknown_transport",
    "pipe_name_missing",
    "pipe_name_invalid",
    "platform_unsupported",
    "win32_unavailable",
    "service_sid_missing",
    "service_sid_invalid",
    "service_sid_not_allowed",
    "client_sid_invalid",
    "client_sid_not_allowed",
    "sids_not_distinct",
    "identity_unverifiable",
    "client_identity_mismatch",
})


def build_developer_broker_client(config: Settings = settings, api: Win32Api | None = None) -> BrokerClient:
    """Fails closed (``BrokerConfigurationError``) unless the Broker is
    enabled AND fully configured AND this is Windows. There is no other
    transport and no TCP fallback."""
    if not config.developer_broker_enabled:
        raise BrokerConfigurationError("disabled")
    secret = BrokerSecret.from_text(config.developer_broker_secret.get_secret_value())
    if config.developer_broker_transport != "named_pipe":
        raise BrokerConfigurationError("unknown_transport")
    pipe_name = validate_pipe_name(config.developer_broker_pipe_name)
    if not config.developer_broker_service_sid.strip():
        raise BrokerConfigurationError("service_sid_missing")
    win32 = api if api is not None else load_win32_api()  # platform_unsupported off Windows
    if config.developer_broker_client_sid.strip():
        client_sid, _ = validate_identity_sids(
            win32, config.developer_broker_client_sid, config.developer_broker_service_sid
        )
        if win32.current_process_user_sid() != client_sid:
            raise BrokerConfigurationError("client_identity_mismatch")
    transport = WindowsNamedPipeTransport(
        pipe_name, expected_server_sid=config.developer_broker_service_sid, api=win32
    )
    return BrokerClient(transport, secret, timeout_seconds=config.developer_broker_timeout_seconds)


def get_developer_broker_client() -> BrokerClient | None:
    """FastAPI dependency. ``None`` means "not usable"; it never raises, so
    it cannot short-circuit the Developer authority declared before it."""
    try:
        return build_developer_broker_client()
    except BrokerConfigurationError as exc:
        code = exc.reason if exc.reason in CONFIGURATION_CODES else exc.code
        logger.warning("Developer Broker no configurado: code=%s", code)
        return None


def _audit_health(db: Session, record: DeveloperSession, capability: str, outcome: str, error: str | None) -> None:
    # Never the Developer token, the HMAC secret, a signature or a payload.
    write_audit_log(
        db,
        action="developer.broker.health",
        entity="developer_session",
        entity_id=record.id,
        user_id=record.user_id,
        new_values={
            "device_id": record.device_id,
            "mobile_session_id": record.mobile_session_id,
            "capability": capability,
            "outcome": outcome,
            "broker_error": error,
        },
    )


def developer_broker_health(
    db: Session, record: DeveloperSession, capability: str, client: BrokerClient | None
) -> dict:
    """``broker.health`` for an already-authorized Developer request."""
    if client is None:
        _audit_health(db, record, capability, "unavailable", "not_configured")
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=BROKER_UNAVAILABLE_DETAIL)
    try:
        health = client.health()
    except BrokerError as exc:
        # Stable code only: ``exc.reason`` may carry transport detail (DEV-1B).
        logger.warning("Developer Broker health falló: code=%s", exc.code)
        _audit_health(db, record, capability, "unavailable", exc.code)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=BROKER_UNAVAILABLE_DETAIL
        ) from None
    _audit_health(db, record, capability, "ok", None)
    db.commit()
    return {
        "status": health.status,
        "protocol": health.protocol,
        "protocol_version": health.protocol_version,
        "supported_versions": list(health.supported_versions),
        "broker_instance_id": health.instance_id,
        "broker_timestamp_ms": health.timestamp_ms,
        "operations": list(health.operations),
        "features": list(health.features),
    }
