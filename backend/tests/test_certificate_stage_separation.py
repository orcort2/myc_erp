from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.certificates import (
    get_service_order_release_readiness,
    manual_accept_match,
    quality_approve,
    release_authenticated_certificates_for_service_order,
    release_to_client,
    return_to_technician,
    validate_pdf_match,
)


def certificate(**overrides):
    values = {
        "id": 10,
        "folio": "MYCA-07-2026-0010",
        "expected_folio": "MYCA-07-2026-0010",
        "service_order_id": 1,
        "status": "ready_for_quality",
        "final_pdf_path": "/tmp/original.pdf",
        "authenticated_pdf_path": None,
        "match_status": "pending",
        "client_visible": False,
        "released_to_client_at": None,
        "released_to_client_by_id": None,
        "released_on": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_quality_cannot_approve_without_a_ready_master():
    db = MagicMock()
    with (
        patch("app.services.certificates.get_certificate", return_value=certificate(status="quality_review")),
        patch("app.services.certificates.capture_master_readiness", return_value={"ready": False, "reason": "El Master esperado no está identificado"}),
    ):
        with pytest.raises(HTTPException, match="Master esperado no está identificado"):
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
        patch("app.services.certificates.capture_master_readiness", return_value={"master": None}),
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
        with pytest.raises(HTTPException) as exc_info:
            release_to_client(db, 10)
    assert exc_info.value.detail["code"] == "certificate_not_authenticated"


def test_release_rejects_incomplete_legacy_authentication_state():
    db = MagicMock()
    current = certificate(
        status="ready_for_quality",
        authenticated_pdf_path="/tmp/authenticated.pdf",
        match_status="mismatch",
    )
    with patch("app.services.certificates.get_certificate", return_value=current):
        with pytest.raises(HTTPException) as exc_info:
            release_to_client(db, 10)
    assert exc_info.value.detail["code"] == "certificate_not_authenticated"


def test_authenticated_certificate_with_pending_match_is_ready_for_release():
    db = MagicMock()
    current = certificate(
        status="authenticated",
        authenticated_pdf_path="certificates/authenticated.pdf",
        match_status="pending",
    )
    with (
        patch("app.services.certificates.get_certificate", side_effect=[current, current]),
        patch("app.services.certificates._authenticated_document_exists", return_value=True),
        patch("app.services.certificates._ensure_payment_allows_release"),
        patch("app.services.certificates.write_audit_log") as audit,
    ):
        updated = release_to_client(db, 10, user_id=7)

    assert updated.status == "released_to_client"
    assert updated.match_status == "pending"
    assert updated.client_visible is True
    assert updated.released_to_client_by_id == 7
    assert updated.released_to_client_at is not None
    assert audit.call_args.kwargs["action"] == "certificate.released_to_client"
    assert audit.call_args.kwargs["user_id"] == 7


def test_release_rejects_missing_authenticated_document_with_specific_code():
    db = MagicMock()
    current = certificate(status="authenticated", authenticated_pdf_path="missing.pdf")
    with (
        patch("app.services.certificates.get_certificate", return_value=current),
        patch("app.services.certificates._authenticated_document_exists", return_value=False),
    ):
        with pytest.raises(HTTPException) as exc_info:
            release_to_client(db, 10)
    assert exc_info.value.detail["code"] == "authenticated_document_missing"


def test_release_rejects_already_released_with_specific_code():
    db = MagicMock()
    current = certificate(status="released_to_client", client_visible=True)
    with patch("app.services.certificates.get_certificate", return_value=current):
        with pytest.raises(HTTPException) as exc_info:
            release_to_client(db, 10)
    assert exc_info.value.detail["code"] == "already_released"


def test_release_preserves_financial_gate_and_returns_payment_code():
    db = MagicMock()
    current = certificate(status="authenticated", authenticated_pdf_path="certificates/authenticated.pdf")
    db.get.return_value = SimpleNamespace(id=1, is_active=True, requires_payment=True)
    db.scalars.return_value.all.return_value = []
    with (
        patch("app.services.certificates.get_certificate", return_value=current),
        patch("app.services.certificates._authenticated_document_exists", return_value=True),
        patch("app.services.certificates.write_audit_log") as audit,
    ):
        with pytest.raises(HTTPException) as exc_info:
            release_to_client(db, 10, user_id=7)
    assert exc_info.value.detail["code"] == "payment_pending"
    assert current.status == "authenticated"
    assert current.client_visible is False
    assert audit.call_args.kwargs["action"] == "certificate.release_blocked"


def test_batch_release_ignores_pending_match_for_authenticated_document():
    db = MagicMock()
    current = certificate(
        status="authenticated",
        authenticated_pdf_path="certificates/authenticated.pdf",
        final_pdf_path=None,
        match_status="pending",
    )
    service_order = SimpleNamespace(status="quality_review")
    db.get.return_value = service_order
    with (
        patch("app.services.certificates.list_certificates", side_effect=[[current], [current]]),
        patch("app.services.certificates.get_service_order_release_readiness", return_value={"release_allowed": True, "payment_status": "paid", "reason": "Pago confirmado"}),
        patch("app.services.certificates._authenticated_document_exists", return_value=True),
        patch("app.services.certificates.write_audit_log") as audit,
    ):
        result = release_authenticated_certificates_for_service_order(db, 1, user_id=7)

    assert result.released == 1
    assert result.skipped == 0
    assert current.status == "released_to_client"
    assert current.match_status == "pending"
    assert service_order.status == "released"
    assert audit.call_args.kwargs["action"] == "certificate.released_to_client"


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
