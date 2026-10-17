"""Regression tests for explicit reopening of accepted quotations."""
from datetime import date, datetime, timezone
from hashlib import sha256

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.quotation import Quotation, QuotationSnapshot
from app.models.quotation_acceptance import QuotationAcceptance
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


def test_reopen_invalidates_acceptance_but_preserves_evidence(db):
    client = Client(legal_name="Cliente firmado", commercial_name="Firmado")
    db.add(client)
    db.flush()
    quotation = Quotation(folio="MYC-TEST-REOPEN-3", client_id=client.id, status="accepted")
    db.add(quotation)
    db.flush()
    snapshot = QuotationSnapshot(
        quotation_id=quotation.id, snapshot_number=1, snapshot_data={"total": "100.00"}
    )
    db.add(snapshot)
    db.flush()
    pdf = b"%PDF-1.4 test frozen quotation"
    now = datetime.now(timezone.utc)
    acceptance = QuotationAcceptance(
        quotation_id=quotation.id,
        snapshot_id=snapshot.id,
        pdf_sha256=sha256(pdf).hexdigest(),
        pdf_bytes=pdf,
        signer_name="Cliente Autorizado",
        signer_email="firmante@example.test",
        consent_text="Acepto la cotizacion",
        evidence={"method": "otp_email"},
        verified_at=now,
        accepted_at=now,
    )
    db.add(acceptance)
    db.commit()

    reopened = reopen_accepted_quotation(db, quotation.id)
    assert reopened.status == "draft"
    db.refresh(acceptance)
    assert acceptance.invalidated_at is not None
    assert acceptance.invalidation_reason == "quotation_reopened"
    assert acceptance.pdf_bytes == pdf
    assert acceptance.pdf_sha256 == sha256(pdf).hexdigest()
