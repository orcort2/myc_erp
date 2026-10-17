"""Real PostgreSQL locking test. Uses a disposable schema, never ERP business rows."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

import app.models  # noqa: F401 - register all ORM tables
from app.core.db import Base
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.email import EmailDelivery
from app.models.quotation import Quotation
from app.services.quotation_email import reconcile_quotation_email_status


@pytest.fixture
def postgres_engine():
    url = os.getenv("QUOTATION_POSTGRES_TEST_URL")
    if not url:
        pytest.skip("set QUOTATION_POSTGRES_TEST_URL to an explicitly approved LOCAL PostgreSQL DSN")
    admin = create_engine(url)
    with admin.connect() as conn:
        assert conn.dialect.name == "postgresql"
        database = conn.scalar(text("SELECT current_database()"))
        assert database == "erp_myc", f"expected local development database erp_myc, got {database}"
        assert conn.scalar(text("SELECT inet_server_addr() IS NULL OR inet_server_addr() IN ('127.0.0.1'::inet, '::1'::inet)")), "remote PostgreSQL is forbidden"
    schema = "quotation_lock_test_" + uuid4().hex
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"}, pool_size=3)
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_concurrent_smtp_reconciliation_commits_once(postgres_engine):
    with Session(postgres_engine) as db:
        client = Client(legal_name="PG concurrency test")
        db.add(client)
        db.flush()
        quotation = Quotation(folio="PG-TEST-" + uuid4().hex[:16], client_id=client.id, status="draft")
        db.add(quotation)
        db.flush()
        delivery = EmailDelivery(
            template_key="quotation_send", related_entity_type="quotation",
            related_entity_id=quotation.id, subject="PG concurrency test",
            body_text_snapshot="test", body_html_snapshot="test",
            status="sent", sent_at=datetime.now(timezone.utc),
        )
        db.add(delivery)
        db.commit()
        qid = quotation.id

    barrier = Barrier(2)

    def reconcile():
        with Session(postgres_engine) as db:
            barrier.wait(timeout=15)
            return reconcile_quotation_email_status(db, qid)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: reconcile(), range(2)))

    assert sorted(results) == [False, True]
    with Session(postgres_engine) as db:
        assert db.get(Quotation, qid).status == "sent"
        logs = db.scalars(select(AuditLog).where(
            AuditLog.entity == "quotations",
            AuditLog.entity_id == qid,
            AuditLog.action == "quotation.sent",
        )).all()
        assert len(logs) == 1
        assert reconcile_quotation_email_status(db, qid) is False
