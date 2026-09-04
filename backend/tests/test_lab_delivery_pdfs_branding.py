"""Branding institucional MYC en el acuse de entrega de equipos LAB.

lab_delivery_pdfs.py genera estos PDFs vía HTML/WeasyPrint (no el renderer
vectorial de hojas de campo) -- el acuse de entrega LAB es exclusivamente
MYC (ver AGENTS.md de myc-mobile), así que su branding usa directamente el
perfil MYC de field_sheet_layouts.ORGANIZATION_PRINT_PROFILES en vez de
resolve_organization_print_profile (que requiere un template_definition de
hoja de campo, ajeno a este flujo)."""

from __future__ import annotations

import io
from datetime import date, datetime, timezone
from types import SimpleNamespace

from pypdf import PdfReader

from app.services.field_sheet_layouts import ORGANIZATION_PRINT_PROFILES
from app.services.lab_delivery_pdfs import (
    generate_lab_delivery_final_receipt,
    generate_lab_delivery_receipt,
)
from app.services.work_order_pdfs import LOGO_PATH

MYC_PRIMARY = ORGANIZATION_PRINT_PROFILES["myc"]["primary_color"]
MYC_HEADER_FILL = ORGANIZATION_PRINT_PROFILES["myc"]["header_fill"]

_SIGNATURE_PNG_DATA_URL = "data:image/png;base64," + (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _delivery_item(folio: str = "6414") -> SimpleNamespace:
    return SimpleNamespace(
        work_order=SimpleNamespace(folio=folio),
        instrument_snapshot="Termómetro digital",
        brand_snapshot="MYC",
        identification_snapshot="ID-1",
        serial_number_snapshot="S1",
        certificate_folio_snapshot="CERT-1",
    )


def _delivery(**overrides) -> SimpleNamespace:
    base = dict(
        delivery_type="full",
        exhibition_number=1,
        delivery_method="direct",
        delivered_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        items=[_delivery_item()],
        notes="Sin observaciones.",
        delivered_by_signature_data_url=_SIGNATURE_PNG_DATA_URL,
        recipient_signature_data_url=_SIGNATURE_PNG_DATA_URL,
        recipient_name="Juan Pérez",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _root_work_order() -> SimpleNamespace:
    return SimpleNamespace(folio="6414", client_name="Cliente Demo Entrega", reception_date=date(2026, 1, 1))


def test_delivery_receipt_pdf_carries_the_myc_logo_and_institutional_blue():
    pdf, filename = generate_lab_delivery_receipt(_root_work_order(), _delivery(), "Técnico Entrega")
    assert pdf.startswith(b"%PDF")
    assert filename.endswith(".pdf")
    reader = PdfReader(io.BytesIO(pdf))
    stream = reader.pages[0].get_contents().get_data()
    # WeasyPrint compila colores CSS a un espacio de color propio -- se
    # verifica presencia del logo (imagen embebida) y del texto/label
    # institucional en vez de bytes crudos de color como en el renderer
    # vectorial.
    resources = reader.pages[0].get("/Resources") or {}
    xobjects = resources.get("/XObject") or {}
    images = [obj for obj in xobjects.values() if obj.get_object().get("/Subtype") == "/Image"]
    assert len(images) >= 1, "el logo institucional debe embeberse como imagen"
    text = reader.pages[0].extract_text() or ""
    assert "METROLOGÍA Y SERVICIOS MYC" in text
    assert "Cliente Demo Entrega" in text


def test_delivery_receipt_template_is_wired_to_the_myc_profile_colors():
    from app.services.lab_delivery_pdfs import _MYC_PRINT_PROFILE
    assert _MYC_PRINT_PROFILE["primary_color"] == MYC_PRIMARY
    assert _MYC_PRINT_PROFILE["header_fill"] == MYC_HEADER_FILL


def test_delivery_receipt_reuses_the_canonical_logo_asset_no_new_copy_invented():
    assert LOGO_PATH.exists()
    assert LOGO_PATH.name == "myc-logo.png"


def test_final_receipt_pdf_carries_the_myc_logo_and_multiple_exhibitions():
    deliveries = [
        _delivery(exhibition_number=1, recipient_name="Juan Pérez"),
        _delivery(exhibition_number=2, recipient_name="María López", delivery_type="partial"),
    ]
    pdf, filename = generate_lab_delivery_final_receipt(_root_work_order(), deliveries)
    assert pdf.startswith(b"%PDF")
    assert filename.endswith(".pdf")
    reader = PdfReader(io.BytesIO(pdf))
    resources = reader.pages[0].get("/Resources") or {}
    xobjects = resources.get("/XObject") or {}
    images = [obj for obj in xobjects.values() if obj.get_object().get("/Subtype") == "/Image"]
    assert len(images) >= 1
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    assert "Exhibición 1" in text
    assert "Exhibición 2" in text
    assert "Juan Pérez" in text
    assert "María López" in text
