from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from weasyprint import HTML

from app.services.field_sheet_pdfs import _render_html
from app.services.field_sheet_templates import (
    CANONICAL_PDF_RENDERER_VERSION,
    normalize_template_definition,
)


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
    assert HTML(string=html).write_pdf().startswith(b"%PDF")


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
    assert HTML(string=html).write_pdf().startswith(b"%PDF")
    assert CANONICAL_PDF_RENDERER_VERSION == 1


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
