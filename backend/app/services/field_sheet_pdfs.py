from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from re import sub
from types import SimpleNamespace
from unicodedata import normalize

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.models.lab_work_order import LabWorkOrderSignatureSession
from app.services.field_sheets import get_field_sheet
from app.services.field_sheet_templates import get_field_sheet_template
from app.services.institutional_configurations import (
    get_or_create_institutional_configuration,
    institutional_snapshot,
    resolve_logo_path,
)


APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_DIR.parents[1]
TEMPLATE_DIR = APP_DIR / "templates"


@dataclass(frozen=True)
class ResultTableSection:
    key: str
    title: str
    columns: list
    rows: list[FieldSheetResult]
    unit_value: str | None = None


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
        section["key"]: [row for row in field_sheet.results_rows if row.section_key == section["key"]]
        for section in template_definition["result_sections"]
    }
    capture_values = field_sheet.capture_values or {}
    for section in template_definition["result_sections"]:
        unit_field = (section.get("metadata") or {}).get("unit_field")
        sections.append(
            ResultTableSection(
                key=section["key"],
                title=section["title"],
                columns=section["columns"],
                rows=rows_by_section.get(section["key"], []),
                unit_value=str(capture_values.get(unit_field) or "") if unit_field else None,
            )
        )
    return sections


def _resolve_field_sheet_signatures(db, field_sheet: FieldSheet) -> list:
    """Una OT LAB se firma una sola vez, en el nivel de la OT/cohorte (ver
    lab_work_orders._sign_members), no por hoja: FieldSheetSignature nunca se
    llena para hojas LAB (update_lab_field_sheet excluye "signatures" del
    payload a propósito). La autoridad real es la misma que ya usa el PDF de
    OT (lab_work_order_pdfs.generate_lab_work_order_pdf): la sesión resuelta
    específicamente por field_sheet.lab_signature_session_id (frozen al
    firmar, no "la firma más reciente del grupo" — así una sesión posterior
    de otra OT del mismo grupo histórico nunca cambia lo que esta hoja ya
    mostró). Sólo se proyecta en memoria para el render; no se persiste nada.

    Mapping documental (sólo hay firma de técnico/cliente en la sesión LAB,
    hay tres slots en la hoja):
    - calibrated_by ("Calibró"): el técnico que ejecutó el servicio -> firma
      de la sesión LAB tipo "technician".
    - reviewed_by ("Revisó") / report_made_by ("Elaboró informe"): etapas de
      Calidad posteriores que el cierre LAB no produce -> quedan Pendiente,
      igual que hoy. Nunca se usa la firma del cliente para llenar estos
      slots ni ninguno de la hoja: la aceptación del cliente pertenece al
      PDF de OT (bloque "RECIBIÓ"/aceptación), no a la hoja de campo.
    - Sheets productivas (equipment_id, no LAB): comportamiento intacto,
      se devuelven las FieldSheetSignature reales tal cual.
    """
    if field_sheet.lab_equipment_id is None or field_sheet.lab_signature_session_id is None:
        return list(field_sheet.signatures)

    session = db.get(LabWorkOrderSignatureSession, field_sheet.lab_signature_session_id)
    technician = next(
        (item for item in (session.signatures if session else []) if item.signature_type == "technician"),
        None,
    )
    resolved = []
    for slot in field_sheet.signatures:
        if slot.role == "calibrated_by" and technician is not None:
            resolved.append(
                SimpleNamespace(
                    role=slot.role,
                    display_label=slot.display_label,
                    name=technician.signer_name,
                    signature_data=technician.signature_data_url,
                    signed_at=technician.signed_at,
                )
            )
        else:
            resolved.append(slot)
    return resolved


def _render_html(
    field_sheet: FieldSheet, template_definition: dict, institution: dict, signatures: list
) -> str:
    lab_equipment = field_sheet.lab_equipment
    equipment = field_sheet.equipment or lab_equipment
    if lab_equipment is not None:
        order = lab_equipment.work_order
        client = SimpleNamespace(
            commercial_name=order.client_name.upper(),
            legal_name=order.client_name.upper(),
        )
        service_order = SimpleNamespace(
            client=client,
            quotation=SimpleNamespace(folio=order.purchase_order) if order.purchase_order else None,
            work_order_number=order.folio,
        )
        certificate = None
    else:
        service_order = equipment.service_order
        client = service_order.client
        certificate = next((item for item in equipment.certificates if item.is_active), None)
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(("html", "xml")),
    )
    env.filters["date"] = _format_date
    template_name = template_definition.get("pdf_template") or "field_sheet_engine_pdf.html"
    template = env.get_template(template_name)
    client_name = (
        field_sheet.company
        if field_sheet.company
        else field_sheet.certificate_client_company
        if field_sheet.certificate_client_mode == "different" and field_sheet.certificate_client_company
        else client.commercial_name or client.legal_name
    )
    if lab_equipment is not None:
        client_name = str(client_name or "").upper()
    client_attention = (
        field_sheet.attention
        if field_sheet.attention
        else field_sheet.certificate_client_attention
        if field_sheet.certificate_client_mode == "different"
        else client.commercial_name or client.legal_name
    )
    if lab_equipment is not None:
        client_attention = str(client_attention or "").upper()
    client_address = (
        field_sheet.address
        or (field_sheet.certificate_client_address if field_sheet.certificate_client_mode == "different" else None)
    )
    if lab_equipment is not None:
        client_address = str(client_address or "").upper()
    capture_values = field_sheet.capture_values or {}
    equipment_values = {
        "name": capture_values.get("instrument")
        or getattr(equipment, "name", None)
        or getattr(equipment, "instrument", None),
        "range_or_capacity": capture_values.get("scope") or getattr(equipment, "range_or_capacity", None),
        "brand": capture_values.get("brand") or equipment.brand,
        "model": capture_values.get("model") or getattr(equipment, "model", None),
        "serial_number": capture_values.get("serial_number") or equipment.serial_number,
        "internal_id": capture_values.get("internal_id")
        or getattr(equipment, "internal_id", None)
        or getattr(equipment, "identification", None),
    }
    if lab_equipment is not None:
        equipment_values = {
            key: value.upper() if isinstance(value, str) else value
            for key, value in equipment_values.items()
        }
    logo_path = resolve_logo_path(institution, PROJECT_ROOT)
    return template.render(
        field_sheet=field_sheet,
        equipment=equipment_values,
        service_order=service_order,
        client=client,
        client_name=client_name,
        client_attention=client_attention,
        client_address=client_address,
        capture_values=capture_values,
        certificate_folio=(
            lab_equipment.certificate_folio
            if lab_equipment is not None
            else (certificate.expected_folio or certificate.folio) if certificate else "-"
        ),
        template_definition=template_definition,
        institution=institution,
        signatures=signatures,
        sections=_group_sections(field_sheet, template_definition),
        row_value=_row_value,
        checkbox=_checkbox,
        logo_uri=logo_path.as_uri() if logo_path else None,
    )


def generate_field_sheet_pdf(db, field_sheet_id: int) -> tuple[bytes, str]:
    field_sheet = get_field_sheet(db, field_sheet_id)
    template_definition = field_sheet.template_definition_json or get_field_sheet_template(
        db,
        field_sheet.template_key,
    )
    institution = field_sheet.institutional_snapshot_json
    if not institution:
        institution = institutional_snapshot(get_or_create_institutional_configuration(db))
    signatures = _resolve_field_sheet_signatures(db, field_sheet)
    html = _render_html(field_sheet, template_definition, institution, signatures)
    pdf = HTML(string=html, base_url=str(APP_DIR)).write_pdf()
    equipment = field_sheet.equipment or field_sheet.lab_equipment
    equipment_name = (
        getattr(equipment, "name", None)
        or getattr(equipment, "instrument", None)
        or f"equipo-{field_sheet.equipment_id or field_sheet.lab_equipment_id}"
    )
    return (
        pdf,
        f"Hoja_Campo_{field_sheet.work_order_number or field_sheet.id}_{_filename(equipment_name)}.pdf",
    )
