import base64
import io
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pypdf import PdfReader
from weasyprint import HTML

from app.services.field_sheet_pdfs import _render_html
from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.services.field_sheet_pdfs import ResultTableSection
from app.services.field_sheet_template_engine import OFFICIAL_MYC_TEMPLATE_KEYS
from app.services.field_sheet_vector_adapter import (
    FIELD_ROW_HEIGHT_COMPACT,
    VectorRenderContext,
    _filter_meaningful_rows,
    _row_display_label,
    render_field_sheet_vector_preview,
)
from app.services.field_sheet_vector_renderer import FieldSheetVectorDocument, VectorBox, mm
from app.services.field_sheet_templates import (
    CANONICAL_PDF_RENDERER_VERSION,
    build_default_result_rows,
    build_fallback_template_definition,
    normalize_template_definition,
)


@pytest.mark.parametrize("template_key", OFFICIAL_MYC_TEMPLATE_KEYS)
def test_all_23_official_templates_render_vector_letter_pdf(template_key):
    definition = build_fallback_template_definition(template_key)
    sheet = FieldSheet(id=1, equipment_id=1, template_key=template_key, work_order_number=6414, template_definition_json=definition, capture_values={})
    sheet.results_rows = build_default_result_rows(definition)
    for section in definition["result_sections"]:
        row = next(item for item in sheet.results_rows if item.section_key == section["key"])
        row.row_data = {column["key"]: (False if column.get("data_type") == "boolean" else "1") for column in section["columns"]}
    pdf = render_field_sheet_vector_preview(VectorRenderContext(
        sheet, definition,
        {"name": "Equipo", "brand": "MYC", "model": "M1", "serial_number": "S1", "internal_id": "I1", "range_or_capacity": "10"},
        "Cliente", "Atención", "Domicilio", "CERT-1",
    ))
    assert pdf.startswith(b"%PDF")
    page = PdfReader(io.BytesIO(pdf)).pages[0]
    assert float(page.mediabox.width) == 612
    assert float(page.mediabox.height) == 792


def test_draw_field_cell_prints_the_value_at_the_compact_row_height_used_by_fields_grid():
    """Regresión de geometría directa sobre FieldSheetVectorDocument: a la
    altura de fila 'compact' que _draw_fields_item usa siempre para cualquier
    campo (field_sheet_vector_adapter.FIELD_ROW_HEIGHT_COMPACT), draw_field_cell
    debe seguir cabiendo tanto la etiqueta como el valor -- antes del fix,
    value_box quedaba con menos altura que value_style.font_size + 2*padding_y
    y draw_wrapped_text descartaba el valor sin dibujar ni un carácter."""

    document = FieldSheetVectorDocument()
    box = VectorBox(x=mm(10), y=mm(10), width=mm(60), height=FIELD_ROW_HEIGHT_COMPACT)
    document.draw_field_cell(box=box, label="Etiqueta", value="ValorCapturado123", compact=True)
    pdf = document.finish()
    text = PdfReader(io.BytesIO(pdf)).pages[0].extract_text() or ""
    assert "Etiqueta" in text
    assert "ValorCapturado123" in text


@pytest.mark.parametrize("template_key", OFFICIAL_MYC_TEMPLATE_KEYS)
def test_all_23_official_templates_print_client_and_equipment_field_values(template_key):
    """Regresión: FieldSheetVectorDocument.draw_field_cell tenía un bug de
    geometría (value_box quedaba más bajo que font_size + 2*padding en filas
    'compact', que es como _draw_fields_item siempre invoca draw_field_grid)
    que hacía que draw_wrapped_text descartara la línea del VALOR antes de
    dibujar nada -- el documento imprimía únicamente las etiquetas ("Empresa",
    "Alcance", etc.) y nunca los datos capturados, en las 23 plantillas
    oficiales por igual. Este test exige que el valor real llegue al PDF."""

    definition = build_fallback_template_definition(template_key)
    sheet = FieldSheet(
        id=1, equipment_id=1, template_key=template_key, work_order_number=6414,
        template_definition_json=definition, capture_values={},
    )
    sheet.results_rows = build_default_result_rows(definition)
    pdf = render_field_sheet_vector_preview(VectorRenderContext(
        sheet, definition,
        {"name": "EquipoValorPrueba", "brand": "MarcaValorPrueba", "model": "M1", "serial_number": "S1", "internal_id": "I1", "range_or_capacity": "10"},
        "ClienteValorPrueba", "AtencionValorPrueba", "DomicilioValorPrueba", "CERT-1",
    ))
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "ClienteValorPrueba" in text
    assert "EquipoValorPrueba" in text


_SIGNATURE_PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
).decode()


def test_vector_v2_signatures_draw_resolved_graphic_name_and_pending_placeholder():
    """El renderer vectorial v2 debe recibir las firmas ya resueltas por la
    autoridad correspondiente (field_sheet_pdfs._resolve_field_sheet_signatures)
    a través de VectorRenderContext.signatures, y dibujar para cada slot: la
    firma gráfica real cuando hay signature_data, el nombre resuelto, y
    "Pendiente" para los slots documentales que la autoridad aún no llenó --
    igual que el renderer HTML legacy (signature.name or 'Pendiente')."""

    template_key = OFFICIAL_MYC_TEMPLATE_KEYS[0]
    definition = build_fallback_template_definition(template_key)
    sheet = FieldSheet(
        id=1, equipment_id=1, template_key=template_key, work_order_number=6414,
        template_definition_json=definition, capture_values={},
    )
    sheet.results_rows = build_default_result_rows(definition)

    resolved_signatures = tuple(
        SimpleNamespace(
            role=slot["role"],
            display_label=slot["display_label"],
            name="Técnico Graficado" if slot["role"] == "calibrated_by" else None,
            signature_data=_SIGNATURE_PNG_DATA_URL if slot["role"] == "calibrated_by" else None,
            signed_at=None,
        )
        for slot in definition["signature_layout"]["slots"]
    )
    assert any(item.signature_data for item in resolved_signatures), "fixture must exercise the graphic path"

    pdf = render_field_sheet_vector_preview(VectorRenderContext(
        sheet, definition,
        {"name": "Equipo", "brand": "MYC", "model": "M1", "serial_number": "S1", "internal_id": "I1", "range_or_capacity": "10"},
        "Cliente", "Atención", "Domicilio", "CERT-1",
        signatures=resolved_signatures,
    ))
    assert pdf.startswith(b"%PDF")
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages).upper()
    assert "TÉCNICO GRAFICADO" in text
    # The other documental slots (Revisó / Elaboró informe) never receive a
    # LAB session signature; they must still show the same "Pendiente"
    # placeholder as the HTML legacy renderer, not a blank/omitted slot.
    assert text.count("PENDIENTE") == len(resolved_signatures) - 1


def test_vector_v2_without_resolved_signatures_shows_pending_for_every_slot():
    """Sin firmas resueltas (contexto por defecto), todos los slots deben
    mostrar 'Pendiente' -- el default de VectorRenderContext.signatures=()
    no debe producir slots en blanco, para no divergir del legacy."""

    template_key = OFFICIAL_MYC_TEMPLATE_KEYS[0]
    definition = build_fallback_template_definition(template_key)
    sheet = FieldSheet(
        id=1, equipment_id=1, template_key=template_key, work_order_number=6414,
        template_definition_json=definition, capture_values={},
    )
    sheet.results_rows = build_default_result_rows(definition)

    pdf = render_field_sheet_vector_preview(VectorRenderContext(
        sheet, definition,
        {"name": "Equipo", "brand": "MYC", "model": "M1", "serial_number": "S1", "internal_id": "I1", "range_or_capacity": "10"},
        "Cliente", "Atención", "Domicilio", "CERT-1",
    ))
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages).upper()
    assert text.count("PENDIENTE") == len(definition["signature_layout"]["slots"])


def test_vector_row_filter_drops_all_empty_rows_and_preserves_zero_false_and_original_number():
    columns = [{"key": "value", "source": "value"}]
    rows = [
        FieldSheetResult(section_key="s", row_number=1, row_data={}),
        FieldSheetResult(section_key="s", row_number=2, row_data={"value": "0"}),
        FieldSheetResult(section_key="s", row_number=3, row_data={}),
        FieldSheetResult(section_key="s", row_number=4, row_data={"value": 0}),
        FieldSheetResult(section_key="s", row_number=5, row_data={"value": False}),
    ]
    section = ResultTableSection(key="s", title="S", columns=columns, rows=rows)
    assert [row.row_number for row in _filter_meaningful_rows(section)] == [2, 4, 5]


def test_vector_row_filter_has_no_exception_for_fixed_row_labels():
    """Filas con row_labels (categorías fijas del documento, p.ej. válvula
    Disparo/Cierre o detector de gases H2S/CO) NO se imprimen sólo porque la
    etiqueta exista -- se filtran igual que cualquier fila de captura libre:
    únicamente si tienen al menos un valor capturado."""

    columns = [{"key": "value", "source": "value"}]

    valve_rows = [
        FieldSheetResult(section_key="valve", row_number=1, row_data={}),
        FieldSheetResult(section_key="valve", row_number=2, row_data={"value": "180 psi"}),
    ]
    valve_section = ResultTableSection(
        key="valve", title="Válvula", columns=columns, rows=valve_rows,
        row_labels=["Disparo", "Cierre"],
    )
    kept = _filter_meaningful_rows(valve_section)
    assert [row.row_number for row in kept] == [2]
    assert _row_display_label(valve_section, kept[0]) == "Cierre"

    gas_rows = [
        FieldSheetResult(section_key="gas", row_number=1, row_data={}),
        FieldSheetResult(section_key="gas", row_number=2, row_data={"value": "50 ppm"}),
    ]
    gas_section = ResultTableSection(
        key="gas", title="Detector de gases", columns=columns, rows=gas_rows,
        row_labels=["H2S", "CO"],
    )
    kept_gas = _filter_meaningful_rows(gas_section)
    assert [row.row_number for row in kept_gas] == [2]
    assert _row_display_label(gas_section, kept_gas[0]) == "CO"


def _column(key: str, label: str, width: str = "25%") -> dict:
    return {"key": key, "label": label, "source": key, "width": width}


def _temperature_definition(**overrides) -> dict:
    block = {
        "key": "temperature_results",
        "block_type": "SimpleComparisonTableBlock",
        "title": "Resultados",
        "rows": 10,
        "columns": [
            _column("ibc", "Valores medidos (IBC)"),
            _column("pattern_1", "1"),
            _column("pattern_2", "2"),
            _column("pattern_3", "3"),
        ],
        "header_rows": [
            {
                "cells": [
                    {"label": "No.", "rowspan": 2, "column_key": "__row_number__"},
                    {"label": "Valores medidos (IBC)", "rowspan": 2, "column_key": "ibc"},
                    {"label": "Patrón", "colspan": 3},
                ]
            },
            {
                "cells": [
                    {"label": "1", "column_key": "pattern_1"},
                    {"label": "2", "column_key": "pattern_2"},
                    {"label": "3", "column_key": "pattern_3"},
                ]
            },
        ],
    }
    block.update(overrides.pop("block", {}))
    payload = {
        "template_key": "temperatura",
        "name": "Fixture temporal temperatura",
        "table_family": "replicated_comparison",
        "blocks": [
            block,
            {
                "key": "signatures",
                "block_type": "SignaturesBlock",
                "title": "Firmas",
            },
        ],
        **overrides,
    }
    return normalize_template_definition(payload, table_family_mode="strict")


def _complex_definition() -> dict:
    columns_a = [_column(f"channel_{index}", f"Canal {index}") for index in range(1, 5)]
    columns_b = [_column("up", "Ascendente", "50%"), _column("down", "Descendente", "50%")]
    return normalize_template_definition(
        {
            "template_key": "electrica",
            "name": "Fixture temporal compleja",
            "table_family": "paired_multichannel",
            "metadata": {"organization_key": "capymet"},
            "print_layout": {
                "page": {
                    "size": "a4",
                    "orientation": "landscape",
                    "margins": {"top": 8, "right": 9, "bottom": 10, "left": 9},
                },
                "document": {
                    "title_visible": True,
                    "header_visible": True,
                    "footer_visible": True,
                    "grid_columns": 2,
                },
            },
            "blocks": [
                {
                    "key": "complex_results",
                    "block_type": "SectionedTableBlock",
                    "title": "Resultados complejos",
                    "print_layout": {"column_span": 2, "grid_columns": 2, "compact": True},
                    "sections": [
                        {
                            "key": "channels",
                            "title": "Canales",
                            "rows": 3,
                            "columns": columns_a,
                            "row_labels": ["Punto A", "Punto B", "Punto C"],
                            "header_rows": [
                                {
                                    "cells": [
                                        {"label": "Punto", "column_key": "__row_number__"},
                                        {"label": "Lecturas", "colspan": 4},
                                    ]
                                }
                            ],
                        },
                        {
                            "key": "cycle",
                            "title": "Ciclo",
                            "rows": 2,
                            "columns": columns_b,
                            "row_labels": ["0 %", "100 %"],
                        },
                    ],
                }
            ],
        },
        table_family_mode="strict",
    )


def _fake_sheet(definition: dict):
    rows = []
    for section in definition["result_sections"]:
        for number in range(1, section["rows"] + 1):
            rows.append(
                SimpleNamespace(
                    section_key=section["key"],
                    row_number=number,
                    row_data={column["key"]: str(number) for column in section["columns"]},
                )
            )
    order = SimpleNamespace(client_name="CLIENTE DEMO", purchase_order=None, folio=6401)
    equipment = SimpleNamespace(
        work_order=order,
        certificate_folio="MYC-26-0001",
        name="TERMÓMETRO",
        instrument="TERMÓMETRO",
        range_or_capacity="0 A 100 °C",
        brand="MARCA",
        model="MODELO",
        serial_number="SERIE",
        internal_id="ID-1",
        identification="ID-1",
    )
    return SimpleNamespace(
        id=1,
        pdf_renderer_key="field_sheet_engine",
        pdf_renderer_version=1,
        lab_equipment=equipment,
        equipment=None,
        capture_values={},
        company=None,
        attention=None,
        address=None,
        certificate_client_mode="billing",
        certificate_client_company=None,
        certificate_client_attention=None,
        certificate_client_address=None,
        work_order_number=6401,
        purchase_order_or_quotation="OC-6401",
        results_rows=rows,
    )


def _signatures() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            role=role,
            display_label=label,
            name=name,
            signature_data=None,
            signed_at=None,
        )
        for role, label, name in (
            ("calibrated_by", "Calibró", "Técnico Uno"),
            ("reviewed_by", "Revisó", "Técnico Dos"),
            ("report_made_by", "Elaboró informe", "Técnico Tres"),
        )
    ]


def _render(
    definition: dict,
    institution: dict | None = None,
    signatures: list[SimpleNamespace] | None = None,
) -> str:
    institution = institution or {
        "legal_name": "METROLOGÍA Y CALIBRACIÓN",
        "address": "Domicilio institucional",
        "phone": "3333333333",
        "email": "correo@example.com",
        "logo_path": None,
    }
    return _render_html(
        _fake_sheet(definition),
        definition,
        institution,
        signatures or [],
    )


def test_flat_header_legacy_keeps_empty_header_rows_and_default_layout():
    definition = _temperature_definition(block={"header_rows": []})
    section = definition["result_sections"][0]
    assert section["header_rows"] == []
    assert definition["print_layout"]["page"] == {
        "size": "letter",
        "orientation": "portrait",
        "margins": {"top": 12, "right": 10, "bottom": 14, "left": 10},
    }
    assert definition["print_layout"]["document"] == {
        "title_visible": True,
        "header_visible": True,
        "footer_visible": True,
        "grid_columns": 1,
    }
    assert definition["blocks"][0]["print_layout"] == {
        "grid_columns": 2,
        "column_span": 1,
        "order": None,
        "title_visible": True,
        "compact": False,
        "border": True,
        "spacing_before": 1.4,
        "spacing_after": 0,
        "break_inside": "avoid",
        "page_break_before": False,
        "label_position": "top",
        "hide_empty_fields": False,
        "metadata": {},
    }
    renderer_source = (
        Path(__file__).parents[1] / "app" / "templates" / "field_sheet_engine_pdf.html"
    ).read_text(encoding="utf-8")
    assert ".block { break-inside: avoid;" in renderer_source
    html = _render(definition)
    assert '<th class="number"' in html


def test_temperature_like_grouped_header_validates_and_renders_pdf():
    definition = _temperature_definition()
    section = definition["result_sections"][0]
    assert len(section["columns"]) == 4
    assert len(section["header_rows"]) == 2
    html = _render(definition)
    assert 'colspan="3"' in html
    assert 'rowspan="2"' in html
    pdf = HTML(string=html).write_pdf()
    assert pdf.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 1
    assert float(reader.pages[0].mediabox.width) == 612
    assert float(reader.pages[0].mediabox.height) == 792


def test_renderer_applies_the_global_compact_print_finish_without_template_branches():
    renderer_source = (
        Path(__file__).parents[1] / "app" / "templates" / "field_sheet_engine_pdf.html"
    ).read_text(encoding="utf-8")

    assert '<div class="results-frame">' in renderer_source
    assert (
        ".results-frame { border: .25mm solid #344054; border-radius: 1.2mm; "
        "overflow: hidden; }" in renderer_source
    )
    assert (
        ".block:not(.without-border) { border-radius: 1.2mm; overflow: hidden; }"
        in renderer_source
    )
    assert (
        ".compact .field-cell { min-height: 6.8mm; padding: .95mm 1.2mm; }"
        in renderer_source
    )
    assert "min-height: 7.6mm" in renderer_source
    assert "line-height: 1.2" in renderer_source
    assert "padding: .7mm .8mm" in renderer_source
    assert "border-collapse: separate" in renderer_source
    assert ".field-grid { border-left: .25mm solid #344054;" in renderer_source
    assert "margin: -.25mm 0 0 -.25mm" not in renderer_source
    assert "border-right: .25mm solid #344054" in renderer_source
    assert CANONICAL_PDF_RENDERER_VERSION == 1


def test_legacy_signature_layout_keeps_the_derived_horizontal_grid():
    definition = _temperature_definition()
    assert definition["signature_layout"]["columns"] is None
    assert definition["signature_layout"]["direction"] == "horizontal"
    assert definition["signature_layout"]["trailing_fields"] == []
    html = _render(definition, signatures=_signatures())
    assert 'data-signature-direction="horizontal"' in html
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in html
    assert '<div class="signature-trailing-fields">' not in html


def test_vertical_signatures_render_trailing_field_and_real_pdf():
    definition = _temperature_definition(
        signature_layout={
            "columns": 1,
            "direction": "vertical",
            "trailing_fields": ["purchase_order_or_quotation"],
        }
    )
    html = _render(definition, signatures=_signatures())
    assert 'data-signature-direction="vertical"' in html
    assert "grid-template-columns: repeat(1, minmax(0, 1fr))" in html
    assert html.count('class="signature"') == 3
    assert 'data-field="purchase_order_or_quotation"' in html
    assert "Orden de compra / cotización" in html
    assert "OC-6401" in html
    pdf = HTML(string=html).write_pdf()
    assert pdf.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 1
    assert float(reader.pages[0].mediabox.width) == 612
    assert float(reader.pages[0].mediabox.height) == 792
    assert CANONICAL_PDF_RENDERER_VERSION == 1


@pytest.mark.parametrize(
    ("template_key", "expected_heading", "expected_revision", "expected_rows", "cycle_labels"),
    [
        ("temperatura", "Patrón", "R-1", 10, ["1", "2", "3"]),
        (
            "presion",
            "Valores Medidos Patrón",
            "R1",
            11,
            ["Acendente", "Descendente", "Ascendente"],
        ),
    ],
)
def test_phase_6a1_official_templates_render_the_source_table_and_pdf(
    template_key: str,
    expected_heading: str,
    expected_revision: str,
    expected_rows: int,
    cycle_labels: list[str],
):
    definition = build_fallback_template_definition(template_key)
    signatures = [
        SimpleNamespace(
            role=slot["role"],
            display_label=slot["display_label"],
            name=f"Firma {index}",
            signature_data=None,
            signed_at=None,
        )
        for index, slot in enumerate(definition["signature_layout"]["slots"], start=1)
    ]

    html = _render(definition, signatures=signatures)
    assert "DATOS DE MEDICION" in html
    assert "FCA-30" in html
    assert expected_revision in html
    assert expected_heading in html
    assert all(label in html for label in cycle_labels)
    assert html.count('class="signature"') == 3
    assert 'data-signature-direction="vertical"' in html
    assert 'data-field="purchase_order_or_quotation"' in html
    assert len(_fake_sheet(definition).results_rows) == expected_rows
    pdf = HTML(string=html).write_pdf()
    assert pdf.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 1
    assert float(reader.pages[0].mediabox.width) == 612
    assert float(reader.pages[0].mediabox.height) == 792


@pytest.mark.parametrize(
    "signature_layout",
    [
        {"trailing_fields": ["unknown_field"]},
        {"columns": 1, "direction": "vertical", "css": "display:none"},
        {"columns": 0},
        {"columns": 5},
        {"direction": "diagonal"},
    ],
)
def test_signature_layout_rejects_invalid_values_fields_and_properties(signature_layout):
    with pytest.raises(HTTPException) as exc_info:
        _temperature_definition(signature_layout=signature_layout)
    assert exc_info.value.status_code == 422


def test_signature_renderer_has_no_template_or_magnitude_branches():
    renderer_source = (
        Path(__file__).parents[1] / "app" / "templates" / "field_sheet_engine_pdf.html"
    ).read_text(encoding="utf-8")
    assert "temperatura" not in renderer_source.lower()
    assert "presión" not in renderer_source.lower()
    assert "presion" not in renderer_source.lower()


@pytest.mark.parametrize(
    "block",
    [
        {"header_rows": [{"cells": [{"label": "Inválida", "colspan": 0}]}]},
        {
            "header_rows": [
                {
                    "cells": [
                        {"label": "No.", "column_key": "__row_number__"},
                        {"label": "Desconocida", "column_key": "missing"},
                        {"label": "Resto", "colspan": 3},
                    ]
                }
            ]
        },
    ],
)
def test_invalid_header_spans_and_column_keys_raise_422(block):
    with pytest.raises(HTTPException) as exc_info:
        _temperature_definition(block=block)
    assert exc_info.value.status_code == 422


@pytest.mark.parametrize(
    "cells",
    [
        [
            {"label": "Mal", "column_key": "pattern_1"},
            {"label": "IBC"},
            {"label": "1"},
            {"label": "2"},
            {"label": "3"},
        ],
        [
            {"label": "No."},
            {"label": "IBC"},
            {"label": "Mal", "column_key": "__row_number__"},
            {"label": "2"},
            {"label": "3"},
        ],
    ],
)
def test_header_column_key_must_match_its_logical_position(cells):
    with pytest.raises(HTTPException) as exc_info:
        _temperature_definition(block={"header_rows": [{"cells": cells}]})
    assert exc_info.value.status_code == 422


def test_row_labels_and_multi_section_geometry_generate_complex_pdf():
    definition = _complex_definition()
    sections = definition["result_sections"]
    assert [len(section["columns"]) for section in sections] == [4, 2]
    assert sections[0]["row_labels"] == ["Punto A", "Punto B", "Punto C"]
    assert sections[1]["row_labels"] == ["0 %", "100 %"]
    html = _render(definition)
    assert "Punto A" in html
    assert "100 %" in html
    assert "size: a4 landscape" in html
    assert "margin: 8.0mm 9.0mm 10.0mm 9.0mm" in html
    assert HTML(string=html).write_pdf().startswith(b"%PDF")


def test_organization_profiles_select_myc_and_capymet_without_template_branching():
    myc = _temperature_definition()
    capymet = _complex_definition()
    assert myc["organization_profile"]["key"] == "myc"
    assert myc["organization_profile"]["logo_key"] == "institutional"
    assert capymet["organization_profile"]["key"] == "capymet"
    assert capymet["organization_profile"]["logo_key"] == "none"
    assert "CAPYMET" in _render(capymet)


def test_capymet_profile_never_inherits_myc_contact_or_logo():
    capymet = _complex_definition()
    html = _render(
        capymet,
        {
            "legal_name": "LEGAL MYC NO DEBE APARECER",
            "address": "DOMICILIO MYC NO DEBE APARECER",
            "phone": "3312345678",
            "email": "myc-no-debe-aparecer@example.com",
            "logo_path": "frontend/src/assets/myc-logo.png",
        },
    )
    assert "CAPYMET" in html
    assert "LEGAL MYC NO DEBE APARECER" not in html
    assert "DOMICILIO MYC NO DEBE APARECER" not in html
    assert "3312345678" not in html
    assert "myc-no-debe-aparecer@example.com" not in html
    assert '<img class="logo"' not in html


@pytest.mark.parametrize(
    "unsafe_layout",
    [
        {"css": "body { display:none }"},
        {"page": {"size": "<script>alert(1)</script>"}},
        {"page": {"background_url": "https://example.com/a.png"}},
    ],
)
def test_print_layout_rejects_arbitrary_css_html_urls_and_unknown_keys(unsafe_layout):
    with pytest.raises(HTTPException) as exc_info:
        _temperature_definition(print_layout=unsafe_layout)
    assert exc_info.value.status_code == 422


def test_header_labels_are_html_escaped():
    definition = _temperature_definition()
    definition["result_sections"][0]["header_rows"][0]["cells"][2]["label"] = "<script>alert(1)</script>"
    html = _render(definition)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_renderer_resolves_profile_values_from_allowlist_not_snapshot_css():
    definition = _temperature_definition()
    definition["organization_profile"]["primary_color"] = "red; background:url(https://example.com/x)"
    html = _render(definition)
    assert "background:url" not in html
    assert "color: #175cd3" in html
