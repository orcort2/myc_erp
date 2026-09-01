from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from re import sub
from types import SimpleNamespace
from unicodedata import normalize

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.models.lab_work_order import LabWorkOrderSignatureSession
from app.services.field_sheet_templates import (
    CANONICAL_PDF_RENDERER_KEY,
    CANONICAL_PDF_RENDERER_VERSION,
    CANONICAL_PDF_TEMPLATE,
    get_field_sheet_template,
)
from app.services.institutional_configurations import (
    get_or_create_institutional_configuration,
    institutional_snapshot,
    resolve_logo_path,
)
from app.services.storage_service import require_deliverable_file, save_validated_content


APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_DIR.parents[1]
TEMPLATE_DIR = APP_DIR / "templates"
FINAL_DOCUMENT_STATUSES = {"completed", "under_review", "approved"}
LEGACY_PDF_TEMPLATES = {
    "field_sheet_general_pdf.html",
    "field_sheet_anemometer_pdf.html",
    "field_sheet_electrical_pdf.html",
}
FIELD_LABELS = {
    "document_code": "Código documental",
    "document_revision": "Revisión",
    "field_sheet_folio": "Hoja de campo",
    "work_order_number": "Orden de trabajo",
    "reserved_certificate_folio": "Certificado",
    "attention": "Atención",
    "company": "Empresa",
    "address": "Domicilio",
    "purchase_order_or_quotation": "Orden de compra / cotización",
    "instrument": "Instrumento",
    "scope": "Alcance",
    "brand": "Marca",
    "model": "Modelo",
    "serial_number": "Serie",
    "internal_id": "Identificación",
    "location": "Ubicación",
    "minimum_division": "División mínima",
    "reception_date": "Fecha de recepción",
    "calibration_date": "Fecha de calibración",
    "next_calibration_date": "Próxima calibración",
    "calibration_place": "Lugar de calibración",
    "environment_humidity_start": "Humedad inicial",
    "environment_humidity_end": "Humedad final",
    "environment_temperature_start": "Temperatura inicial",
    "environment_temperature_end": "Temperatura final",
    "initial_condition": "Condición inicial",
    "final_condition": "Condición final",
    "pattern_used": "Patrón usado",
    "method": "Método",
    "units": "Unidades",
    "observations": "Observaciones",
    "evidence_notes": "Evidencia / notas",
    "calibrated_by": "Calibró",
    "reviewed_by": "Revisó",
    "report_made_by": "Elaboró informe",
}


@dataclass(frozen=True)
class ResultTableSection:
    key: str
    title: str
    columns: list
    rows: list[FieldSheetResult]
    unit_value: str | None = None


@dataclass(frozen=True)
class PrintField:
    key: str
    label: str
    value: str


@dataclass(frozen=True)
class PrintBlock:
    key: str
    block_type: str
    title: str
    fields: list[PrintField]
    sections: list[ResultTableSection]
    table_family: str
    metadata: dict
    grid_columns: int = 2


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


def resolve_field_sheet_pdf_renderer(field_sheet: FieldSheet, template_definition: dict) -> tuple[str, int, str]:
    key = field_sheet.pdf_renderer_key or template_definition.get("pdf_renderer_key")
    version = field_sheet.pdf_renderer_version or template_definition.get("pdf_renderer_version") or 1
    legacy_template = template_definition.get("pdf_template")
    if not key:
        key = (
            f"legacy:{legacy_template}"
            if legacy_template in LEGACY_PDF_TEMPLATES
            else CANONICAL_PDF_RENDERER_KEY
        )
    if key == CANONICAL_PDF_RENDERER_KEY and int(version) == CANONICAL_PDF_RENDERER_VERSION:
        return key, int(version), CANONICAL_PDF_TEMPLATE
    if key.startswith("legacy:") and int(version) == 1:
        template_name = key.removeprefix("legacy:")
        if template_name in LEGACY_PDF_TEMPLATES:
            return key, int(version), template_name
    raise HTTPException(status_code=409, detail="Renderer de hoja de campo no disponible")


def _display_value(value) -> str:
    if value in (None, ""):
        return "-"
    if hasattr(value, "strftime"):
        return _format_date(value)
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


def _field_value(
    key: str,
    *,
    field_sheet: FieldSheet,
    template_definition: dict,
    equipment: dict,
    client_name: str,
    client_attention: str,
    client_address: str | None,
    certificate_folio: str | None,
) -> str:
    special = {
        "document_code": template_definition.get("document_code") or template_definition.get("code"),
        "document_revision": template_definition.get("document_revision") or template_definition.get("revision"),
        "field_sheet_folio": field_sheet.id,
        "work_order_number": field_sheet.work_order_number,
        "reserved_certificate_folio": certificate_folio,
        "attention": client_attention,
        "company": client_name,
        "address": client_address,
        "instrument": equipment.get("name"),
        "scope": equipment.get("range_or_capacity"),
        "brand": equipment.get("brand"),
        "model": equipment.get("model"),
        "serial_number": equipment.get("serial_number"),
        "internal_id": equipment.get("internal_id"),
    }
    if key in special:
        return _display_value(special[key])
    model_key = {
        "humidity_start": "environment_humidity_start",
        "humidity_end": "environment_humidity_end",
        "temperature_start": "environment_temperature_start",
        "temperature_end": "environment_temperature_end",
    }.get(key, key)
    value = getattr(field_sheet, model_key, None)
    if value in (None, ""):
        value = (field_sheet.capture_values or {}).get(key)
    return _display_value(value)


def _build_print_blocks(
    field_sheet: FieldSheet,
    template_definition: dict,
    *,
    equipment: dict,
    client_name: str,
    client_attention: str,
    client_address: str | None,
    certificate_folio: str | None,
) -> list[PrintBlock]:
    sections_by_key = {section.key: section for section in _group_sections(field_sheet, template_definition)}
    result: list[PrintBlock] = []
    for block in sorted(
        template_definition.get("blocks") or [],
        key=lambda item: (item.get("print_order", 0), item.get("capture_order", 0)),
    ):
        if block.get("visible", True) is False or block.get("print_visible", True) is False or block.get("pdf_visible", True) is False:
            continue
        block_key = block.get("block_key") or block.get("key") or block["block_type"]
        field_specs = {item.get("key"): item for item in block.get("fields") or []}
        fields = [
            PrintField(
                key=key,
                label=(field_specs.get(key) or {}).get("label") or FIELD_LABELS.get(key, key.replace("_", " ").title()),
                value=_field_value(
                    key,
                    field_sheet=field_sheet,
                    template_definition=template_definition,
                    equipment=equipment,
                    client_name=client_name,
                    client_attention=client_attention,
                    client_address=client_address,
                    certificate_folio=certificate_folio,
                ),
            )
            for key in block.get("visible_fields") or []
        ]
        section_keys = [item.get("key") for item in block.get("sections") or []]
        if not section_keys and block_key in sections_by_key:
            section_keys = [block_key]
        metadata = dict(block.get("metadata") or {})
        result.append(
            PrintBlock(
                key=block_key,
                block_type=block["block_type"],
                title=block.get("title") or block["block_type"],
                fields=fields,
                sections=[sections_by_key[key] for key in section_keys if key in sections_by_key],
                table_family=template_definition.get("table_family") or "custom",
                metadata=metadata,
                grid_columns=max(1, min(int(metadata.get("columns") or 2), 4)),
            )
        )
    return result


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
    _, _, template_name = resolve_field_sheet_pdf_renderer(field_sheet, template_definition)
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
    certificate_folio = (
        lab_equipment.certificate_folio
        if lab_equipment is not None
        else (certificate.expected_folio or certificate.folio) if certificate else "-"
    )
    print_blocks = _build_print_blocks(
        field_sheet,
        template_definition,
        equipment=equipment_values,
        client_name=client_name,
        client_attention=client_attention,
        client_address=client_address,
        certificate_folio=certificate_folio,
    )
    return template.render(
        field_sheet=field_sheet,
        equipment=equipment_values,
        service_order=service_order,
        client=client,
        client_name=client_name,
        client_attention=client_attention,
        client_address=client_address,
        capture_values=capture_values,
        certificate_folio=certificate_folio,
        template_definition=template_definition,
        institution=institution,
        signatures=signatures,
        sections=_group_sections(field_sheet, template_definition),
        print_blocks=print_blocks,
        row_value=_row_value,
        checkbox=_checkbox,
        logo_uri=logo_path.as_uri() if logo_path else None,
    )


def _render_pdf(db, field_sheet: FieldSheet) -> tuple[bytes, str]:
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


def freeze_final_field_sheet_pdf(db, field_sheet: FieldSheet) -> tuple[bytes, str]:
    if field_sheet.final_pdf_path:
        stored = require_deliverable_file(
            field_sheet.final_pdf_path,
            not_found_detail="El PDF final congelado no está disponible",
        )
        content = stored.read_bytes()
        if not field_sheet.final_pdf_sha256 or sha256(content).hexdigest() != field_sheet.final_pdf_sha256:
            raise HTTPException(status_code=409, detail="El PDF final congelado no coincide con su SHA-256")
        return content, stored.name

    renderer_key, renderer_version, _ = resolve_field_sheet_pdf_renderer(
        field_sheet,
        field_sheet.template_definition_json or {},
    )
    content, filename = _render_pdf(db, field_sheet)
    stored = save_validated_content(
        directory=Path("field-sheets") / str(field_sheet.id) / "final",
        filename=f"renderer-{renderer_version}.pdf",
        content=content,
        original_filename=filename,
    )
    field_sheet.pdf_renderer_key = renderer_key
    field_sheet.pdf_renderer_version = renderer_version
    field_sheet.final_pdf_path = stored.relative_path
    field_sheet.final_pdf_sha256 = stored.checksum_sha256
    field_sheet.final_pdf_template_definition_version = field_sheet.template_definition_version
    field_sheet.final_pdf_generated_at = datetime.now(timezone.utc)
    db.flush()
    return content, filename


def generate_field_sheet_pdf(db, field_sheet_id: int) -> tuple[bytes, str]:
    # Local import avoids a service cycle: completion invokes the low-level
    # freezer while the read endpoint still reuses the canonical loader.
    from app.services.field_sheets import get_field_sheet

    field_sheet = get_field_sheet(db, field_sheet_id)
    if field_sheet.status in FINAL_DOCUMENT_STATUSES:
        needs_persistence = not field_sheet.final_pdf_path
        content, filename = freeze_final_field_sheet_pdf(db, field_sheet)
        if needs_persistence:
            db.commit()
        return content, filename
    return _render_pdf(db, field_sheet)
