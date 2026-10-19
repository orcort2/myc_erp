"""Acceptance orchestration regression: evidence, OTP and ETS share a transaction."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services.quotation_signing_acceptance import accept_signed_quotation


def _settings():
    return Settings(
        quotation_signing_enabled=True,
        secret_key="test-signing-secret-with-sufficient-randomness-12345",
    )


def _context():
    now = datetime.now(timezone.utc)
    pdf = b"%PDF-1.4 frozen-test"
    quotation = SimpleNamespace(
        id=18, folio="MYC-TEST-18", status="sent",
        client_id=5, advisor_id=7, is_active=True,
    )
    document = SimpleNamespace(
        id=10, quotation_id=18, snapshot_id=12,
        snapshot_sha256="commercial-digest",
        pdf_sha256=sha256(pdf).hexdigest(), pdf_bytes=pdf,
    )
    link = SimpleNamespace(id=20, recipient_email="contact@example.com")
    challenge = SimpleNamespace(
        id=30, signing_link_id=20, snapshot_id=12,
        recipient_email="contact@example.com",
        verified_at=now, consumed_at=None, revoked_at=None,
        expires_at=now + timedelta(minutes=5),
    )
    return quotation, document, link, challenge


def test_acceptance_creates_ets_without_committing():
    db = MagicMock()
    quotation, document, link, challenge = _context()
    db.scalar.side_effect = [quotation, challenge, None, None]
    def flush():
        db.add.call_args.args[0].id = 40
    db.flush.side_effect = flush
    with (
        patch(
            "app.services.quotation_signing_acceptance.authorize_document_link",
            return_value=(document, link),
        ) as authorize,
        patch("app.services.service_orders.create_service_order") as create_ets,
        patch(
            "app.services.quotation_signing_acceptance.invalidate_document_links"
        ) as invalidate,
        patch("app.services.quotation_signing_acceptance.write_audit_log") as audit,
        patch("app.services.quotation_signing_acceptance.queue_notification_for_delivery") as enqueue,
        patch(
            "app.services.quotation_signing_acceptance.next_acceptance_confirmation_folio",
            return_value="MYC-AC-2026-000002",
        ),
        patch("app.services.quotation_signing_acceptance.publish_event") as publish,
    ):
        create_ets.return_value = SimpleNamespace(id=55, folio="OSMYC-26-10-0001")
        result = accept_signed_quotation(
            db, signing_token="test-token", challenge_id=30,
            signer_name="  Persona Autorizada  ", consent=True,
            settings=_settings(),
        )
    assert result.confirmation_folio == "MYC-AC-2026-000002"
    publish.assert_called_once()
    event = publish.call_args.kwargs
    assert event["event_code"] == "quotation.accepted_electronically"
    assert event["idempotency_key"] == "quotation:18:acceptance:40"
    assert event["metadata"]["confirmation_folio"] == "MYC-AC-2026-000002"
    assert event["metadata"]["service_order_id"] == 55
    assert "pdf_bytes" not in event["metadata"]
    assert authorize.call_count == 2
    assert result.id == 40
    assert result.signer_name == "Persona Autorizada"
    assert result.pdf_bytes == document.pdf_bytes
    assert result.snapshot_id == document.snapshot_id
    assert quotation.status == "accepted"
    assert challenge.consumed_at is not None
    assert create_ets.call_count == 1
    assert create_ets.call_args.kwargs["commit"] is False
    assert create_ets.call_args.kwargs["user_id"] == 7
    invalidate.assert_called_once_with(db, quotation_id=18)
    audit.assert_called_once()
    enqueue.assert_called_once()
    notification = enqueue.call_args.args[1]
    assert notification.recipient_user_id == 7
    assert notification.notification_type == "quotation.accepted"
    assert notification.event_key == "quotation:18:acceptance:40:advisor:7"
    assert notification.metadata_json["frontend_path"] == "/quotations?quotation_id=18"
    db.commit.assert_not_called()


def test_acceptance_requires_advisor_before_ets_and_no_commit():
    db = MagicMock()
    quotation, document, link, challenge = _context()
    quotation.advisor_id = None
    db.scalar.side_effect = [quotation, challenge, None]
    with (
        patch(
            "app.services.quotation_signing_acceptance.authorize_document_link",
            return_value=(document, link),
        ),
        patch("app.services.service_orders.create_service_order") as create_ets,
        patch("app.services.quotation_signing_acceptance.invalidate_document_links") as invalidate,
    ):
        with pytest.raises(HTTPException) as exc:
            accept_signed_quotation(
                db, signing_token="test-token", challenge_id=30,
                signer_name="Persona Autorizada", consent=True,
                settings=_settings(),
            )
    assert exc.value.status_code == 409
    create_ets.assert_not_called()
    invalidate.assert_not_called()
    db.commit.assert_not_called()


def test_acceptance_rejects_unverified_otp_without_mutating_status():
    db = MagicMock()
    quotation, document, link, challenge = _context()
    challenge.verified_at = None
    db.scalar.side_effect = [quotation, challenge]
    with patch(
        "app.services.quotation_signing_acceptance.authorize_document_link",
        return_value=(document, link),
    ):
        with pytest.raises(HTTPException) as exc:
            accept_signed_quotation(
                db, signing_token="test-token", challenge_id=30,
                signer_name="Persona Autorizada", consent=True,
                settings=_settings(),
            )
    assert exc.value.status_code == 409
    assert quotation.status == "sent"
    assert challenge.consumed_at is None
    db.add.assert_not_called()
    db.commit.assert_not_called()
