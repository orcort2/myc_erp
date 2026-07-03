from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


FieldType = Literal["text", "date", "number", "checkbox", "textarea"]


@dataclass(frozen=True)
class FieldDefinition:
    key: str
    label: str
    field_type: FieldType = "text"
    required: bool = False


@dataclass(frozen=True)
class ResultColumn:
    key: str
    label: str
    width: str | None = None


@dataclass(frozen=True)
class ResultSection:
    key: str
    title: str
    rows: int
    columns: list[ResultColumn]


@dataclass(frozen=True)
class FieldSheetTemplate:
    key: str
    name: str
    code: str
    revision: str
    pages: int
    pdf_template: str

    common_fields: list[FieldDefinition] = field(default_factory=list)

    extra_fields: list[FieldDefinition] = field(default_factory=list)

    result_sections: list[ResultSection] = field(default_factory=list)


COMMON_FIELDS: list[FieldDefinition] = [
    FieldDefinition("work_order_number", "Orden de trabajo"),
    FieldDefinition("certificate_number", "Certificado No."),
    FieldDefinition("attention", "Atención"),
    FieldDefinition("company", "Empresa"),
    FieldDefinition("address", "Dirección"),
    FieldDefinition("instrument", "Instrumento"),
    FieldDefinition("scope", "Alcance"),
    FieldDefinition("minimum_division", "Div. mínima"),
    FieldDefinition("brand", "Marca"),
    FieldDefinition("serial_number", "No. serie"),
    FieldDefinition("model", "Modelo"),
    FieldDefinition("internal_id", "Identificación"),
    FieldDefinition("location", "Ubicación"),
    FieldDefinition("calibration_place", "Lugar de calibración"),
    FieldDefinition("reception_date", "Fecha de recepción", "date"),
    FieldDefinition("calibration_date", "Fecha de calibración", "date"),
    FieldDefinition("next_calibration_date", "Próxima calibración", "date"),
    FieldDefinition("humidity_start", "Humedad relativa inicio"),
    FieldDefinition("humidity_end", "Humedad relativa final"),
    FieldDefinition("temperature_start", "Temperatura inicio"),
    FieldDefinition("temperature_end", "Temperatura final"),
    FieldDefinition("equipment_good_condition", "Equipo en buen estado general", "checkbox"),
    FieldDefinition("consider_deviations", "Considerar desviaciones del equipo", "checkbox"),
    FieldDefinition("units", "Unidades"),
    FieldDefinition("observations", "Observaciones", "textarea"),
    FieldDefinition("others", "Otros", "textarea"),
    FieldDefinition("calibrated_by", "Calibró"),
    FieldDefinition("reviewed_by", "Revisó"),
    FieldDefinition("report_made_by", "Realizó informe"),
    FieldDefinition("purchase_order_or_quotation", "Orden de compra/cotización"),
]


TABLE_PATTERN_3 = [
    ResultColumn("pattern", "Patrón"),
    ResultColumn("ibc_1", "1"),
    ResultColumn("ibc_2", "2"),
    ResultColumn("ibc_3", "3"),
]


FIELD_SHEET_TEMPLATES: dict[str, FieldSheetTemplate] = {
    "anemometro": FieldSheetTemplate(
        key="anemometro",
        name="Hoja de Campo Anemómetro",
        code="FCA-30",
        revision="R1",
        pages=1,
        pdf_template="field_sheets/anemometro.html",
        common_fields=COMMON_FIELDS,
        result_sections=[
            ResultSection(
                key="calibration_results",
                title="Resultados de Calibración",
                rows=10,
                columns=TABLE_PATTERN_3,
            )
        ],
    ),
    "temperatura": FieldSheetTemplate(
        key="temperatura",
        name="Hoja de Campo Temperatura",
        code="FCA-30",
        revision="R-1",
        pages=1,
        pdf_template="field_sheets/temperatura.html",
        common_fields=COMMON_FIELDS,
        result_sections=[
            ResultSection(
                key="calibration_results",
                title="Resultados de la Calibración",
                rows=10,
                columns=TABLE_PATTERN_3,
            )
        ],
    ),
    "sonido": FieldSheetTemplate(
        key="sonido",
        name="Hoja de Campo Sonido",
        code="FCA-30",
        revision="R1",
        pages=1,
        pdf_template="field_sheets/sonido.html",
        common_fields=COMMON_FIELDS,
        result_sections=[
            ResultSection(
                key="calibration_results",
                title="Resultados de Calibración",
                rows=10,
                columns=TABLE_PATTERN_3,
            )
        ],
    ),
    "dimensional": FieldSheetTemplate(
        key="dimensional",
        name="Hoja de Campo Dimensional",
        code="FCA-30",
        revision="R1",
        pages=1,
        pdf_template="field_sheets/dimensional.html",
        common_fields=COMMON_FIELDS,
        result_sections=[
            ResultSection(
                key="calibration_results",
                title="Resultados de la Calibración",
                rows=10,
                columns=TABLE_PATTERN_3,
            )
        ],
    ),
}


def list_field_sheet_templates() -> list[FieldSheetTemplate]:
    templates = []

    for template in FIELD_SHEET_TEMPLATES.values():
        template.common_fields = COMMON_FIELDS

        templates.append(template)

    return templates


def get_field_sheet_template(template_key: str) -> FieldSheetTemplate:
    try:
        return FIELD_SHEET_TEMPLATES[template_key]
    except KeyError as exc:
        raise ValueError(f"Plantilla de hoja de campo no soportada: {template_key}") from exc


def build_empty_result_rows(template_key: str) -> dict[str, list[dict[str, str]]]:
    template = get_field_sheet_template(template_key)
    sections: dict[str, list[dict[str, str]]] = {}

    for section in template.result_sections:
        rows = []
        for index in range(1, section.rows + 1):
            row = {"row_number": str(index)}
            for column in section.columns:
                row[column.key] = ""
            rows.append(row)

        sections[section.key] = rows

    return sections