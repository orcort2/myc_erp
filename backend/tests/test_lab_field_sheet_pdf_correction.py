"""Regression checks for controlled LAB field-sheet PDF correction.

These are isolated unit tests; full end-to-end authorization and signature
preservation require an integration test with the correction workflow.
"""
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.services import field_sheet_pdfs as pdfs


def _sheet(content: bytes = b"%PDF-1.4 original"):
    return SimpleNamespace(
        id=365,
        lab_equipment_id=624,
        is_current=True,
        status="completed",
        lab_signature_session_id=94,
        final_pdf_path="field-sheets/365/final/renderer-2.pdf",
        final_pdf_sha256=sha256(content).hexdigest(),
        final_pdf_generated_at=None,
    )


@pytest.mark.parametrize("change", [
    {"lab_equipment_id": None},
    {"is_current": False},
    {"status": "draft"},
    {"lab_signature_session_id": None},
    {"final_pdf_path": None},
])
def test_rejects_ineligible_correction(monkeypatch, change):
    sheet = _sheet()
    for key, value in change.items():
        setattr(sheet, key, value)
    monkeypatch.setattr(pdfs, "require_deliverable_file", Mock())
    with pytest.raises(HTTPException) as exc:
        pdfs.regenerate_corrected_lab_field_sheet_pdf(Mock(), sheet)
    assert exc.value.status_code == 409
    pdfs.require_deliverable_file.assert_not_called()


def test_rejects_tampered_original_without_render(monkeypatch):
    sheet = _sheet()
    monkeypatch.setattr(
        pdfs, "require_deliverable_file",
        Mock(return_value=SimpleNamespace(read_bytes=lambda: b"tampered")),
    )
    render = Mock()
    monkeypatch.setattr(pdfs, "_render_pdf", render)
    with pytest.raises(HTTPException) as exc:
        pdfs.regenerate_corrected_lab_field_sheet_pdf(Mock(), sheet)
    assert exc.value.status_code == 409
    render.assert_not_called()


def test_corrected_folio_creates_distinct_artifact_and_updates_pointer(monkeypatch):
    old = b"%PDF-1.4 folio MYCA-10-26-5087"
    new = b"%PDF-1.4 folio MYCA-09-26-5087"
    sheet = _sheet(old)
    original_path = sheet.final_pdf_path
    original_hash = sheet.final_pdf_sha256
    monkeypatch.setattr(
        pdfs, "require_deliverable_file",
        Mock(return_value=SimpleNamespace(read_bytes=lambda: old)),
    )
    monkeypatch.setattr(pdfs, "_render_pdf", Mock(return_value=(new, "hoja.pdf")))
    save = Mock(return_value=SimpleNamespace(
        relative_path="field-sheets/365/final/corrected-new.pdf",
        checksum_sha256=sha256(new).hexdigest(),
    ))
    monkeypatch.setattr(pdfs, "save_validated_content", save)
    db = Mock()

    result, _ = pdfs.regenerate_corrected_lab_field_sheet_pdf(db, sheet)

    assert result == new
    assert original_hash == sha256(old).hexdigest()
    assert original_path != sheet.final_pdf_path
    assert sheet.final_pdf_sha256 == sha256(new).hexdigest()
    assert sheet.lab_signature_session_id == 94
    assert sheet.status == "completed"
    assert "corrected-" + sha256(new).hexdigest() + ".pdf" == save.call_args.kwargs["filename"]
    db.flush.assert_called_once()


def test_identical_render_does_not_write(monkeypatch):
    content = b"%PDF-1.4 unchanged"
    sheet = _sheet(content)
    monkeypatch.setattr(
        pdfs, "require_deliverable_file",
        Mock(return_value=SimpleNamespace(read_bytes=lambda: content)),
    )
    monkeypatch.setattr(pdfs, "_render_pdf", Mock(return_value=(content, "hoja.pdf")))
    save = Mock()
    monkeypatch.setattr(pdfs, "save_validated_content", save)
    db = Mock()
    result, _ = pdfs.regenerate_corrected_lab_field_sheet_pdf(db, sheet)
    assert result == content
    save.assert_not_called()
    db.flush.assert_not_called()
