from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from re import sub
from unicodedata import normalize

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.models.client import Client
from app.models.service_order import ServiceOrder
from app.services.service_orders import get_service_order


APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_DIR.parents[1]
TEMPLATE_DIR = APP_DIR / "templates"
LOGO_PATH = PROJECT_ROOT / "frontend" / "src" / "assets" / "myc-logo.png"


@dataclass(frozen=True)
class WorkOrderEquipmentLine:
    index: int
    quantity: int
    description: str
    brand: str
    internal_id: str
    serial_number: str
    certificate_folio: str


def _filename(value: str) -> str:
    ascii_value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    safe = sub(r"[^A-Za-z0-9_.-]+", "-", ascii_value).strip("-_.")
    return safe or "orden-trabajo"


def _format_date(value) -> str:
    if value is None:
        return "-"
    return value.strftime("%d/%m/%Y")


def _client_address(client: Client) -> str:
    parts = [
        getattr(client, "street", None),
        getattr(client, "exterior_number", None),
        getattr(client, "interior_number", None),
        getattr(client, "neighborhood", None),
        getattr(client, "city", None),
        getattr(client, "state", None),
        getattr(client, "postal_code", None),
        getattr(client, "country", None),
    ]
    return ", ".join(part for part in parts if part)


def _build_equipment_lines(service_order: ServiceOrder) -> list[WorkOrderEquipmentLine]:
    lines = []

    for index, equipment in enumerate(
        [item for item in service_order.equipment if item.is_active],
        start=1,
    ):
        certificate = next(
            (
                item for item in equipment.certificates
                if item.is_active
            ),
            None,
        )

        WorkOrderEquipmentLine(
            index=index,
            quantity=1,
            description=equipment.name or "Equipo",
            brand=equipment.brand or "",
            internal_id=equipment.internal_id or "",
            serial_number=equipment.serial_number or "",
            certificate_folio=(
                certificate.expected_folio
                or certificate.folio
                if certificate
                else ""
            ),
        )

    while len(lines) < 10:
        lines.append(
            WorkOrderEquipmentLine(
                index=len(lines) + 1,
                quantity=0,
                description="",
                brand="",
                internal_id="",
                serial_number="",
                certificate_folio="",
            )
        )

    return lines[:10]


def _render_html(service_order: ServiceOrder) -> str:
    client = service_order.client
    contact = next((item for item in client.contacts if item.is_active), None)
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(("html", "xml")),
    )
    env.filters["date"] = _format_date
    template = env.get_template("work_order_pdf.html")
    return template.render(
        service_order=service_order,
        client=client,
        contact=contact,
        equipment_lines=_build_equipment_lines(service_order),
        client_address=_client_address(client),
        logo_uri=LOGO_PATH.as_uri() if LOGO_PATH.exists() else None,
    )


def generate_work_order_pdf(db, service_order_id: int) -> tuple[bytes, str]:
    service_order = get_service_order(db, service_order_id)
    html = _render_html(service_order)
    pdf = HTML(string=html, base_url=str(APP_DIR)).write_pdf()
    client_name = service_order.client.commercial_name or service_order.client.legal_name or service_order.client.rfc
    return (
        pdf,
        f"Orden_Trabajo_{service_order.work_order_number}_{_filename(client_name)}.pdf",
    )
