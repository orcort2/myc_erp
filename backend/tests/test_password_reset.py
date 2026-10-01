from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select, update

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.audit_log import AuditLog
from app.models.email import EmailDelivery
from app.models.mobile_auth_session import MobileAuthSession
from app.models.mobile_biometric_credential import MobileBiometricCredential
from app.models.mobile_trusted_device import MobileTrustedDevice
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services import password_reset as service
from app.services.email.transport import SmtpTransport
from test_email_infrastructure import FakeSMTP, make_settings, reset_fake  # noqa: F401
from test_mobile_biometric import DEVICE, enroll, exchange, headers, login as mobile_login
from test_mobile_security_context import PASSWORD, mobile_security_api  # noqa: F401

NEW_PASSWORD = "NuevaClave456"
FORGOT = "/api/auth/forgot-password"
RESET = "/api/auth/reset-password"


class _KeepOpen:
    """Background task closes its session; keep the shared test session alive."""

    def __init__(self, db):
        self._db = db

    def __getattr__(self, name):
        return getattr(self._db, name)

    def close(self):
        pass


@pytest.fixture()
def env(mobile_security_api, monkeypatch):
    api, db, data = mobile_security_api
    settings = make_settings(public_app_base_url="https://erp.example.test", password_reset_cooldown_seconds=0)
    for target in ("app.services.password_reset.get_settings", "app.services.email.service.get_settings"):
        monkeypatch.setattr(target, lambda settings=settings: settings)
    monkeypatch.setattr("app.services.email.service.SmtpTransport", lambda s: SmtpTransport(s, smtp_factory=FakeSMTP))
    monkeypatch.setattr("app.services.password_reset.SessionLocal", lambda: _KeepOpen(db))
    return api, db, data, settings


def web_login(api, email, password=PASSWORD):
    return api.post("/api/auth/login", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def issue_token(db, user, settings=None):
    pending = service.request_password_reset(db, user.email, settings)
    assert pending is not None
    return pending.token


def sent_link_token():
    body = FakeSMTP.instances[-1].sent[0].get_body(("plain",)).get_content()
    return body.split("#token=")[1].split()[0]


# ---------------------------------------------------------------- forgot
def test_forgot_for_eligible_account_stores_only_the_hash_and_emails_the_link(env):
    api, db, data, _ = env
    response = api.post(FORGOT, json={"email": data["staff"].email})
    assert response.status_code == 200 and response.json()["message"] == service.REQUEST_MESSAGE
    record = db.scalar(select(PasswordResetToken))
    token = sent_link_token()
    assert record.token_hash == service.hash_reset_token(token) and len(token) >= 60
    ttl = record.expires_at.replace(tzinfo=timezone.utc) - record.created_at.replace(tzinfo=timezone.utc)
    assert timedelta(minutes=29, seconds=50) <= ttl <= timedelta(minutes=30, seconds=10)
    assert FakeSMTP.instances[-1].sent[0]["To"] == data["staff"].email
    delivery = db.scalar(select(EmailDelivery))
    assert delivery.template_key == "password_reset" and delivery.status == "sent"
    assert "https://erp.example.test/reset-password#token=" in FakeSMTP.instances[-1].sent[0].get_body(("plain",)).get_content()


def test_reset_url_carries_the_token_in_the_fragment_never_in_the_query(env):
    from urllib.parse import urlsplit

    api, db, data, _ = env
    api.post(FORGOT, json={"email": data["staff"].email})
    message = FakeSMTP.instances[-1].sent[0]
    for part in (message.get_body(("plain",)).get_content(), message.get_body(("html",)).get_content()):
        assert "?token=" not in part and "#token=" in part
    token = sent_link_token()
    url = f"https://erp.example.test/reset-password#token={token}"
    parts = urlsplit(url)
    # everything an HTTP request line / Host / proxy log can see excludes the token
    assert token not in parts.path and token not in parts.query and token not in parts.netloc
    assert parts.fragment == f"token={token}" and parts.query == ""
    stored = db.scalar(select(EmailDelivery))
    assert "#token=" not in stored.body_text_snapshot + stored.body_html_snapshot
    assert token not in stored.body_text_snapshot + stored.body_html_snapshot + (stored.last_error or "")


def test_token_is_never_persisted_audited_or_snapshotted(env):
    api, db, data, _ = env
    api.post(FORGOT, json={"email": data["staff"].email})
    token = sent_link_token()
    api.post(RESET, json={"token": token, "new_password": NEW_PASSWORD})
    for model in (PasswordResetToken, EmailDelivery, AuditLog):
        for row in db.scalars(select(model)).all():
            values = " ".join(str(getattr(row, c.name)) for c in model.__table__.columns)
            assert token not in values, model.__name__
            assert NEW_PASSWORD not in values and "reset-password#token" not in values and "reset-password?token" not in values
    actions = {row.action for row in db.scalars(select(AuditLog)).all()}
    assert {"auth.password_reset.requested", "auth.password_reset.completed", "auth.sessions.revoked"} <= actions


def test_forgot_is_indistinguishable_for_unknown_inactive_and_ineligible_accounts(env):
    api, db, data, _ = env
    inactive = data["admin"]
    inactive.status = "disabled"
    db.commit()
    baseline = api.post(FORGOT, json={"email": data["staff"].email})
    for email in ("nobody@example.com", inactive.email, data["viewer"].email):  # unknown, inactive, client_portal
        response = api.post(FORGOT, json={"email": email})
        assert (response.status_code, response.json()) == (baseline.status_code, baseline.json())
    assert [row.user_id for row in db.scalars(select(PasswordResetToken)).all()] == [data["staff"].id]
    # unknown accounts leave no audit trace either
    assert len(db.scalars(select(AuditLog).where(AuditLog.action == "auth.password_reset.requested")).all()) == 1


def test_new_request_revokes_previous_usable_tokens(env):
    api, db, data, _ = env
    first = issue_token(db, data["staff"])
    second = issue_token(db, data["staff"])
    assert api.post(RESET, json={"token": first, "new_password": NEW_PASSWORD}).status_code == 400
    assert api.post(RESET, json={"token": second, "new_password": NEW_PASSWORD}).status_code == 200


def test_cooldown_blocks_new_tokens_without_changing_the_public_response(env, monkeypatch):
    api, db, data, _ = env
    cooled = make_settings(public_app_base_url="https://erp.example.test", password_reset_cooldown_seconds=60)
    monkeypatch.setattr("app.services.password_reset.get_settings", lambda: cooled)
    first = api.post(FORGOT, json={"email": data["staff"].email})
    sent = len(FakeSMTP.instances)
    second = api.post(FORGOT, json={"email": data["staff"].email})
    assert (second.status_code, second.json()) == (first.status_code, first.json())
    assert len(db.scalars(select(PasswordResetToken)).all()) == 1 and len(FakeSMTP.instances) == sent
    db.execute(update(PasswordResetToken).values(created_at=datetime.now(timezone.utc) - timedelta(seconds=61)))
    db.commit()
    api.post(FORGOT, json={"email": data["staff"].email})
    assert len(db.scalars(select(PasswordResetToken)).all()) == 2


def test_smtp_failure_does_not_roll_back_the_token(env):
    api, db, data, _ = env
    FakeSMTP.fail_with = TimeoutError("relay down")
    response = api.post(FORGOT, json={"email": data["staff"].email})
    assert response.status_code == 200 and response.json()["message"] == service.REQUEST_MESSAGE
    assert db.scalar(select(PasswordResetToken)) is not None
    delivery = db.scalar(select(EmailDelivery))
    assert delivery.status == "failed" and delivery.template_key == "password_reset"


def test_missing_public_url_in_production_sends_nothing_but_keeps_response(env, monkeypatch):
    api, db, data, _ = env
    prod = make_settings(environment="production", secret_key="Zq8!vN3#rT6@wK1$yB9%xC4^mD7&hF2*", email_enabled=False)
    monkeypatch.setattr("app.services.password_reset.get_settings", lambda: prod)
    assert api.post(FORGOT, json={"email": data["staff"].email}).status_code == 200
    assert db.scalar(select(EmailDelivery)) is None and not FakeSMTP.instances


def test_legacy_portal_base_url_is_used_as_fallback_and_new_name_wins():
    legacy = make_settings(portal_public_base_url="https://legacy.example.test/")
    assert legacy.effective_public_base_url == "https://legacy.example.test"
    both = make_settings(portal_public_base_url="https://legacy.example.test", public_app_base_url="https://app.example.test")
    assert both.effective_public_base_url == "https://app.example.test"
    prod = dict(environment="production", secret_key="Zq8!vN3#rT6@wK1$yB9%xC4^mD7&hF2*", smtp_host="smtp-relay.gmail.com")
    with pytest.raises(ValueError, match="https"):
        make_settings(**prod)
    assert make_settings(**prod, public_app_base_url="https://erp.example.test").email_enabled


# ----------------------------------------------------------------- reset
def test_reset_changes_password_and_clears_security_state(env):
    api, db, data, _ = env
    user = data["staff"]
    user.failed_login_attempts, user.locked_until, user.must_change_password = 5, datetime.now(timezone.utc) + timedelta(minutes=10), True
    db.commit()
    token, other = issue_token(db, user), None
    before_version = user.auth_version
    response = api.post(RESET, json={"token": token, "new_password": NEW_PASSWORD})
    assert response.status_code == 200 and "access_token" not in response.text  # no auto-login
    db.refresh(user)
    assert user.auth_version == before_version + 1 and user.password_changed_at is not None
    assert (user.failed_login_attempts, user.locked_until, user.must_change_password) == (0, None, False)
    assert web_login(api, user.email).status_code == 401
    assert web_login(api, user.email, NEW_PASSWORD).status_code == 200
    assert db.scalar(select(PasswordResetToken)).used_at is not None


@pytest.mark.parametrize("mutate", ["used", "expired", "revoked"])
def test_reset_rejects_used_expired_and_revoked_tokens(env, mutate):
    api, db, data, _ = env
    token = issue_token(db, data["staff"])
    if mutate == "used":
        assert api.post(RESET, json={"token": token, "new_password": NEW_PASSWORD}).status_code == 200
    else:
        field = {"expired": "expires_at", "revoked": "revoked_at"}[mutate]
        value = datetime.now(timezone.utc) - timedelta(seconds=1) if mutate == "expired" else datetime.now(timezone.utc)
        db.execute(update(PasswordResetToken).values(**{field: value}))
        db.commit()
    response = api.post(RESET, json={"token": token, "new_password": "OtraClave789"})
    assert response.status_code == 400 and response.json()["detail"] == service.INVALID_LINK_MESSAGE
    assert web_login(api, data["staff"].email, "OtraClave789").status_code == 401


def test_reset_validates_token_password_and_account(env):
    api, db, data, _ = env
    token = issue_token(db, data["staff"])
    assert api.post(RESET, json={"token": "x" * 40, "new_password": NEW_PASSWORD}).status_code == 400
    assert api.post(RESET, json={"token": token, "new_password": "short"}).status_code == 422
    assert api.post(RESET, json={"token": "", "new_password": NEW_PASSWORD}).status_code == 422
    data["staff"].status = "disabled"
    db.commit()
    assert api.post(RESET, json={"token": token, "new_password": NEW_PASSWORD}).status_code == 400


def test_concurrent_double_consumption_is_blocked_atomically(env, monkeypatch):
    api, db, data, _ = env
    token = issue_token(db, data["staff"])
    record = db.scalar(select(PasswordResetToken))
    original, raced = db.execute, []

    def racing_execute(statement, *args, **kwargs):
        if not raced and str(statement).startswith("UPDATE password_reset_tokens"):
            raced.append(True)  # a competing request consumes the token first
            original(update(PasswordResetToken).where(PasswordResetToken.id == record.id).values(used_at=datetime.now(timezone.utc)))
        return original(statement, *args, **kwargs)

    monkeypatch.setattr(db, "execute", racing_execute)
    with pytest.raises(HTTPException) as caught:
        service.reset_password(db, token, NEW_PASSWORD)
    assert caught.value.status_code == 400
    monkeypatch.undo()
    db.refresh(data["staff"])
    assert web_login(api, data["staff"].email, NEW_PASSWORD).status_code == 401  # password unchanged


# ------------------------------------------------------------ web JWTs
def test_new_web_tokens_carry_auth_version_and_mismatches_are_rejected(env):
    api, db, data, _ = env
    pair = web_login(api, data["staff"].email).json()
    assert decode_token(pair["access_token"])["auth_version"] == 1
    assert decode_token(pair["refresh_token"])["auth_version"] == 1
    assert api.get("/api/auth/me", headers=bearer(pair["access_token"])).status_code == 200
    stale = {"auth_context": "internal", "auth_version": 99}
    assert api.get("/api/auth/me", headers=bearer(create_access_token(str(data["staff"].id), stale))).status_code == 401
    assert api.post("/api/auth/refresh", json={"refresh_token": create_refresh_token(str(data["staff"].id), stale)}).status_code == 401


def test_legacy_tokens_survive_only_while_auth_version_is_one(env):
    api, db, data, _ = env
    user = data["staff"]
    legacy_access = create_access_token(str(user.id), {"auth_context": "internal"})
    legacy_refresh = create_refresh_token(str(user.id), {"auth_context": "internal"})
    assert api.get("/api/auth/me", headers=bearer(legacy_access)).status_code == 200
    assert api.post("/api/auth/refresh", json={"refresh_token": legacy_refresh}).status_code == 200
    pair = web_login(api, user.email).json()
    api.post(RESET, json={"token": issue_token(db, user), "new_password": NEW_PASSWORD})
    assert api.get("/api/auth/me", headers=bearer(legacy_access)).status_code == 401
    assert api.post("/api/auth/refresh", json={"refresh_token": legacy_refresh}).status_code == 401
    assert api.get("/api/auth/me", headers=bearer(pair["access_token"])).status_code == 401
    assert api.post("/api/auth/refresh", json={"refresh_token": pair["refresh_token"]}).status_code == 401
    fresh = web_login(api, user.email, NEW_PASSWORD).json()
    assert decode_token(fresh["access_token"])["auth_version"] == 2
    assert api.get("/api/auth/me", headers=bearer(fresh["access_token"])).status_code == 200
    # the legacy-ERP-token compatibility path in Mobile honors the same authority
    assert api.get("/api/mobile/v1/auth/me", headers=bearer(legacy_access)).status_code == 401


# --------------------------------------------------------------- Mobile
def test_reset_revokes_mobile_sessions_and_biometrics_but_keeps_trusted_devices(env):
    api, db, data, _ = env
    user = data["staff"]
    pair = mobile_login(api, user)
    credential = enroll(api, pair).json()["biometric_credential"]
    assert exchange(api, credential).status_code == 200
    assert api.get("/api/mobile/v1/auth/me", headers=headers(pair)).status_code == 200

    assert api.post(RESET, json={"token": issue_token(db, user), "new_password": NEW_PASSWORD}).status_code == 200

    db.expire_all()
    assert all(s.revoked_at is not None for s in db.scalars(select(MobileAuthSession).where(MobileAuthSession.user_id == user.id)))
    assert all(c.revoked_at is not None for c in db.scalars(select(MobileBiometricCredential).where(MobileBiometricCredential.user_id == user.id)))
    devices = db.scalars(select(MobileTrustedDevice).where(MobileTrustedDevice.user_id == user.id)).all()
    assert devices and all(d.is_active and d.revoked_at is None for d in devices)
    assert api.post("/api/mobile/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]}).status_code == 401
    assert api.get("/api/mobile/v1/auth/me", headers=headers(pair)).status_code == 401
    assert exchange(api, credential).status_code == 401
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "auth.sessions.revoked"))
    assert audit.new_values["trusted_devices_revoked"] == 0 and audit.new_values["mobile_sessions_revoked"] >= 1

    old = api.post("/api/mobile/v1/auth/login", json={"email": user.email, "password": PASSWORD, "device": DEVICE})
    assert old.status_code == 401
    fresh = api.post("/api/mobile/v1/auth/login", json={"email": user.email, "password": NEW_PASSWORD, "device": DEVICE})
    assert fresh.status_code == 200
    assert enroll(api, fresh.json()).status_code == 200  # biometrics can be enabled again
