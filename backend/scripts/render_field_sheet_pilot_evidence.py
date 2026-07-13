from pathlib import Path
from types import SimpleNamespace

from weasyprint import HTML

from app.models.field_sheet import FieldSheetResult
from app.services.field_sheet_pdfs import APP_DIR, _render_html
from app.services.field_sheet_templates import build_fallback_template_definition


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output" / "pdf"
INSTITUTION = {
    "configuration_key": "default",
    "legal_name": "METROLOGÍA Y SERVICIOS MYC",
    "document_code": "FCA-30",
    "initial_revision": "R1",
    "address": "Configuración institucional del ERP",
    "phone": "Teléfono institucional",
    "email": "correo@institucional.mx",
    "logo_path": "frontend/src/assets/myc-logo.png",
}


def _sheet(template_key: str, definition: dict):
    client = SimpleNamespace(commercial_name="Cliente de evidencia", legal_name="Cliente de evidencia")
    service_order = SimpleNamespace(client=client, work_order_number=1234)
    equipment = SimpleNamespace(
        name=definition["name"].replace("Hoja de Campo ", ""),
        brand="Marca",
        model="Modelo",
        serial_number="SER-001",
        internal_id="MYC-001",
        service_order=service_order,
        certificates=[],
    )
    rows = []
    for section in definition["result_sections"]:
        for row_number in range(1, section["rows"] + 1):
            row_data = {
                column["source"]: f"{row_number}.{column_index}"
                for column_index, column in enumerate(section["columns"], start=1)
            }
            rows.append(
                FieldSheetResult(
                    section_key=section["key"],
                    row_number=row_number,
                    row_data=row_data,
                )
            )
    signatures = [
        SimpleNamespace(role="calibrated_by", display_label="Calibró", name="Técnico MYC", signature_data=None, signed_at=None, user_id=1, position=0),
        SimpleNamespace(role="reviewed_by", display_label="Revisó", name="Calidad MYC", signature_data=None, signed_at=None, user_id=2, position=1),
        SimpleNamespace(role="report_made_by", display_label="Elaboró informe", name="Captura MYC", signature_data=None, signed_at=None, user_id=3, position=2),
    ]
    return SimpleNamespace(
        template_key=template_key,
        equipment=equipment,
        work_order_number=1234,
        company="Cliente de evidencia",
        attention="Responsable de laboratorio",
        address="Domicilio del cliente",
        certificate_client_mode="billing",
        certificate_client_company=None,
        certificate_client_attention=None,
        certificate_client_address=None,
        minimum_division="0.01",
        reception_date=None,
        calibration_date=None,
        next_calibration_date=None,
        calibration_place="Laboratorio MYC",
        environment_humidity_start="45 %",
        environment_humidity_end="46 %",
        environment_temperature_start="23 °C",
        environment_temperature_end="24 °C",
        initial_condition="Equipo recibido en condición operativa.",
        final_condition="Equipo entregado en condición operativa.",
        observations="Captura manual sin cálculos metrológicos automáticos.",
        results_rows=rows,
        signatures=signatures,
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for template_key in ("anemometro", "calibradores", "presion", "bascula"):
        definition = build_fallback_template_definition(template_key)
        field_sheet = _sheet(template_key, definition)
        html = _render_html(field_sheet, definition, INSTITUTION)
        target = OUTPUT_DIR / f"evidencia_hoja_campo_{template_key}.pdf"
        HTML(string=html, base_url=str(APP_DIR)).write_pdf(target)
        print(target)


if __name__ == "__main__":
    main()

