"""Concurrencia real del desbloqueo sobre PostgreSQL (se omite sin PG_CONCURRENCY_URL).

    PG_CONCURRENCY_URL=postgresql+psycopg://localhost:5432/<base_vacia_desechable> pytest ...
"""
import os
import threading

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.quotation import Quotation
from app.models.service_order import ServiceOrder
from app.models.service_order_archive import ServiceOrderArchive
from app.models.user import User
from app.schemas.quotation_service_change import QuotationUnlockApply
from app.services.quotation_service_changes import apply_change

import test_quotation_service_change_exception as base

URL = os.environ.get("PG_CONCURRENCY_URL")
pytestmark = pytest.mark.skipif(not URL, reason="PG_CONCURRENCY_URL no definido")


@pytest.fixture()
def db():
    engine = create_engine(URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.factory = factory
        yield session
    engine.dispose()


context = base.context


def test_two_simultaneous_applies_archive_and_delete_exactly_once(db, context):
    authorized = base._request_and_authorize(db, context)
    folio, user_id = authorized["folio"], context.requester.id
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def worker():
        with db.factory() as session:
            user = session.get(User, user_id)
            barrier.wait()
            try:
                apply_change(session, folio, QuotationUnlockApply(expected_snapshot_number=1), user)
                outcomes.append("ok")
            except HTTPException as error:
                session.rollback()
                outcomes.append(f"http{error.status_code}")

    threads = [threading.Thread(target=worker) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(outcomes) == ["http409", "ok"]
    db.expire_all()
    assert db.scalar(select(func.count(ServiceOrderArchive.id))) == 1
    assert db.scalar(select(func.count(ServiceOrder.id))) == 0
    assert db.get(Quotation, context.quotation.id).status == "in_revision"
