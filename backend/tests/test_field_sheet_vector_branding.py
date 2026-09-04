"""Branding institucional MYC en los PDF vectoriales de hojas de campo.

Cubre tres capas:

A) primitivas de color en field_sheet_vector_renderer.py (VectorTextStyle,
   draw_line, draw_rounded_box, draw_structured_result_table) -- puramente
   geométrico/gráfico, sin conocer organización ni template_key;
B) proyección del perfil de organización en field_sheet_vector_adapter.py
   (resolve_organization_print_profile + resolve_logo_path) sobre el
   documento -- por organización, nunca por template_key;
C) cobertura transversal: los 23 templates oficiales MYC pasan por la misma
   ruta de branding sin ninguna rama especial por template_key;
D) PDFs representativos inspeccionados a nivel de bytes (color stream +
   XObject de imagen), incluyendo páginas de continuación.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pypdf import PdfReader
from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas

from app.models.field_sheet import FieldSheet
from app.services.field_sheet_layouts import resolve_organization_print_profile
from app.services.field_sheet_template_engine import OFFICIAL_MYC_TEMPLATE_KEYS
from app.services.field_sheet_templates import (
    build_default_result_rows,
    build_fallback_template_definition,
    normalize_template_definition,
)
from app.services.field_sheet_vector_adapter import (
    PROJECT_ROOT,
    VectorRenderContext,
    render_field_sheet_vector_preview,
)
from app.services.field_sheet_vector_renderer import (
    FieldSheetVectorDocument,
    VectorBox,
    mm,
    VectorTextStyle,
)

# Perfil MYC vigente (backend/app/services/field_sheet_layouts.py). Los tests
# no redeclaran otra fuente de verdad -- si el perfil cambia ahí, estas
# constantes deben actualizarse junto con él.
MYC_PRIMARY = "#175cd3"
MYC_HEADER_FILL = "#dbeafe"
CAPYMET_PRIMARY = "#344054"
CAPYMET_HEADER_FILL = "#eaecf0"
LOGO_RELATIVE_PATH = "frontend/src/assets/myc-logo.png"

# Bytes exactos que ReportLab escribe en el content stream del PDF para cada
# color (RG/rg de PDF, 6 decimales, sin el "0." inicial -- verificado
# empíricamente contra la salida real de HexColor(...).
_MYC_STROKE = b".090196 .360784 .827451 RG"
_MYC_FILL_OR_TEXT = b".090196 .360784 .827451 rg"
_MYC_HEADER_BAND = b".858824 .917647 .996078 rg"
_CAPYMET_STROKE = b".203922 .25098 .329412 RG"
_CAPYMET_HEADER_BAND = b".917647 .92549 .941176 rg"

_EQUIPMENT = {
    "name": "Equipo", "brand": "MYC", "model": "M1", "serial_number": "S1",
    "internal_id": "I1", "range_or_capacity": "10",
}


def _myc_institution() -> dict:
    return {
        "legal_name": "METROLOGÍA Y SERVICIOS MYC",
        "address": "Av. Cristóbal Colón 6086",
        "phone": "33 5009 2659",
        "email": "contacto@mycmetrology.com.mx",
        "logo_path": LOGO_RELATIVE_PATH,
    }


def _sheet(definition: dict, *, capture_all_rows: bool = True) -> FieldSheet:
    sheet = FieldSheet(
        id=1, equipment_id=1, template_key=definition["template_key"], work_order_number=6414,
        template_definition_json=definition, capture_values={},
    )
    sheet.results_rows = build_default_result_rows(definition)
    if capture_all_rows:
        for section in definition["result_sections"]:
            for row in (item for item in sheet.results_rows if item.section_key == section["key"]):
                row.row_data = {
                    column["key"]: (False if column.get("data_type") == "boolean" else "1")
                    for column in section["columns"]
                }
    return sheet


def _page_content_bytes(reader: PdfReader, index: int) -> bytes:
    return reader.pages[index].get_contents().get_data()


def _image_xobject_count(reader: PdfReader, index: int) -> int:
    resources = reader.pages[index].get("/Resources") or {}
    xobjects = resources.get("/XObject")
    if xobjects is None:
        return 0
    return sum(1 for obj in xobjects.values() if obj.get_object().get("/Subtype") == "/Image")


# ---------------------------------------------------------------------------
# A) primitivas del renderer vectorial
# ---------------------------------------------------------------------------


def test_vector_text_style_color_triggers_set_fill_color():
    document = FieldSheetVectorDocument()
    with patch.object(Canvas, "setFillColor") as spy:
        document.draw_text("MYC", x=mm(5), y=mm(5), style=VectorTextStyle(color=MYC_PRIMARY))
    assert spy.call_args.args[0] == HexColor(MYC_PRIMARY)


def test_draw_line_color_applies_stroke_color():
    document = FieldSheetVectorDocument()
    with patch.object(Canvas, "setStrokeColor") as spy:
        document.draw_line(x1=0, y1=0, x2=mm(10), y2=0, color=MYC_PRIMARY)
    assert spy.call_args.args[0] == HexColor(MYC_PRIMARY)


def test_draw_rounded_box_applies_both_stroke_and_fill_color():
    document = FieldSheetVectorDocument()
    box = VectorBox(x=mm(5), y=mm(5), width=mm(20), height=mm(10))
    with patch.object(Canvas, "setStrokeColor") as stroke_spy, patch.object(Canvas, "setFillColor") as fill_spy:
        document.draw_rounded_box(box, stroke_color=MYC_PRIMARY, fill=True, fill_color=MYC_HEADER_FILL)
    assert stroke_spy.call_args.args[0] == HexColor(MYC_PRIMARY)
    assert fill_spy.call_args.args[0] == HexColor(MYC_HEADER_FILL)


def test_draw_rounded_box_does_not_force_fill_true_just_because_fill_color_is_given():
    """fill_color por sí solo no debe activar fill -- sólo si el caller pasa
    fill=True explícitamente (regla explícita del cambio quirúrgico)."""
    document = FieldSheetVectorDocument()
    box = VectorBox(x=mm(5), y=mm(5), width=mm(20), height=mm(10))
    with patch.object(Canvas, "roundRect") as spy:
        document.draw_rounded_box(box, fill_color=MYC_HEADER_FILL)
    assert spy.call_args.kwargs["fill"] == 0


def test_color_state_never_leaks_into_the_next_draw_call():
    """saveState/restoreState deben aislar cada primitiva -- el color de un
    título no debe contaminar el siguiente draw_text/draw_line."""
    document = FieldSheetVectorDocument()
    document.draw_text("Azul", x=mm(5), y=mm(20), style=VectorTextStyle(color=MYC_PRIMARY))
    assert document.canvas._fillColorObj == (0, 0, 0)
    document.draw_line(x1=0, y1=0, x2=mm(5), y2=0, color=MYC_PRIMARY)
    assert document.canvas._strokeColorObj == (0, 0, 0)
    document.draw_rounded_box(
        VectorBox(x=mm(5), y=mm(5), width=mm(10), height=mm(10)),
        fill=True, fill_color=MYC_HEADER_FILL, stroke_color=MYC_PRIMARY,
    )
    assert document.canvas._fillColorObj == (0, 0, 0)
    assert document.canvas._strokeColorObj == (0, 0, 0)


def test_without_explicit_color_behavior_is_unchanged():
    document = FieldSheetVectorDocument()
    with patch.object(Canvas, "setFillColor") as fill_spy, patch.object(Canvas, "setStrokeColor") as stroke_spy:
        document.draw_text("Sin color", x=mm(5), y=mm(5))
        document.draw_centered_text("Sin color", box=VectorBox(x=mm(5), y=mm(5), width=mm(20), height=mm(10)))
        document.draw_wrapped_text("Sin color", box=VectorBox(x=mm(5), y=mm(5), width=mm(20), height=mm(10)))
        document.draw_line(x1=0, y1=0, x2=mm(5), y2=0)
        document.draw_rounded_box(VectorBox(x=mm(5), y=mm(5), width=mm(10), height=mm(10)))
    fill_spy.assert_not_called()
    stroke_spy.assert_not_called()


def test_structured_result_table_paints_header_band_and_accent_border_without_moving_geometry():
    from app.services.field_sheet_vector_renderer import VectorHeaderCell

    def _table_kwargs():
        return dict(
            column_widths=[0.2, 0.4, 0.4],
            header_cells=[
                VectorHeaderCell(label="No.", row=0, column=0),
                VectorHeaderCell(label="A", row=0, column=1),
                VectorHeaderCell(label="B", row=0, column=2),
            ],
            header_row_heights=[mm(5.4)],
            rows=[["1", "x", "y"]],
        )

    table_box = VectorBox(x=mm(5), y=mm(5), width=mm(100), height=mm(30))
    real_draw_rounded_box = FieldSheetVectorDocument.draw_rounded_box

    plain = FieldSheetVectorDocument()
    calls_plain = []

    def _spy(self, box, **kwargs):
        calls_plain.append(box)
        return real_draw_rounded_box(self, box, **kwargs)

    with patch.object(FieldSheetVectorDocument, "draw_rounded_box", _spy):
        plain.draw_structured_result_table(box=table_box, **_table_kwargs())
    plain_pdf = plain.finish()

    branded = FieldSheetVectorDocument()
    calls_branded = []

    def _spy_branded(self, box, **kwargs):
        calls_branded.append(box)
        return real_draw_rounded_box(self, box, **kwargs)

    with patch.object(FieldSheetVectorDocument, "draw_rounded_box", _spy_branded):
        branded.draw_structured_result_table(
            box=table_box, header_fill=MYC_HEADER_FILL, accent_color=MYC_PRIMARY, **_table_kwargs()
        )
    branded_pdf = branded.finish()

    plain_stream = PdfReader(io.BytesIO(plain_pdf)).pages[0].get_contents().get_data()
    branded_stream = PdfReader(io.BytesIO(branded_pdf)).pages[0].get_contents().get_data()

    assert _MYC_HEADER_BAND not in plain_stream
    assert _MYC_STROKE not in plain_stream
    assert _MYC_HEADER_BAND in branded_stream
    assert _MYC_STROKE in branded_stream

    # El outer border (la caja más alta -- header + body) es la misma en
    # ambos: header_fill agrega una banda de fondo *adicional*, nunca mueve
    # ni redimensiona el marco exterior de la tabla.
    plain_outer = max(calls_plain, key=lambda box: box.height)
    branded_outer = max(calls_branded, key=lambda box: box.height)
    assert (plain_outer.x, plain_outer.y, plain_outer.width, plain_outer.height) == (
        branded_outer.x, branded_outer.y, branded_outer.width, branded_outer.height
    )
    # header_fill sólo agrega UNA caja extra (la banda del header); todo lo
    # demás de la geometría de dibujo permanece igual.
    assert len(calls_branded) == len(calls_plain) + 1


# ---------------------------------------------------------------------------
# B) adapter / perfil de organización
# ---------------------------------------------------------------------------


def test_myc_sheet_resolves_profile_and_paints_primary_and_header_fill():
    definition = build_fallback_template_definition(OFFICIAL_MYC_TEMPLATE_KEYS[0])
    sheet = _sheet(definition)
    pdf = render_field_sheet_vector_preview(VectorRenderContext(
        sheet, definition, _EQUIPMENT, "Cliente", "Atención", "Domicilio", "CERT-1",
        institution=_myc_institution(),
    ))
    stream = PdfReader(io.BytesIO(pdf)).pages[0].get_contents().get_data()
    assert _MYC_STROKE in stream
    assert _MYC_HEADER_BAND in stream


def test_myc_sheet_draws_the_canonical_institutional_logo_asset():
    definition = build_fallback_template_definition(OFFICIAL_MYC_TEMPLATE_KEYS[0])
    sheet = _sheet(definition)
    with patch.object(FieldSheetVectorDocument, "draw_image") as spy:
        render_field_sheet_vector_preview(VectorRenderContext(
            sheet, definition, _EQUIPMENT, "Cliente", "Atención", "Domicilio", "CERT-1",
            institution=_myc_institution(),
        ))
    assert spy.called
    drawn_path = Path(spy.call_args.args[0])
    assert drawn_path == (PROJECT_ROOT / LOGO_RELATIVE_PATH).resolve()
    assert drawn_path.is_file()


def test_capymet_sheet_never_draws_the_myc_logo_even_if_institution_has_one():
    definition = normalize_template_definition({
        "template_key": "electrica",
        "name": "Fixture CAPYMET",
        "table_family": "paired_multichannel",
        "metadata": {"organization_key": "capymet"},
        "blocks": [
            {
                "key": "results",
                "block_type": "SectionedTableBlock",
                "title": "Resultados",
                "sections": [{"key": "s", "title": "S", "rows": 2, "columns": [{"key": "v", "label": "Valor", "source": "v"}]}],
            },
        ],
    }, table_family_mode="strict")
    sheet = _sheet(definition)
    with patch.object(FieldSheetVectorDocument, "draw_image") as spy:
        pdf = render_field_sheet_vector_preview(VectorRenderContext(
            sheet, definition, _EQUIPMENT, "Cliente", "Atención", "Domicilio", "CERT-1",
            # El institution snapshot SÍ trae un logo_path MYC -- CAPYMET debe
            # ignorarlo por completo (logo_key == "none" en su perfil).
            institution=_myc_institution(),
        ))
    spy.assert_not_called()
    stream = PdfReader(io.BytesIO(pdf)).pages[0].get_contents().get_data()
    assert _MYC_STROKE not in stream
    assert _MYC_HEADER_BAND not in stream
    assert _CAPYMET_STROKE in stream
    assert _CAPYMET_HEADER_BAND in stream


def test_unknown_organization_never_falls_back_to_myc_branding():
    """resolve_organization_print_profile (autoridad existente) rechaza
    explícitamente una organización no soportada -- nunca renderiza con azul
    MYC "por defecto" para una clave desconocida."""
    definition = build_fallback_template_definition(OFFICIAL_MYC_TEMPLATE_KEYS[0])
    definition["metadata"] = {**(definition.get("metadata") or {}), "organization_key": "acme"}
    definition["organization_profile"] = {"key": "acme"}
    with pytest.raises(HTTPException) as exc_info:
        resolve_organization_print_profile(definition)
    assert exc_info.value.status_code == 422


def test_organization_profile_resolution_has_no_template_key_branching():
    """El mismo template_key ('electrica') debe producir branding MYC o
    CAPYMET únicamente según metadata.organization_key -- nunca según
    template_key."""
    myc_definition = normalize_template_definition({
        "template_key": "electrica", "name": "MYC", "table_family": "paired_multichannel",
        "blocks": [{"key": "s", "block_type": "SignaturesBlock", "title": "Firmas"}],
    }, table_family_mode="strict")
    capymet_definition = normalize_template_definition({
        "template_key": "electrica", "name": "CAPYMET", "table_family": "paired_multichannel",
        "metadata": {"organization_key": "capymet"},
        "blocks": [{"key": "s", "block_type": "SignaturesBlock", "title": "Firmas"}],
    }, table_family_mode="strict")
    myc_profile = resolve_organization_print_profile(myc_definition)
    capymet_profile = resolve_organization_print_profile(capymet_definition)
    assert myc_profile["primary_color"] == MYC_PRIMARY
    assert capymet_profile["primary_color"] == CAPYMET_PRIMARY


# ---------------------------------------------------------------------------
# C) cobertura transversal: los 23 templates oficiales MYC
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("template_key", OFFICIAL_MYC_TEMPLATE_KEYS)
def test_every_official_myc_template_renders_with_institutional_branding(template_key):
    definition = build_fallback_template_definition(template_key)
    sheet = _sheet(definition)
    pdf = render_field_sheet_vector_preview(VectorRenderContext(
        sheet, definition, _EQUIPMENT, "Cliente", "Atención", "Domicilio", "CERT-1",
        institution=_myc_institution(),
    ))
    assert pdf.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(pdf))
    first_page_stream = _page_content_bytes(reader, 0)
    assert _MYC_STROKE in first_page_stream, f"{template_key}: falta color institucional en header/tabla"
    assert _image_xobject_count(reader, 0) >= 1, f"{template_key}: falta el logo institucional"


# ---------------------------------------------------------------------------
# D) PDFs representativos, inspeccionados a nivel de bytes
# ---------------------------------------------------------------------------


def _write_representative_pdf(name: str, pdf: bytes) -> Path:
    out_dir = Path(tempfile.gettempdir()) / "myc_field_sheet_branding_pdfs"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_bytes(pdf)
    return path


def test_representative_pdf_simple_table():
    template_key = "regla"
    definition = build_fallback_template_definition(template_key)
    sheet = _sheet(definition)
    pdf = render_field_sheet_vector_preview(VectorRenderContext(
        sheet, definition, _EQUIPMENT, "Cliente Representativo", "Atención", "Domicilio", "CERT-1",
        institution=_myc_institution(),
    ))
    path = _write_representative_pdf("1_simple_table.pdf", pdf)
    reader = PdfReader(io.BytesIO(pdf))
    stream = _page_content_bytes(reader, 0)
    text = reader.pages[0].extract_text() or ""
    assert _MYC_STROKE in stream
    assert _MYC_HEADER_BAND in stream
    assert _image_xobject_count(reader, 0) == 1
    assert "Cliente Representativo" in text
    assert path.is_file()


def test_representative_pdf_grouped_header():
    template_key = "presion"
    definition = build_fallback_template_definition(template_key)
    sheet = _sheet(definition)
    pdf = render_field_sheet_vector_preview(VectorRenderContext(
        sheet, definition, _EQUIPMENT, "Cliente Grouped", "Atención", "Domicilio", "CERT-1",
        institution=_myc_institution(),
    ))
    path = _write_representative_pdf("2_grouped_header.pdf", pdf)
    reader = PdfReader(io.BytesIO(pdf))
    stream = _page_content_bytes(reader, 0)
    assert _MYC_STROKE in stream
    assert _MYC_HEADER_BAND in stream
    assert _image_xobject_count(reader, 0) == 1
    assert path.is_file()


def _many_blocks_definition(block_count: int = 6, rows_per_block: int = 10) -> dict:
    blocks = [
        {
            "key": f"table_{index}",
            "block_type": "SimpleComparisonTableBlock",
            "title": f"Sección {index + 1}",
            "rows": rows_per_block,
            "columns": [{"key": "value", "label": "Valor", "source": "value"}],
        }
        for index in range(block_count)
    ]
    blocks.append({"key": "signatures", "block_type": "SignaturesBlock", "title": "Firmas"})
    return normalize_template_definition(
        {
            "template_key": "temperatura",
            "name": "Fixture branding paginación",
            "table_family": "replicated_comparison",
            "blocks": blocks,
        },
        table_family_mode="strict",
    )


def test_representative_pdf_many_rows_paginates_and_brands_every_page():
    definition = _many_blocks_definition()
    sheet = _sheet(definition)
    pdf = render_field_sheet_vector_preview(VectorRenderContext(
        sheet, definition, _EQUIPMENT, "Cliente Paginado", "Atención", "Domicilio", "CERT-1",
        institution=_myc_institution(),
    ))
    path = _write_representative_pdf("3_many_rows_pagination.pdf", pdf)
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) >= 2, "fixture debe forzar al menos 2 páginas para probar continuación"
    for index in range(len(reader.pages)):
        stream = _page_content_bytes(reader, index)
        assert _MYC_STROKE in stream, f"página {index + 1} sin marco institucional"
        assert _MYC_HEADER_BAND in stream, f"página {index + 1} sin fondo de header institucional"
        assert _image_xobject_count(reader, index) == 1, f"página {index + 1} sin logo institucional"
    assert path.is_file()


_SIGNATURE_PNG_DATA_URL = "data:image/png;base64," + (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_representative_pdf_signatures_and_results():
    template_key = OFFICIAL_MYC_TEMPLATE_KEYS[0]
    definition = build_fallback_template_definition(template_key)
    sheet = _sheet(definition)
    signatures = tuple(
        SimpleNamespace(
            role=slot["role"],
            display_label=slot["display_label"],
            name="Técnico Firmante",
            signature_data=_SIGNATURE_PNG_DATA_URL if slot["role"] == "calibrated_by" else None,
            signed_at=None,
        )
        for slot in definition["signature_layout"]["slots"]
    )
    pdf = render_field_sheet_vector_preview(VectorRenderContext(
        sheet, definition, _EQUIPMENT, "Cliente Firmas", "Atención", "Domicilio", "CERT-1",
        institution=_myc_institution(),
        signatures=signatures,
    ))
    path = _write_representative_pdf("4_signatures_and_results.pdf", pdf)
    reader = PdfReader(io.BytesIO(pdf))
    stream = _page_content_bytes(reader, 0)
    text = reader.pages[0].extract_text() or ""
    assert _MYC_STROKE in stream
    assert "TÉCNICO FIRMANTE" in text.upper()
    # Logo + al menos una firma gráfica resuelta -- ambas son imágenes.
    assert _image_xobject_count(reader, 0) == 2
    assert path.is_file()
