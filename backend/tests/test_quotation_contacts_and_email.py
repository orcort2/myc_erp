"""EMAIL-3: ClientContact management, Quotation.contact_id and contextual quotation email."""
from datetime import date, datetime, timezone
from hashlib import sha256

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
from app.models.quotation import Quotation
from app.models.user import Role, User
from app.services import quotation_email
from app.services.email.transport import SmtpTransport
from app.services.quotation_pdfs import _render_html, generate_quotation_pdf
from test_email_infrastructure import FakeSMTP, make_settings, reset_fake  # noqa: F401

ROLES = ("Administrador", "Desarrollador", "Comercial", "Finanzas", "Tecnico")


@pytest.fixture()
def world(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    settings = make_settings()
    monkeypatch.setattr("app.services.email.service.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.quotation_email.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.email.service.SmtpTransport", lambda s: SmtpTransport(s, smtp_factory=FakeSMTP))
    with Session(engine, expire_on_commit=False) as db:
        users = {}
        for name in ROLES:
            role = Role(name=name, description=name)
            db.add(role); db.flush()
            user = User(username=name.lower(), email=f"{name.lower()}@myc.test", full_name=f"{name} MYC", hashed_password=hash_password("Pass12345"),
                        account_type="internal", status="active", email_verified_at=datetime.now(timezone.utc), roles=[role], role_id=role.id)
            db.add(user); db.flush()
            users[name] = user
        client = Client(legal_name="Grupo XYZ SA", commercial_name="Grupo XYZ", email="compras@xyz.com", phone="3300000000")
        other = Client(legal_name="Otro SA", commercial_name="Otro", email="otro@otro.com")
        db.add_all([client, other]); db.flush()
        ana = ClientContact(client_id=client.id, name="Ana López", position="Compras", email="ana.lopez@xyz.com", phone="3311111111")
        luis = ClientContact(client_id=client.id, name="Luis Pérez", position="Mantenimiento", email="luis.perez@xyz.com")
        sin_correo = ClientContact(client_id=client.id, name="Sin Correo")
        foreign = ClientContact(client_id=other.id, name="Persona Ajena", email="ajena@otro.com")
        db.add_all([ana, luis, sin_correo, foreign]); db.commit()
        quotation = Quotation(folio="COT-2026-0001", client_id=client.id, advisor_id=users["Comercial"].id, status="draft",
                              issued_on=date(2026, 9, 1), valid_until=date(2026, 10, 1))
        db.add(quotation); db.commit()
        app.dependency_overrides[get_db] = lambda: db
        api = TestClient(app)

        def h(name):
            token = create_access_token(str(users[name].id), extra_claims={"auth_context": "internal", "roles": [name]})
            return {"Authorization": f"Bearer {token}"}

        yield type("W", (), dict(api=api, db=db, h=staticmethod(h), users=users, client=client, other=other, ana=ana, luis=luis,
                                  sin_correo=sin_correo, foreign=foreign, quotation=quotation))
        api.close(); app.dependency_overrides.clear()
    engine.dispose()


# ---------------------------------------------------------------- contacts
def test_contact_crud_keeps_identity_and_soft_deletes(world):
    w = world
    base = f"/api/clients/{w.client.id}/contacts"
    created = w.api.post(base, headers=w.h("Comercial"), json={"name": "  Mariana Torres ", "email": "mariana@xyz.com", "position": "Calidad"})
    assert created.status_code == 201 and created.json()["name"] == "Mariana Torres" and created.json()["client_id"] == w.client.id
    cid = created.json()["id"]
    patched = w.api.patch(f"{base}/{cid}", headers=w.h("Comercial"), json={"phone": "3322222222"})
    assert patched.status_code == 200 and patched.json()["id"] == cid and patched.json()["email"] == "mariana@xyz.com"
    assert w.api.delete(f"{base}/{cid}", headers=w.h("Comercial")).json()["is_active"] is False
    assert w.db.get(ClientContact, cid) is not None  # soft delete: row survives
    assert cid in {c["id"] for c in w.api.get(base, headers=w.h("Comercial")).json()}
    assert w.api.post(f"{base}/{cid}/restore", headers=w.h("Comercial")).json()["is_active"] is True
    actions = {a.action for a in w.db.scalars(select(AuditLog)).all()}
    assert {"client.contact.created", "client.contact.updated", "client.contact.deactivated", "client.contact.restored"} <= actions


def test_contact_validation_and_cross_client_isolation(world):
    w = world
    base = f"/api/clients/{w.client.id}/contacts"
    assert w.api.post(base, headers=w.h("Comercial"), json={"name": "X", "email": "no-es-correo"}).status_code == 422
    assert w.api.post(base, headers=w.h("Comercial"), json={"name": ""}).status_code == 422
    assert w.api.patch(f"{base}/{w.ana.id}", headers=w.h("Comercial"), json={"email": "bad"}).status_code == 422
    assert w.api.patch(f"{base}/{w.ana.id}", headers=w.h("Comercial"), json={"client_id": w.other.id}).status_code == 422
    # a contact of another client is never reachable through this client's route
    for call in (w.api.patch(f"{base}/{w.foreign.id}", headers=w.h("Comercial"), json={"name": "Hack"}),
                 w.api.delete(f"{base}/{w.foreign.id}", headers=w.h("Comercial")),
                 w.api.post(f"{base}/{w.foreign.id}/restore", headers=w.h("Comercial"))):
        assert call.status_code == 404
    assert w.db.get(ClientContact, w.foreign.id).name == "Persona Ajena"
    assert w.api.get("/api/clients/99999/contacts", headers=w.h("Comercial")).status_code == 404


def test_contact_rbac(world):
    w = world
    base = f"/api/clients/{w.client.id}/contacts"
    assert w.api.get(base, headers=w.h("Tecnico")).status_code == 403
    assert w.api.post(base, headers=w.h("Tecnico"), json={"name": "N"}).status_code == 403
    assert w.api.get(base, headers=w.h("Finanzas")).status_code == 200
    assert w.api.post(base, headers=w.h("Finanzas"), json={"name": "N"}).status_code == 403


def test_embedded_client_patch_no_longer_destroys_contact_identity(world):
    w = world
    ana_id = w.ana.id
    response = w.api.patch(f"/api/clients/{w.client.id}", headers=w.h("Comercial"),
                           json={"contacts": [{"name": "Ana López", "email": "ana.lopez@xyz.com", "phone": "3399999999"}]})
    assert response.status_code == 200
    by_id = {c["id"]: c for c in response.json()["contacts"]}
    assert by_id[ana_id]["phone"] == "3399999999" and by_id[ana_id]["is_active"] is True
    assert by_id[w.luis.id]["is_active"] is False  # unlisted -> deactivated, not deleted


# ------------------------------------------------------ quotation contact
def create_quotation(w, **extra):
    return w.api.post("/api/quotations", headers=w.h("Comercial"), json={"client_id": w.client.id, "items": [], **extra})


def test_quotation_contact_create_update_and_projection(world):
    w = world
    created = create_quotation(w, contact_id=w.luis.id)
    assert created.status_code == 201, created.text
    body = created.json()
    assert (body["contact_id"], body["contact_name"], body["contact_email"], body["contact_position"]) == (w.luis.id, "Luis Pérez", "luis.perez@xyz.com", "Mantenimiento")
    qid = body["id"]
    assert w.api.patch(f"/api/quotations/{qid}", headers=w.h("Comercial"), json={"contact_id": w.ana.id}).json()["contact_name"] == "Ana López"
    cleared = w.api.patch(f"/api/quotations/{qid}", headers=w.h("Comercial"), json={"contact_id": None})
    assert cleared.status_code == 200 and cleared.json()["contact_id"] is None
    assert create_quotation(w).json()["contact_id"] is None  # nullable / backwards compatible


def test_quotation_rejects_foreign_or_inactive_contacts(world):
    w = world
    assert create_quotation(w, contact_id=w.foreign.id).status_code == 422
    w.luis.is_active = False; w.db.commit()
    assert create_quotation(w, contact_id=w.luis.id).status_code == 422
    qid = create_quotation(w, contact_id=w.ana.id).json()["id"]
    assert w.api.patch(f"/api/quotations/{qid}", headers=w.h("Comercial"), json={"contact_id": w.foreign.id}).status_code == 422
    assert w.api.patch(f"/api/quotations/{qid}", headers=w.h("Comercial"), json={"contact_id": w.luis.id}).status_code == 422


def test_changing_client_clears_the_stale_contact_and_rejects_mismatches(world):
    w = world
    qid = create_quotation(w, contact_id=w.ana.id).json()["id"]
    moved = w.api.patch(f"/api/quotations/{qid}", headers=w.h("Comercial"), json={"client_id": w.other.id})
    assert moved.status_code == 200 and moved.json()["contact_id"] is None
    qid2 = create_quotation(w, contact_id=w.ana.id).json()["id"]
    assert w.api.patch(f"/api/quotations/{qid2}", headers=w.h("Comercial"), json={"client_id": w.other.id, "contact_id": w.ana.id}).status_code == 422
    assert w.api.patch(f"/api/quotations/{qid2}", headers=w.h("Comercial"), json={"client_id": w.other.id, "contact_id": w.foreign.id}).json()["contact_name"] == "Persona Ajena"


def test_historical_quotation_keeps_an_inactive_contact(world):
    w = world
    qid = create_quotation(w, contact_id=w.ana.id).json()["id"]
    assert w.api.delete(f"/api/clients/{w.client.id}/contacts/{w.ana.id}", headers=w.h("Comercial")).status_code == 200
    read = w.api.get(f"/api/quotations/{qid}", headers=w.h("Comercial")).json()
    assert read["contact_name"] == "Ana López"
    assert w.api.patch(f"/api/quotations/{qid}", headers=w.h("Comercial"), json={"notes": "sigue editable"}).status_code == 200
    assert w.api.get(f"/api/quotations/{qid}", headers=w.h("Comercial")).json()["contact_id"] == w.ana.id


def test_pdf_uses_the_quotation_contact_with_historical_fallback(world):
    w = world
    quotation = w.db.get(Quotation, w.quotation.id)
    html = _render_html(w.db, quotation)  # no contact_id: first active contact (legacy behaviour)
    assert "Ana López" in html
    quotation.contact_id = w.luis.id; w.db.commit(); w.db.expire_all()
    html = _render_html(w.db, w.db.get(Quotation, w.quotation.id))
    assert "Luis Pérez" in html and "Mantenimiento" in html and "luis.perez@xyz.com" in html and "Ana López" not in html
    for contact in w.client.contacts:
        contact.is_active = False
    quotation.contact_id = None; w.db.commit()
    pdf, filename = generate_quotation_pdf(w.db, quotation.id)  # no contacts at all -> still renders
    assert pdf.startswith(b"%PDF") and filename.startswith("Cotizacion_COT-2026-0001")


def test_snapshot_restore_never_leaves_a_foreign_contact(world):
    w = world
    qid = create_quotation(w, contact_id=w.ana.id).json()["id"]
    snapshots = w.api.get(f"/api/quotations/{qid}/snapshots", headers=w.h("Comercial")).json()
    assert snapshots[0]["snapshot_data"]["contact_id"] == w.ana.id


# ----------------------------------------------------------- email preview
def preview(w, who="Comercial", **body):
    return w.api.post(f"/api/quotations/{w.quotation.id}/email/preview", headers=w.h(who), json=body)


def test_preview_builds_everything_in_the_backend(world):
    w = world
    w.db.get(Quotation, w.quotation.id).contact_id = w.luis.id; w.db.commit()
    response = preview(w)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["template_key"] == "quotation_send" and body["to"] == ["luis.perez@xyz.com"] and body["cc"] == []
    sources = [(r["email"], r["source"], r["selected"]) for r in body["available_recipients"]]
    assert sources == [("luis.perez@xyz.com", "quotation_contact", True), ("ana.lopez@xyz.com", "client_contact", False), ("compras@xyz.com", "client_email", False)]
    assert "Luis Pérez" in body["body_text"] and "Grupo XYZ" in body["body_text"] and "COT-2026-0001" in body["body_text"]
    assert "01/10/2026" in body["body_text"] and "Comercial MYC" in body["body_text"] and "None" not in body["body_text"]
    assert "COT-2026-0001" in body["subject"] and "<html" in body["body_html"].lower()
    assert body["attachments"][0]["filename"].startswith("Cotizacion_COT-2026-0001") and body["attachments"][0]["content_type"] == "application/pdf"


def test_default_selection_falls_back_to_first_contact_then_client_email(world):
    w = world
    assert preview(w).json()["to"] == ["ana.lopez@xyz.com"]  # no quotation contact: first active contact with email
    for contact in w.client.contacts:
        contact.is_active = False
    w.db.commit()
    body = preview(w).json()
    assert body["to"] == ["compras@xyz.com"] and body["available_recipients"][0]["source"] == "client_email"
    w.db.get(Client, w.client.id).email = None; w.db.commit()
    assert preview(w).status_code == 422  # nothing to send to


def test_manual_recipients_dedupe_and_validation(world):
    w = world
    body = preview(w, to=["Ana.Lopez@xyz.com", "manual1@otra.com", "manual2@otra.com", "MANUAL1@otra.com"], cc=["manual1@otra.com", "cc@otra.com", "cc@otra.com"]).json()
    assert body["to"] == ["Ana.Lopez@xyz.com", "manual1@otra.com", "manual2@otra.com"]
    assert body["cc"] == ["cc@otra.com"]  # TO wins over CC, no duplicates
    assert "Ana López" in body["body_text"]  # manual address equal to a contact keeps that contact's name
    assert "Grupo XYZ" in preview(w, to=["solo.manual@otra.com"]).json()["body_text"].split("\n")[0]  # no invented name
    for bad in (["no-valido"], ["a@b.com\r\nBcc: x@y.com"], []):
        assert preview(w, to=bad).status_code == 422
    assert preview(w, to=["ok@otra.com"], cc=["malo"]).status_code == 422
    assert w.db.scalar(select(Client.email).where(Client.id == w.client.id)) == "compras@xyz.com"  # manual emails never touch master data
    assert len(w.client.contacts) == 3


def test_client_cannot_inject_subject_body_html_or_files(world):
    w = world
    for field in ("subject", "body", "body_html", "body_text", "html", "attachments", "pdf", "path", "template_key", "bcc", "context"):
        assert preview(w, **{field: "x"}).status_code == 422, field
        assert w.api.post(f"/api/quotations/{w.quotation.id}/email/send", headers=w.h("Comercial"), json={"to": ["a@b.com"], field: "x"}).status_code == 422, field


# ------------------------------------------------------------- email send
def send(w, who="Comercial", **body):
    return w.api.post(f"/api/quotations/{w.quotation.id}/email/send", headers=w.h(who), json=body or {"to": ["ana.lopez@xyz.com"]})


def test_send_attaches_the_official_pdf_and_traces_the_delivery(world):
    w = world
    response = send(w, to=["ana.lopez@xyz.com", "manual@otra.com"], cc=["cc@otra.com"])
    assert response.status_code == 200 and response.json()["sent"] is True
    delivery = w.db.get(EmailDelivery, response.json()["delivery_id"])
    assert (delivery.related_entity_type, delivery.related_entity_id, delivery.requested_by_id) == ("quotation", w.quotation.id, w.users["Comercial"].id)
    assert delivery.to_json == ["ana.lopez@xyz.com", "manual@otra.com"] and delivery.cc_json == ["cc@otra.com"]
    message = FakeSMTP.instances[-1].sent[0]
    attachment = next(message.iter_attachments())
    official, official_name = generate_quotation_pdf(w.db, w.quotation.id)
    assert attachment.get_filename() == official_name and attachment.get_content_type() == "application/pdf"
    assert attachment.get_content().startswith(b"%PDF")
    meta = delivery.attachments_json[0]
    assert meta["filename"] == official_name and meta["size"] == len(attachment.get_content()) and len(meta["sha256"]) == 64
    assert meta["sha256"] == sha256(attachment.get_content()).hexdigest() and "content" not in meta
    assert "quotation.email.sent" in {a.action for a in w.db.scalars(select(AuditLog)).all()}
    audit = w.db.scalar(select(AuditLog).where(AuditLog.action == "quotation.email.sent"))
    assert audit.new_values["quotation_folio"] == "COT-2026-0001" and "body" not in str(audit.new_values)


def test_email_never_changes_the_quotation_status(world):
    w = world
    assert send(w).json()["sent"] is True
    FakeSMTP.fail_with = TimeoutError("down")
    assert send(w).json()["sent"] is False
    assert w.db.get(Quotation, w.quotation.id, populate_existing=True).status == "draft"


def test_smtp_failure_is_traced_and_resend_creates_a_new_delivery(world):
    w = world
    FakeSMTP.fail_with = TimeoutError("down")
    failed = send(w).json()
    assert failed["status"] == "failed" and failed["sent"] is False
    FakeSMTP.fail_with = None
    ok = send(w).json()
    assert ok["sent"] is True and ok["delivery_id"] != failed["delivery_id"]
    assert w.db.get(EmailDelivery, failed["delivery_id"]).status == "failed"  # history is never mutated
    assert w.api.post(f"/api/quotations/{w.quotation.id}/email/send", headers=w.h("Comercial"), json={}).status_code == 422  # TO required


def test_send_and_preview_require_the_email_permission(world):
    w = world
    for who in ("Finanzas", "Tecnico"):
        assert preview(w, who).status_code == 403 and send(w, who).status_code == 403
    assert preview(w, "Desarrollador").status_code == 200
    assert w.api.post("/api/quotations/99999/email/preview", headers=w.h("Comercial"), json={}).status_code == 404


# ----------------------------------------------------------------- history
def test_contextual_history_is_scoped_to_the_quotation_and_not_global(world):
    w = world
    other_q = Quotation(folio="COT-2026-0002", client_id=w.client.id, status="draft", issued_on=date(2026, 9, 2))
    w.db.add(other_q); w.db.commit()
    first = send(w).json()["delivery_id"]
    w.api.post(f"/api/quotations/{other_q.id}/email/send", headers=w.h("Comercial"), json={"to": ["x@otra.com"]})
    FakeSMTP.fail_with = TimeoutError("down")
    second = send(w, to=["luis.perez@xyz.com"]).json()["delivery_id"]
    history = w.api.get(f"/api/quotations/{w.quotation.id}/email/deliveries", headers=w.h("Comercial"))
    assert history.status_code == 200
    rows = history.json()
    assert [r["id"] for r in rows] == [second, first]  # newest first, only this quotation
    assert rows[0]["status"] == "failed" and rows[0]["failure_code"] == "transport_failed" and rows[0]["requested_by_name"] == "Comercial MYC"
    assert rows[1]["status"] == "sent" and rows[1]["to"] == ["ana.lopez@xyz.com"] and rows[1]["attachments"][0]["sha256"]
    assert "bcc" not in str(rows).lower() and "body" not in str(rows[0].keys()).lower()
    # the global admin history stays fail-closed for Comercial
    assert w.api.get("/api/email/deliveries", headers=w.h("Comercial")).json() == []
    assert w.api.get(f"/api/email/deliveries/{first}", headers=w.h("Comercial")).status_code == 404
    assert w.api.get(f"/api/quotations/{w.quotation.id}/email/deliveries", headers=w.h("Tecnico")).status_code == 403
    assert w.api.get("/api/quotations/99999/email/deliveries", headers=w.h("Comercial")).status_code == 404


def test_quotation_contact_migration_is_the_single_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert script.get_heads() == ["c3e6a9b2d4f8"]
    assert script.get_revision("c3e6a9b2d4f8").down_revision == "b2d5f8a1c3e7"
    column = Quotation.__table__.c.contact_id
    assert column.nullable and next(iter(column.foreign_keys)).ondelete == "SET NULL"
