"""BIOMETRIC-2: real PostgreSQL row locking for concurrent biometric enroll."""
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
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.mobile import biometric, security
from app.core.security import hash_password
from app.core.mobile.biometric_credentials import hash_biometric_credential
from app.models.mobile_biometric_credential import MobileBiometricCredential
from app.models.user import Role, User
from app.schemas.mobile_auth import MobileSecurityDeviceInput


def _load_migration(name: str, filename: str):
    path = Path(__file__).parents[1] / "migrations/versions" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOBILE_TABLES = {"mobile_trusted_devices", "mobile_auth_sessions", "mobile_biometric_credentials"}


@pytest.fixture(scope="module")
def pg_engine():
    url = os.getenv("MOBILE_AUTH_POSTGRES_TEST_URL")
    if not url:
        pytest.skip("requires MOBILE_AUTH_POSTGRES_TEST_URL for real PostgreSQL locking")
    schema = f"mobile_biometric_test_{uuid4().hex}"
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    session_migration = _load_migration("biometric_pg_session_migration", "b10a1c202601_mobile_session_authority.py")
    credential_migration = _load_migration("biometric_pg_credential_migration", "9970e12e5f0d_biometric_2_add_mobile_biometric_.py")
    try:
        Base.metadata.create_all(engine, tables=[table for table in Base.metadata.tables.values()
            if table.name not in MOBILE_TABLES])
        with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
            session_migration.upgrade()
            credential_migration.upgrade()
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def new_login(engine):
    with Session(engine) as db:
        role = db.scalar(select(Role).where(Role.name == "Tecnico"))
        if role is None:
            role = Role(name="Tecnico", description="Test")
            db.add(role)
            db.flush()
        name = uuid4().hex
        user = User(username=name, email=f"{name}@example.com", full_name="PG Biometric Test",
                    hashed_password=hash_password("test-password"), account_type="internal",
                    status="active", roles=[role], role_id=role.id)
        db.add(user)
        db.commit()
        return security.authenticate_mobile_user(db, user.email, "test-password",
            MobileSecurityDeviceInput(device_uuid=str(uuid4()), platform="ios"))


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


def synchronize(monkeypatch, module, helper):
    # Patches the name as bound in `module`'s own namespace (a `from x import
    # y` binds a separate reference there), so both concurrent enroll calls
    # actually reach the real, PostgreSQL-backed `_lock_device` at the same
    # instant instead of racing at the Python thread-scheduling level.
    original = getattr(module, helper)
    barrier = Barrier(2)

    def locked(*args):
        barrier.wait(timeout=10)
        return original(*args)

    monkeypatch.setattr(module, helper, locked)


def test_two_concurrent_enrolls_leave_exactly_one_active_credential(pg_engine, monkeypatch):
    engine = pg_engine
    pair = new_login(engine)
    with Session(engine) as db:
        context = security.resolve_mobile_token(db, pair["access_token"])
        device_id = db.get(security.MobileAuthSession, context.mobile_session_id).device_id

    synchronize(monkeypatch, biometric, "_lock_device")

    def enroll(db):
        ctx = security.resolve_mobile_token(db, pair["access_token"])
        return biometric.enroll_biometric_credential(db, ctx)

    results = concurrent_calls(engine, [enroll, enroll])

    # Both requests must terminate deterministically (no deadlock, no hang):
    # ThreadPoolExecutor's `future.result(timeout=20)` above already asserts
    # that by not raising/timing out. Both succeed structurally -- enroll
    # never rejects a second attempt, it revokes-and-replaces.
    assert [status for status, _ in results] == [200, 200]

    with Session(engine) as db:
        rows = db.scalars(
            select(MobileBiometricCredential).where(
                MobileBiometricCredential.user_id == context.user.id,
                MobileBiometricCredential.device_id == device_id,
            )
        ).all()
        assert len(rows) == 2
        active = [row for row in rows if row.revoked_at is None]
        revoked = [row for row in rows if row.revoked_at is not None]
        assert len(active) == 1
        assert len(revoked) == 1

        winner_credential = next(
            body["biometric_credential"] for _, body in results
            if hash_biometric_credential(body["biometric_credential"]) == active[0].credential_hash
        )
        loser_credential = next(
            body["biometric_credential"] for _, body in results
            if hash_biometric_credential(body["biometric_credential"]) == revoked[0].credential_hash
        )
        assert winner_credential != loser_credential

        # The surviving credential is the one that actually works in exchange.
        exchanged = biometric.exchange_biometric_credential(db, winner_credential)
        assert exchanged["user"]["id"] == context.user.id
        with pytest.raises(HTTPException):
            biometric.exchange_biometric_credential(db, loser_credential)
