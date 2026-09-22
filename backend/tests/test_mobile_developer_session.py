"""DEV-0: DeveloperSession authority -- biometric-gated Developer unlock,
status and lock on top of BIOMETRIC-2's real biometric credential and
BIOMETRIC-1's Mobile session authority. Never a second biometric authority,
never a substitute for MobileAuthSession."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

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


# --- documented central-permission semantics ("*") ---------------------------------

def test_admin_wildcard_still_grants_developer_access(mobile_security_api):
    """Documents CURRENT accepted semantics: '*' (Administrador) already
    grants every permission centrally (app/services/auth.py::user_has_permission),
    including developer.access. DEV-0 gates through the same central
    mechanism every other Mobile endpoint uses
    (require_internal_mobile_permission) and does not carve out a special
    case or an email/user-id hack for it. See
    docs/architecture/MOBILE_DEVELOPER_AUTHORITY.md for the accepted risk and
    the tighter, explicit policy a future stage should define."""
    api, db, data = mobile_security_api
    pair = login(api, data["admin"].email)
    credential = enroll(api, pair)
    assert unlock(api, pair, credential).status_code == 200
