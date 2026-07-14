from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.certificates import (
    get_service_order_release_readiness,
    manual_accept_match,
    quality_approve,
    release_to_client,
    return_to_technician,
    validate_pdf_match,
)


def certificate(**overrides):
    values = {
        "id": 10,
        "service_order_id": 1,
        "status": "ready_for_quality",
        "final_pdf_path": "/tmp/original.pdf",
        "authenticated_pdf_path": None,
        "match_status": "pending",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_quality_cannot_approve_before_match_is_validated():
    db = MagicMock()
    with patch("app.services.certificates.get_certificate", return_value=certificate()):
        with pytest.raises(HTTPException, match="validar o aceptar el match"):
            quality_approve(db, 10)


def test_match_validation_is_rejected_outside_quality():
    db = MagicMock()
    current = certificate(status="capture_in_progress")
    with patch("app.services.certificates.get_certificate", return_value=current):
        with pytest.raises(HTTPException, match="durante Calidad"):
            validate_pdf_match(db, 10)


def test_match_validation_advances_the_single_certificate_state():
    db = MagicMock()
    current = certificate()
    with (
        patch("app.services.certificates.get_certificate", side_effect=[current, current]),
        patch("app.services.certificates.validate_certificate_pdf_match", return_value={"status": "matched", "score": 100}),
        patch("app.services.certificates.write_audit_log"),
    ):
        updated = validate_pdf_match(db, 10, user_id=4)
    assert updated.status == "match_validated"
    assert updated.match_status == "matched"


def test_manual_match_requires_prior_validation():
    db = MagicMock()
    with patch("app.services.certificates.get_certificate", return_value=certificate(match_status="mismatch")):
        with pytest.raises(HTTPException, match="Primero debe validarse"):
            manual_accept_match(db, 10)


def test_return_to_capture_keeps_the_linked_field_sheet_state():
    db = MagicMock()
    sheet = SimpleNamespace(status="approved")
    current = certificate(status="match_validated", field_sheet=sheet, field_sheet_id=22)
    payload = SimpleNamespace(reason="Falta identificar el patrón", comment=None)
    with (
        patch("app.services.certificates.get_certificate", return_value=current),
        patch("app.services.certificates._set_status", side_effect=lambda _db, cert, new_status, **_kwargs: SimpleNamespace(**{**cert.__dict__, "status": new_status})),
    ):
        updated = return_to_technician(db, 10, payload, user_id=4)
    assert updated.status == "correction_requested"
    assert sheet.status == "approved"
    assert current.quality_rejection_reason == "Falta identificar el patrón"


def test_release_requires_an_authenticated_pdf():
    db = MagicMock()
    current = certificate(status="quality_approved", authenticated_pdf_path=None, match_status="matched")
    with patch("app.services.certificates.get_certificate", return_value=current):
        with pytest.raises(HTTPException, match="Solo certificados autenticados"):
            release_to_client(db, 10)


def test_release_rejects_incomplete_legacy_authentication_state():
    db = MagicMock()
    current = certificate(
        status="ready_for_quality",
        authenticated_pdf_path="/tmp/authenticated.pdf",
        match_status="mismatch",
    )
    with patch("app.services.certificates.get_certificate", return_value=current):
        with pytest.raises(HTTPException, match="Solo certificados autenticados"):
            release_to_client(db, 10)


def test_payment_gate_blocks_required_order_without_paid_invoice():
    db = MagicMock()
    db.get.return_value = SimpleNamespace(id=1, is_active=True, requires_payment=True)
    db.scalars.return_value.all.return_value = []
    readiness = get_service_order_release_readiness(db, 1)
    assert readiness["release_allowed"] is False
    assert readiness["payment_status"] == "pending"


def test_payment_gate_allows_order_that_does_not_require_payment():
    db = MagicMock()
    db.get.return_value = SimpleNamespace(id=1, is_active=True, requires_payment=False)
    readiness = get_service_order_release_readiness(db, 1)
    assert readiness["release_allowed"] is True
    assert readiness["payment_status"] == "not_required"
