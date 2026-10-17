"""Regression tests for quotation-signing SMTP reconciliation.

No network or production database is needed.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import quotation_email as email
from app.services import quotation_signing_authority as authority


def _delivery(identifier, sent=True):
    return SimpleNamespace(
        id=identifier,
        status="sent" if sent else "failed",
        sent_at=datetime.now(timezone.utc) if sent else None,
        template_key="quotation_send_signing",
        related_entity_type="quotation",
        related_entity_id=18,
        to_json=["contact@example.com"],
        requested_by_id=12,
    )


def _link(identifier, delivery_id, activated=False):
    return SimpleNamespace(
        id=identifier,
        delivery_id=delivery_id,
        revoked_at=None,
        activated_at=datetime.now(timezone.utc) if activated else None,
    )


def test_reconcile_activates_all_deliveries_without_resending_email():
    db = MagicMock()
    quotation = SimpleNamespace(id=18, status="draft", is_active=True)
    d1, d2 = _delivery(101), _delivery(102)
    l1, l2 = _link(201, 101), _link(202, 102)
    db.scalar.return_value = quotation
    db.scalars.side_effect = [
        SimpleNamespace(all=lambda: [d1, d2]),
        SimpleNamespace(all=lambda: [l1]),
        SimpleNamespace(all=lambda: [l2]),
    ]
    with (
        patch.object(email, "activate_document_link") as activate,
        patch.object(email, "write_audit_log"),
        patch.object(email, "publish_event"),
    ):
        changed = email.reconcile_quotation_email_status(db, 18, actor_id=12)

    assert changed is True
    assert quotation.status == "sent"
    assert activate.call_count == 2
    activate.assert_any_call(db, link_id=201, delivery_id=101)
    activate.assert_any_call(db, link_id=202, delivery_id=102)
    db.commit.assert_called_once()


def test_reconcile_existing_sent_activates_pending_without_retransition():
    db = MagicMock()
    quotation = SimpleNamespace(id=18, status="sent", is_active=True)
    d = _delivery(101)
    pending = _link(201, 101)
    active = _link(202, 101, activated=True)
    db.scalar.return_value = quotation
    db.scalars.side_effect = [
        SimpleNamespace(all=lambda: [d]),
        SimpleNamespace(all=lambda: [pending, active]),
    ]
    with (
        patch.object(email, "activate_document_link") as activate,
        patch.object(email, "write_audit_log") as audit,
        patch.object(email, "publish_event") as publish,
    ):
        changed = email.reconcile_quotation_email_status(db, 18, actor_id=12)

    assert changed is False
    assert quotation.status == "sent"
    activate.assert_called_once_with(db, link_id=201, delivery_id=101)
    audit.assert_not_called()
    publish.assert_not_called()
    db.commit.assert_called_once()


def test_activation_rejects_different_delivery_even_if_recipient_matches():
    db = MagicMock()
    link = SimpleNamespace(
        id=201, document_id=301, revoked_at=None,
        activated_at=None, delivery_id=101, recipient_email="contact@example.com",
    )
    delivery = _delivery(102)
    document = SimpleNamespace(id=301, quotation_id=18, invalidated_at=None)
    db.scalar.side_effect = [link, delivery]
    db.get.return_value = document

    with pytest.raises(HTTPException) as exc:
        authority.activate_document_link(db, link_id=201, delivery_id=102)

    assert exc.value.status_code == 404
    assert link.activated_at is None
    db.flush.assert_not_called()
