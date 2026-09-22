"""BIOMETRIC-1 behavior tests. Legacy UUID is presented, not historical proof."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from app.core.mobile import security
from app.core.mobile.refresh_credentials import hash_refresh_credential, is_legacy_refresh_format
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.mobile_auth_session import MobileAuthSession
from app.models.mobile_trusted_device import MobileTrustedDevice
from app.models.notification import PushDevice
from app.models.client_portal_membership import ClientPortalMembership
from app.models.user import User
from test_mobile_security_context import mobile_security_api, PASSWORD  # noqa: F401

DEVICE = {"device_uuid": "71ed56b4-516b-4705-a496-aebf294d32a4", "platform": "ios", "device_name": "Test phone", "app_version": "1.0"}
BASE = "/api/mobile/v1/auth"


def login(api, user, device=None):
    response = api.post(f"{BASE}/login", json={"email": user.email, "password": PASSWORD, "device": device or DEVICE})
    assert response.status_code == 200, response.text
    return response.json()


def refresh(api, pair, **kwargs):
    return api.post(f"{BASE}/refresh", json={"refresh_token": pair["refresh_token"], **kwargs})


def headers(pair):
    return {"Authorization": f"Bearer {pair['access_token']}"}


def session_for(db, pair):
    return db.get(MobileAuthSession, decode_token(pair["access_token"])["mobile_session_id"], populate_existing=True)


def legacy(db, user, context=None):
    claims = {"auth_context": context or ("mobile_internal" if user.account_type == "internal" else "mobile_client"),
              "actor_type": "internal" if user.account_type == "internal" else "client"}
    if user.account_type != "internal":
        membership = db.scalar(select(ClientPortalMembership).where(ClientPortalMembership.user_id == user.id))
        claims.update(membership_id=membership.id, client_id=membership.client_id)
    # Fixed, short expiry keeps tests independent of the configured 30-day TTL.
    claims["exp"] = datetime.now(timezone.utc) + timedelta(hours=1)
    return {"refresh_token": create_refresh_token(str(user.id), claims)}


@pytest.fixture(autouse=True)
def legacy_window(monkeypatch):
    monkeypatch.setattr(security, "LEGACY_REFRESH_DEADLINE", datetime.now(timezone.utc) + timedelta(days=2))


@pytest.mark.parametrize("actor", ["staff", "jr"])
def test_login_creates_bound_session_and_only_hashes(mobile_security_api, actor):
    api, db, data = mobile_security_api
    pair = login(api, data[actor])
    session = session_for(db, pair)
    device = db.get(MobileTrustedDevice, session.device_id)
    assert device.user_id == session.user_id == data[actor].id
    assert device.device_uuid == DEVICE["device_uuid"]
    assert device.trusted_at and device.last_seen_at and device.is_active
    assert session.refresh_token_hash == hash_refresh_credential(pair["refresh_token"])
    assert len(session.refresh_token_hash) == 64
    assert not is_legacy_refresh_format(pair["refresh_token"])
    assert all(pair["refresh_token"] != getattr(session, c.name) for c in MobileAuthSession.__table__.columns)
    assert db.scalar(select(func.count(PushDevice.id))) == 0
    claims = decode_token(pair["access_token"])
    assert claims["actor_type"] == pair["user"]["actor_type"]
    assert claims["auth_context"] == f"mobile_{claims['actor_type']}"
    assert api.get(f"{BASE}/me", headers=headers(pair)).status_code == 200


def test_login_reuses_device_but_not_family_and_never_reactivates(mobile_security_api):
    api, db, data = mobile_security_api
    first = login(api, data["staff"])
    second = login(api, data["staff"])
    assert session_for(db, first).device_id == session_for(db, second).device_id
    assert session_for(db, first).family_id != session_for(db, second).family_id
    device = db.get(MobileTrustedDevice, session_for(db, first).device_id)
    device.revoked_at = datetime.now(timezone.utc)
    db.commit()
    response = api.post(f"{BASE}/login", json={"email": data["staff"].email, "password": PASSWORD, "device": DEVICE})
    assert response.status_code == 401
    assert device.revoked_at is not None
    assert db.scalar(select(func.count(MobileAuthSession.id))) == 2


@pytest.mark.parametrize("actor", ["staff", "jr"])
def test_rotation_preserves_scope_and_reuse_revokes_every_successor(mobile_security_api, actor):
    api, db, data = mobile_security_api
    first = login(api, data[actor])
    second_response = refresh(api, first)
    assert second_response.status_code == 200, second_response.text
    second = second_response.json()
    third = refresh(api, second).json()
    assert len({first['refresh_token'], second['refresh_token'], third['refresh_token']}) == 3
    assert first['user'] == second['user'] == third['user']
    original = session_for(db, first)
    assert original.revoked_at and original.replaced_by_id == session_for(db, second).id
    assert original.family_id == session_for(db, third).family_id
    assert original.expires_at == session_for(db, third).expires_at
    assert api.get(f"{BASE}/me", headers=headers(first)).status_code == 401
    assert refresh(api, first).status_code == 401
    db.expire_all()
    rows = db.scalars(select(MobileAuthSession).where(MobileAuthSession.family_id == original.family_id)).all()
    assert len(rows) == 3 and all(row.revoked_at for row in rows)
    assert session_for(db, first).reuse_detected_at
    assert refresh(api, third).status_code == 401
    assert api.get(f"{BASE}/me", headers=headers(third)).status_code == 401


@pytest.mark.parametrize("condition", ["expired", "device_revoked", "device_inactive", "user_inactive", "user_status", "permission_removed"])
def test_refresh_revalidates_authority(mobile_security_api, condition):
    api, db, data = mobile_security_api
    pair = login(api, data["staff"])
    session = session_for(db, pair)
    device = db.get(MobileTrustedDevice, session.device_id)
    if condition == 'expired': session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    if condition == 'device_revoked': device.revoked_at = datetime.now(timezone.utc)
    if condition == 'device_inactive': device.is_active = False
    if condition == 'user_inactive':
        # Exercise the independent is_active guard even against inconsistent legacy data.
        db.execute(update(User).where(User.id == data['staff'].id).values(is_active=False))
    if condition == 'user_status': data['staff'].status = 'suspended'
    if condition == 'permission_removed': data['staff'].roles[0].is_active = False
    db.commit()
    assert refresh(api, pair).status_code == 401
    assert db.scalar(select(func.count(MobileAuthSession.id))) == 1


def test_random_and_invalid_jwt_are_generic_unauthorized(mobile_security_api):
    api, db, data = mobile_security_api
    unknown = refresh(api, {"refresh_token": "random-credential"})
    invalid = refresh(api, {"refresh_token": "aaa.bbb.ccc"}, device=DEVICE)
    assert unknown.status_code == invalid.status_code == 401
    assert unknown.json() == invalid.json()
    assert db.scalar(select(func.count(MobileTrustedDevice.id))) == 0


def test_logout_only_revokes_current_family(mobile_security_api):
    api, db, data = mobile_security_api
    first = login(api, data['staff'])
    same_device = login(api, data['staff'])
    other_device = login(api, data['staff'], {**DEVICE, 'device_uuid': str(uuid4())})
    current = refresh(api, first).json()
    assert api.post(f'{BASE}/logout', headers=headers(current)).status_code == 204
    assert refresh(api, current).status_code == 401
    assert api.get(f'{BASE}/me', headers=headers(current)).status_code == 401
    assert refresh(api, same_device).status_code == 200
    assert refresh(api, other_device).status_code == 200
    assert db.get(MobileTrustedDevice, session_for(db, current).device_id).is_active


@pytest.mark.parametrize('actor,auth_context', [('staff', 'mobile_internal'), ('staff', 'internal'), ('jr', 'mobile_client')])
def test_legacy_migrates_once_with_presented_device(mobile_security_api, actor, auth_context):
    # This UUID is supplied now. The legacy signature cannot prove historical device ownership.
    api, db, data = mobile_security_api
    old = legacy(db, data[actor], auth_context)
    initial_claims = decode_token(old['refresh_token'])
    migrated_response = refresh(api, old, device=DEVICE)
    assert migrated_response.status_code == 200, migrated_response.text
    migrated = migrated_response.json()
    new_claims = decode_token(migrated['access_token'])
    for key in ('actor_type', 'client_id', 'membership_id'):
        assert new_claims.get(key) == initial_claims.get(key)
    assert 'mobile.access' in migrated['user']['permissions']
    assert not is_legacy_refresh_format(migrated['refresh_token'])
    assert db.scalar(select(func.count(MobileTrustedDevice.id))) == 1
    assert db.scalar(select(func.count(MobileAuthSession.id))) == 1
    assert session_for(db, migrated).legacy_refresh_token_hash == hash_refresh_credential(old['refresh_token'])
    successor = refresh(api, migrated)
    assert successor.status_code == 200
    assert refresh(api, old, device={**DEVICE, 'device_uuid': str(uuid4())}).status_code == 401
    assert refresh(api, successor.json()).status_code == 401
    assert db.scalar(select(func.count(MobileTrustedDevice.id))) == 1


def test_legacy_requires_device_even_with_existing_push_registration(mobile_security_api):
    api, db, data = mobile_security_api
    db.add(PushDevice(user_id=data['staff'].id, expo_push_token='ExponentPushToken[test]', platform='ios', last_seen_at=datetime.now(timezone.utc)))
    db.commit()
    old = legacy(db, data['staff'])
    assert refresh(api, old).status_code == 422
    assert db.scalar(select(func.count(MobileTrustedDevice.id))) == 0
    migrated = refresh(api, old, device=DEVICE)
    assert migrated.status_code == 200
    assert db.scalar(select(func.count(PushDevice.id))) == 1
    assert db.scalar(select(func.count(MobileTrustedDevice.id))) == 1


@pytest.mark.parametrize('metadata', [DEVICE, None])
def test_opaque_rejects_explicit_device_including_null(mobile_security_api, metadata):
    api, db, data = mobile_security_api
    pair = login(api, data['staff'])
    assert refresh(api, pair, device=metadata).status_code == 422
    assert refresh(api, pair).status_code == 200


def test_revoked_device_blocks_legacy(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data['staff'])
    device = db.get(MobileTrustedDevice, session_for(db, pair).device_id)
    device.revoked_at = datetime.now(timezone.utc)
    db.commit()
    assert refresh(api, legacy(db, data['staff']), device=DEVICE).status_code == 401
    assert db.scalar(select(func.count(MobileAuthSession.id))) == 1


def test_legacy_cutoff_is_enforced(mobile_security_api, monkeypatch):
    api, db, data = mobile_security_api
    old = legacy(db, data['staff'])
    monkeypatch.setattr(security, 'LEGACY_REFRESH_DEADLINE', datetime.now(timezone.utc) - timedelta(seconds=1))
    assert refresh(api, old, device=DEVICE).status_code == 401
    assert db.scalar(select(func.count(MobileAuthSession.id))) == 0


@pytest.mark.parametrize('context', ['client_portal', 'internal', 'mobile_internal'])
def test_client_cannot_migrate_through_other_contexts(mobile_security_api, context):
    api, db, data = mobile_security_api
    assert refresh(api, legacy(db, data['jr'], context), device=DEVICE).status_code == 401


def test_access_cannot_be_used_as_refresh_and_session_claim_cannot_be_rebound(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data['staff'])
    assert refresh(api, {'refresh_token': pair['access_token']}, device=DEVICE).status_code == 401
    forged = create_access_token(str(data['admin'].id), {'auth_context': 'mobile_internal', 'actor_type': 'internal', 'mobile_session_id': session_for(db, pair).id})
    assert api.get(f'{BASE}/me', headers={'Authorization': f'Bearer {forged}'}).status_code == 401


def test_client_membership_cannot_move_during_refresh(mobile_security_api):
    api, db, data = mobile_security_api
    pair = login(api, data['jr'])
    membership = db.get(ClientPortalMembership, pair['user']['membership_id'])
    membership.client_id = data['client_b'].id
    db.commit()
    assert refresh(api, pair).status_code == 401


def test_mobile_device_contract_is_required_and_validated(mobile_security_api):
    api, db, data = mobile_security_api
    body = {'email': data['staff'].email, 'password': PASSWORD}
    assert api.post(f'{BASE}/login', json=body).status_code == 422
    for device in ({**DEVICE, 'platform': 'web'}, {**DEVICE, 'device_uuid': 'push-token'}):
        assert api.post(f'{BASE}/login', json={**body, 'device': device}).status_code == 422


def test_alternate_signature_encoding_cannot_bypass_legacy_single_use(mobile_security_api):
    import base64
    api, db, data = mobile_security_api
    old = legacy(db, data['staff'])
    prefix, signature = old['refresh_token'].rsplit('.', 1)
    alternate = next(signature[:-1] + char for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
        if char != signature[-1] and base64.urlsafe_b64decode(signature[:-1] + char + '=') == base64.urlsafe_b64decode(signature + '='))
    alternate_token = prefix + '.' + alternate
    assert decode_token(alternate_token) == decode_token(old['refresh_token'])
    assert refresh(api, old, device=DEVICE).status_code == 200
    assert refresh(api, {'refresh_token': alternate_token}, device={**DEVICE, 'device_uuid': str(uuid4())}).status_code == 401
    assert db.scalar(select(func.count(MobileAuthSession.id))) == 1
