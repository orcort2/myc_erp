"""BIOMETRIC-2: enroll/exchange/revoke behavior for device-bound biometric login."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.security import decode_token
from app.models.mobile_auth_session import MobileAuthSession
from app.models.mobile_biometric_credential import MobileBiometricCredential
from app.models.mobile_trusted_device import MobileTrustedDevice
from app.models.notification import PushDevice
from test_mobile_security_context import mobile_security_api, PASSWORD  # noqa: F401

DEVICE = {"device_uuid": "71ed56b4-516b-4705-a496-aebf294d32a4", "platform": "ios", "device_name": "Test phone", "app_version": "1.0"}
AUTH_BASE = "/api/mobile/v1/auth"
BIOMETRIC_BASE = f"{AUTH_BASE}/biometric"


def login(api, user, device=None):
    response = api.post(f"{AUTH_BASE}/login", json={"email": user.email, "password": PASSWORD, "device": device or DEVICE})
    assert response.status_code == 200, response.text
    return response.json()


def headers(pair):
    return {"Authorization": f"Bearer {pair['access_token']}"}


def enroll(api, pair):
    return api.post(f"{BIOMETRIC_BASE}/enroll", headers=headers(pair))


def exchange(api, credential):
    return api.post(f"{BIOMETRIC_BASE}/exchange", json={"biometric_credential": credential})


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


def test_enroll_requires_valid_mobile_session(mobile_security_api):
    api, db, data = mobile_security_api
    assert enroll(api, {"access_token": "garbage"}).status_code == 401
    pair = login(api, data["staff"])
    response = enroll(api, pair)
    assert response.status_code == 200, response.text
    assert "biometric_credential" in response.json()
    assert "expires_at" in response.json()


def test_enroll_creates_credential_for_current_device(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    enroll(api, pair)
    session = session_for(db, pair)
    record = credential_for(db, data["staff"].id, session.device_id)
    assert record is not None
    assert record.device_id == session.device_id
    assert record.user_id == data["staff"].id


def test_credential_plaintext_never_persisted(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    plaintext = enroll(api, pair).json()["biometric_credential"]
    session = session_for(db, pair)
    record = credential_for(db, data["staff"].id, session.device_id)
    assert record.credential_hash != plaintext
    assert len(record.credential_hash) == 64
    assert all(plaintext != getattr(record, c.name) for c in MobileBiometricCredential.__table__.columns)


def test_second_enroll_revokes_previous_credential(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    first = enroll(api, pair).json()["biometric_credential"]
    second = enroll(api, pair).json()["biometric_credential"]
    assert first != second
    session = session_for(db, pair)
    active = db.scalars(
        select(MobileBiometricCredential).where(
            MobileBiometricCredential.user_id == data["staff"].id,
            MobileBiometricCredential.device_id == session.device_id,
        )
    ).all()
    assert len(active) == 2
    assert sum(1 for c in active if c.revoked_at is None) == 1
    assert exchange(api, first).status_code == 401
    assert exchange(api, second).status_code == 200


def test_exchange_creates_new_mobile_auth_session(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    credential = enroll(api, pair).json()["biometric_credential"]
    original_session = session_for(db, pair)
    response = exchange(api, credential)
    assert response.status_code == 200, response.text
    new_pair = response.json()
    new_session = session_for(db, new_pair)
    assert new_session.id != original_session.id
    assert new_pair["refresh_token"] != pair["refresh_token"]


def test_exchange_reuses_same_trusted_device_never_creates_new(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    credential = enroll(api, pair).json()["biometric_credential"]
    original_session = session_for(db, pair)
    device_count_before = db.scalar(select(func.count(MobileTrustedDevice.id)))
    new_pair = exchange(api, credential).json()
    new_session = session_for(db, new_pair)
    assert new_session.device_id == original_session.device_id
    assert db.scalar(select(func.count(MobileTrustedDevice.id))) == device_count_before


def test_exchange_rebuilds_current_internal_permissions(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    credential = enroll(api, pair).json()["biometric_credential"]
    new_pair = exchange(api, credential).json()
    assert new_pair["user"]["actor_type"] == "internal"
    assert "mobile.access" in new_pair["user"]["permissions"]
    assert new_pair["user"]["id"] == data["staff"].id


def test_exchange_client_actor_resolves_scope(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["jr"])
    assert pair["user"]["actor_type"] == "client"
    credential = enroll(api, pair).json()["biometric_credential"]
    new_pair = exchange(api, credential).json()
    assert new_pair["user"]["actor_type"] == "client"
    assert new_pair["user"]["client_id"] == pair["user"]["client_id"]
    assert new_pair["user"]["membership_id"] == pair["user"]["membership_id"]


def test_revoked_credential_returns_401(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    credential = enroll(api, pair).json()["biometric_credential"]
    assert api.delete(f"{BIOMETRIC_BASE}", headers=headers(pair)).status_code == 204
    assert exchange(api, credential).status_code == 401


def test_expired_credential_returns_401(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    credential = enroll(api, pair).json()["biometric_credential"]
    session = session_for(db, pair)
    record = credential_for(db, data["staff"].id, session.device_id)
    record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    assert exchange(api, credential).status_code == 401


def test_disabled_user_returns_401(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    credential = enroll(api, pair).json()["biometric_credential"]
    data["staff"].status = "disabled"
    db.commit()
    assert exchange(api, credential).status_code == 401


def test_mobile_access_removed_returns_403(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    credential = enroll(api, pair).json()["biometric_credential"]
    data["staff"].roles = []
    db.commit()
    response = exchange(api, credential)
    assert response.status_code == 403


def test_revoked_device_returns_401(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    credential = enroll(api, pair).json()["biometric_credential"]
    session = session_for(db, pair)
    device = db.get(MobileTrustedDevice, session.device_id)
    device.revoked_at = datetime.now(timezone.utc)
    db.commit()
    assert exchange(api, credential).status_code == 401


def test_password_changed_after_enroll_invalidates_credential(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    credential = enroll(api, pair).json()["biometric_credential"]
    data["staff"].password_changed_at = datetime.now(timezone.utc)
    db.commit()
    assert exchange(api, credential).status_code == 401
    # Password login remains available; a fresh enroll snapshots the new password.
    fresh_pair = login(api, data["staff"])
    new_credential = enroll(api, fresh_pair).json()["biometric_credential"]
    assert exchange(api, new_credential).status_code == 200


def test_delete_biometric_revokes_current_user_current_device(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    credential = enroll(api, pair).json()["biometric_credential"]
    response = api.delete(f"{BIOMETRIC_BASE}", headers=headers(pair))
    assert response.status_code == 204
    session = session_for(db, pair)
    record = credential_for(db, data["staff"].id, session.device_id)
    assert record is None
    assert exchange(api, credential).status_code == 401


def test_delete_biometric_does_not_revoke_other_installations(mobile_security_api):
    api, db, data = mobile_security_api
    device_a = DEVICE
    device_b = {**DEVICE, "device_uuid": "9c1e2f3a-4b5c-6d7e-8f90-a1b2c3d4e5f6"}
    pair_a = login(api, data["staff"], device_a)
    pair_b = login(api, data["staff"], device_b)
    credential_a = enroll(api, pair_a).json()["biometric_credential"]
    credential_b = enroll(api, pair_b).json()["biometric_credential"]
    assert api.delete(f"{BIOMETRIC_BASE}", headers=headers(pair_a)).status_code == 204
    assert exchange(api, credential_a).status_code == 401
    assert exchange(api, credential_b).status_code == 200


def test_push_device_is_never_consulted_as_authority(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    credential = enroll(api, pair).json()["biometric_credential"]
    assert db.scalar(select(func.count(PushDevice.id))) == 0
    response = exchange(api, credential)
    assert response.status_code == 200
    assert db.scalar(select(func.count(PushDevice.id))) == 0


def test_exchange_rejects_client_supplied_device(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    credential = enroll(api, pair).json()["biometric_credential"]
    response = api.post(f"{BIOMETRIC_BASE}/exchange", json={"biometric_credential": credential, "device": DEVICE})
    assert response.status_code == 422
