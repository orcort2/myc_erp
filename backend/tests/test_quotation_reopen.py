"""Regression tests for explicit reopening of accepted quotations."""
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.quotation import Quotation
from app.services.quotations import reopen_accepted_quotation


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


def test_reopen_accepted_returns_to_draft_and_audits(db):
    client = Client(legal_name="Cliente de prueba", commercial_name="Prueba")
    db.add(client)
    db.flush()
    quotation = Quotation(
        folio="MYC-TEST-REOPEN-1",
        client_id=client.id,
        status="accepted",
        issued_on=date(2026, 10, 16),
    )
    db.add(quotation)
    db.commit()

    result = reopen_accepted_quotation(db, quotation.id)
    assert result.status == "draft"
    audit = db.scalar(
        select(AuditLog).where(
            AuditLog.entity == "quotations",
            AuditLog.entity_id == quotation.id,
            AuditLog.action == "quotation.reopened",
        )
    )
    assert audit is not None


def test_reopen_rejects_nonaccepted_without_mutation(db):
    client = Client(legal_name="Cliente sin firma", commercial_name="Sin firma")
    db.add(client)
    db.flush()
    quotation = Quotation(folio="MYC-TEST-REOPEN-2", client_id=client.id, status="sent")
    db.add(quotation)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        reopen_accepted_quotation(db, quotation.id)
    assert exc.value.status_code == 409
    assert db.get(Quotation, quotation.id).status == "sent"
