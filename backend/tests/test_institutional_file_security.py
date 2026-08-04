from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
from dataclasses import replace

import pytest
from fastapi import HTTPException, UploadFile
from pypdf import PdfWriter

from app.core.config import settings
from app.services.file_security import POLICIES, validate_content, validate_upload, validate_xml
from app.services.storage_service import atomic_write, build_storage_path, resolve_storage_path


def _zip(entries: dict[str, bytes]) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return output.getvalue()


def _upload(filename: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content), headers={"content-type": content_type})


def test_rejects_oversized_upload_before_unbounded_read(monkeypatch):
    policy = POLICIES["tax_constancy"]
    monkeypatch.setitem(POLICIES, "tax_constancy", replace(policy, max_bytes=8))
    with pytest.raises(HTTPException) as error:
        validate_upload(_upload("constancia.pdf", b"%PDF-1.7\n%%EOF-extra", "application/pdf"), "tax_constancy")
    assert error.value.status_code == 413


@pytest.mark.parametrize("name", ["../escape.xlsx", "/absolute.xlsx", "folder\\escape.xlsx"])
def test_rejects_unsafe_outer_filename(name):
    with pytest.raises(HTTPException):
        validate_upload(_upload(name, b"PK\x03\x04", "application/octet-stream"), "certificate_master")


def test_rejects_zip_slip_member():
    payload = _zip({"../escape.xlsx": b"content"})
    with pytest.raises(HTTPException) as error:
        validate_content(payload, ".zip", POLICIES["capture_package"])
    assert "ruta insegura" in error.value.detail


def test_rejects_zip_expansion_ratio():
    payload = _zip({"large.txt": b"0" * (2 * 1024 * 1024)})
    with pytest.raises(HTTPException) as error:
        validate_content(payload, ".zip", POLICIES["capture_package"])
    assert "expansión" in error.value.detail


def test_rejects_duplicate_archive_names():
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("same.txt", b"one")
        archive.writestr("SAME.TXT", b"two")
    with pytest.raises(HTTPException) as error:
        validate_content(output.getvalue(), ".zip", POLICIES["capture_package"])
    assert "duplicados" in error.value.detail


def test_rejects_archive_symlink():
    output = BytesIO()
    info = ZipInfo("link")
    info.create_system = 3
    info.external_attr = 0o120777 << 16
    with ZipFile(output, "w") as archive:
        archive.writestr(info, "target")
    with pytest.raises(HTTPException) as error:
        validate_content(output.getvalue(), ".zip", POLICIES["capture_package"])
    assert "enlaces" in error.value.detail


def test_rejects_encrypted_archive_flag():
    payload = bytearray(_zip({"safe.txt": b"content"}))
    payload[6:8] = (1).to_bytes(2, "little")
    central = payload.find(b"PK\x01\x02")
    payload[central + 8:central + 10] = (1).to_bytes(2, "little")
    with pytest.raises(HTTPException) as error:
        validate_content(bytes(payload), ".zip", POLICIES["capture_package"])
    assert "cifrados" in error.value.detail


def test_rejects_empty_upload_and_mime_mismatch():
    with pytest.raises(HTTPException):
        validate_upload(_upload("constancia.pdf", b"", "application/pdf"), "tax_constancy")
    with pytest.raises(HTTPException) as error:
        validate_upload(_upload("constancia.pdf", b"%PDF-1.7\n%%EOF", "image/png"), "tax_constancy")
    assert error.value.status_code == 415


def test_rejects_office_container_without_expected_structure():
    payload = _zip({"word/document.xml": b"<document/>"})
    with pytest.raises(HTTPException) as error:
        validate_content(payload, ".xlsx", POLICIES["certificate_master"])
    assert "estructura" in error.value.detail


def test_rejects_truncated_pdf_and_accepts_complete_pdf():
    with pytest.raises(HTTPException):
        validate_content(b"%PDF-1.7\nbody", ".pdf", POLICIES["certificate_pdf"])
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(output)
    validate_content(output.getvalue(), ".pdf", POLICIES["certificate_pdf"])


def test_xml_rejects_external_entities_and_malformed_content():
    with pytest.raises(HTTPException):
        validate_xml(b'<!DOCTYPE x [<!ENTITY ext SYSTEM "file:///etc/passwd">]><x>&ext;</x>')
    with pytest.raises(HTTPException):
        validate_xml(b"<root>")
    validate_xml(b"<root><value>ok</value></root>")


def test_storage_rejects_traversal_and_writes_atomically(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    assert resolve_storage_path("../escape.txt") is None
    with pytest.raises(HTTPException):
        build_storage_path(directory="../escape", filename="unsafe.txt")

    target = build_storage_path(directory="safe", filename="result.txt")
    atomic_write(target, b"complete")
    assert target.read_bytes() == b"complete"
    assert not list(target.parent.glob(".upload-*"))
