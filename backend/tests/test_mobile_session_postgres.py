"""Actual PostgreSQL locks and reversible migration, in a disposable schema."""
import importlib.util
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.mobile import security
from app.core.security import hash_password, create_refresh_token
from app.models.mobile_auth_session import MobileAuthSession
from app.models.user import Role, User
from app.schemas.mobile_auth import MobileSecurityDeviceInput


@pytest.fixture(scope='module')
def pg_engine():
    url = os.getenv('MOBILE_AUTH_POSTGRES_TEST_URL')
    if not url:
        pytest.skip('requires MOBILE_AUTH_POSTGRES_TEST_URL for real PostgreSQL locking')
    schema = f'mobile_auth_test_{uuid4().hex}'
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={'options': f'-csearch_path={schema}'})
    path = Path(__file__).parents[1] / 'migrations/versions/b10a1c202601_mobile_session_authority.py'
    spec = importlib.util.spec_from_file_location('session_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    try:
        # BIOMETRIC-2's mobile_biometric_credentials FKs to mobile_trusted_devices,
        # which this fixture creates via the migration below, not create_all;
        # excluded here too since this file never needs that table to exist.
        Base.metadata.create_all(engine, tables=[table for table in Base.metadata.tables.values()
            if table.name not in {'mobile_auth_sessions', 'mobile_trusted_devices', 'mobile_biometric_credentials'}])
        with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        yield engine, migration
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_migration_upgrade_downgrade_and_constraints(pg_engine):
    engine, migration = pg_engine
    inspector = inspect(engine)
    assert {'mobile_trusted_devices', 'mobile_auth_sessions'} <= set(inspector.get_table_names())
    assert {item['name'] for item in inspector.get_indexes('mobile_auth_sessions')} >= {
        f'ix_mobile_auth_sessions_{name}' for name in ('user_id', 'device_id', 'family_id', 'refresh_token_hash', 'expires_at', 'revoked_at')}
    assert any(item['unique'] and item['column_names'] == ['refresh_token_hash'] for item in inspector.get_indexes('mobile_auth_sessions'))
    assert {tuple(item['constrained_columns']) for item in inspector.get_foreign_keys('mobile_auth_sessions')} >= {('user_id',), ('device_id',), ('replaced_by_id',)}
    with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
        migration.downgrade()
    assert not {'mobile_trusted_devices', 'mobile_auth_sessions'} & set(inspect(engine).get_table_names())
    with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
        migration.upgrade()


def new_login(engine):
    with Session(engine) as db:
        role = db.scalar(select(Role).where(Role.name == 'Tecnico'))
        if role is None:
            role = Role(name='Tecnico', description='Test')
            db.add(role)
            db.flush()
        name = uuid4().hex
        user = User(username=name, email=f'{name}@example.com', full_name='PG Test',
                    hashed_password=hash_password('test-password'), account_type='internal', status='active', roles=[role], role_id=role.id)
        db.add(user)
        db.commit()
        return security.authenticate_mobile_user(db, user.email, 'test-password',
            MobileSecurityDeviceInput(device_uuid=str(uuid4()), platform='ios'))


def concurrent_calls(engine, callbacks):
    def run(callback):
        with Session(engine) as db:
            try:
                return 200, callback(db)
            except HTTPException as exc:
                db.rollback()
                return exc.status_code, None
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, callback) for callback in callbacks]
        return [future.result(timeout=20) for future in futures]


def synchronize(monkeypatch, helper):
    original = getattr(security, helper)
    barrier = Barrier(2)
    def locked(*args):
        barrier.wait(timeout=10)
        return original(*args)
    monkeypatch.setattr(security, helper, locked)


def test_two_rotations_cannot_create_two_valid_successors(pg_engine, monkeypatch):
    engine, _ = pg_engine
    pair = new_login(engine)
    synchronize(monkeypatch, '_lock_device')
    results = concurrent_calls(engine, [lambda db: security.refresh_mobile_tokens(db, pair['refresh_token'])] * 2)
    assert sorted(status for status, _ in results) == [200, 401]
    successor = next(pair for status, pair in results if status == 200)
    with Session(engine) as db:
        root = db.scalar(select(MobileAuthSession).where(MobileAuthSession.refresh_token_hash == security.hash_refresh_credential(pair['refresh_token'])))
        rows = db.scalars(select(MobileAuthSession).where(MobileAuthSession.family_id == root.family_id)).all()
        assert len(rows) == 2
        assert all(row.revoked_at for row in rows)
        assert root.replaced_by_id and root.reuse_detected_at
        with pytest.raises(HTTPException):
            security.resolve_mobile_token(db, successor['access_token'])


def test_reuse_racing_successor_cannot_escape_family_revocation(pg_engine, monkeypatch):
    engine, _ = pg_engine
    first = new_login(engine)
    with Session(engine) as db:
        second = security.refresh_mobile_tokens(db, first['refresh_token'])
    synchronize(monkeypatch, '_lock_device')
    results = concurrent_calls(engine, [
        lambda db: security.refresh_mobile_tokens(db, first['refresh_token']),
        lambda db: security.refresh_mobile_tokens(db, second['refresh_token']),
    ])
    assert results[0][0] == 401
    with Session(engine) as db:
        root = db.scalar(select(MobileAuthSession).where(MobileAuthSession.refresh_token_hash == security.hash_refresh_credential(first['refresh_token'])))
        assert all(row.revoked_at for row in db.scalars(select(MobileAuthSession).where(MobileAuthSession.family_id == root.family_id)))


def test_logout_racing_rotation_revokes_successor(pg_engine, monkeypatch):
    engine, _ = pg_engine
    pair = new_login(engine)
    with Session(engine) as db:
        context = security.resolve_mobile_token(db, pair['access_token'])
    synchronize(monkeypatch, '_lock_device')
    concurrent_calls(engine, [lambda db: security.logout_mobile_session(db, context),
                             lambda db: security.refresh_mobile_tokens(db, pair['refresh_token'])])
    with Session(engine) as db:
        root = db.get(MobileAuthSession, context.mobile_session_id)
        assert all(row.revoked_at for row in db.scalars(select(MobileAuthSession).where(MobileAuthSession.family_id == root.family_id)))


def test_concurrent_legacy_redemption_is_single_use(pg_engine, monkeypatch):
    engine, _ = pg_engine
    pair = new_login(engine)
    with Session(engine) as db:
        context = security.resolve_mobile_token(db, pair['access_token'])
    from datetime import timedelta
    monkeypatch.setattr(security, 'LEGACY_REFRESH_DEADLINE', security.utc_now() + timedelta(days=2))
    old = create_refresh_token(str(context.user.id), {'auth_context': 'mobile_internal',
        'actor_type': 'internal', 'exp': security.utc_now() + timedelta(hours=1)})
    device = MobileSecurityDeviceInput(device_uuid=str(uuid4()), platform='android')
    synchronize(monkeypatch, '_lock_user')
    results = concurrent_calls(engine, [lambda db: security.refresh_mobile_tokens(db, old, device)] * 2)
    assert sorted(status for status, _ in results) == [200, 401]
    with Session(engine) as db:
        roots = db.scalars(select(MobileAuthSession).where(MobileAuthSession.legacy_refresh_token_hash == security.hash_refresh_credential(old))).all()
        assert len(roots) == 1 and roots[0].reuse_detected_at and roots[0].revoked_at


def test_login_and_rotation_do_not_deadlock_on_user_foreign_key(pg_engine, monkeypatch):
    from threading import Event
    engine, _ = pg_engine
    pair = new_login(engine)
    with Session(engine) as db:
        context = security.resolve_mobile_token(db, pair['access_token'])
        row = db.get(MobileAuthSession, context.mobile_session_id)
        device = db.get(security.MobileTrustedDevice, row.device_id)
        metadata = MobileSecurityDeviceInput(device_uuid=device.device_uuid, platform=device.platform)
        email = context.user.email
    login_has_user = Event()
    refresh_has_device = Event()
    resolve_device = security._resolve_device
    lock_device = security._lock_device

    def delayed_device(*args):
        login_has_user.set()  # Login already holds its user registration lock.
        assert refresh_has_device.wait(timeout=10)
        return resolve_device(*args)

    def signaled_device(*args):
        result = lock_device(*args)
        refresh_has_device.set()
        return result

    def rotate(db):
        assert login_has_user.wait(timeout=10)
        return security.refresh_mobile_tokens(db, pair['refresh_token'])

    monkeypatch.setattr(security, '_resolve_device', delayed_device)
    monkeypatch.setattr(security, '_lock_device', signaled_device)
    results = concurrent_calls(engine, [
        lambda db: security.authenticate_mobile_user(db, email, 'test-password', metadata),
        rotate,
    ])
    assert [status for status, _ in results] == [200, 200]
