"""MYC-ASSISTANT-1A: real PostgreSQL row locking and migration reversibility.

Requires ASSISTANT_LINK_POSTGRES_TEST_URL pointing at a database already
migrated to the Alembic head (never the development database)."""
import importlib.util
import os
import threading
import time
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from app.core.login_policy import utc_now
from app.core.mobile.biometric_credentials import generate_biometric_credential, hash_biometric_credential
from app.core.mobile.security import MobileSecurityContext
from app.core.security import hash_password
from app.models.assistant_account_link import AssistantAccountLink
from app.models.assistant_link_request import AssistantLinkRequest
from app.models.mobile_auth_session import MobileAuthSession
from app.models.mobile_biometric_credential import MobileBiometricCredential
from app.models.mobile_trusted_device import MobileTrustedDevice
from app.models.user import User
from app.services import assistant_account_linking as svc
from app.services.assistant_account_linking import AssistantLinkError

MIGRATION_FILE = "b7d2e4a6c8f1_assistant_account_linking.py"
TABLES = {"assistant_link_requests", "assistant_account_links"}


@pytest.fixture(scope="module")
def pg_engine():
    url = os.getenv("ASSISTANT_LINK_POSTGRES_TEST_URL")
    if not url:
        pytest.skip("requires ASSISTANT_LINK_POSTGRES_TEST_URL for real PostgreSQL locking")
    # Bounded waits for the whole suite: a lock/statement that hangs fails instead of freezing CI.
    engine = create_engine(url, connect_args={"options": "-c lock_timeout=20000 -c statement_timeout=40000"})
    assert "test" in (engine.url.database or ""), "refusing to run against a non-test database"
    assert TABLES <= set(inspect(engine).get_table_names()), "database is not migrated to head"
    yield engine
    engine.dispose()


def _mobile_actor(engine):
    """Committed internal user + trusted device + session + biometric credential."""
    suffix = uuid4().hex[:10]
    credential = generate_biometric_credential()
    with Session(engine) as db:
        user = User(username=f"pg-{suffix}@myc.example.com", email=f"pg-{suffix}@myc.example.com",
                    full_name="PG Linker", hashed_password=hash_password("x"),
                    account_type="internal", status="active")
        db.add(user)
        db.flush()
        now = utc_now()
        device = MobileTrustedDevice(user_id=user.id, device_uuid=uuid4().hex, platform="ios",
                                     trusted_at=now, last_seen_at=now)
        db.add(device)
        db.flush()
        session = MobileAuthSession(user_id=user.id, device_id=device.id, family_id=str(uuid4()),
                                    refresh_token_hash=uuid4().hex + uuid4().hex, actor_type="internal",
                                    last_used_at=now, expires_at=now + timedelta(days=1))
        db.add(session)
        db.add(MobileBiometricCredential(user_id=user.id, device_id=device.id,
                                         credential_hash=hash_biometric_credential(credential),
                                         last_used_at=now, expires_at=now + timedelta(days=1)))
        db.commit()
        return user.id, session.id, credential


def _tg() -> int:
    return int(uuid4().int % 10**12) + 1


def test_concurrent_approvals_create_exactly_one_link(pg_engine):
    user_id, session_id, credential = _mobile_actor(pg_engine)
    tg = _tg()
    with Session(pg_engine) as db:
        request = svc.create_link_request(db, telegram_user_id=tg, telegram_chat_id=tg, candidate_user_id=user_id)
        public_id = request.public_id
    workers = 6
    barrier = Barrier(workers)

    def attempt(_):
        with Session(pg_engine) as db:
            context = MobileSecurityContext(user=db.get(User, user_id), actor_type="internal",
                                            permissions=frozenset(), mobile_session_id=session_id)
            barrier.wait()
            try:
                svc.approve_link_request(db, public_id=public_id, context=context, biometric_credential=credential)
                return "ok"
            except AssistantLinkError as exc:
                return exc.code

    with ThreadPoolExecutor(workers) as pool:
        outcomes = list(pool.map(attempt, range(workers)))
    assert outcomes.count("ok") == 1, outcomes
    assert set(outcomes) - {"ok"} <= {"not_pending", "already_linked"}, outcomes
    with Session(pg_engine) as db:
        assert db.scalar(select(func.count()).select_from(AssistantAccountLink)
                         .where(AssistantAccountLink.user_id == user_id)) == 1


def test_concurrent_requests_for_one_telegram_identity_leave_one_pending(pg_engine):
    users = [_mobile_actor(pg_engine)[0] for _ in range(4)]
    tg = _tg()
    barrier = Barrier(len(users))

    def attempt(user_id):
        with Session(pg_engine) as db:
            barrier.wait()
            try:
                svc.create_link_request(db, telegram_user_id=tg, telegram_chat_id=tg, candidate_user_id=user_id)
                return "ok"
            except AssistantLinkError as exc:
                return exc.code

    with ThreadPoolExecutor(len(users)) as pool:
        outcomes = list(pool.map(attempt, users))
    assert "ok" in outcomes and set(outcomes) <= {"ok", "conflict"}, outcomes
    with Session(pg_engine) as db:
        assert db.scalar(select(func.count()).select_from(AssistantLinkRequest).where(
            AssistantLinkRequest.telegram_user_id == tg, AssistantLinkRequest.status == "pending")) == 1


def test_migration_downgrade_and_upgrade_are_reversible(pg_engine):
    path = Path(__file__).parents[1] / "migrations/versions" / MIGRATION_FILE
    spec = importlib.util.spec_from_file_location("assistant_link_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with pg_engine.connect() as connection:
        transaction = connection.begin()  # PostgreSQL DDL is transactional: rolled back below
        try:
            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
                assert not TABLES & set(inspect(connection).get_table_names())
                migration.upgrade()
                assert TABLES <= set(inspect(connection).get_table_names())
        finally:
            transaction.rollback()


# --- 1A.1 race matrix ----------------------------------------------------------

ROUNDS = 8


def _race(engine, *jobs):
    """Runs each job(db) in its own Session/thread, released together by a
    barrier. Returns "ok" or the AssistantLinkError code per job; any other
    exception (deadlock, IntegrityError leak, ...) propagates and fails the test."""
    barrier = Barrier(len(jobs))

    def run(job):
        with Session(engine) as db:
            barrier.wait()
            try:
                job(db)
                return "ok"
            except AssistantLinkError as exc:
                return exc.code

    with ThreadPoolExecutor(len(jobs)) as pool:
        futures = [pool.submit(run, job) for job in jobs]
        return [future.result(timeout=30) for future in futures]


def _ctx(db, user_id, session_id):
    return MobileSecurityContext(user=db.get(User, user_id), actor_type="internal",
                                 permissions=frozenset(), mobile_session_id=session_id)


def _approve(user_id, session_id, credential, public_id):
    def job(db):
        svc.approve_link_request(db, public_id=public_id, context=_ctx(db, user_id, session_id),
                                 biometric_credential=credential)
    return job


def _create(user_id, tg):
    def job(db):
        svc.create_link_request(db, telegram_user_id=tg, telegram_chat_id=tg, candidate_user_id=user_id)
    return job


def _new(engine, user_id, tg):
    with Session(engine) as db:
        return svc.create_link_request(db, telegram_user_id=tg, telegram_chat_id=tg, candidate_user_id=user_id)


def _active_links(engine, **where):
    with Session(engine) as db:
        return db.scalars(select(AssistantAccountLink).where(
            AssistantAccountLink.status == "active",
            *[getattr(AssistantAccountLink, k) == v for k, v in where.items()])).all()


def test_create_and_approve_concurrently_for_one_user_never_deadlock(pg_engine):
    for _ in range(ROUNDS):
        user_id, session_id, credential = _mobile_actor(pg_engine)
        first = _new(pg_engine, user_id, _tg())
        outcomes = _race(pg_engine, _approve(user_id, session_id, credential, first.public_id),
                         _create(user_id, _tg()))
        assert outcomes[0] == "ok" and outcomes[1] in {"ok", "already_linked"}, outcomes
        assert len(_active_links(pg_engine, user_id=user_id)) == 1


def test_approve_and_reject_concurrently_decide_exactly_once(pg_engine):
    def reject(user_id, session_id, public_id):
        def job(db):
            svc.reject_link_request(db, public_id=public_id, context=_ctx(db, user_id, session_id))
        return job

    for _ in range(ROUNDS):
        user_id, session_id, credential = _mobile_actor(pg_engine)
        request = _new(pg_engine, user_id, _tg())
        outcomes = _race(pg_engine, _approve(user_id, session_id, credential, request.public_id),
                         reject(user_id, session_id, request.public_id))
        assert sorted(outcomes) == ["not_pending", "ok"], outcomes
        with Session(pg_engine) as db:
            row = db.get(AssistantLinkRequest, request.id)
            links = len(_active_links(pg_engine, user_id=user_id))
            assert (row.status, links) in {("approved", 1), ("rejected", 0)}
            assert row.comparison_code is None


def test_reads_never_transition_and_approval_during_expiry_is_decided_under_lock(pg_engine):
    def read(user_id, request, tg):
        def job(db):
            seen = svc.get_request_for_telegram(db, public_id=request.public_id, telegram_user_id=tg,
                                                telegram_chat_id=tg)
            assert seen.comparison_code is None
        return job

    # (a) a decided request whose expires_at later passes is never flipped to "expired" by readers
    user_id, session_id, credential = _mobile_actor(pg_engine)
    tg = _tg()
    request = _new(pg_engine, user_id, tg)
    with Session(pg_engine) as db:
        _approve(user_id, session_id, credential, request.public_id)(db)
    with Session(pg_engine) as db:
        db.get(AssistantLinkRequest, request.id).expires_at = utc_now() - timedelta(minutes=1)
        db.commit()
    assert set(_race(pg_engine, *[read(user_id, request, tg)] * 6)) == {"ok"}
    with Session(pg_engine) as db:
        assert db.get(AssistantLinkRequest, request.id).status == "approved"

    # (b) pending but past expiry: readers see "expired" without writing; approval settles it once
    user_id, session_id, credential = _mobile_actor(pg_engine)
    tg = _tg()
    request = _new(pg_engine, user_id, tg)
    with Session(pg_engine) as db:
        db.get(AssistantLinkRequest, request.id).expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
    def expired_audits():
        with Session(pg_engine) as db:
            from app.models.audit_log import AuditLog
            return db.scalar(select(func.count()).select_from(AuditLog).where(
                AuditLog.action == "assistant_link.request_expired", AuditLog.entity_id == request.id))

    audits_before = expired_audits()  # table ids may be reused across migration cycles
    outcomes = _race(pg_engine, *[read(user_id, request, tg)] * 4,
                     _approve(user_id, session_id, credential, request.public_id))
    assert outcomes == ["ok"] * 4 + ["expired"], outcomes
    with Session(pg_engine) as db:
        assert db.get(AssistantLinkRequest, request.id).status == "expired"
    assert expired_audits() - audits_before == 1
    assert _active_links(pg_engine, user_id=user_id) == []


def test_two_telegram_identities_cannot_both_link_one_user(pg_engine):
    for _ in range(ROUNDS):
        user_id, session_id, credential = _mobile_actor(pg_engine)
        a, b = _new(pg_engine, user_id, _tg()), _new(pg_engine, user_id, _tg())
        outcomes = _race(pg_engine, _approve(user_id, session_id, credential, a.public_id),
                         _approve(user_id, session_id, credential, b.public_id))
        assert sorted(outcomes) == ["already_linked", "ok"], outcomes
        assert len(_active_links(pg_engine, user_id=user_id)) == 1


def test_two_users_cannot_both_link_one_telegram_identity(pg_engine):
    for _ in range(ROUNDS):
        (ua, sa, ca), (ub, _sb, _cb) = _mobile_actor(pg_engine), _mobile_actor(pg_engine)
        tg = _tg()
        request_a = _new(pg_engine, ua, tg)
        outcomes = _race(pg_engine, _approve(ua, sa, ca, request_a.public_id), _create(ub, tg))
        assert outcomes[0] in {"ok", "not_pending"} and outcomes[1] in {"ok", "already_linked"}, outcomes
        assert len(_active_links(pg_engine, telegram_user_id=tg)) <= 1
        with Session(pg_engine) as db:
            assert db.scalar(select(func.count()).select_from(AssistantLinkRequest).where(
                AssistantLinkRequest.telegram_user_id == tg, AssistantLinkRequest.status == "pending")) <= 1


def test_database_matches_migrated_constraints(pg_engine):
    insp = inspect(pg_engine)
    uniques = {ix["name"]: ix for t in TABLES for ix in insp.get_indexes(t) if ix["unique"]}
    for name in ("uq_assistant_link_requests_pending_telegram", "uq_assistant_links_active_user",
                 "uq_assistant_links_active_telegram_user", "uq_assistant_links_active_telegram_chat"):
        assert name in uniques and "status" in uniques[name]["dialect_options"]["postgresql_where"]
    checks = {c["name"] for t in TABLES for c in insp.get_check_constraints(t)}
    assert {"ck_assistant_link_request_status", "ck_assistant_link_request_code", "ck_assistant_link_request_decided",
            "ck_assistant_link_request_approver", "ck_assistant_account_link_status",
            "ck_assistant_account_link_revocation"} <= checks
    fk = {(t, f["referred_table"]) for t in TABLES for f in insp.get_foreign_keys(t)}
    assert {("assistant_link_requests", "users"), ("assistant_link_requests", "mobile_trusted_devices"),
            ("assistant_account_links", "users"), ("assistant_account_links", "assistant_link_requests")} <= fk


# --- 1A.2 deterministic interleavings --------------------------------------------

def _overlap(engine, monkeypatch, hook, job_a, job_b):
    """Thread A runs ``job_a`` and is parked INSIDE service function ``hook``
    (after it acquired its locks); thread B then starts ``job_b``. B must be
    blocked while A is parked. Releases A and returns (outcome_a, outcome_b)."""
    reached, release = threading.Event(), threading.Event()
    real = getattr(svc, hook)

    def parked(*args, **kwargs):
        result = real(*args, **kwargs)
        if threading.current_thread().name == "parked-a":
            reached.set()
            assert release.wait(15), "test harness never released the parked transaction"
        return result

    monkeypatch.setattr(svc, hook, parked)
    results = {}

    def run(key, job):
        with Session(engine) as db:
            try:
                job(db)
                results[key] = "ok"
            except AssistantLinkError as exc:
                results[key] = exc.code
            except BaseException as exc:  # surfaced by the assertions below
                results[key] = exc

    thread_a = threading.Thread(target=run, args=("a", job_a), name="parked-a")
    thread_b = threading.Thread(target=run, args=("b", job_b), name="runner-b")
    thread_a.start()
    assert reached.wait(15), "A never reached the critical section"
    thread_b.start()
    time.sleep(0.7)
    assert "b" not in results, f"B was not blocked by A's locks: {results}"
    release.set()
    thread_a.join(20)
    thread_b.join(20)
    assert not thread_a.is_alive() and not thread_b.is_alive(), "transactions did not finish"
    return results["a"], results["b"]


def _revoke(actor_id, link_id):
    def job(db):
        svc.revoke_link(db, link_id=link_id, actor=db.get(User, actor_id))
    return job


def _link_for(engine, user_id, session_id, credential, tg):
    request = _new(engine, user_id, tg)
    with Session(engine) as db:
        return svc.approve_link_request(db, public_id=request.public_id, context=_ctx(db, user_id, session_id),
                                        biometric_credential=credential).id


def _pending_and_link(engine, user_id, session_id, credential):
    """A still-pending request plus an already active link (requests cannot be opened once linked)."""
    pending = _new(engine, user_id, _tg())
    return pending, _link_for(engine, user_id, session_id, credential, _tg())


def test_create_waits_for_approve_then_sees_the_new_link(pg_engine, monkeypatch):
    user_id, session_id, credential = _mobile_actor(pg_engine)
    request = _new(pg_engine, user_id, _tg())
    a, b = _overlap(pg_engine, monkeypatch, "_lock_request",
                    _approve(user_id, session_id, credential, request.public_id), _create(user_id, _tg()))
    assert (a, b) == ("ok", "already_linked")
    assert len(_active_links(pg_engine, user_id=user_id)) == 1


def test_two_requests_for_one_user_serialize_to_a_single_link(pg_engine, monkeypatch):
    user_id, session_id, credential = _mobile_actor(pg_engine)
    first, second = _new(pg_engine, user_id, _tg()), _new(pg_engine, user_id, _tg())
    a, b = _overlap(pg_engine, monkeypatch, "_lock_request",
                    _approve(user_id, session_id, credential, first.public_id),
                    _approve(user_id, session_id, credential, second.public_id))
    assert (a, b) == ("ok", "already_linked")
    assert len(_active_links(pg_engine, user_id=user_id)) == 1
    with Session(pg_engine) as db:
        assert db.get(AssistantLinkRequest, second.id).status == "pending"  # untouched by the denied approval


def test_approve_blocked_behind_revoke_then_links_again(pg_engine, monkeypatch):
    user_id, session_id, credential = _mobile_actor(pg_engine)
    pending, old_link = _pending_and_link(pg_engine, user_id, session_id, credential)
    a, b = _overlap(pg_engine, monkeypatch, "_lock_link", _revoke(user_id, old_link),
                    _approve(user_id, session_id, credential, pending.public_id))
    assert (a, b) == ("ok", "ok")
    active = _active_links(pg_engine, user_id=user_id)
    assert len(active) == 1 and active[0].id != old_link
    with Session(pg_engine) as db:
        assert db.get(AssistantAccountLink, old_link).status == "revoked"


def test_revoke_blocked_behind_approve_that_is_denied(pg_engine, monkeypatch):
    user_id, session_id, credential = _mobile_actor(pg_engine)
    pending, old_link = _pending_and_link(pg_engine, user_id, session_id, credential)
    a, b = _overlap(pg_engine, monkeypatch, "_lock_request",
                    _approve(user_id, session_id, credential, pending.public_id), _revoke(user_id, old_link))
    assert (a, b) == ("already_linked", "ok")  # approve saw the still-active link; revoke then completed
    assert _active_links(pg_engine, user_id=user_id) == []
    with Session(pg_engine) as db:
        link = db.get(AssistantAccountLink, old_link)
        assert (link.status, link.revocation_reason) == ("revoked", "user")
        assert db.get(AssistantLinkRequest, pending.id).status == "pending"
        from app.models.audit_log import AuditLog
        assert db.scalar(select(func.count()).select_from(AuditLog).where(
            AuditLog.action == "assistant_link.revoked", AuditLog.entity_id == old_link)) >= 1


def test_audit_failure_leaves_no_partial_state_and_no_held_locks(pg_engine, monkeypatch):
    user_id, session_id, credential = _mobile_actor(pg_engine)
    request = _new(pg_engine, user_id, _tg())
    real_audit = svc._audit

    def failing(session, action, *a, **k):
        if action == "assistant_link.created":
            raise RuntimeError("audit store down")
        return real_audit(session, action, *a, **k)

    monkeypatch.setattr(svc, "_audit", failing)
    with Session(pg_engine) as db:
        with pytest.raises(RuntimeError):
            svc.approve_link_request(db, public_id=request.public_id, context=_ctx(db, user_id, session_id),
                                     biometric_credential=credential)
    with Session(pg_engine) as db:
        assert db.get(AssistantLinkRequest, request.id).status == "pending"
    assert _active_links(pg_engine, user_id=user_id) == []
    monkeypatch.setattr(svc, "_audit", real_audit)  # rows were unlocked: a retry succeeds immediately
    assert _race(pg_engine, _approve(user_id, session_id, credential, request.public_id)) == ["ok"]


def test_integrity_error_does_not_confirm_partial_state(pg_engine, monkeypatch):
    (ua, sa, ca), (ub, sb, cb) = _mobile_actor(pg_engine), _mobile_actor(pg_engine)
    taken = _tg()
    _link_for(pg_engine, ua, sa, ca, taken)
    request = _new(pg_engine, ub, _tg())
    with Session(pg_engine) as db:  # make B's request collide with A's active identity
        row = db.get(AssistantLinkRequest, request.id)
        row.telegram_user_id = row.telegram_chat_id = taken
        db.commit()
    monkeypatch.setattr(svc, "_active_link_exists", lambda *a, **k: False)  # only the unique index can stop it
    assert _race(pg_engine, _approve(ub, sb, cb, request.public_id)) == ["already_linked"]
    with Session(pg_engine) as db:
        row = db.get(AssistantLinkRequest, request.id)
        assert (row.status, row.approved_by_user_id) == ("pending", None) and row.comparison_code
    assert _active_links(pg_engine, user_id=ub) == []


def test_lock_wait_is_bounded(pg_engine, monkeypatch):
    from sqlalchemy.exc import OperationalError
    user_id, _s, _c = _mobile_actor(pg_engine)
    monkeypatch.setattr(svc, "LOCK_TIMEOUT_MS", 300)
    with Session(pg_engine) as holder:
        holder.execute(select(User).where(User.id == user_id).with_for_update())
        started = time.monotonic()
        tg = _tg()
        with Session(pg_engine) as db:
            with pytest.raises(OperationalError):
                svc.create_link_request(db, telegram_user_id=tg, telegram_chat_id=tg, candidate_user_id=user_id)
        assert time.monotonic() - started < 5
    assert _race(pg_engine, _create(user_id, _tg())) == ["ok"]  # nothing was left locked or half-written


def test_denial_audit_is_independent_of_the_domain_session(pg_engine):
    from sqlalchemy.orm import sessionmaker
    from app.models.audit_log import AuditLog
    user_id, _s, _c = _mobile_actor(pg_engine)
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    marker = f"unrelated.marker.{uuid4().hex}"
    with Session(pg_engine) as domain:
        domain.add(AuditLog(action=marker, entity="marker", entity_id=None))
        domain.flush()  # pending in the domain transaction
        assert svc.record_link_denial(action="assistant_link.approve_denied", code="not_found",
                                      user_id=user_id, session_factory=factory) is True
        assert svc.record_link_denial(action="assistant_link.approve_denied", code="not_found",
                                      user_id=2_000_000_000, session_factory=factory) is False  # dangling FK
        domain.rollback()
    with Session(pg_engine) as db:
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == marker)) == 0
        assert db.scalar(select(func.count()).select_from(AuditLog).where(
            AuditLog.action == "assistant_link.approve_denied", AuditLog.user_id == user_id)) == 1
