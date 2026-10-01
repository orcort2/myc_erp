"""Settings write contract and real transactional internal folio allocation."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import get_db
from app.models.invoice import InvoiceSettings
from app.routers.invoices import router
from app.services.invoices import _next_invoice_folio, get_invoice_settings


@pytest.fixture
def engine():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    InvoiceSettings.__table__.create(engine)
    yield engine
    engine.dispose()


def test_settings_patch_rejects_numbering_and_preserves_editable_fields(engine):
    app = FastAPI()
    app.include_router(router)
    with Session(engine) as db:
        original = get_invoice_settings(db)
        app.dependency_overrides[get_db] = lambda: db
        for route in router.routes:
            for dependency in route.dependant.dependencies:
                if dependency.name == 'current_user':
                    app.dependency_overrides[dependency.call] = lambda: object()
        with TestClient(app) as client:
            for key, value in [('default_series', 'X'), ('next_sequence', 999), ('reset_annually', True), ('allow_manual_folio', True)]:
                response = client.patch('/invoice-settings', json={key: value, 'default_currency': 'USD'})
                assert response.status_code == 422
                db.refresh(original)
                assert original.next_sequence == 1
                assert original.default_series == 'F'
                assert original.default_currency == 'MXN'
            response = client.patch('/invoice-settings', json={'default_currency': 'USD', 'default_credit_days': 15})
            assert response.status_code == 200
            assert response.json()['default_currency'] == 'USD'
            assert response.json()['default_credit_days'] == 15
            assert response.json()['next_sequence'] == 1


def test_allocation_uses_issue_year_and_rolls_back(engine):
    with Session(engine) as db:
        settings = get_invoice_settings(db)
        assert _next_invoice_folio(db, settings, issued_on=date(2025, 12, 31)) == ('F', 'MYCF-2025-0001')
        assert _next_invoice_folio(db, settings, issued_on=date(2027, 1, 1)) == ('F', 'MYCF-2027-0002')
        db.rollback()
        assert db.scalar(select(InvoiceSettings.next_sequence)) == 1


@pytest.fixture
def postgres_engine():
    url = os.getenv('BILLING_POSTGRES_TEST_URL')
    if not url:
        pytest.skip('requires BILLING_POSTGRES_TEST_URL for real PostgreSQL concurrency')
    schema = f'billing_test_{uuid4().hex}'
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={'options': f'-csearch_path={schema}'})
    InvoiceSettings.__table__.create(engine)
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_postgres_concurrent_allocations_with_stale_sessions(postgres_engine):
    with Session(postgres_engine) as db:
        get_invoice_settings(db)
    barrier = Barrier(2)

    def allocate():
        with Session(postgres_engine) as db:
            settings = get_invoice_settings(db)
            assert settings.next_sequence == 1
            barrier.wait(timeout=10)
            identity = _next_invoice_folio(db, settings, issued_on=date(2026, 10, 1))
            db.commit()
            return identity

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: allocate(), range(2)))
    assert set(results) == {('F', 'MYCF-2026-0001'), ('F', 'MYCF-2026-0002')}
    with Session(postgres_engine) as db:
        assert db.scalar(select(InvoiceSettings.next_sequence)) == 3


def test_postgres_first_settings_creation_is_atomic(postgres_engine):
    with Session(postgres_engine) as db:
        settings = get_invoice_settings(db, commit=False)
        _next_invoice_folio(db, settings, issued_on=date(2026, 10, 1))
        db.rollback()
    with Session(postgres_engine) as db:
        assert db.scalar(select(InvoiceSettings)) is None


def test_postgres_concurrent_first_use(postgres_engine):
    barrier = Barrier(2)

    def allocate():
        with Session(postgres_engine) as db:
            barrier.wait(timeout=10)
            settings = get_invoice_settings(db, commit=False)
            identity = _next_invoice_folio(db, settings, issued_on=date(2026, 10, 1))
            db.commit()
            return identity

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: allocate(), range(2)))
    assert len(set(results)) == 2


def test_invoice_creation_ignores_legacy_manual_numbering(engine):
    from app.core.db import Base
    from app.models.client import Client
    from app.models.quotation import Quotation
    from app.models.service_order import ServiceOrder
    from app.schemas.invoice import InvoiceCreate
    from app.services.invoices import create_invoice

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        settings = get_invoice_settings(db)
        settings.allow_manual_folio = True  # Persisted legacy flag cannot bypass allocation.
        customer = Client(legal_name='Cliente de prueba')
        db.add(customer)
        db.flush()
        quotation = Quotation(folio='Q-1', client_id=customer.id, status='approved')
        db.add(quotation)
        db.flush()
        order = ServiceOrder(folio='ETS-1', client_id=customer.id, quotation_id=quotation.id)
        db.add(order)
        db.commit()
        invoice = create_invoice(db, InvoiceCreate(
            client_id=customer.id, quotation_id=quotation.id, service_order_id=order.id,
            issued_on=date(2028, 1, 1), series='MANUAL', folio='OVERRIDE',
        ))
        assert invoice.series == 'F'
        assert invoice.folio == 'MYCF-2028-0001'
        assert db.scalar(select(InvoiceSettings.next_sequence)) == 2
