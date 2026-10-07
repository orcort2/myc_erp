"""Branding y estructura del PDF de Reporte de Instalación (SG-4G): mismo
perfil institucional MYC que el acuse de entrega, sin comparar el HTML exacto."""

from __future__ import annotations

import base64
import io

from PIL import Image
from pypdf import PdfReader

from app.services.field_sheet_layouts import ORGANIZATION_PRINT_PROFILES
from app.services.technical_report_pdfs import (
    EFFECTIVENESS_LABELS,
    _view_model,
    installation_report_filename,
    render_installation_report_pdf,
)
from app.services.work_order_pdfs import LOGO_PATH


def _png(color: str = "navy") -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (60, 30), color).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def _snapshot(**capture) -> dict:
    return {
        "document": {"folio": "MYC-IN10-26-0042", "revision_number": 2, "report_type": "installation"},
        "work_order": {"folio": 6400, "purchase_order": "OC-9"},
        "client": {"name": "Cliente SA", "address": "Calle 1", "contact_name": "Ana"},
        "equipment": {"instrument": "Compresor", "brand": "MYC", "model": "K1", "identification": "ID", "serial_number": "S-1", "report_number": "NO-USAR"},
        "capture_values": {
            "installation_date": "2026-10-08", "installation_location": "Planta", "initial_condition": "Empacado",
            "installation_description": "Se instaló", "activities_performed": "Nivelación", "has_incidents": False,
            "functional_test_performed": True, "effectiveness_result": "satisfactory", **capture,
        },
        "technician": {"performed_by_name_snapshot": "Técnico Uno", "performed_at": "2026-10-08T15:30:00+00:00"},
        "delivery": {"delivery_method": "client_pickup", "delivered_at": "2026-10-08T17:00:00+00:00", "delivered_by_name": "Técnico Uno", "recipient_name": "Persona Recibe"},
        "client_conformity_text": "Texto de conformidad congelado.",
        "evidence": [{"id": 1, "evidence_type": "before", "position": 1, "caption": None}],
    }


def _text(**capture) -> str:
    pdf = render_installation_report_pdf(_snapshot(**capture), {1: _png("green")}, {"delivered_by": _png(), "recipient": _png("red")})
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)


def test_view_model_uses_the_myc_institutional_profile_and_logo():
    model = _view_model(_snapshot(), {1: _png()}, {"delivered_by": _png(), "recipient": _png()})
    assert model["primary_color"] == ORGANIZATION_PRINT_PROFILES["myc"]["primary_color"]
    assert model["header_fill"] == ORGANIZATION_PRINT_PROFILES["myc"]["header_fill"]
    assert (model["logo_uri"] is not None) == LOGO_PATH.exists()


def test_pdf_has_title_identity_sections_and_human_labels():
    text = _text()
    for expected in (
        "METROLOGÍA Y SERVICIOS MYC", "REPORTE DE INSTALACIÓN", "MYC-IN10-26-0042", "6400", "Cliente SA", "OC-9",
        "Compresor", "S-1", "Planta", "Nivelación", "08/10/2026", "Satisfactorio", "Texto de conformidad congelado.",
        "Entregado por", "Recibido por", "Persona Recibe", "Recolección por cliente", "Técnico Uno",
        "Rev. 2", "Página 1 de",
    ):
        assert expected in text, expected
    assert "NO-USAR" not in text, "el report_number del equipo nunca sustituye al folio del reporte"
    assert "satisfactory" not in text.replace("Satisfactorio", "")


def test_effectiveness_results_use_spanish_labels():
    assert EFFECTIVENESS_LABELS == {
        "satisfactory": "Satisfactorio",
        "satisfactory_with_observations": "Satisfactorio con observaciones",
        "unsatisfactory": "No satisfactorio",
    }
    assert "Satisfactorio con observaciones" in _text(effectiveness_result="satisfactory_with_observations")


def test_optional_sections_are_omitted_cleanly():
    text = _text()
    assert "No se reportaron incidencias durante la instalación." in text
    assert "Observaciones finales" not in text and "Acción correctiva" not in text
    assert "Observaciones finales" in _text(final_observations="Todo bien")


def test_download_filename_includes_folio_and_revision():
    assert installation_report_filename(_snapshot()) == "Reporte-instalacion-MYC-IN10-26-0042-r2.pdf"
