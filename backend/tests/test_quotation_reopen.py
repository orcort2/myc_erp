"""El endpoint /reopen ya no puede eludir el desbloqueo autorizado (EXV)."""
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
from app.services.quotations import ALLOWED_TRANSITIONS, reopen_accepted_quotation


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


def _quotation(db, folio, status):
    client = Client(legal_name=f"Cliente {folio}", commercial_name=folio)
    db.add(client)
    db.flush()
    quotation = Quotation(
        folio=folio, client_id=client.id, status=status, issued_on=date(2026, 10, 16)
    )
    db.add(quotation)
    db.flush()
    return quotation


def test_reopen_accepted_is_rejected_without_mutation(db):
    quotation = _quotation(db, "MYC-TEST-REOPEN-1", "accepted")
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

    with pytest.raises(HTTPException) as exc:
        reopen_accepted_quotation(db, quotation.id)
    assert exc.value.status_code == 409
    assert "desbloqueo autorizado" in exc.value.detail
    db.refresh(quotation)
    db.refresh(acceptance)
    assert quotation.status == "accepted"
    assert acceptance.invalidated_at is None
    assert db.scalar(
        select(AuditLog).where(AuditLog.action == "quotation.reopened")
    ) is None


def test_reopen_rejects_nonaccepted_without_mutation(db):
    quotation = _quotation(db, "MYC-TEST-REOPEN-2", "sent")
    db.commit()
    with pytest.raises(HTTPException) as exc:
        reopen_accepted_quotation(db, quotation.id)
    assert exc.value.status_code == 409
    assert db.get(Quotation, quotation.id).status == "sent"


def test_status_table_has_in_revision_and_accepted_stays_terminal():
    assert ALLOWED_TRANSITIONS["accepted"] == set()
    assert ALLOWED_TRANSITIONS["in_revision"] == {"sent", "cancelled"}
    assert all("in_revision" not in targets for targets in ALLOWED_TRANSITIONS.values())
