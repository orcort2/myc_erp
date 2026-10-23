"""MYC-ASSISTANT-1A: Telegram <-> MYC account linking domain core."""
import inspect
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.login_policy import utc_now
from app.core.mobile.security import resolve_mobile_token
from app.core.security import decode_token, hash_password
from app.models.assistant_account_link import AssistantAccountLink
from app.models.assistant_link_request import AssistantLinkRequest
from app.models.audit_log import AuditLog
from app.models.mobile_biometric_credential import MobileBiometricCredential
from app.models.user import User
from app.services import assistant_account_linking as svc
from app.services.assistant_account_linking import AssistantLinkError
from test_mobile_developer_session import BIOMETRIC_BASE, DEVICE, DEVICE_B, headers, login
from test_mobile_security_context import PASSWORD, mobile_security_api  # noqa: F401

TG = 700_000_001
TG_OTHER = 700_000_002


def enroll(api, pair):
    response = api.post(f"{BIOMETRIC_BASE}/enroll", headers=headers(pair))
    assert response.status_code == 200, response.text
    return response.json()["biometric_credential"]


def mobile(api, db, user, device=None):
    """(context, biometric credential) for a really logged-in Mobile session."""
    pair = login(api, user.email, device)
    return resolve_mobile_token(db, pair["access_token"]), enroll(api, pair), pair


def new_request(db, user, tg=TG):
    return svc.create_link_request(db, telegram_user_id=tg, telegram_chat_id=tg, candidate_user_id=user.id)


def row(db, view):
    """Fresh ORM row behind a LinkRequestView."""
    return db.get(AssistantLinkRequest, view.id, populate_existing=True)


def code_of(db, action):
    return db.scalars(select(AuditLog).where(AuditLog.action == action)).all()


def err(call, *args, **kwargs) -> str:
    with pytest.raises(AssistantLinkError) as info:
        call(*args, **kwargs)
    return info.value.code


# --- creation -----------------------------------------------------------------

def test_create_request_shape_and_audit(mobile_security_api):
    api, db, data = mobile_security_api
    before = utc_now()
    request = new_request(db, data["staff"])
    assert request.status == "pending"
    assert request.comparison_code.isdigit() and len(request.comparison_code) == 6
    assert len(request.public_id) >= 40
    ttl = svc.as_utc(request.expires_at) - before
    assert timedelta(minutes=4, seconds=55) < ttl <= timedelta(minutes=5, seconds=2)
    assert row(db, request).approved_by_user_id is None
    assert new_request(db, data["staff"], TG).public_id != request.public_id
    created = code_of(db, "assistant_link.request_created")
    assert created and request.comparison_code not in str(created[0].new_values)


@pytest.mark.parametrize("user_id,chat_id", [(TG, TG + 1), (TG, -TG), (-TG, -TG), (0, 0), (True, True)])
def test_create_rejects_non_private_or_malformed_identity(mobile_security_api, user_id, chat_id):
    api, db, data = mobile_security_api
    assert err(svc.create_link_request, db, telegram_user_id=user_id, telegram_chat_id=chat_id,
               candidate_user_id=data["staff"].id) == "invalid_identity"
    assert db.scalar(select(AssistantLinkRequest.id)) is None


def test_create_rejects_unlinkable_accounts(mobile_security_api):
    api, db, data = mobile_security_api
    assert err(new_request, db, data["viewer"]) == "invalid_account"  # client portal
    inactive = data["staff_without_mobile"]
    inactive.status = "disabled"  # status is the account authority
    db.commit()
    assert err(new_request, db, inactive) == "invalid_account"
    locked = data["admin"]
    locked.status = "suspended"
    db.commit()
    assert err(new_request, db, locked) == "invalid_account"
    assert err(svc.create_link_request, db, telegram_user_id=TG, telegram_chat_id=TG,
               candidate_user_id=999_999) == "invalid_account"


def test_new_request_supersedes_previous_one_per_telegram_identity(mobile_security_api):
    api, db, data = mobile_security_api
    first = new_request(db, data["staff"])
    second = new_request(db, data["admin"])
    assert (row(db, first).status, second.status) == ("superseded", "pending")
    assert row(db, first).comparison_code is None
    assert code_of(db, "assistant_link.request_superseded")


def test_pending_requests_per_candidate_are_capped(mobile_security_api):
    api, db, data = mobile_security_api
    for offset in range(svc.MAX_PENDING_PER_CANDIDATE):
        new_request(db, data["staff"], TG + offset)
    assert err(new_request, db, data["staff"], TG + 50) == "too_many_pending"


def test_create_skips_expired_pending_and_marks_it(mobile_security_api):
    api, db, data = mobile_security_api
    stale = new_request(db, data["staff"])
    row(db, stale).expires_at = utc_now() - timedelta(seconds=1)
    db.commit()
    fresh = new_request(db, data["staff"])
    assert (row(db, stale).status, fresh.status) == ("expired", "pending")


# --- consult ------------------------------------------------------------------

def test_request_visible_only_to_candidate_and_origin_telegram(mobile_security_api):
    api, db, data = mobile_security_api
    request = new_request(db, data["staff"])
    assert svc.get_request_for_candidate(db, public_id=request.public_id, user=data["staff"]).id == request.id
    assert err(svc.get_request_for_candidate, db, public_id=request.public_id, user=data["admin"]) == "not_found"
    assert err(svc.get_request_for_candidate, db, public_id="nope", user=data["staff"]) == "not_found"
    assert svc.get_request_for_telegram(db, public_id=request.public_id, telegram_user_id=TG,
                                        telegram_chat_id=TG).id == request.id
    assert err(svc.get_request_for_telegram, db, public_id=request.public_id,
               telegram_user_id=TG_OTHER, telegram_chat_id=TG_OTHER) == "not_found"


def test_consult_reports_effective_expiry_without_writing(mobile_security_api):
    api, db, data = mobile_security_api
    request = new_request(db, data["staff"])
    row(db, request).expires_at = utc_now() - timedelta(seconds=1)
    db.commit()
    audits = len(db.scalars(select(AuditLog)).all())
    seen = svc.get_request_for_candidate(db, public_id=request.public_id, user=data["staff"])
    assert (seen.status, seen.comparison_code) == ("expired", None)
    assert row(db, request).status == "pending"  # the read did not transition anything
    assert len(db.scalars(select(AuditLog)).all()) == audits


# --- approval -----------------------------------------------------------------

def test_approve_creates_link_with_server_derived_approver_and_device(mobile_security_api):
    api, db, data = mobile_security_api
    context, credential, pair = mobile(api, db, data["staff"])
    request = new_request(db, data["staff"])
    shown_code = request.comparison_code
    link = svc.approve_link_request(db, public_id=request.public_id, context=context, biometric_credential=credential)
    request = row(db, request)
    assert (link.status, link.user_id, link.telegram_user_id, link.telegram_chat_id) == ("active", data["staff"].id, TG, TG)
    assert request.status == "approved" and request.comparison_code is None and request.approved_by_user_id == data["staff"].id
    from app.models.mobile_auth_session import MobileAuthSession
    session = db.get(MobileAuthSession, decode_token(pair["access_token"])["mobile_session_id"])
    assert request.approved_device_id == session.device_id
    assert svc.resolve_active_link(db, telegram_user_id=TG, telegram_chat_id=TG).id == link.id
    for action in ("assistant_link.approved", "assistant_link.created"):
        rows = code_of(db, action)
        assert len(rows) == 1 and rows[0].user_id == data["staff"].id
        assert credential not in str(rows[0].new_values) and shown_code not in str(rows[0].new_values)


def test_approve_has_no_client_supplied_proof_parameters():
    params = inspect.signature(svc.approve_link_request).parameters
    assert set(params) == {"db", "public_id", "context", "biometric_credential"}
    assert all(p.annotation is not bool for p in params.values())
    for forbidden in ("comparison_code", "code", "biometric_ok", "verified"):
        assert forbidden not in params


@pytest.mark.parametrize("claim", [True, "", None, 1, "client-says-ok"])
def test_approve_rejects_missing_or_forged_biometric_proof(mobile_security_api, claim):
    api, db, data = mobile_security_api
    context, _credential, _ = mobile(api, db, data["staff"])
    request = new_request(db, data["staff"])
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=context,
               biometric_credential=claim) in {"strong_auth_required", "strong_auth_failed"}
    assert row(db, request).status == "pending" and db.scalar(select(AssistantAccountLink.id)) is None


def test_comparison_code_cannot_authorize(mobile_security_api):
    api, db, data = mobile_security_api
    context, _credential, _ = mobile(api, db, data["staff"])
    request = new_request(db, data["staff"])
    with pytest.raises(TypeError):
        svc.approve_link_request(db, public_id=request.public_id, context=context,
                                 comparison_code=request.comparison_code)
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=context,
               biometric_credential=request.comparison_code) == "strong_auth_failed"
    assert code_of(db, "assistant_link.approve_denied") == []  # the domain never audits denials


def test_approve_rejects_other_users_credential(mobile_security_api):
    api, db, data = mobile_security_api
    context, _own, _ = mobile(api, db, data["staff"])
    _ctx, admin_credential, _ = mobile(api, db, data["admin"])
    request = new_request(db, data["staff"])
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=context,
               biometric_credential=admin_credential) == "strong_auth_failed"


def test_approve_rejects_credential_from_a_different_device(mobile_security_api):
    api, db, data = mobile_security_api
    context, _own, _ = mobile(api, db, data["staff"], DEVICE)
    _ctx, credential_b, _ = mobile(api, db, data["staff"], DEVICE_B)
    request = new_request(db, data["staff"])
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=context,
               biometric_credential=credential_b) == "strong_auth_failed"
    assert db.scalar(select(AssistantAccountLink.id)) is None


def test_approve_rejects_revoked_or_expired_biometric_credential(mobile_security_api):
    api, db, data = mobile_security_api
    context, credential, _ = mobile(api, db, data["staff"])
    record = db.scalar(select(MobileBiometricCredential))
    request = new_request(db, data["staff"])
    record.expires_at = utc_now() - timedelta(seconds=1)
    db.commit()
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=context,
               biometric_credential=credential) == "strong_auth_failed"
    record.expires_at = utc_now() + timedelta(days=1)
    record.revoked_at = utc_now()
    db.commit()
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=context,
               biometric_credential=credential) == "strong_auth_failed"


def test_approve_requires_live_mobile_session_and_internal_actor(mobile_security_api):
    api, db, data = mobile_security_api
    context, credential, _ = mobile(api, db, data["staff"])
    request = new_request(db, data["staff"])
    from dataclasses import replace
    assert err(svc.approve_link_request, db, public_id=request.public_id,
               context=replace(context, mobile_session_id=None), biometric_credential=credential) == "forbidden"
    assert err(svc.approve_link_request, db, public_id=request.public_id,
               context=replace(context, actor_type="client"), biometric_credential=credential) == "forbidden"
    from app.models.mobile_auth_session import MobileAuthSession
    session = db.get(MobileAuthSession, context.mobile_session_id)
    session.revoked_at = utc_now()
    db.commit()
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=context,
               biometric_credential=credential) == "forbidden"


def test_non_candidate_cannot_approve_even_with_valid_biometric(mobile_security_api):
    api, db, data = mobile_security_api
    admin_context, admin_credential, _ = mobile(api, db, data["admin"])
    request = new_request(db, data["staff"])
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=admin_context,
               biometric_credential=admin_credential) == "not_found"
    assert db.scalar(select(AssistantAccountLink.id)) is None


def test_expired_request_cannot_be_approved(mobile_security_api):
    api, db, data = mobile_security_api
    context, credential, _ = mobile(api, db, data["staff"])
    request = new_request(db, data["staff"])
    row(db, request).expires_at = utc_now() - timedelta(seconds=1)
    db.commit()
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=context,
               biometric_credential=credential) == "expired"
    assert row(db, request).status == "expired" and row(db, request).comparison_code is None and db.scalar(select(AssistantAccountLink.id)) is None
    assert code_of(db, "assistant_link.request_expired")


def test_double_approval_creates_a_single_link(mobile_security_api):
    api, db, data = mobile_security_api
    context, credential, _ = mobile(api, db, data["staff"])
    request = new_request(db, data["staff"])
    svc.approve_link_request(db, public_id=request.public_id, context=context, biometric_credential=credential)
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=context,
               biometric_credential=credential) == "not_pending"
    assert len(db.scalars(select(AssistantAccountLink)).all()) == 1


def test_approve_rechecks_account_and_existing_links(mobile_security_api):
    api, db, data = mobile_security_api
    context, credential, _ = mobile(api, db, data["staff"])
    request = new_request(db, data["staff"])
    data["staff"].status = "disabled"
    db.commit()
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=context,
               biometric_credential=credential) == "strong_auth_failed"  # biometric authority denies it first
    data["staff"].status = "active"
    db.commit()
    # Telegram identity linked elsewhere while this request was pending.
    db.add(AssistantAccountLink(user_id=data["admin"].id, telegram_user_id=TG, telegram_chat_id=TG,
                                link_request_id=request.id, status="active", linked_at=utc_now()))
    db.commit()
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=context,
               biometric_credential=credential) == "already_linked"


def test_unknown_request_is_denied_and_audited(mobile_security_api):
    api, db, data = mobile_security_api
    context, credential, _ = mobile(api, db, data["staff"])
    assert err(svc.approve_link_request, db, public_id="missing", context=context,
               biometric_credential=credential) == "not_found"
    assert code_of(db, "assistant_link.approve_denied") == []


# --- reject -------------------------------------------------------------------

def test_reject_by_candidate_only_and_final(mobile_security_api):
    api, db, data = mobile_security_api
    context, credential, _ = mobile(api, db, data["staff"])
    other_context, _c, _ = mobile(api, db, data["admin"])
    request = new_request(db, data["staff"])
    assert err(svc.reject_link_request, db, public_id=request.public_id, context=other_context) == "not_found"
    assert svc.reject_link_request(db, public_id=request.public_id, context=context).status == "rejected"
    assert code_of(db, "assistant_link.rejected")
    assert err(svc.reject_link_request, db, public_id=request.public_id, context=context) == "not_pending"
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=context,
               biometric_credential=credential) == "not_pending"


# --- revoke / resolve ---------------------------------------------------------

def _linked(api, db, user, tg=TG):
    context, credential, _ = mobile(api, db, user)
    request = new_request(db, user, tg)
    return svc.approve_link_request(db, public_id=request.public_id, context=context, biometric_credential=credential)


def test_owner_and_admin_can_revoke_strangers_cannot(mobile_security_api):
    api, db, data = mobile_security_api
    link = _linked(api, db, data["staff"])
    assert err(svc.revoke_link, db, link_id=link.id, actor=data["staff_without_mobile"]) == "not_found"
    assert err(svc.revoke_link, db, link_id=9999, actor=data["staff"]) == "not_found"
    revoked = svc.revoke_link(db, link_id=link.id, actor=data["staff"])
    assert (revoked.status, revoked.revocation_reason, revoked.revoked_by_user_id) == ("revoked", "user", data["staff"].id)
    assert svc.resolve_active_link(db, telegram_user_id=TG, telegram_chat_id=TG) is None
    assert err(svc.revoke_link, db, link_id=link.id, actor=data["staff"]) == "not_active"
    assert code_of(db, "assistant_link.revoked")

    again = _linked(api, db, data["staff"], TG_OTHER)
    admin_revoked = svc.revoke_link(db, link_id=again.id, actor=data["admin"])
    assert admin_revoked.revocation_reason == "admin"


def test_relink_after_revocation_keeps_history(mobile_security_api):
    api, db, data = mobile_security_api
    link = _linked(api, db, data["staff"])
    svc.revoke_link(db, link_id=link.id, actor=data["staff"])
    second = _linked(api, db, data["staff"])
    rows = db.scalars(select(AssistantAccountLink)).all()
    assert sorted(r.status for r in rows) == ["active", "revoked"] and second.id != link.id


def test_resolve_denies_when_account_no_longer_linkable(mobile_security_api):
    api, db, data = mobile_security_api
    _linked(api, db, data["staff"])
    assert svc.resolve_active_link(db, telegram_user_id=TG, telegram_chat_id=TG) is not None
    assert svc.resolve_active_link(db, telegram_user_id=TG, telegram_chat_id=TG + 1) is None
    data["staff"].status = "disabled"
    db.commit()
    assert svc.resolve_active_link(db, telegram_user_id=TG, telegram_chat_id=TG) is None


def test_cannot_link_when_user_or_telegram_already_linked(mobile_security_api):
    api, db, data = mobile_security_api
    _linked(api, db, data["staff"])
    assert err(new_request, db, data["staff"], TG_OTHER) == "already_linked"
    assert err(new_request, db, data["admin"], TG) == "already_linked"


# --- storage backstops --------------------------------------------------------

def test_database_rejects_duplicate_active_links_and_pending_requests(mobile_security_api):
    api, db, data = mobile_security_api
    link = _linked(api, db, data["staff"])

    def raw_link(user, tg, request_id):
        return AssistantAccountLink(user_id=user.id, telegram_user_id=tg, telegram_chat_id=tg,
                                    link_request_id=request_id, status="active", linked_at=utc_now())
    spare = [new_request(db, data["admin"], 700_000_010 + i) for i in range(3)]
    for bad in (raw_link(data["staff"], 700_000_099, spare[0].id),   # same MYC user
                raw_link(data["admin"], TG, spare[1].id)):           # same Telegram identity
        db.add(bad)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    db.add(AssistantLinkRequest(public_id="dup", telegram_user_id=700_000_010, telegram_chat_id=700_000_010,
                                candidate_user_id=data["admin"].id, status="pending",
                                comparison_code="123456", expires_at=utc_now() + timedelta(minutes=5)))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert link.status == "active"


def test_database_check_constraints(mobile_security_api):
    api, db, data = mobile_security_api
    base = dict(telegram_user_id=1, telegram_chat_id=1, candidate_user_id=data["staff"].id,
                expires_at=utc_now() + timedelta(minutes=5))
    for bad in (dict(public_id="a", status="pending", comparison_code="12345"),
                dict(public_id="b", status="bogus", comparison_code="123456"),
                dict(public_id="c", status="approved", comparison_code="123456", decided_at=utc_now())):
        db.add(AssistantLinkRequest(**base, **bad))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


# --- 1A.1: code lifecycle, transactions, admin hardening ------------------------

def test_comparison_code_is_sanitized_in_every_terminal_state(mobile_security_api):
    api, db, data = mobile_security_api
    ctx, credential, _ = mobile(api, db, data["staff"])
    # approved
    approved = new_request(db, data["staff"], TG)
    assert approved.comparison_code and row(db, approved).comparison_code
    svc.approve_link_request(db, public_id=approved.public_id, context=ctx, biometric_credential=credential)
    # rejected
    rejected = new_request(db, data["admin"], TG_OTHER)
    admin_ctx, _c, _ = mobile(api, db, data["admin"])
    svc.reject_link_request(db, public_id=rejected.public_id, context=admin_ctx)
    # superseded + expired
    first = new_request(db, data["admin"], TG + 10)
    second = new_request(db, data["admin"], TG + 10)
    row(db, second).expires_at = utc_now() - timedelta(seconds=1)
    db.commit()
    new_request(db, data["admin"], TG + 11)  # create settles the stale pending of its candidate
    states = {v.id: row(db, v) for v in (approved, rejected, first, second)}
    assert [r.status for r in states.values()] == ["approved", "rejected", "superseded", "expired"]
    assert all(r.comparison_code is None for r in states.values())
    for view in (approved, rejected, first, second):
        seen = svc.get_request_for_telegram(db, public_id=view.public_id,
                                            telegram_user_id=view.telegram_user_id,
                                            telegram_chat_id=view.telegram_chat_id)
        assert seen.comparison_code is None


def test_code_visible_only_through_identity_checked_readers_while_pending(mobile_security_api):
    api, db, data = mobile_security_api
    created = new_request(db, data["staff"])
    by_user = svc.get_request_for_candidate(db, public_id=created.public_id, user=data["staff"])
    by_tg = svc.get_request_for_telegram(db, public_id=created.public_id, telegram_user_id=TG, telegram_chat_id=TG)
    assert by_user.comparison_code == by_tg.comparison_code == created.comparison_code
    assert err(svc.get_request_for_candidate, db, public_id=created.public_id, user=data["admin"]) == "not_found"
    assert not hasattr(svc, "get_comparison_code")


def test_code_never_reaches_audit_or_logs(mobile_security_api, caplog):
    api, db, data = mobile_security_api
    caplog.set_level("DEBUG")
    ctx, credential, _ = mobile(api, db, data["staff"])
    created = new_request(db, data["staff"])
    code = created.comparison_code
    err(svc.approve_link_request, db, public_id=created.public_id, context=ctx, biometric_credential="x" * 40)
    svc.approve_link_request(db, public_id=created.public_id, context=ctx, biometric_credential=credential)
    err(svc.approve_link_request, db, public_id=created.public_id, context=ctx, biometric_credential=credential)
    blob = " ".join(f"{r.action} {r.new_values} {r.comment}" for r in db.scalars(select(AuditLog)).all())
    assert f"'{code}'" not in blob and f'"{code}"' not in blob and "comparison" not in blob
    assert code not in caplog.text


def test_denial_never_commits_pending_changes_of_the_session(mobile_security_api):
    api, db, data = mobile_security_api
    ctx, _credential, _ = mobile(api, db, data["staff"])
    created = new_request(db, data["staff"])
    db.add(AuditLog(action="unrelated.marker", entity="marker", entity_id=None))  # pending, uncommitted
    assert err(svc.approve_link_request, db, public_id=created.public_id, context=ctx,
               biometric_credential="x" * 40) == "strong_auth_failed"
    assert code_of(db, "unrelated.marker") == []
    assert code_of(db, "assistant_link.approve_denied") == []  # denial auditing belongs to the adapter


def test_integrity_error_rolls_back_without_partial_commit(mobile_security_api, monkeypatch):
    api, db, data = mobile_security_api
    first = _linked(api, db, data["staff"])  # TG is now actively linked
    ctx, credential, _ = mobile(api, db, data["admin"])
    request = new_request(db, data["admin"], TG_OTHER)
    # Make the pre-check blind so only the unique index can stop the insert.
    monkeypatch.setattr(svc, "_active_link_exists", lambda *a, **k: False)
    row(db, request).telegram_user_id = TG  # collide with the active Telegram identity
    row(db, request).telegram_chat_id = TG
    db.commit()
    db.add(AuditLog(action="unrelated.marker", entity="marker", entity_id=None))
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=ctx,
               biometric_credential=credential) == "already_linked"
    after = row(db, request)
    assert after.status == "pending" and after.approved_by_user_id is None
    assert len(db.scalars(select(AssistantAccountLink)).all()) == 1 and first.status == "active"
    assert code_of(db, "assistant_link.approved") and len(code_of(db, "assistant_link.approved")) == 1
    assert code_of(db, "unrelated.marker") == []


def test_account_disabled_during_approval_is_denied(mobile_security_api, monkeypatch):
    api, db, data = mobile_security_api
    ctx, credential, _ = mobile(api, db, data["staff"])
    request = new_request(db, data["staff"])
    real = svc.resolve_biometric_credential

    def resolve_then_disable(session, value):
        resolved = real(session, value)
        data["staff"].status = "disabled"  # account disabled right after biometric success
        session.commit()
        return resolved

    monkeypatch.setattr(svc, "resolve_biometric_credential", resolve_then_disable)
    assert err(svc.approve_link_request, db, public_id=request.public_id, context=ctx,
               biometric_credential=credential) == "invalid_account"
    assert row(db, request).status == "pending" and db.scalar(select(AssistantAccountLink.id)) is None


def test_admin_revocation_requires_active_internal_admin(mobile_security_api):
    api, db, data = mobile_security_api
    link = _linked(api, db, data["staff"])
    admin = data["admin"]
    admin.status = "suspended"
    db.commit()
    assert err(svc.revoke_link, db, link_id=link.id, actor=admin) == "not_found"
    admin.status = "active"
    admin.account_type = "client_portal"
    db.commit()
    assert err(svc.revoke_link, db, link_id=link.id, actor=admin) == "not_found"
    admin.account_type = "internal"
    db.commit()
    assert svc.get_active_link_for_user(db, user=data["staff"]).id == link.id
    assert svc.revoke_link(db, link_id=link.id, actor=admin).revocation_reason == "admin"


def test_owner_revocation_requires_active_account(mobile_security_api):
    api, db, data = mobile_security_api
    link = _linked(api, db, data["staff"])
    data["staff"].status = "suspended"
    db.commit()
    assert err(svc.revoke_link, db, link_id=link.id, actor=data["staff"]) == "not_found"
    data["staff"].status = "active"
    db.commit()
    assert svc.revoke_link(db, link_id=link.id, actor=data["staff"]).revocation_reason == "user"


def test_terminal_request_with_code_is_rejected_by_database(mobile_security_api):
    api, db, data = mobile_security_api
    db.add(AssistantLinkRequest(public_id="t1", telegram_user_id=1, telegram_chat_id=1,
                                candidate_user_id=data["staff"].id, status="rejected", comparison_code="123456",
                                decided_at=utc_now(), expires_at=utc_now() + timedelta(minutes=5)))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_record_link_denial_is_independent_and_best_effort(mobile_security_api):
    from sqlalchemy.orm import sessionmaker
    api, db, data = mobile_security_api
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    assert svc.record_link_denial(action="assistant_link.approve_denied", code="not_found",
                                  user_id=data["staff"].id, session_factory=factory) is True
    rows = code_of(db, "assistant_link.approve_denied")
    assert len(rows) == 1 and rows[0].new_values == {"reason": "not_found"}
    # Any audit-store failure is reported, never raised or masked.
    from sqlalchemy.exc import OperationalError

    def broken_factory():
        raise OperationalError("connect", {}, Exception("audit store down"))
    assert svc.record_link_denial(action="assistant_link.approve_denied", code="not_found",
                                  session_factory=broken_factory) is False
    assert len(code_of(db, "assistant_link.approve_denied")) == 1


def test_unexpected_failure_rolls_back_and_releases_state(mobile_security_api, monkeypatch):
    api, db, data = mobile_security_api
    ctx, credential, _ = mobile(api, db, data["staff"])
    request = new_request(db, data["staff"])
    real_audit = svc._audit

    def failing_audit(session, action, *a, **k):
        if action == "assistant_link.created":
            raise RuntimeError("audit store down")
        return real_audit(session, action, *a, **k)

    monkeypatch.setattr(svc, "_audit", failing_audit)
    with pytest.raises(RuntimeError):
        svc.approve_link_request(db, public_id=request.public_id, context=ctx, biometric_credential=credential)
    assert row(db, request).status == "pending" and db.scalar(select(AssistantAccountLink.id)) is None
    assert code_of(db, "assistant_link.approved") == []
    monkeypatch.setattr(svc, "_audit", real_audit)
    assert svc.approve_link_request(db, public_id=request.public_id, context=ctx,
                                    biometric_credential=credential).status == "active"


def test_direct_domain_error_rolls_back_pending_changes(mobile_security_api):
    api, db, data = mobile_security_api
    db.add(AuditLog(action="unrelated.direct_error_marker", entity="marker", entity_id=None))
    assert err(
        svc.create_link_request,
        db,
        telegram_user_id=TG,
        telegram_chat_id=TG + 1,
        candidate_user_id=data["staff"].id,
    ) == "invalid_identity"
    assert not db.in_transaction()
    assert code_of(db, "unrelated.direct_error_marker") == []


def test_missing_strong_auth_rolls_back_pending_changes(mobile_security_api):
    api, db, data = mobile_security_api
    ctx, _credential, _ = mobile(api, db, data["staff"])
    request = new_request(db, data["staff"])
    db.add(AuditLog(action="unrelated.strong_auth_marker", entity="marker", entity_id=None))
    assert err(
        svc.approve_link_request,
        db,
        public_id=request.public_id,
        context=ctx,
        biometric_credential="",
    ) == "strong_auth_required"
    assert not db.in_transaction()
    assert code_of(db, "unrelated.strong_auth_marker") == []


def test_denial_audit_error_does_not_log_database_parameters(mobile_security_api, caplog):
    from sqlalchemy.exc import OperationalError

    def broken_factory():
        raise OperationalError("SENSITIVE_SQL_STATEMENT", {"token": "SENSITIVE_VALUE"}, Exception("down"))

    with caplog.at_level("WARNING", logger=svc.__name__):
        assert svc.record_link_denial(
            action="assistant_link.approve_denied", code="not_found", session_factory=broken_factory
        ) is False
    assert "assistant link denial audit could not be persisted" in caplog.text
    assert "SENSITIVE_SQL_STATEMENT" not in caplog.text
    assert "SENSITIVE_VALUE" not in caplog.text
