import smtplib
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.db import Base, get_db
from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.email import EmailDelivery, EmailTemplate
from app.models.user import Role, User
from app.services.email import EmailAttachment, retry_delivery, send_email
from app.services.email.catalog import TEMPLATE_DEFINITIONS
from app.services.email.errors import EmailTemplateError
from app.services.email.renderer import render_email
from app.services.email.service import RetryNotAllowed, preview_email
from app.services.email.templates import ensure_default_templates, update_template
from app.services.email.transport import OutgoingMessage, SmtpTransport, normalize_address

SECRET_URL = "https://erp.example.test/portal/verificar-correo?token=SUPERSECRETTOKEN"


def make_settings(**overrides) -> Settings:
    values = dict(
        email_enabled=True, smtp_host="smtp.test", smtp_port=587, smtp_use_starttls=True,
        smtp_username="", email_from_address="erp@mycmetrology.com.mx", email_from_name="MYC",
        email_reply_to="", environment="development",
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


class FakeSMTP:
    instances: list["FakeSMTP"] = []
    fail_with: Exception | None = None

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.timeout, self.calls, self.sent = host, port, timeout, [], None
        FakeSMTP.instances.append(self)

    def ehlo(self): self.calls.append("ehlo")
    def starttls(self, context=None): self.calls.append("starttls")
    def login(self, user, password): self.calls.append(("login", user, password))
    def quit(self): self.calls.append("quit")

    def send_message(self, message, from_addr, to_addrs):
        if FakeSMTP.fail_with:
            raise FakeSMTP.fail_with
        self.sent = (message, from_addr, to_addrs)
        return {}


@pytest.fixture(autouse=True)
def reset_fake():
    FakeSMTP.instances, FakeSMTP.fail_with = [], None


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


def transport(settings):
    return SmtpTransport(settings, smtp_factory=FakeSMTP)


def message(**kw):
    return OutgoingMessage(subject="Hola", body_text="texto", body_html="<p>html</p>", to=["a@example.com"], **kw)


# --- A. renderer -----------------------------------------------------------
DEF = TEMPLATE_DEFINITIONS["portal_invitation"]


def render(body, context, subject="Asunto", **kw):
    return render_email(DEF, subject_template=subject, body_template=body, context=context, **kw)


def test_renderer_substitutes_text_html_and_subject():
    out = render("Hola {recipient_name}\n\n{invitation_url}", {"recipient_name": "Ana <b>", "invitation_url": "https://x.test/a?b=1&c=2"})
    assert "Hola Ana <b>" in out.body_text and "https://x.test/a?b=1&c=2" in out.body_text
    assert "Ana &lt;b&gt;" in out.body_html and "<b>" not in out.body_html.replace("<br>", "")
    assert 'href="https://x.test/a?b=1&amp;c=2"' in out.body_html
    assert out.subject == "Asunto"


def test_renderer_rejects_unknown_placeholder_context_and_missing_values():
    with pytest.raises(EmailTemplateError):
        render("Hola {unknown}", {})
    with pytest.raises(EmailTemplateError):
        render("Hola {recipient_name}", {"recipient_name": "A", "extra": "x"})
    with pytest.raises(EmailTemplateError):
        render("Hola {recipient_name}", {})


def test_renderer_does_not_evaluate_expressions_or_traverse_attributes():
    for body in ("{recipient_name.__class__}", "{recipient_name!r}", "{recipient_name:>10}", "{{7*7}}", "{0}", "{ recipient_name }", "{recipient_name"):
        with pytest.raises(EmailTemplateError):
            render(body, {"recipient_name": "A"})
    out = render("{recipient_name}", {"recipient_name": "{invitation_url}"})
    assert out.body_text == "{invitation_url}"  # values are never re-interpreted


def test_renderer_blocks_header_injection_and_bad_urls():
    out = render_email(TEMPLATE_DEFINITIONS["password_reset"], subject_template="Reset {recipient_name}", body_template="{reset_url} {expires_in}",
                       context={"recipient_name": "A\r\nBcc: evil@x.test", "reset_url": "https://x.test/r", "expires_in": "1 h"})
    assert "\r" not in out.subject and "\n" not in out.subject
    with pytest.raises(EmailTemplateError):
        render("{invitation_url}", {"invitation_url": "javascript:alert(1)"})


def test_renderer_redacts_secret_variables_for_snapshots():
    out = render("{invitation_url}", {"invitation_url": SECRET_URL}, redact_secrets=True)
    assert "SUPERSECRETTOKEN" not in out.body_text + out.body_html


# --- B. templates ----------------------------------------------------------
def test_default_templates_are_idempotent_and_never_overwrite_edits(db):
    ensure_default_templates(db); ensure_default_templates(db)
    keys = set(db.scalars(select(EmailTemplate.template_key)).all())
    assert keys == {"portal_email_verification", "portal_invitation", "password_reset", "quotation_send", "invoice_send"}
    update_template(db, "quotation_send", actor_id=1, subject_template="Nueva {quotation_folio}")
    ensure_default_templates(db)
    assert db.scalar(select(EmailTemplate).where(EmailTemplate.template_key == "quotation_send")).subject_template == "Nueva {quotation_folio}"
    assert db.scalar(select(AuditLog).where(AuditLog.action == "email.template.updated"))


def test_template_key_is_unique(db):
    ensure_default_templates(db)
    db.add(EmailTemplate(template_key="invoice_send", name="x", subject_template="s", body_template="b"))
    with pytest.raises(Exception):
        db.commit()
    db.rollback()


def test_update_rejects_disallowed_variables(db):
    with pytest.raises(EmailTemplateError):
        update_template(db, "invoice_send", actor_id=1, body_template="Hola {reset_url}")
    with pytest.raises(EmailTemplateError):
        update_template(db, "nope", actor_id=1, body_template="x")


# --- C. transport ----------------------------------------------------------
def test_transport_uses_starttls_and_no_auth_without_credentials():
    settings = make_settings()
    result = transport(settings).send(message(bcc=["hidden@example.com"]))
    smtp = FakeSMTP.instances[0]
    assert smtp.calls == ["ehlo", "starttls", "ehlo", "quit"]
    assert (smtp.host, smtp.port, smtp.timeout) == ("smtp.test", 587, 15)
    assert not any(isinstance(c, tuple) and c[0] == "login" for c in smtp.calls)
    email, sender, recipients = smtp.sent
    assert sender == "erp@mycmetrology.com.mx" and recipients == ["a@example.com", "hidden@example.com"]
    assert "hidden@example.com" not in email.as_string() and email["Bcc"] is None
    assert result.message_id == email["Message-ID"]


def test_transport_authenticates_only_when_configured():
    transport(make_settings(smtp_username="user", smtp_password="s3cret")).send(message())
    assert ("login", "user", "s3cret") in FakeSMTP.instances[0].calls
    FakeSMTP.instances.clear()
    transport(make_settings(smtp_username="user")).send(message())  # username without password: no AUTH
    assert not any(isinstance(c, tuple) for c in FakeSMTP.instances[0].calls)


def test_transport_headers_reply_to_and_attachment():
    settings = make_settings(email_reply_to="ventas@mycmetrology.com.mx")
    msg = message(cc=["c@example.com"], attachments=(EmailAttachment("../../etc/passwd.pdf", b"%PDF", "application/pdf"),))
    transport(settings).send(msg)
    email = FakeSMTP.instances[0].sent[0]
    assert email["Reply-To"] == "ventas@mycmetrology.com.mx" and email["Cc"] == "c@example.com"
    assert email["From"] == "MYC <erp@mycmetrology.com.mx>"
    parts = list(email.iter_attachments())
    assert len(parts) == 1 and parts[0].get_filename() == "passwd.pdf" and parts[0].get_content_type() == "application/pdf"


def test_transport_rejects_header_injection_and_invalid_addresses():
    for bad in ("a@example.com\r\nBcc: x@y.test", "no-at-sign", "a@b", "a b@example.com", ""):
        with pytest.raises(Exception):
            normalize_address(bad)
    with pytest.raises(Exception):
        transport(make_settings()).send(OutgoingMessage("Hi\r\nBcc: x@y.test", "t", "h", ["a@example.com"]))
    assert not FakeSMTP.instances


def test_transport_errors_are_normalized_without_secrets():
    FakeSMTP.fail_with = smtplib.SMTPServerDisconnected("conn lost with s3cret and user")
    with pytest.raises(Exception) as caught:
        transport(make_settings(smtp_username="user", smtp_password="s3cret")).send(message())
    assert "s3cret" not in str(caught.value) and "user" not in str(caught.value)
    FakeSMTP.fail_with = smtplib.SMTPAuthenticationError(535, b"bad s3cret")
    with pytest.raises(Exception) as caught:
        transport(make_settings(smtp_username="user", smtp_password="s3cret")).send(message())
    assert "s3cret" not in str(caught.value)
    FakeSMTP.fail_with = TimeoutError("timed out")
    with pytest.raises(Exception):
        transport(make_settings()).send(message())


# --- D/E. delivery ---------------------------------------------------------
CTX = {"recipient_name": "Ana", "verification_url": SECRET_URL}


def send(db, settings=None, **kw):
    settings = settings or make_settings()
    args = dict(template_key="portal_email_verification", context=CTX, to=["ana@example.com"],
                related_entity_type="portal_registration", related_entity_id=5, requested_by_id=None)
    args.update(kw)
    return send_email(db, settings=settings, transport=transport(settings), **args)


def test_successful_delivery_lifecycle_and_redacted_snapshot(db):
    result = send(db)
    delivery = db.get(EmailDelivery, result.delivery_id)
    assert result.sent and result.status == delivery.status == "sent"
    assert delivery.attempt_count == 1 and delivery.sent_at and delivery.failed_at is None
    assert delivery.provider_message_id and delivery.to_json == ["ana@example.com"]
    assert "SUPERSECRETTOKEN" not in delivery.body_text_snapshot + delivery.body_html_snapshot + (delivery.provider_response or "")
    # ...but the real message that left the building carries the real link
    sent_email = FakeSMTP.instances[0].sent[0]
    assert "SUPERSECRETTOKEN" in sent_email.get_body(("plain",)).get_content()
    log = db.scalar(select(AuditLog).where(AuditLog.action == "email.delivery.sent"))
    assert "SUPERSECRETTOKEN" not in str(log.new_values) and log.new_values["template_key"] == "portal_email_verification"


def test_preview_matches_what_is_sent(db):
    previewed = preview_email(db, template_key="portal_email_verification", context=CTX, settings=make_settings())
    send(db)
    sent = FakeSMTP.instances[0].sent[0]
    assert sent["Subject"] == previewed.subject
    assert sent.get_body(("plain",)).get_content().strip() == previewed.body_text
    assert sent.get_body(("html",)).get_content().strip() == previewed.body_html


def test_transport_failure_is_recorded_not_raised(db):
    FakeSMTP.fail_with = TimeoutError("boom")
    result = send(db)
    delivery = db.get(EmailDelivery, result.delivery_id)
    assert not result.sent and delivery.status == "failed" and delivery.failed_at and delivery.last_error
    assert delivery.attempt_count == 1 and delivery.status != "sending"
    assert db.scalar(select(AuditLog).where(AuditLog.action == "email.delivery.failed"))


def test_disabled_email_never_reports_sent_and_never_connects(db):
    result = send(db, make_settings(email_enabled=False))
    delivery = db.get(EmailDelivery, result.delivery_id)
    assert not result.sent and result.reason == "email_disabled"
    assert delivery.status == "failed" and delivery.attempt_count == 0 and "EMAIL_ENABLED=false" in delivery.last_error
    assert not FakeSMTP.instances


def test_validation_errors_persist_nothing(db):
    with pytest.raises(EmailTemplateError):
        send(db, context={"recipient_name": "A"})
    with pytest.raises(Exception):
        send(db, to=["bad"])
    assert db.scalar(select(EmailDelivery)) is None


def test_retry_rules(db):
    ctx = {"contact_name": "Ana", "client_name": "ACME", "fiscal_identifier": "F-1", "cfdi_uuid": "u", "total": "$1"}
    FakeSMTP.fail_with = TimeoutError("boom")
    failed = send(db, template_key="invoice_send", context=ctx, related_entity_type="invoice", related_entity_id=1)
    FakeSMTP.fail_with = None
    settings = make_settings()
    with pytest.raises(RetryNotAllowed):
        retry_delivery(db, 9999, actor_id=1, settings=settings, transport=transport(settings))
    again = retry_delivery(db, failed.delivery_id, actor_id=1, settings=settings, transport=transport(settings))
    delivery = db.get(EmailDelivery, failed.delivery_id)
    assert again.sent and delivery.status == "sent" and delivery.attempt_count == 2 and delivery.failed_at is None and delivery.last_error is None
    assert db.scalar(select(AuditLog).where(AuditLog.action == "email.delivery.retried"))
    with pytest.raises(RetryNotAllowed):  # already sent
        retry_delivery(db, failed.delivery_id, actor_id=1, settings=settings, transport=transport(settings))


def test_retry_refused_for_secret_templates_and_attachments(db):
    FakeSMTP.fail_with = TimeoutError("boom")
    secret = send(db)
    settings = make_settings()
    with pytest.raises(RetryNotAllowed):
        retry_delivery(db, secret.delivery_id, actor_id=1, settings=settings, transport=transport(settings))
    ctx = {"contact_name": "Ana", "client_name": "ACME", "fiscal_identifier": "F-1", "cfdi_uuid": "u", "total": "$1"}
    with_pdf = send(db, template_key="invoice_send", context=ctx, attachments=[EmailAttachment("f.pdf", b"%PDF", "application/pdf")])
    delivery = db.get(EmailDelivery, with_pdf.delivery_id)
    assert delivery.attachments_json[0]["filename"] == "f.pdf" and "content" not in delivery.attachments_json[0]
    with pytest.raises(RetryNotAllowed):
        retry_delivery(db, with_pdf.delivery_id, actor_id=1, settings=settings, transport=transport(settings))


def test_retry_attempts_are_capped(db):
    ctx = {"contact_name": "Ana", "client_name": "ACME", "fiscal_identifier": "F-1", "cfdi_uuid": "u", "total": "$1"}
    FakeSMTP.fail_with = TimeoutError("boom")
    result = send(db, template_key="invoice_send", context=ctx)
    settings = make_settings()
    for _ in range(4):
        retry_delivery(db, result.delivery_id, actor_id=1, settings=settings, transport=transport(settings))
    with pytest.raises(RetryNotAllowed):
        retry_delivery(db, result.delivery_id, actor_id=1, settings=settings, transport=transport(settings))


# --- F. RBAC ---------------------------------------------------------------
def test_role_permissions():
    p = ROLE_PERMISSIONS
    assert {"email.templates.read", "email.deliveries.read", "quotations.email.send"} <= p["Comercial"]
    assert "invoices.email.send" not in p["Comercial"] and "email.deliveries.retry" not in p["Comercial"]
    assert {"email.templates.read", "email.deliveries.read", "email.deliveries.retry", "invoices.email.send"} <= p["Finanzas"]
    assert "quotations.email.send" not in p["Finanzas"]
    assert {"email.templates.manage", "email.transport.status", "quotations.email.send", "invoices.email.send"} <= p["Desarrollador"]
    for role in ("Calidad", "Tecnico", "Captura", "Cliente"):
        assert not any(x.startswith("email.") or x.endswith(".email.send") for x in p[role])
    assert p["Administrador"] == {"*"}


# --- G. API / transport status / scope -------------------------------------
@pytest.fixture()
def api(db):
    users = {}
    for role_name in ("Administrador", "Desarrollador", "Comercial", "Finanzas", "Tecnico"):
        role = Role(name=role_name, description=role_name)
        db.add(role); db.flush()
        user = User(username=role_name.lower(), email=f"{role_name.lower()}@myc.test", full_name=role_name, hashed_password=hash_password("Pass12345"),
                    account_type="internal", status="active", email_verified_at=datetime.now(timezone.utc), roles=[role], role_id=role.id)
        db.add(user); db.flush()
        users[role_name] = user
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    def headers(name):
        user = users[name]
        token = create_access_token(str(user.id), extra_claims={"auth_context": "internal", "roles": [name]})
        return {"Authorization": f"Bearer {token}"}

    yield client, headers
    client.close(); app.dependency_overrides.clear()


def test_api_permissions_and_template_update(api):
    client, h = api
    assert client.get("/api/email/templates", headers=h("Tecnico")).status_code == 403
    assert client.get("/api/email/templates", headers=h("Comercial")).status_code == 200
    assert client.patch("/api/email/templates/invoice_send", headers=h("Comercial"), json={"subject_template": "x"}).status_code == 403
    bad = client.patch("/api/email/templates/invoice_send", headers=h("Administrador"), json={"body_template": "{reset_url}"})
    assert bad.status_code == 422
    good = client.patch("/api/email/templates/invoice_send", headers=h("Administrador"), json={"subject_template": "Factura {fiscal_identifier}"})
    assert good.status_code == 200 and "fiscal_identifier" in good.json()["allowed_variables"]
    assert client.get("/api/email/templates/nope", headers=h("Administrador")).status_code == 404


def test_transport_status_distinguishes_enabled_from_configured_and_hides_secrets(api, monkeypatch):
    client, h = api
    from app.routers import email as email_router
    monkeypatch.setattr(email_router, "get_settings", lambda: make_settings(email_enabled=False, smtp_username="user", smtp_password="s3cret"))
    assert client.get("/api/email/transport/status", headers=h("Comercial")).status_code == 403
    body = client.get("/api/email/transport/status", headers=h("Administrador")).json()
    assert body["enabled"] is False and body["configured"] is True and body["authentication_mode"] == "smtp_auth"
    assert "s3cret" not in str(body) and "password" not in str(body).lower() and "user" not in body
    monkeypatch.setattr(email_router, "get_settings", lambda: make_settings(email_enabled=True, smtp_host=""))
    body = client.get("/api/email/transport/status", headers=h("Administrador")).json()
    assert body["enabled"] is True and body["configured"] is False and body["authentication_mode"] == "none_ip_allowlist"


INVOICE_CTX = {"contact_name": "A", "client_name": "B", "fiscal_identifier": "F", "cfdi_uuid": "u", "total": "$1"}


def test_global_delivery_history_is_fail_closed_for_commercial_and_finance(api, db):
    client, h = api
    quotation = send(db, template_key="invoice_send", context=INVOICE_CTX, related_entity_type="quotation", related_entity_id=1)
    invoice = send(db, template_key="invoice_send", context=INVOICE_CTX, related_entity_type="invoice", related_entity_id=2)
    unknown = send(db, template_key="invoice_send", context=INVOICE_CTX, related_entity_type="mystery", related_entity_id=3)
    orphan = send(db, template_key="invoice_send", context=INVOICE_CTX)
    ids = {quotation.delivery_id, invoice.delivery_id, unknown.delivery_id, orphan.delivery_id}
    # Having quotations.read / invoices.read does not open arbitrary deliveries.
    assert client.get(f"/api/email/deliveries/{quotation.delivery_id}", headers=h("Comercial")).status_code == 404
    assert client.get(f"/api/email/deliveries/{invoice.delivery_id}", headers=h("Finanzas")).status_code == 404
    assert client.get(f"/api/email/deliveries/{unknown.delivery_id}", headers=h("Finanzas")).status_code == 404
    assert client.get(f"/api/email/deliveries/{orphan.delivery_id}", headers=h("Comercial")).status_code == 404
    assert client.get("/api/email/deliveries", headers=h("Comercial")).json() == []
    assert client.get("/api/email/deliveries", headers=h("Finanzas")).json() == []
    assert client.get("/api/email/deliveries", headers=h("Tecnico")).status_code == 403
    for admin in ("Administrador", "Desarrollador"):
        assert {row["id"] for row in client.get("/api/email/deliveries", headers=h(admin)).json()} == ids
        assert client.get(f"/api/email/deliveries/{unknown.delivery_id}", headers=h(admin)).status_code == 200
    assert client.get("/api/email/deliveries/99999", headers=h("Administrador")).status_code == 404


def test_delivery_detail_never_exposes_one_time_secrets(api, db):
    client, h = api
    portal = send(db)
    assert "SUPERSECRETTOKEN" not in client.get(f"/api/email/deliveries/{portal.delivery_id}", headers=h("Administrador")).text


def test_global_retry_endpoint_is_fail_closed_and_enforces_rules(api, db, monkeypatch):
    client, h = api
    settings = make_settings()
    monkeypatch.setattr("app.services.email.service.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.email.service.SmtpTransport", lambda s: transport(s))
    FakeSMTP.fail_with = TimeoutError("down")
    failed = send(db, settings, template_key="invoice_send", context=INVOICE_CTX, related_entity_type="invoice", related_entity_id=1)
    FakeSMTP.fail_with = None
    url = f"/api/email/deliveries/{failed.delivery_id}/retry"
    assert client.post(url, headers=h("Comercial")).status_code == 403  # no retry capability
    assert client.post(url, headers=h("Finanzas")).status_code == 404  # has capability, but global scope is admin-only
    response = client.post(url, headers=h("Desarrollador"))
    assert response.status_code == 200 and response.json()["sent"] is True
    secret = send(db, settings)
    FakeSMTP.fail_with = None
    db.get(EmailDelivery, secret.delivery_id).status = "failed"; db.commit()
    assert client.post(f"/api/email/deliveries/{secret.delivery_id}/retry", headers=h("Administrador")).status_code == 409


def test_disabled_delivery_is_not_retryable_and_counts_only_real_smtp_attempts(db, api):
    client, h = api
    disabled = make_settings(email_enabled=False)
    result = send(db, disabled, template_key="invoice_send", context=INVOICE_CTX, related_entity_type="invoice", related_entity_id=1)
    delivery = db.get(EmailDelivery, result.delivery_id)
    assert delivery.status == "failed" and delivery.failure_code == "email_disabled" and delivery.attempt_count == 0
    assert not FakeSMTP.instances
    for _ in range(3):  # enabled or not, it is never retried
        with pytest.raises(RetryNotAllowed, match="deshabilitado"):
            retry_delivery(db, result.delivery_id, actor_id=1, settings=make_settings(), transport=transport(make_settings()))
    assert delivery.attempt_count == 0 and not FakeSMTP.instances
    assert client.post(f"/api/email/deliveries/{result.delivery_id}/retry", headers=h("Administrador")).status_code == 409
    assert not FakeSMTP.instances
    assert client.get(f"/api/email/deliveries/{result.delivery_id}", headers=h("Administrador")).json()["failure_code"] == "email_disabled"


def test_real_smtp_failure_records_failure_code_and_counts_attempt(db):
    FakeSMTP.fail_with = TimeoutError("boom")
    result = send(db, template_key="invoice_send", context=INVOICE_CTX)
    delivery = db.get(EmailDelivery, result.delivery_id)
    assert (delivery.failure_code, delivery.attempt_count) == ("transport_failed", 1)


# --- config fail-fast ------------------------------------------------------
PROD = dict(environment="production", secret_key="Zq8!vN3#rT6@wK1$yB9%xC4^mD7&hF2*")


@pytest.mark.parametrize("overrides", [
    {"smtp_host": ""}, {"smtp_host": "   "}, {"email_from_address": ""}, {"email_from_address": "  "},
    {"email_from_address": "not-an-address"}, {"smtp_use_starttls": False},
])
def test_production_with_email_enabled_rejects_incomplete_smtp_config(overrides):
    with pytest.raises(ValueError):
        make_settings(**PROD, **overrides)


def test_google_relay_by_ip_without_credentials_is_valid_in_production():
    settings = make_settings(**PROD, smtp_host="smtp-relay.gmail.com", smtp_username="", smtp_password="", public_app_base_url="https://erp.example.test")
    assert settings.smtp_port == 587 and settings.smtp_use_starttls


def test_email_disabled_needs_no_smtp_config_in_any_environment():
    assert make_settings(email_enabled=False, smtp_host="", email_from_address="").email_enabled is False
    assert make_settings(**PROD, email_enabled=False, smtp_host="", email_from_address="").email_enabled is False
    assert Settings(_env_file=None).email_enabled is False  # development defaults
