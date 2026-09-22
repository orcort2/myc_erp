"""DEV-1A: GET /api/mobile/v1/developer/broker/health -- the only Developer
surface of the Broker boundary. Gated by the DEV-0 authority (live
DeveloperSession + explicit ``developer.system.read``), never by the generic
ERP permission guard; reaches the Broker only through BrokerClient."""
import json
import logging
import secrets

import pytest
from sqlalchemy import select

from app.core.permissions import ROLE_PERMISSIONS
from app.developer_broker.client import BrokerClient
from app.developer_broker.protocol import (
    BrokerConfigurationError,
    BrokerResponseError,
    BrokerSecret,
    BrokerUnavailableError,
)
from app.developer_broker.server import BrokerServer
from app.developer_broker.transport import InMemoryBrokerTransport
from app.main import app
from app.models.audit_log import AuditLog
import app.services.developer_broker as developer_broker_service
from app.services.developer_broker import get_developer_broker_client
from test_mobile_developer_session import (  # noqa: F401
    _developer_user,
    _role,
    dev_headers,
    enroll,
    headers,
    lock,
    login,
    mobile_security_api,
    unlock,
)

HEALTH = "/api/mobile/v1/developer/broker/health"


class SpyTransport:
    """In-memory Broker that records whether it was ever reached."""

    def __init__(self, server):
        self.inner = InMemoryBrokerTransport(server)
        self.calls = 0

    def exchange(self, frame, *, timeout_seconds):
        self.calls += 1
        return self.inner.exchange(frame, timeout_seconds=timeout_seconds)


class DownTransport:
    calls = 0

    def exchange(self, frame, *, timeout_seconds):
        self.calls += 1
        raise BrokerUnavailableError()


@pytest.fixture
def broker():
    """Wires an in-memory Broker behind the FastAPI dependency; yields the
    secret text (runtime-generated) and the spy transport."""
    secret_text = secrets.token_urlsafe(48)
    secret = BrokerSecret.from_text(secret_text)
    transport = SpyTransport(BrokerServer(secret))
    app.dependency_overrides[get_developer_broker_client] = lambda: BrokerClient(transport, secret)
    yield secret_text, transport
    app.dependency_overrides.pop(get_developer_broker_client, None)


def developer_token(api, db, user):
    pair = login(api, user.email)
    body = unlock(api, pair, enroll(api, pair))
    assert body.status_code == 200, body.text
    return pair, body.json()


def _health_audits(db):
    return db.scalars(select(AuditLog).where(AuditLog.action == "developer.broker.health")).all()


# --- rejections (the Broker is never reached) -----------------------------------------

def test_without_developer_session_is_rejected(mobile_security_api, broker):
    api, db, data = mobile_security_api
    _, transport = broker
    dev = _developer_user(db)
    pair = login(api, dev.email)
    assert api.get(HEALTH).status_code == 401  # no Mobile Bearer at all
    assert api.get(HEALTH, headers=headers(pair)).status_code == 422  # no Developer token header
    assert api.get(HEALTH, headers=dev_headers(pair, "not-a-real-token")).status_code == 401
    assert transport.calls == 0


def test_locked_developer_session_is_rejected(mobile_security_api, broker):
    api, db, data = mobile_security_api
    _, transport = broker
    pair, body = developer_token(api, db, _developer_user(db))
    lock(api, pair, body["developer_token"])
    assert api.get(HEALTH, headers=dev_headers(pair, body["developer_token"])).status_code == 401
    assert transport.calls == 0


def test_developer_session_without_system_read_is_rejected(mobile_security_api, broker, monkeypatch):
    api, db, data = mobile_security_api
    _, transport = broker
    monkeypatch.setitem(ROLE_PERMISSIONS, "DesarrolladorAcceso", {"mobile.access", "developer.access"})
    user = _developer_user(db)
    user.roles = [_role(db, "DesarrolladorAcceso")]
    db.commit()
    pair, body = developer_token(api, db, user)
    response = api.get(HEALTH, headers=dev_headers(pair, body["developer_token"]))
    assert response.status_code == 403
    assert transport.calls == 0


@pytest.mark.parametrize("wildcards", [{"*"}, {"*", "developer.*"}])
def test_erp_wildcard_without_explicit_capability_is_rejected(mobile_security_api, broker, monkeypatch, wildcards):
    """Administrador ERP != Administrador de infraestructura: "*" (and the
    literal "developer.*") never stand in for developer.system.read."""
    api, db, data = mobile_security_api
    _, transport = broker
    monkeypatch.setitem(ROLE_PERMISSIONS, "Comodin", {"mobile.access", "developer.access", *wildcards})
    admin = data["admin"]  # Administrador = {"*"}
    admin.roles = [*admin.roles, _role(db, "Comodin")]
    db.commit()
    pair, body = developer_token(api, db, admin)
    assert api.get(HEALTH, headers=dev_headers(pair, body["developer_token"])).status_code == 403
    assert transport.calls == 0


def test_client_actor_never_reaches_the_broker(mobile_security_api, broker):
    api, db, data = mobile_security_api
    _, transport = broker
    pair = login(api, data["jr"].email)
    assert api.get(HEALTH, headers=dev_headers(pair, "x" * 64)).status_code in {401, 403}
    assert transport.calls == 0


# --- allowed --------------------------------------------------------------------------

def test_explicit_system_read_reaches_broker_health(mobile_security_api, broker):
    api, db, data = mobile_security_api
    secret_text, transport = broker
    dev = _developer_user(db)
    pair, body = developer_token(api, db, dev)
    response = api.get(HEALTH, headers=dev_headers(pair, body["developer_token"]))
    assert response.status_code == 200, response.text
    health = response.json()
    assert set(health) == {
        "status", "protocol", "protocol_version", "supported_versions",
        "broker_instance_id", "broker_timestamp_ms", "operations", "features",
    }
    assert health["status"] == "ok"
    assert health["protocol_version"] == 1
    assert health["operations"] == ["broker.health"]
    assert transport.calls == 1

    [audit] = _health_audits(db)
    assert audit.user_id == dev.id
    assert audit.entity == "developer_session" and audit.entity_id == body["session_id"]
    assert audit.new_values["outcome"] == "ok"
    assert audit.new_values["capability"] == "developer.system.read"
    serialized = json.dumps(audit.new_values) + response.text
    assert body["developer_token"] not in serialized
    assert secret_text not in serialized


# --- Broker unusable: controlled failure -----------------------------------------------

def test_broker_not_configured_fails_closed(mobile_security_api, caplog):
    """Default configuration: the Broker is disabled, the ERP runs normally
    and the route answers a generic 503 (no traceback, no config detail)."""
    api, db, data = mobile_security_api
    pair, body = developer_token(api, db, _developer_user(db))
    with caplog.at_level(logging.WARNING):
        response = api.get(HEALTH, headers=dev_headers(pair, body["developer_token"]))
    assert response.status_code == 503
    assert response.json() == {"detail": "Developer Broker no disponible"}
    [audit] = _health_audits(db)
    assert audit.new_values["outcome"] == "unavailable"
    assert audit.new_values["broker_error"] == "not_configured"


def test_broker_unavailable_fails_closed(mobile_security_api):
    api, db, data = mobile_security_api
    secret = BrokerSecret.from_text(secrets.token_urlsafe(48))
    transport = DownTransport()
    app.dependency_overrides[get_developer_broker_client] = lambda: BrokerClient(transport, secret)
    pair, body = developer_token(api, db, _developer_user(db))
    response = api.get(HEALTH, headers=dev_headers(pair, body["developer_token"]))
    assert response.status_code == 503
    assert response.json() == {"detail": "Developer Broker no disponible"}
    assert transport.calls == 1
    assert _health_audits(db)[0].new_values["broker_error"] == "unavailable"


def test_broker_with_mismatched_secret_fails_closed_without_leaking(mobile_security_api, caplog):
    api, db, data = mobile_security_api
    erp_secret_text = secrets.token_urlsafe(48)
    broker_secret_text = secrets.token_urlsafe(48)
    server = BrokerServer(BrokerSecret.from_text(broker_secret_text))
    app.dependency_overrides[get_developer_broker_client] = lambda: BrokerClient(
        InMemoryBrokerTransport(server), BrokerSecret.from_text(erp_secret_text)
    )
    pair, body = developer_token(api, db, _developer_user(db))
    with caplog.at_level(logging.DEBUG):
        response = api.get(HEALTH, headers=dev_headers(pair, body["developer_token"]))
    assert response.status_code == 503
    visible = response.text + "\n".join(record.getMessage() for record in caplog.records)
    visible += json.dumps([audit.new_values for audit in _health_audits(db)])
    for secret_text in (erp_secret_text, broker_secret_text):
        assert secret_text not in visible
    assert body["developer_token"] not in visible


# --- Control Plane never logs/returns/audits a BrokerError's internal reason ------------

SENSITIVE_REASON = "/very/sensitive/windows/path"


class RaisingClient:
    def __init__(self, error):
        self.error = error

    def health(self):
        raise self.error


@pytest.mark.parametrize(
    "error",
    [BrokerUnavailableError(SENSITIVE_REASON), BrokerResponseError(SENSITIVE_REASON)],
    ids=["unavailable", "invalid_response"],
)
def test_control_plane_never_exposes_broker_error_reason(mobile_security_api, caplog, error):
    api, db, data = mobile_security_api
    app.dependency_overrides[get_developer_broker_client] = lambda: RaisingClient(error)
    pair, body = developer_token(api, db, _developer_user(db))
    with caplog.at_level(logging.DEBUG):
        response = api.get(HEALTH, headers=dev_headers(pair, body["developer_token"]))
    assert response.status_code == 503
    assert SENSITIVE_REASON not in response.text
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert SENSITIVE_REASON not in logs
    assert f"code={error.code}" in logs
    [audit] = _health_audits(db)
    assert SENSITIVE_REASON not in json.dumps(audit.new_values)
    assert audit.new_values["broker_error"] == error.code


def test_configuration_logging_only_emits_known_codes(monkeypatch, caplog):
    def build():
        raise BrokerConfigurationError(SENSITIVE_REASON)

    monkeypatch.setattr(developer_broker_service, "build_developer_broker_client", build)
    with caplog.at_level(logging.DEBUG):
        assert get_developer_broker_client() is None
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert SENSITIVE_REASON not in logs
    assert "code=not_configured" in logs


def test_configuration_logging_keeps_stable_diagnostic_codes(caplog):
    with caplog.at_level(logging.DEBUG):
        assert get_developer_broker_client() is None  # default config: disabled
    assert "code=disabled" in "\n".join(record.getMessage() for record in caplog.records)
