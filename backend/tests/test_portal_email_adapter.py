import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.models.email import EmailDelivery
from app.models.portal_registration import PortalRegistration
from app.services.email.transport import SmtpTransport
from app.services.portal.mail_service import development_outbox
from tests.test_client_portal_integration import _admin_headers, portal_api  # noqa: F401
from tests.test_email_infrastructure import FakeSMTP, make_settings, reset_fake  # noqa: F401

REGISTRATION = {"username": "cliente.portal", "email": "cliente@example.com", "full_name": "Persona Cliente", "password": "ClientePass123",
                "password_confirmation": "ClientePass123", "declared_company_name": "Cliente Portal SA", "declared_company_rfc": "ABC010101ABC",
                "contact_phone": None, "job_title": "Calidad"}


@pytest.fixture()
def smtp_on(monkeypatch):
    settings = make_settings(portal_public_base_url="https://erp.example.test")
    monkeypatch.setattr("app.services.email.service.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.email.service.SmtpTransport", lambda s: SmtpTransport(s, smtp_factory=FakeSMTP))
    monkeypatch.setattr("app.services.portal.mail_service.settings", settings)
    return settings


def test_registration_sends_verification_through_email_service(portal_api, smtp_on):
    api, db, *_ = portal_api
    assert api.post("/api/portal/registration", json=REGISTRATION).status_code == 201
    token = development_outbox[-1].token
    delivery = db.scalar(select(EmailDelivery))
    assert delivery.template_key == "portal_email_verification" and delivery.status == "sent"
    assert (delivery.related_entity_type, delivery.to_json) == ("portal_registration", ["cliente@example.com"])
    real = FakeSMTP.instances[0].sent[0].get_body(("plain",)).get_content()
    assert f"https://erp.example.test/portal/verificar-correo?token={token}" in real
    assert token not in delivery.body_text_snapshot + delivery.body_html_snapshot + str(delivery.provider_response)
    # resend renews the token and uses the same service
    assert api.post("/api/portal/registration/resend-verification", json={"email": "cliente@example.com"}).status_code in {200, 202}
    assert len(db.scalars(select(EmailDelivery)).all()) == 2
    assert development_outbox[-1].token != token


def test_smtp_failure_does_not_revert_registration(portal_api, smtp_on):
    api, db, *_ = portal_api
    FakeSMTP.fail_with = TimeoutError("smtp down")
    response = api.post("/api/portal/registration", json=REGISTRATION)
    assert response.status_code == 201
    assert db.scalar(select(PortalRegistration)).verification_token_hash
    assert db.scalar(select(EmailDelivery)).status == "failed"


def test_disabled_email_keeps_portal_working_and_records_honestly(portal_api):
    api, db, *_ = portal_api
    assert api.post("/api/portal/registration", json=REGISTRATION).status_code == 201
    delivery = db.scalar(select(EmailDelivery))
    assert delivery.status == "failed" and delivery.attempt_count == 0
    assert development_outbox[-1].kind == "verification"


def test_invitation_create_and_resend_use_email_service(portal_api, smtp_on):
    api, db, admin, client = portal_api
    headers = _admin_headers(admin)
    created = api.post("/api/client-portal/invitations", headers=headers, json={"client_id": client.id, "email": "nuevo@example.com", "full_name": "Nuevo", "role_codes": ["viewer"]})
    assert created.status_code in {200, 201}, created.text
    first = db.scalar(select(EmailDelivery))
    assert first.template_key == "portal_invitation" and first.status == "sent"
    assert "Cliente Portal" in FakeSMTP.instances[0].sent[0].get_body(("plain",)).get_content()
    token = development_outbox[-1].token
    assert token not in first.body_text_snapshot + first.body_html_snapshot
    FakeSMTP.fail_with = TimeoutError("down")
    resent = api.post(f"/api/client-portal/invitations/{created.json()['id']}/resend", headers=headers)
    assert resent.status_code in {200, 201}, resent.text
    assert [d.status for d in db.scalars(select(EmailDelivery).order_by(EmailDelivery.id)).all()] == ["sent", "failed"]


def test_production_without_base_url_does_not_send_or_leak(portal_api, monkeypatch):
    api, db, *_ = portal_api
    settings = make_settings(environment="production", secret_key="Zq8!vN3#rT6@wK1$yB9%xC4^mD7&hF2*", portal_public_base_url="")
    monkeypatch.setattr("app.services.portal.mail_service.settings", settings)
    development_outbox.clear()
    assert api.post("/api/portal/registration", json=REGISTRATION).status_code == 201
    assert development_outbox == [] and db.scalar(select(EmailDelivery)) is None


def test_production_rejects_email_without_starttls():
    with pytest.raises(ValueError, match="STARTTLS"):
        make_settings(environment="production", secret_key="Zq8!vN3#rT6@wK1$yB9%xC4^mD7&hF2*", smtp_use_starttls=False)
