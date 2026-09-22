"""DEV-1A: Developer Control Plane side of the Broker boundary.

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
from app.developer_broker.protocol import BrokerConfigurationError, BrokerError, BrokerSecret
from app.models.developer_session import DeveloperSession
from app.services.audit_logs import write_audit_log


logger = logging.getLogger("app.developer_broker.control_plane")

BROKER_UNAVAILABLE_DETAIL = "Developer Broker no disponible"
# Stable, non-sensitive configuration codes this module raises itself. Any
# other ``reason`` is never logged verbatim (it could carry transport or
# host detail once the Windows adapter exists).
CONFIGURATION_CODES = frozenset(
    {"disabled", "secret_missing_or_too_short", "pipe_name_missing", "named_pipe_adapter_pending", "unknown_transport"}
)


def build_developer_broker_client(config: Settings = settings) -> BrokerClient:
    if not config.developer_broker_enabled:
        raise BrokerConfigurationError("disabled")
    secret = BrokerSecret.from_text(config.developer_broker_secret.get_secret_value())
    if config.developer_broker_transport == "named_pipe":
        if not config.developer_broker_pipe_name.strip():
            raise BrokerConfigurationError("pipe_name_missing")
        # The Windows Named Pipe adapter is DEV-1B: it cannot be validated
        # from macOS and is deliberately not simulated (no TCP fallback).
        raise BrokerConfigurationError("named_pipe_adapter_pending")
    raise BrokerConfigurationError("unknown_transport")


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
