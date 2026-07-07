from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from re import sub
from unicodedata import normalize

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.services.field_sheets import get_field_sheet
from app.services.field_sheet_templates import get_field_sheet_template


APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_DIR.parents[1]
TEMPLATE_DIR = APP_DIR / "templates"
LOGO_PATH = PROJECT_ROOT / "frontend" / "src" / "assets" / "myc-logo.png"


@dataclass(frozen=True)
class ResultTableSection:
    key: str
    title: str
    columns: list
    rows: list[FieldSheetResult]


def _filename(value: str) -> str:
    ascii_value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    safe = sub(r"[^A-Za-z0-9_.-]+", "-", ascii_value).strip("-_.")
    return safe or "hoja-campo"


def _format_date(value) -> str:
    if value is None:
        return "-"
    return value.strftime("%d/%m/%Y")


def _checkbox(value: bool | None) -> str:
    return "X" if value else ""


def _row_value(row: FieldSheetResult, column) -> str:
    source = column["source"] if isinstance(column, dict) else column.source
    if row.row_data and source in row.row_data:
        value = row.row_data.get(source)
        return "" if value is None else str(value)
    value = getattr(row, source, None)
    return "" if value is None else str(value)


def _group_sections(field_sheet: FieldSheet, template_definition: dict) -> list[ResultTableSection]:
    sections: list[ResultTableSection] = []
    rows_by_section = {
        section.key: [row for row in field_sheet.results_rows if row.section_key == section.key]
        for section in template_definition["result_sections"]
    }
    for section in template_definition["result_sections"]:
        sections.append(
            ResultTableSection(
                key=section["key"],
                title=section["title"],
                columns=section["columns"],
                rows=rows_by_section.get(section["key"], []),
            )
        )
    return sections


def _render_html(field_sheet: FieldSheet, template_definition: dict) -> str:
    equipment = field_sheet.equipment
    service_order = equipment.service_order
    client = service_order.client
    certificate = next((item for item in equipment.certificates if item.is_active), None)
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(("html", "xml")),
    )
    env.filters["date"] = _format_date
    template_map = {
        "electrica": "field_sheet_electrical_pdf.html",
        "anemometro": "field_sheet_anemometer_pdf.html",
    }

    template_name = template_map.get(
        field_sheet.template_key,
        "field_sheet_general_pdf.html",
    )
    template = env.get_template(template_name)
    client_name = (
        field_sheet.company
        if field_sheet.company
        else field_sheet.certificate_client_company
        if field_sheet.certificate_client_mode == "different" and field_sheet.certificate_client_company
        else client.commercial_name or client.legal_name
    )
    client_attention = (
        field_sheet.attention
        if field_sheet.attention
        else field_sheet.certificate_client_attention
        if field_sheet.certificate_client_mode == "different"
        else client.commercial_name or client.legal_name
    )
    client_address = (
        field_sheet.address
        or (field_sheet.certificate_client_address if field_sheet.certificate_client_mode == "different" else None)
    )
    return template.render(
        field_sheet=field_sheet,
        equipment=equipment,
        service_order=service_order,
        client=client,
        client_name=client_name,
        client_attention=client_attention,
        client_address=client_address,
        certificate_folio=(certificate.expected_folio or certificate.folio) if certificate else "-",
        template_definition=template_definition,
        sections=_group_sections(field_sheet, template_definition),
        row_value=_row_value,
        checkbox=_checkbox,
        logo_uri=LOGO_PATH.as_uri() if LOGO_PATH.exists() else None,
    )


def generate_field_sheet_pdf(db, field_sheet_id: int) -> tuple[bytes, str]:
    field_sheet = get_field_sheet(db, field_sheet_id)
    template_definition = field_sheet.template_definition_json or get_field_sheet_template(
        db,
        field_sheet.template_key,
    )
    html = _render_html(field_sheet, template_definition)
    pdf = HTML(string=html, base_url=str(APP_DIR)).write_pdf()
    equipment_name = field_sheet.equipment.name or f"equipo-{field_sheet.equipment_id}"
    return (
        pdf,
        f"Hoja_Campo_{field_sheet.work_order_number or field_sheet.id}_{_filename(equipment_name)}.pdf",
    )
