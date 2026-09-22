"""DEV-0: DeveloperSession authority -- biometric-gated Developer unlock,
status and lock on top of BIOMETRIC-2's real biometric credential and
BIOMETRIC-1's Mobile session authority. Never a second biometric authority,
never a substitute for MobileAuthSession."""
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import app.core.mobile.security as mobile_security_module
from app.core.db import Base, get_db
from app.core.developer_policy import (
    DEVELOPER_CAPABILITIES,
    actor_has_developer_capability,
    grants_developer_capability,
    user_has_developer_capability,
)
from app.core.mobile.developer import (
    authorize_developer_operation,
    open_developer_session,
    require_developer_session,
)
from app.core.mobile.security import resolve_mobile_token
from app.core.permissions import ROLE_PERMISSIONS
from app.main import app

from app.core.security import decode_token, hash_password
from app.models.audit_log import AuditLog
from app.models.developer_session import DeveloperSession
from app.models.mobile_auth_session import MobileAuthSession
from app.models.mobile_biometric_credential import MobileBiometricCredential
from app.models.mobile_trusted_device import MobileTrustedDevice
from app.models.user import Role, User
from test_mobile_security_context import mobile_security_api, PASSWORD  # noqa: F401

DEVICE = {"device_uuid": "71ed56b4-516b-4705-a496-aebf294d32a4", "platform": "ios", "device_name": "Test phone", "app_version": "1.0"}
DEVICE_B = {**DEVICE, "device_uuid": "9c1e2f3a-4b5c-6d7e-8f90-a1b2c3d4e5f6"}
AUTH_BASE = "/api/mobile/v1/auth"
BIOMETRIC_BASE = f"{AUTH_BASE}/biometric"
DEVELOPER_BASE = "/api/mobile/v1/developer/session"


def _developer_user(db) -> User:
    role = db.scalar(select(Role).where(Role.name == "Desarrollador"))
    if role is None:
        role = Role(name="Desarrollador", description="Desarrollador MYC")
        db.add(role)
        db.flush()
    user = User(
        username="dev@myc.example.com",
        email="dev@myc.example.com",
        full_name="Dev User",
        hashed_password=hash_password(PASSWORD),
        account_type="internal",
        status="active",
        roles=[role],
        role_id=role.id,
    )
    db.add(user)
    db.commit()
    return user


def login(api, email, device=None):
    response = api.post(f"{AUTH_BASE}/login", json={"email": email, "password": PASSWORD, "device": device or DEVICE})
    assert response.status_code == 200, response.text
    return response.json()


def headers(pair):
    return {"Authorization": f"Bearer {pair['access_token']}"}


def enroll(api, pair):
    response = api.post(f"{BIOMETRIC_BASE}/enroll", headers=headers(pair))
    assert response.status_code == 200, response.text
    return response.json()["biometric_credential"]


def unlock(api, pair, credential):
    return api.post(DEVELOPER_BASE, json={"biometric_credential": credential}, headers=headers(pair))


def dev_headers(pair, developer_token):
    return {**headers(pair), "X-MYC-Developer-Token": developer_token}


def status_(api, pair, developer_token):
    return api.get(DEVELOPER_BASE, headers=dev_headers(pair, developer_token))


def lock(api, pair, developer_token):
    return api.delete(DEVELOPER_BASE, headers=dev_headers(pair, developer_token))


def session_for(db, pair):
    return db.get(MobileAuthSession, decode_token(pair["access_token"])["mobile_session_id"], populate_existing=True)


def credential_for(db, user_id, device_id):
    return db.scalar(
        select(MobileBiometricCredential).where(
            MobileBiometricCredential.user_id == user_id,
            MobileBiometricCredential.device_id == device_id,
            MobileBiometricCredential.revoked_at.is_(None),
        )
    )


# --- opening a DeveloperSession -----------------------------------------------

def test_open_succeeds_for_internal_developer_with_valid_biometric(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    response = unlock(api, pair, credential)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"developer_token", "expires_at", "session_id"}
    record = db.get(DeveloperSession, body["session_id"])
    assert record.user_id == dev.id
    assert record.revoked_at is None


def test_open_rejects_user_without_developer_access(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"].email)  # Tecnico: mobile.access but no developer.access
    credential = enroll(api, pair)
    assert unlock(api, pair, credential).status_code == 403


def test_open_rejects_client_actor(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["jr"].email)
    credential = enroll(api, pair)
    assert unlock(api, pair, credential).status_code == 403


def test_open_rejects_credential_of_another_user(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    other_pair = login(api, data["staff"].email, DEVICE_B)
    other_credential = enroll(api, other_pair)
    dev_pair = login(api, dev.email)
    assert unlock(api, dev_pair, other_credential).status_code == 401


def test_open_rejects_credential_of_same_user_other_device(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair_a = login(api, dev.email, DEVICE)
    pair_b = login(api, dev.email, DEVICE_B)
    credential_b = enroll(api, pair_b)  # bound to device B
    assert unlock(api, pair_a, credential_b).status_code == 401  # unlocked from device A's Mobile session


def test_open_rejects_revoked_biometric_credential(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    assert api.delete(BIOMETRIC_BASE, headers=headers(pair)).status_code == 204
    assert unlock(api, pair, credential).status_code == 401


def test_open_rejects_expired_biometric_credential(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    session = session_for(db, pair)
    record = credential_for(db, dev.id, session.device_id)
    record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    assert unlock(api, pair, credential).status_code == 401


def test_open_rejects_password_changed_since_enrollment(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    dev.password_changed_at = datetime.now(timezone.utc)
    db.commit()
    assert unlock(api, pair, credential).status_code == 401


def test_open_rejects_revoked_trusted_device(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    session = session_for(db, pair)
    device = db.get(MobileTrustedDevice, session.device_id)
    device.revoked_at = datetime.now(timezone.utc)
    db.commit()
    assert unlock(api, pair, credential).status_code == 401


def test_open_rejects_revoked_mobile_session(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    assert api.post(f"{AUTH_BASE}/logout", headers=headers(pair)).status_code == 204
    assert unlock(api, pair, credential).status_code == 401


def test_open_rejects_disabled_user(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    dev.status = "disabled"
    db.commit()
    assert unlock(api, pair, credential).status_code == 401


def test_open_writes_audit_event(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    body = unlock(api, pair, credential).json()
    log = db.scalar(select(AuditLog).where(
        AuditLog.action == "developer_session.opened",
        AuditLog.entity_id == body["session_id"],
    ))
    assert log is not None
    assert log.entity == "developer_session"
    assert log.user_id == dev.id


# --- status (GET) ---------------------------------------------------------------

def test_valid_developer_token_reports_active_status(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    token = unlock(api, pair, credential).json()["developer_token"]
    response = status_(api, pair, token)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["active"] is True
    assert body["user_id"] == dev.id
    assert 0 < body["remaining_seconds"] <= 600


def test_status_requires_developer_token_header(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    assert api.get(DEVELOPER_BASE, headers=headers(pair)).status_code == 422


def test_status_never_leaks_token_hash(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    token = unlock(api, pair, credential).json()["developer_token"]
    assert "token_hash" not in status_(api, pair, token).json()


def test_status_rejects_foreign_developer_token(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    token = unlock(api, pair, credential).json()["developer_token"]
    other_pair = login(api, data["admin"].email, DEVICE_B)
    response = status_(api, other_pair, token)
    assert response.status_code == 200
    assert response.json()["active"] is False


def test_expired_developer_session_reports_inactive_and_is_lazily_revoked(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    body = unlock(api, pair, credential).json()
    record = db.get(DeveloperSession, body["session_id"])
    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    response = status_(api, pair, body["developer_token"])
    assert response.status_code == 200
    assert response.json()["active"] is False
    db.refresh(record)
    assert record.revoked_at is not None
    assert record.revocation_reason == "expired"
    assert db.scalar(select(AuditLog).where(
        AuditLog.action == "developer_session.expired", AuditLog.entity_id == record.id,
    )) is not None


def test_status_reports_inactive_once_developer_access_is_retracted(mobile_security_api):
    """Section 9: authority is re-derived on every use, never trusted from
    the claims captured when the DeveloperSession was opened."""
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    token = unlock(api, pair, credential).json()["developer_token"]
    technician_role = db.scalar(select(Role).where(Role.name == "Tecnico"))
    dev.roles = [technician_role]  # keeps mobile.access, drops developer.access
    db.commit()
    response = status_(api, pair, token)
    assert response.status_code == 200
    assert response.json()["active"] is False


# --- lock (DELETE) ----------------------------------------------------------------

def test_delete_revokes_only_the_developer_session(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    token = unlock(api, pair, credential).json()["developer_token"]
    assert lock(api, pair, token).status_code == 204
    assert status_(api, pair, token).json()["active"] is False
    # Mobile session remains active.
    assert api.get(f"{AUTH_BASE}/me", headers=headers(pair)).status_code == 200
    # Biometric enrollment remains active.
    assert api.post(f"{BIOMETRIC_BASE}/exchange", json={"biometric_credential": credential}).status_code == 200


def test_delete_is_idempotent(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    token = unlock(api, pair, credential).json()["developer_token"]
    assert lock(api, pair, token).status_code == 204
    assert lock(api, pair, token).status_code == 204
    assert lock(api, pair, "not-a-real-token").status_code == 204


def test_delete_requires_developer_token_header(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    assert api.delete(DEVELOPER_BASE, headers=headers(pair)).status_code == 422


def test_lock_writes_audit_event(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    body = unlock(api, pair, credential).json()
    lock(api, pair, body["developer_token"])
    log = db.scalar(select(AuditLog).where(
        AuditLog.action == "developer_session.revoked", AuditLog.entity_id == body["session_id"],
    ))
    assert log is not None


# --- token storage -----------------------------------------------------------------

def test_developer_token_stored_only_as_hash(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    body = unlock(api, pair, credential).json()
    record = db.get(DeveloperSession, body["session_id"])
    assert record.token_hash != body["developer_token"]
    assert len(record.token_hash) == 64
    assert all(
        body["developer_token"] != getattr(record, column.name)
        for column in DeveloperSession.__table__.columns
    )


# --- P0: explicit Developer policy ("*" alone never opens Developer) -----------

def _role(db, name):
    role = db.scalar(select(Role).where(Role.name == name))
    if role is None:
        role = Role(name=name, description=name)
        db.add(role)
        db.flush()
    return role


def test_policy_requires_exact_developer_capability_never_wildcards():
    assert grants_developer_capability({"developer.access"}) is True
    assert grants_developer_capability({"*"}) is False
    assert grants_developer_capability({"developer.*"}) is False
    assert grants_developer_capability({"*", "mobile.access"}) is False
    with pytest.raises(ValueError):
        grants_developer_capability({"*"}, "clients.read")  # not a Developer capability
    assert "developer.access" in DEVELOPER_CAPABILITIES
    assert DEVELOPER_CAPABILITIES <= ROLE_PERMISSIONS["Desarrollador"]
    # The generic ERP semantics of "*" is untouched.
    assert ROLE_PERMISSIONS["Administrador"] == {"*"}


def test_explicit_developer_is_allowed(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    assert user_has_developer_capability(dev) is True
    assert actor_has_developer_capability("internal", dev) is True
    pair = login(api, dev.email)
    assert unlock(api, pair, enroll(api, pair)).status_code == 200


def test_administrator_with_only_wildcard_is_denied(mobile_security_api):
    """Administrador ERP != Administrador de infraestructura."""
    api, db, data = mobile_security_api
    admin = data["admin"]
    assert user_has_developer_capability(admin) is False
    pair = login(api, admin.email)
    credential = enroll(api, pair)
    assert unlock(api, pair, credential).status_code == 403
    assert db.scalar(select(func.count()).select_from(DeveloperSession)) == 0
    # Administrador keeps every ERP/Mobile permission it had.
    assert api.get(f"{AUTH_BASE}/me", headers=headers(pair)).status_code == 200


def test_administrator_who_also_has_explicit_developer_role_is_allowed(mobile_security_api):
    api, db, data = mobile_security_api
    admin = data["admin"]
    admin.roles = [*admin.roles, _role(db, "Desarrollador")]
    db.commit()
    pair = login(api, admin.email)
    assert unlock(api, pair, enroll(api, pair)).status_code == 200


def test_internal_actor_without_developer_is_denied(mobile_security_api):
    api, db, data = mobile_security_api
    staff = data["staff"]  # Tecnico
    assert user_has_developer_capability(staff) is False
    pair = login(api, staff.email)
    assert unlock(api, pair, enroll(api, pair)).status_code == 403


def test_client_actor_is_denied_even_carrying_developer_strings(mobile_security_api, monkeypatch):
    api, db, data = mobile_security_api
    client = data["jr"]
    assert actor_has_developer_capability("client", client) is False
    # Even a client user bound to the Desarrollador role is not an internal actor.
    client.roles = [_role(db, "Desarrollador")]
    db.commit()
    assert user_has_developer_capability(client) is False
    original = mobile_security_module.resolve_permissions
    monkeypatch.setattr(
        mobile_security_module,
        "resolve_permissions",
        lambda db_, membership_id: frozenset(original(db_, membership_id)) | DEVELOPER_CAPABILITIES,
    )
    pair = login(api, client.email)
    assert "developer.access" in pair["user"]["permissions"]
    assert unlock(api, pair, enroll(api, pair)).status_code == 403


def test_retracting_explicit_capability_after_open_ends_the_session(mobile_security_api):
    """Admin + Desarrollador opens; dropping Desarrollador leaves only "*",
    which must NOT keep the already-open DeveloperSession alive."""
    api, db, data = mobile_security_api
    admin = data["admin"]
    administrator_role = admin.roles[0]
    admin.roles = [administrator_role, _role(db, "Desarrollador")]
    db.commit()
    pair = login(api, admin.email)
    body = unlock(api, pair, enroll(api, pair)).json()
    assert status_(api, pair, body["developer_token"]).json()["active"] is True
    admin.roles = [administrator_role]
    db.commit()
    assert status_(api, pair, body["developer_token"]).json()["active"] is False
    record = db.get(DeveloperSession, body["session_id"], populate_existing=True)
    assert record.revocation_reason == "authority_revoked"


# --- P1: at most one active DeveloperSession per Mobile authority -----------------

def _active_sessions(db):
    return db.scalars(
        select(DeveloperSession)
        .where(DeveloperSession.revoked_at.is_(None))
        .execution_options(populate_existing=True)
    ).all()


def test_second_open_supersedes_the_first(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    first = unlock(api, pair, credential).json()
    assert status_(api, pair, first["developer_token"]).json()["active"] is True

    second = unlock(api, pair, credential).json()
    record_a = db.get(DeveloperSession, first["session_id"], populate_existing=True)
    assert record_a.revoked_at is not None
    assert record_a.revocation_reason == "superseded"
    assert [item.id for item in _active_sessions(db)] == [second["session_id"]]

    assert status_(api, pair, first["developer_token"]).json()["active"] is False
    assert status_(api, pair, second["developer_token"]).json()["active"] is True


def test_supersession_is_audited_without_secrets(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    first = unlock(api, pair, credential).json()
    second = unlock(api, pair, credential).json()
    revoked = db.scalar(select(AuditLog).where(
        AuditLog.action == "developer_session.revoked", AuditLog.entity_id == first["session_id"],
    ))
    assert revoked is not None
    assert revoked.new_values["revocation_reason"] == "superseded"
    assert revoked.new_values["superseded_by_session_id"] == second["session_id"]
    opened = db.scalar(select(AuditLog).where(
        AuditLog.action == "developer_session.opened", AuditLog.entity_id == second["session_id"],
    ))
    assert opened.new_values["superseded_session_ids"] == [first["session_id"]]
    record = db.get(DeveloperSession, first["session_id"])
    serialized = repr([revoked.new_values, opened.new_values])
    for secret in (first["developer_token"], second["developer_token"], record.token_hash, credential):
        assert secret not in serialized


def test_supersede_of_an_already_expired_session_is_recorded_as_expired(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    credential = enroll(api, pair)
    first = unlock(api, pair, credential).json()
    record = db.get(DeveloperSession, first["session_id"])
    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    unlock(api, pair, credential)
    record = db.get(DeveloperSession, first["session_id"], populate_existing=True)
    assert record.revocation_reason == "expired"
    assert len(_active_sessions(db)) == 1


def test_open_from_another_mobile_session_of_same_user_and_device_supersedes(mobile_security_api):
    """Documented policy: the scope is the trusted device (user + installation),
    which strictly contains the MobileAuthSession scope. A second legitimate
    MobileAuthSession on the same device supersedes the first one's Developer."""
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair_1 = login(api, dev.email)
    pair_2 = login(api, dev.email)
    assert session_for(db, pair_1).id != session_for(db, pair_2).id
    assert session_for(db, pair_1).device_id == session_for(db, pair_2).device_id
    token_1 = unlock(api, pair_1, enroll(api, pair_1)).json()["developer_token"]
    token_2 = unlock(api, pair_2, enroll(api, pair_2)).json()["developer_token"]
    assert status_(api, pair_1, token_1).json()["active"] is False
    assert status_(api, pair_2, token_2).json()["active"] is True
    assert len(_active_sessions(db)) == 1


def test_other_device_of_same_user_keeps_its_own_session(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair_a = login(api, dev.email, DEVICE)
    pair_b = login(api, dev.email, DEVICE_B)
    token_a = unlock(api, pair_a, enroll(api, pair_a)).json()["developer_token"]
    token_b = unlock(api, pair_b, enroll(api, pair_b)).json()["developer_token"]
    assert status_(api, pair_a, token_a).json()["active"] is True
    assert status_(api, pair_b, token_b).json()["active"] is True


def test_storage_rejects_two_active_sessions_for_one_device(mobile_security_api):
    """Backstop: uq_developer_sessions_active_device (partial unique index)."""
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    unlock(api, pair, enroll(api, pair))
    existing = _active_sessions(db)[0]
    now = datetime.now(timezone.utc)
    db.add(DeveloperSession(
        user_id=existing.user_id, device_id=existing.device_id,
        mobile_session_id=existing.mobile_session_id, token_hash="f" * 64,
        last_used_at=now, expires_at=now + timedelta(minutes=10),
    ))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# --- section 4: a Developer token is bound to its exact Mobile authority ----------

def test_token_is_inactive_from_another_mobile_session_of_same_user_device(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair_1 = login(api, dev.email)
    pair_2 = login(api, dev.email)  # same user, same trusted device, other session
    token_1 = unlock(api, pair_1, enroll(api, pair_1)).json()["developer_token"]
    assert status_(api, pair_2, token_1).json()["active"] is False
    assert lock(api, pair_2, token_1).status_code == 204  # no-op, never revokes it
    assert status_(api, pair_1, token_1).json()["active"] is True


def test_token_is_inactive_from_another_device(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair_a = login(api, dev.email, DEVICE)
    pair_b = login(api, dev.email, DEVICE_B)
    token_a = unlock(api, pair_a, enroll(api, pair_a)).json()["developer_token"]
    assert status_(api, pair_b, token_a).json()["active"] is False
    assert lock(api, pair_b, token_a).status_code == 204
    assert status_(api, pair_a, token_a).json()["active"] is True


def test_token_is_inactive_for_another_identity(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    token = unlock(api, pair, enroll(api, pair)).json()["developer_token"]
    other = login(api, data["staff"].email, DEVICE_B)
    assert status_(api, other, token).json()["active"] is False
    assert lock(api, other, token).status_code == 204
    assert status_(api, pair, token).json()["active"] is True


def test_token_does_not_survive_mobile_refresh_rotation(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    token = unlock(api, pair, enroll(api, pair)).json()["developer_token"]
    rotated = api.post(f"{AUTH_BASE}/refresh", json={"refresh_token": pair["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    assert status_(api, rotated.json(), token).json()["active"] is False


def test_token_does_not_survive_logout(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    body = unlock(api, pair, enroll(api, pair)).json()
    assert api.post(f"{AUTH_BASE}/logout", headers=headers(pair)).status_code == 204
    fresh = login(api, dev.email)
    assert status_(api, fresh, body["developer_token"]).json()["active"] is False


# --- invariant for DEV-1+: privileged operations reject, status merely reports -----

def _probe_client(db):
    probe = FastAPI()

    @probe.post("/developer/database/query")
    def query(record=Depends(require_developer_session("developer.database.read"))):
        return {"developer_session_id": record.id}

    probe.dependency_overrides[get_db] = lambda: db
    return TestClient(probe)


def test_future_operation_guard_requires_live_session_and_granular_capability(mobile_security_api):
    api, db, data = mobile_security_api
    dev = _developer_user(db)
    pair = login(api, dev.email)
    body = unlock(api, pair, enroll(api, pair)).json()
    probe = _probe_client(db)
    ok = probe.post("/developer/database/query", headers=dev_headers(pair, body["developer_token"]))
    assert ok.status_code == 200, ok.text
    assert ok.json() == {"developer_session_id": body["session_id"]}

    # Invalid token: the status probe says active:false, the operation REJECTS.
    assert status_(api, pair, "not-a-real-token").json()["active"] is False
    assert probe.post(
        "/developer/database/query", headers=dev_headers(pair, "not-a-real-token")
    ).status_code == 401
    assert probe.post("/developer/database/query", headers=headers(pair)).status_code == 422

    lock(api, pair, body["developer_token"])
    assert probe.post(
        "/developer/database/query", headers=dev_headers(pair, body["developer_token"])
    ).status_code == 401


def test_future_operation_guard_denies_missing_granular_capability(mobile_security_api, monkeypatch):
    api, db, data = mobile_security_api
    monkeypatch.setitem(ROLE_PERMISSIONS, "DesarrolladorLectura", {"mobile.access", "developer.access"})
    user = _developer_user(db)
    user.roles = [_role(db, "DesarrolladorLectura")]
    db.commit()
    pair = login(api, user.email)
    body = unlock(api, pair, enroll(api, pair)).json()
    context = resolve_mobile_token(db, pair["access_token"])
    with pytest.raises(HTTPException) as denied:
        authorize_developer_operation(db, context, body["developer_token"], "developer.database.admin")
    assert denied.value.status_code == 403


# --- P1: concurrent double open on real PostgreSQL row locks ------------------------

def test_postgresql_concurrent_double_open_leaves_exactly_one_active_session():
    """SQLite has no real row locks between transactions; only PostgreSQL can
    prove the device lock serializes two concurrent opens so the second
    supersedes the first instead of leaving two live DeveloperSessions."""
    database_url = os.getenv("LAB_POSTGRES_TEST_URL")
    if not database_url:
        pytest.skip("requiere LAB_POSTGRES_TEST_URL para probar locking PostgreSQL real")

    from sqlalchemy import text as sa_text

    schema = f"dev0_developer_session_{uuid.uuid4().hex}"
    with create_engine(database_url).begin() as connection:
        connection.execute(sa_text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(database_url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with factory() as db:
            role = Role(name="Desarrollador", description="Desarrollador")
            db.add(role)
            db.flush()
            db.add(User(
                username="pg-dev@myc.example.com", email="pg-dev@myc.example.com",
                full_name="PG Dev", hashed_password=hash_password(PASSWORD),
                account_type="internal", status="active", is_active=True,
                role_id=role.id, roles=[role],
            ))
            db.commit()

        def override_db():
            with factory() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        try:
            with TestClient(app) as api:
                pair = login(api, "pg-dev@myc.example.com")
                credential = enroll(api, pair)
        finally:
            app.dependency_overrides.clear()

        barrier = threading.Barrier(2)

        def open_once(_):
            with factory() as db:
                context = resolve_mobile_token(db, pair["access_token"])
                barrier.wait()
                return open_developer_session(db, context, credential)["session_id"]

        for _ in range(3):
            with ThreadPoolExecutor(max_workers=2) as pool:
                opened = list(pool.map(open_once, range(2)))
            assert len(set(opened)) == 2
            with factory() as db:
                active = db.scalars(
                    select(DeveloperSession).where(DeveloperSession.revoked_at.is_(None))
                ).all()
                assert len(active) == 1
                assert active[0].id in opened
                loser = db.get(DeveloperSession, (set(opened) - {active[0].id}).pop())
                assert loser.revocation_reason == "superseded"
    finally:
        engine.dispose()
        with create_engine(database_url).begin() as connection:
            connection.execute(sa_text(f'DROP SCHEMA "{schema}" CASCADE'))
