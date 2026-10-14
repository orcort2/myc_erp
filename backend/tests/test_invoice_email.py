import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.client import Client, ClientContact
from app.models.email import EmailDelivery
from app.models.invoice import Invoice
from app.models.quotation import Quotation
from app.models.service_order import ServiceOrder
from app.models.user import Role, User
from app.schemas.invoice import InvoiceCreate
from app.services.email.transport import SmtpTransport
from app.services.invoices import create_invoice
from app.services import invoice_email
from test_email_infrastructure import FakeSMTP, make_settings
from unittest.mock import patch
from fastapi import HTTPException


ROLES = (
    "Administrador",
    "Desarrollador",
    "Comercial",
    "Finanzas",
    "Tecnico",
)

@pytest.fixture()
def world(monkeypatch, tmp_path):
    postgres_url = os.environ.get("MYC_INVOICE_EMAIL_TEST_DATABASE_URL")

    if postgres_url:
        from sqlalchemy.engine import make_url

        parsed = make_url(postgres_url)

        if (
            parsed.get_backend_name() != "postgresql"
            or parsed.database != "erp_myc_invoice_email_test"
            or parsed.host != "127.0.0.1"
            or parsed.port != 5432
            or parsed.username != "saulcortes"
        ):
            raise RuntimeError(
                "Base PostgreSQL de pruebas no autorizada."
            )

        engine = create_engine(postgres_url, pool_pre_ping=True)

        from sqlalchemy import text

        with engine.begin() as connection:
            database_name = connection.scalar(
                text("SELECT current_database()")
            )

            if database_name != "erp_myc_invoice_email_test":
                raise RuntimeError(
                    "Inicializacion bloqueada: base no autorizada."
                )

            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    else:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    Base.metadata.create_all(engine)

    settings = make_settings()

    monkeypatch.setattr(
        "app.services.email.service.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "app.services.invoice_email.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "app.services.email.service.SmtpTransport",
        lambda s: SmtpTransport(s, smtp_factory=FakeSMTP),
    )

    with Session(engine, expire_on_commit=False) as db:
        users = {}

        for name in ROLES:
            role = Role(
                name=name,
                description=name,
            )
            db.add(role)
            db.flush()

            user = User(
                username=name.lower(),
                email=f"{name.lower()}@myc.test",
                full_name=f"{name} MYC",
                hashed_password=hash_password("Pass12345"),
                account_type="internal",
                status="active",
                email_verified_at=datetime.now(timezone.utc),
                roles=[role],
                role_id=role.id,
            )
            db.add(user)
            db.flush()
            users[name] = user

        client = Client(
            legal_name="Grupo XYZ SA",
            commercial_name="Grupo XYZ",
            email="compras@xyz.com",
            phone="3300000000",
        )
        other = Client(
            legal_name="Otro SA",
            commercial_name="Otro",
            email="otro@otro.com",
        )

        db.add_all([client, other])
        db.flush()

        ana = ClientContact(
            client_id=client.id,
            name="Ana López",
            position="Facturación",
            email="ana.lopez@xyz.com",
        )
        luis = ClientContact(
            client_id=client.id,
            name="Luis Pérez",
            position="Compras",
            email="luis.perez@xyz.com",
        )
        foreign = ClientContact(
            client_id=other.id,
            name="Persona Ajena",
            email="ajena@otro.com",
        )

        db.add_all([ana, luis, foreign])
        db.flush()

        quotation = Quotation(
            folio="COT-2026-0100",
            client_id=client.id,
            contact_id=ana.id,
            status="approved",
            issued_on=date(2026, 10, 1),
        )
        db.add(quotation)
        db.flush()

        order = ServiceOrder(
            folio="ETS-EMAIL-4",
            client_id=client.id,
            quotation_id=quotation.id,
        )
        db.add(order)
        db.commit()

        invoice = create_invoice(
            db,
            InvoiceCreate(
                client_id=client.id,
                quotation_id=quotation.id,
                service_order_id=order.id,
                issued_on=date(2026, 10, 2),
                items=[],
            ),
        )

        app.dependency_overrides[get_db] = lambda: db
        api = TestClient(app)

        def h(name):
            token = create_access_token(
                str(users[name].id),
                extra_claims={
                    "auth_context": "internal",
                    "roles": [name],
                },
            )
            return {"Authorization": f"Bearer {token}"}

        yield type(
            "W",
            (),
            dict(
                api=api,
                db=db,
                h=staticmethod(h),
                users=users,
                client=client,
                other=other,
                ana=ana,
                luis=luis,
                foreign=foreign,
                quotation=quotation,
                order=order,
                invoice=invoice,
                tmp_path=tmp_path,
            ),
        )

        api.close()
        app.dependency_overrides.clear()

    if postgres_url:
        from sqlalchemy import text

        with engine.begin() as connection:
            database_name = connection.scalar(
                text("SELECT current_database()")
            )

            if database_name != "erp_myc_invoice_email_test":
                raise RuntimeError(
                    "Limpieza bloqueada: base no autorizada."
                )

            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))

    engine.dispose()

def test_world_builds_a_valid_invoice(world):
    assert world.invoice.id is not None
    assert world.invoice.quotation_id == world.quotation.id
    assert world.invoice.client_id == world.client.id
    assert world.quotation.contact_id == world.ana.id


def test_draft_preview_uses_institutional_pdf_only_and_non_fiscal_template(world):
    w = world

    preview = invoice_email.preview_invoice_email(
        w.db,
        w.invoice.id,
    )

    assert preview.invoice_id == w.invoice.id
    assert preview.document_mode == "draft"
    assert preview.template_key == "invoice_draft_send"

    assert preview.to == ["ana.lopez@xyz.com"]
    assert preview.cc == []

    sources = [
        (item.email, item.source, item.selected)
        for item in preview.available_recipients
    ]
    assert sources == [
        ("ana.lopez@xyz.com", "quotation_contact", True),
        ("luis.perez@xyz.com", "client_contact", False),
        ("compras@xyz.com", "client_email", False),
    ]

    assert "Ana López" in preview.body_text
    assert "Grupo XYZ" in preview.body_text
    assert w.invoice.folio in preview.subject
    assert "no constituye un CFDI" in preview.body_text
    assert "validez fiscal" in preview.body_text

    assert len(preview.attachments) == 1
    attachment = preview.attachments[0]
    assert attachment.content_type == "application/pdf"
    assert attachment.filename.lower().endswith(".pdf")

def test_issued_preview_uses_institutional_pdf_and_fiscal_xml(world, tmp_path):
    w = world

    xml_path = tmp_path / "cfdi.xml"
    xml_path.write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" '
        b'Serie="MYCF" Folio="100"/>'
    )

    invoice = w.db.get(Invoice, w.invoice.id)
    invoice.cfdi_uuid = "UUID-EMAIL-4-001"
    invoice.facturama_xml_path = "facturama/test/cfdi.xml"
    invoice.stamped_at = datetime.now(timezone.utc)
    invoice.status = "issued"
    w.db.commit()

    with patch(
        "app.services.invoice_pdfs.resolve_storage_path",
        return_value=xml_path,
    ):
        preview = invoice_email.preview_invoice_email(
            w.db,
            invoice.id,
        )

    assert preview.document_mode == "issued"
    assert preview.template_key == "invoice_send"

    assert "UUID-EMAIL-4-001" in preview.body_text
    assert "no constituye un CFDI" not in preview.body_text

    assert len(preview.attachments) == 2

    by_type = {
        item.content_type: item
        for item in preview.attachments
    }

    assert "application/pdf" in by_type
    assert "application/xml" in by_type

    assert by_type["application/pdf"].filename.lower().endswith(".pdf")
    assert by_type["application/xml"].filename.lower().endswith(".xml")


def test_partial_fiscal_evidence_blocks_invoice_email(world):
    w = world

    invoice = w.db.get(Invoice, w.invoice.id)
    invoice.cfdi_uuid = "UUID-SIN-XML"
    invoice.facturama_xml_path = None
    w.db.commit()

    with pytest.raises(HTTPException) as exc_info:
        invoice_email.preview_invoice_email(
            w.db,
            invoice.id,
        )

    assert exc_info.value.status_code == 409


def test_xml_without_uuid_also_blocks_invoice_email(world):
    w = world

    invoice = w.db.get(Invoice, w.invoice.id)
    invoice.cfdi_uuid = None
    invoice.facturama_xml_path = "facturama/test/cfdi.xml"
    w.db.commit()

    with pytest.raises(HTTPException) as exc_info:
        invoice_email.preview_invoice_email(
            w.db,
            invoice.id,
        )

    assert exc_info.value.status_code == 409

def test_draft_send_creates_delivery_and_does_not_change_invoice_state(world):
    w = world

    invoice = w.db.get(Invoice, w.invoice.id)
    original_status = invoice.status

    result = invoice_email.send_invoice_email(
        w.db,
        invoice.id,
        to=["ana.lopez@xyz.com", "manual@otra.com"],
        cc=["cc@otra.com"],
        actor=w.users["Comercial"],
    )

    assert result.sent is True
    assert result.status == "sent"

    delivery = w.db.get(EmailDelivery, result.delivery_id)

    assert delivery.related_entity_type == "invoice"
    assert delivery.related_entity_id == invoice.id
    assert delivery.requested_by_id == w.users["Comercial"].id
    assert delivery.template_key == "invoice_draft_send"

    assert delivery.to_json == [
        "ana.lopez@xyz.com",
        "manual@otra.com",
    ]
    assert delivery.cc_json == ["cc@otra.com"]

    refreshed = w.db.get(
        Invoice,
        invoice.id,
        populate_existing=True,
    )

    assert refreshed.status == original_status
    assert refreshed.cfdi_uuid is None
    assert refreshed.facturama_id is None

    message = FakeSMTP.instances[-1].sent[0]
    attachments = list(message.iter_attachments())

    assert len(attachments) == 1
    assert attachments[0].get_content_type() == "application/pdf"
    assert attachments[0].get_filename().lower().endswith(".pdf")

    body = message.get_body(preferencelist=("plain",)).get_content()
    assert "no constituye un CFDI" in body
    assert "validez fiscal" in body


def test_issued_send_attaches_institutional_pdf_and_fiscal_xml(world, tmp_path):
    w = world

    xml_path = tmp_path / "cfdi.xml"
    xml_path.write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" '
        b'Serie="MYCF" Folio="100"/>'
    )

    invoice = w.db.get(Invoice, w.invoice.id)
    invoice.cfdi_uuid = "UUID-EMAIL-4-SEND"
    invoice.facturama_xml_path = "facturama/test/cfdi.xml"
    invoice.stamped_at = datetime.now(timezone.utc)
    invoice.status = "issued"
    invoice.due_on = date.today() + timedelta(days=30)
    w.db.commit()

    with patch(
        "app.services.invoice_pdfs.resolve_storage_path",
        return_value=xml_path,
    ):
        result = invoice_email.send_invoice_email(
            w.db,
            invoice.id,
            to=["ana.lopez@xyz.com"],
            cc=[],
            actor=w.users["Comercial"],
        )

    assert result.sent is True

    delivery = w.db.get(EmailDelivery, result.delivery_id)

    assert delivery.template_key == "invoice_send"
    assert delivery.related_entity_type == "invoice"
    assert delivery.related_entity_id == invoice.id

    message = FakeSMTP.instances[-1].sent[0]
    attachments = list(message.iter_attachments())

    assert len(attachments) == 2

    content_types = {
        item.get_content_type()
        for item in attachments
    }

    assert content_types == {
        "application/pdf",
        "application/xml",
    }

    filenames = [
        item.get_filename().lower()
        for item in attachments
    ]

    assert any(name.endswith(".pdf") for name in filenames)
    assert any(name.endswith(".xml") for name in filenames)

    refreshed = w.db.get(
        Invoice,
        invoice.id,
        populate_existing=True,
    )

    assert refreshed.status == "issued"
    assert refreshed.cfdi_uuid == "UUID-EMAIL-4-SEND"

def test_invoice_email_history_is_scoped_to_invoice(world):
    w = world

    first = invoice_email.send_invoice_email(
        w.db,
        w.invoice.id,
        to=["ana.lopez@xyz.com"],
        cc=[],
        actor=w.users["Comercial"],
    )

    second_invoice = Invoice(
        internal_uuid="SECOND-INVOICE-EMAIL-4",
        series="F",
        folio="MYCF-2026-9999",
        client_id=w.client.id,
        fiscal_client_id=w.client.id,
        service_order_id=w.order.id,
        quotation_id=w.quotation.id,
        status="draft",
        total=0,
        balance_due=0,
        amount_paid=0,
    )
    w.db.add(second_invoice)
    w.db.commit()

    invoice_email.send_invoice_email(
        w.db,
        second_invoice.id,
        to=["luis.perez@xyz.com"],
        cc=[],
        actor=w.users["Comercial"],
    )

    history = invoice_email.list_invoice_email_deliveries(
        w.db,
        w.invoice.id,
    )

    assert [item.id for item in history] == [first.delivery_id]
    assert history[0].requested_by_name == "Comercial MYC"
    assert history[0].to == ["ana.lopez@xyz.com"]
    assert history[0].attachments

def test_invoice_manual_recipients_are_deduplicated_and_do_not_modify_contacts(world):
    w = world

    preview = invoice_email.preview_invoice_email(
        w.db,
        w.invoice.id,
        to=[
            "Ana.Lopez@xyz.com",
            "manual1@otra.com",
            "manual2@otra.com",
            "MANUAL1@otra.com",
        ],
        cc=[
            "manual1@otra.com",
            "cc@otra.com",
            "cc@otra.com",
        ],
    )

    assert preview.to == [
        "Ana.Lopez@xyz.com",
        "manual1@otra.com",
        "manual2@otra.com",
    ]

    assert preview.cc == ["cc@otra.com"]

    assert len(w.client.contacts) == 2
    assert w.client.email == "compras@xyz.com"




def test_invoice_email_preview_does_not_mutate_financial_state(world):
    """Preview must not recalculate or persist an overdue invoice."""
    from datetime import timedelta

    w = world
    invoice = w.db.get(Invoice, w.invoice.id)

    invoice.status = "issued"
    invoice.due_on = date.today() - timedelta(days=10)
    w.db.commit()

    original_status = invoice.status

    invoice_email.preview_invoice_email(
        w.db,
        invoice.id,
        to=["ana.lopez@xyz.com"],
        cc=[],
    )

    refreshed = w.db.get(
        Invoice,
        invoice.id,
        populate_existing=True,
    )

    assert refreshed.status == original_status


def test_invoice_email_send_preserves_persisted_financial_state(world):
    """Email delivery commits must not change persisted invoice finances."""
    w = world
    invoice = w.db.get(Invoice, w.invoice.id)

    invoice.status = "issued"
    invoice.due_on = date.today() - timedelta(days=10)
    w.db.commit()

    invoice_id = invoice.id

    def financial_snapshot():
        w.db.expire_all()
        record = w.db.get(Invoice, invoice_id)
        return {
            "status": record.status,
            "subtotal": record.subtotal,
            "discount_total": record.discount_total,
            "tax_total": record.tax_total,
            "total": record.total,
            "amount_paid": record.amount_paid,
            "balance_due": record.balance_due,
            "items": [
                (
                    item.id,
                    item.discount_total,
                    item.tax_total,
                    item.line_total,
                )
                for item in sorted(record.items, key=lambda item: item.id)
            ],
        }

    before = financial_snapshot()

    result = invoice_email.send_invoice_email(
        w.db,
        invoice_id,
        to=["ana.lopez@xyz.com"],
        cc=[],
        actor=w.users["Comercial"],
    )

    assert result.sent is True
    assert financial_snapshot() == before

    delivery = w.db.get(EmailDelivery, result.delivery_id)
    assert delivery is not None
    assert delivery.related_entity_id == invoice_id


def test_invoice_email_send_does_not_commit_pending_financial_changes(world):
    """Delivery and audit persist without committing pending financial changes."""
    from sqlalchemy import inspect

    w = world
    invoice = w.db.get(Invoice, w.invoice.id)
    invoice_id = invoice.id

    original_status = invoice.status
    pending_status = "overdue" if original_status != "overdue" else "issued"

    invoice.status = pending_status
    assert inspect(invoice).attrs.status.history.has_changes()

    result = invoice_email.send_invoice_email(
        w.db,
        invoice_id,
        to=["ana.lopez@xyz.com"],
        cc=[],
        actor=w.users["Comercial"],
    )

    assert result.sent is True
    assert result.status == "sent"

    with Session(w.db.get_bind()) as independent_db:
        stored_status = independent_db.scalar(
            select(Invoice.status).where(Invoice.id == invoice_id)
        )

        delivery = independent_db.get(EmailDelivery, result.delivery_id)

        audit = independent_db.scalar(
            select(AuditLog)
            .where(
                AuditLog.action == "invoice.email.sent",
                AuditLog.entity == "invoices",
                AuditLog.entity_id == invoice_id,
            )
            .order_by(AuditLog.id.desc())
        )

        assert stored_status == original_status, (
            "El envío confirmó cambios financieros pendientes."
        )

        assert delivery is not None
        assert delivery.status == "sent"
        assert delivery.related_entity_type == "invoice"
        assert delivery.related_entity_id == invoice_id

        assert audit is not None
        assert audit.user_id == w.users["Comercial"].id
        assert audit.new_values["delivery_id"] == result.delivery_id
        assert audit.new_values["status"] == "sent"

    assert inspect(invoice).attrs.status.history.has_changes()




def test_invoice_email_transport_failure_preserves_financial_isolation(world, monkeypatch):
    """Failed SMTP delivery and audits persist without flushing invoice changes."""
    from sqlalchemy import inspect

    w = world
    invoice = w.db.get(Invoice, w.invoice.id)
    invoice_id = invoice.id
    original_status = invoice.status

    invoice.status = "overdue" if original_status != "overdue" else "issued"
    assert inspect(invoice).attrs.status.history.has_changes()

    monkeypatch.setattr(FakeSMTP, "fail_with", TimeoutError("simulated outage"))

    result = invoice_email.send_invoice_email(
        w.db,
        invoice_id,
        to=["ana.lopez@xyz.com"],
        cc=[],
        actor=w.users["Comercial"],
    )

    assert result.sent is False
    assert result.status == "failed"
    assert result.reason == "transport_failed"

    with Session(w.db.get_bind()) as independent_db:
        assert independent_db.scalar(
            select(Invoice.status).where(Invoice.id == invoice_id)
        ) == original_status

        delivery = independent_db.get(EmailDelivery, result.delivery_id)

        assert delivery is not None
        assert delivery.status == "failed"
        assert delivery.failure_code == "transport_failed"
        assert delivery.attempt_count == 1
        assert delivery.related_entity_type == "invoice"
        assert delivery.related_entity_id == invoice_id

        delivery_audit = independent_db.scalar(
            select(AuditLog).where(
                AuditLog.action == "email.delivery.failed",
                AuditLog.entity == "email_deliveries",
                AuditLog.entity_id == result.delivery_id,
            )
        )

        invoice_audit = independent_db.scalar(
            select(AuditLog).where(
                AuditLog.action == "invoice.email.failed",
                AuditLog.entity == "invoices",
                AuditLog.entity_id == invoice_id,
            )
        )

        assert delivery_audit is not None
        assert invoice_audit is not None
        assert invoice_audit.new_values["delivery_id"] == result.delivery_id
        assert invoice_audit.new_values["status"] == "failed"

    assert inspect(invoice).attrs.status.history.has_changes()



def test_invoice_email_preview_does_not_commit_pending_invoice_changes(world):
    """Preview must not commit unrelated pending financial changes."""
    from sqlalchemy import inspect

    w = world
    invoice = w.db.get(Invoice, w.invoice.id)
    invoice_id = invoice.id

    original_status = invoice.status
    pending_status = "overdue" if original_status != "overdue" else "issued"

    invoice.status = pending_status

    assert inspect(invoice).attrs.status.history.has_changes()

    invoice_email.preview_invoice_email(
        w.db,
        invoice_id,
        to=["ana.lopez@xyz.com"],
        cc=[],
    )

    with Session(w.db.get_bind()) as independent_db:
        stored_status = independent_db.scalar(
            select(Invoice.status).where(Invoice.id == invoice_id)
        )

    assert stored_status == original_status


def test_invoice_email_preview_does_not_call_commit(world, monkeypatch):
    """Preview must never commit the caller's transaction."""
    w = world
    commits = []
    original_commit = w.db.commit

    def tracked_commit():
        commits.append("commit")
        return original_commit()

    monkeypatch.setattr(w.db, "commit", tracked_commit)

    invoice_email.preview_invoice_email(
        w.db,
        w.invoice.id,
        to=["ana.lopez@xyz.com"],
        cc=[],
    )

    assert commits == [], (
        f"La vista previa ejecutó {len(commits)} commit(s) inesperados."
    )


def test_invoice_email_preview_does_not_flush_pending_financial_changes(world):
    """Preview must not flush unrelated pending invoice changes."""
    from sqlalchemy import event, inspect

    w = world
    invoice = w.db.get(Invoice, w.invoice.id)
    invoice.status = "overdue" if invoice.status != "overdue" else "issued"

    assert inspect(invoice).attrs.status.history.has_changes()

    flushes = []

    def before_flush(session, flush_context, instances):
        flushes.append([
            type(obj).__name__
            for obj in session.dirty
        ])

    event.listen(w.db, "before_flush", before_flush)

    try:
        invoice_email.preview_invoice_email(
            w.db,
            invoice.id,
            to=["ana.lopez@xyz.com"],
            cc=[],
        )
    finally:
        event.remove(w.db, "before_flush", before_flush)

    assert not any("Invoice" in objects for objects in flushes), (
        f"La vista previa ejecutó flush de una factura pendiente: {flushes}"
    )


def test_invoice_email_http_role_permissions(world):
    """Invoice email endpoints enforce distinct send and history permissions."""
    w = world
    base = f"/api/invoices/{w.invoice.id}/email"

    for role in ("Tecnico", "Comercial"):
        for suffix in ("preview", "send"):
            response = w.api.post(
                f"{base}/{suffix}",
                headers=w.h(role),
                json={"to": ["ana.lopez@xyz.com"]},
            )
            assert response.status_code == 403, (
                role, suffix, response.status_code, response.text
            )

    for role in ("Finanzas", "Desarrollador"):
        response = w.api.post(
            f"{base}/preview",
            headers=w.h(role),
            json={},
        )
        assert response.status_code == 200, (
            role, response.status_code, response.text
        )

    response = w.api.get(
        f"{base}/deliveries",
        headers=w.h("Tecnico"),
    )
    assert response.status_code == 403

    response = w.api.get(
        f"{base}/deliveries",
        headers=w.h("Finanzas"),
    )
    assert response.status_code == 200, response.text
    assert response.json() == []

    response = w.api.get(
        f"{base}/deliveries",
        headers=w.h("Desarrollador"),
    )
    assert response.status_code == 403, response.text



def test_invoice_email_http_send_and_history(world):
    """HTTP send persists delivery and exposes it in invoice history."""
    w = world
    base = f"/api/invoices/{w.invoice.id}/email"

    response = w.api.post(
        f"{base}/send",
        headers=w.h("Finanzas"),
        json={"to": ["ana.lopez@xyz.com"]},
    )

    assert response.status_code == 200, (
        response.status_code, response.text
    )

    result = response.json()
    assert result["delivery_id"] is not None
    assert result["sent"] is True
    assert result["status"] == "sent"

    history = w.api.get(
        f"{base}/deliveries",
        headers=w.h("Finanzas"),
    )

    assert history.status_code == 200, history.text

    deliveries = history.json()
    matching = [
        row for row in deliveries
        if row["id"] == result["delivery_id"]
    ]

    assert len(matching) == 1
    assert matching[0]["status"] == "sent"
    assert "ana.lopez@xyz.com" in matching[0]["to"]



def test_invoice_email_http_validation_and_missing_invoice(world):
    """Invalid requests and missing invoices must not create deliveries."""
    w = world
    base = f"/api/invoices/{w.invoice.id}/email"
    headers = w.h("Finanzas")

    invalid_cases = (
        ("preview", {"to": ["ana.lopez@xyz.com"], "unexpected": True}),
        ("send", {"to": ["ana.lopez@xyz.com"], "unexpected": True}),
        ("preview", {"to": ["valid@example.com"] * 21}),
        ("send", {"to": ["valid@example.com"] * 21}),
    )

    for endpoint, payload in invalid_cases:
        response = w.api.post(
            f"{base}/{endpoint}",
            headers=headers,
            json=payload,
        )
        assert response.status_code == 422, (
            endpoint, response.status_code, response.text
        )

    for endpoint in ("preview", "send"):
        response = w.api.post(
            f"/api/invoices/99999999/email/{endpoint}",
            headers=headers,
            json={"to": ["ana.lopez@xyz.com"]},
        )
        assert response.status_code == 404, (
            endpoint, response.status_code, response.text
        )

    response = w.api.get(
        "/api/invoices/99999999/email/deliveries",
        headers=headers,
    )
    assert response.status_code == 404, response.text

    history = w.api.get(
        f"{base}/deliveries",
        headers=headers,
    )
    assert history.status_code == 200, history.text
    assert history.json() == []
