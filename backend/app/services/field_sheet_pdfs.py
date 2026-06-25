from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from re import sub
from unicodedata import normalize

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.services.field_sheets import get_field_sheet


APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_DIR.parents[1]
TEMPLATE_DIR = APP_DIR / "templates"
LOGO_PATH = PROJECT_ROOT / "frontend" / "src" / "assets" / "myc-logo.png"


@dataclass(frozen=True)
class ResultTableSection:
    title: str
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


def _group_sections(field_sheet: FieldSheet) -> list[ResultTableSection]:
    sections: list[ResultTableSection] = []
    labels = {
        "main": "Resultados",
        "page2_a": "Resultados complementarios A",
        "page2_b": "Resultados complementarios B",
        "page2_c": "Resultados complementarios C",
        "page2_d": "Resultados complementarios D",
        "page2_e": "Resultados complementarios E",
    }
    for section_key in sorted({row.section_key for row in field_sheet.results_rows}):
        rows = [row for row in field_sheet.results_rows if row.section_key == section_key]
        sections.append(ResultTableSection(title=labels.get(section_key, section_key), rows=rows))
    return sections


def _render_html(field_sheet: FieldSheet) -> str:
    equipment = field_sheet.equipment
    service_order = equipment.service_order
    client = service_order.client
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(("html", "xml")),
    )
    env.filters["date"] = _format_date
    template_name = (
        "field_sheet_electrical_pdf.html"
        if field_sheet.template_key == "electrica"
        else "field_sheet_general_pdf.html"
    )
    template = env.get_template(template_name)
    return template.render(
        field_sheet=field_sheet,
        equipment=equipment,
        service_order=service_order,
        client=client,
        sections=_group_sections(field_sheet),
        checkbox=_checkbox,
        logo_uri=LOGO_PATH.as_uri() if LOGO_PATH.exists() else None,
    )


def generate_field_sheet_pdf(db, field_sheet_id: int) -> tuple[bytes, str]:
    field_sheet = get_field_sheet(db, field_sheet_id)
    html = _render_html(field_sheet)
    pdf = HTML(string=html, base_url=str(APP_DIR)).write_pdf()
    equipment_name = field_sheet.equipment.name or f"equipo-{field_sheet.equipment_id}"
    return (
        pdf,
        f"Hoja_Campo_{field_sheet.work_order_number or field_sheet.id}_{_filename(equipment_name)}.pdf",
    )
