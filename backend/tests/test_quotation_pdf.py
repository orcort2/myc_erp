"""Authenticated quotation PDFs and persisted template flag combinations."""

from datetime import date
from io import BytesIO
from itertools import product
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.client import Client
from app.models.document_template import DocumentTemplate
from app.models.quotation import Quotation
from app.models.user import Role, User
from app.services.quotation_pdfs import _render_html


@pytest.fixture()
def quotation_pdf_context():
    engine = create_engine('sqlite+pysqlite:///:memory:',
                           connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        users = {}
        for name in ('Comercial', 'Tecnico'):
            role = Role(name=name)
            user = User(username=name, email=f'{name}@example.test', full_name=name,
                        hashed_password='unused', roles=[role])
            db.add(user)
            users[name] = user
        client = Client(legal_name='Cliente PDF', commercial_name='Cliente PDF')
        db.add(client)
        db.flush()
        quotation = Quotation(folio='COT-PRUEBA-1', client_id=client.id, issued_on=date(2026, 9, 29),
                               status='draft', notes='NOTA INDEPENDIENTE')
        db.add(quotation)
        db.commit()
        quotation_id = quotation.id
        headers = {name: {'Authorization': f'Bearer {create_access_token(str(user.id))}'}
                   for name, user in users.items()}

    def override_db():
        with factory() as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as http:
            yield SimpleNamespace(http=http, factory=factory, headers=headers, quotation_id=quotation_id)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


FLAGS = list(product((True, False), repeat=3))


@pytest.mark.parametrize('summary,full,signature', FLAGS)
def test_persisted_flags_control_pdf_sections_independently(quotation_pdf_context, summary, full, signature):
    ctx = quotation_pdf_context
    headers = ctx.headers['Comercial']
    content = dict(commercial_terms='COMERCIAL UNICO', metrological_terms='METROLOGIA UNICA',
                   legal_terms='LEGAL UNICO', privacy_notice='PRIVACIDAD UNICA',
                   acceptance_text='FIRMA INDEPENDIENTE', terms_version='VERSION-PRUEBA')
    flags = dict(show_summary_terms=summary, show_full_terms=full, show_acceptance_signature=signature)
    saved = ctx.http.patch('/api/document-templates/quotation', json=content | flags, headers=headers)
    assert saved.status_code == 200, saved.text
    reread = ctx.http.get('/api/document-templates/quotation', headers=headers)
    assert reread.status_code == 200
    assert {key: reread.json()[key] for key in flags} == flags
    assert {key: reread.json()[key] for key in content} == content

    with ctx.factory() as db:
        template = db.get(DocumentTemplate, saved.json()['id'])
        assert {key: getattr(template, key) for key in flags} == flags
        html = _render_html(db, db.get(Quotation, ctx.quotation_id))
    initial, _, complete = html.partition('<section class="full-terms">')
    assert ('<h3>Condiciones comerciales</h3>' in initial) is summary
    assert ('VERSION-PRUEBA' in initial) is summary
    assert 'NOTA INDEPENDIENTE' in initial
    assert bool(complete) is full
    assert ('FIRMA INDEPENDIENTE' in initial) is signature
    assert ('FIRMA INDEPENDIENTE' in complete) is (signature and full)

    response = ctx.http.get(f'/api/quotations/{ctx.quotation_id}/pdf', headers=headers)
    assert response.status_code == 200, response.text
    assert response.headers['content-type'] == 'application/pdf'
    assert response.headers['content-disposition'] == 'inline; filename="Cotizacion_COT-PRUEBA-1_Cliente-PDF.pdf"'
    assert response.content.startswith(b'%PDF-')
    pages = [page.extract_text() for page in PdfReader(BytesIO(response.content)).pages]
    first = pages[0]
    all_text = '\n'.join(pages)
    assert ('COMERCIAL UNICO' in first) is summary
    assert ('VERSION-PRUEBA' in first) is summary
    assert 'NOTA INDEPENDIENTE' in first
    assert len(pages) == (2 if full else 1)
    assert all_text.count('COMERCIAL UNICO') == int(summary) + int(full)
    for value in ('METROLOGIA UNICA', 'LEGAL UNICO', 'PRIVACIDAD UNICA'):
        assert (value in all_text) is full
    assert all_text.count('FIRMA INDEPENDIENTE') == int(signature) * (1 + int(full))
    with ctx.factory() as db:
        template = db.get(DocumentTemplate, saved.json()['id'])
        assert {key: getattr(template, key) for key in content} == content


def test_pdf_endpoint_remains_protected(quotation_pdf_context):
    ctx = quotation_pdf_context
    path = f'/api/quotations/{ctx.quotation_id}/pdf'
    assert ctx.http.get(path).status_code == 401
    assert ctx.http.get(path, headers=ctx.headers['Tecnico']).status_code == 403
    assert ctx.http.get(path, headers=ctx.headers['Comercial']).status_code == 200
