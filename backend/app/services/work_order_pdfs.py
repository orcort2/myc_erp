from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from re import sub
from unicodedata import normalize

from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from weasyprint import HTML

from app.models.client import Client
from app.models.equipment import Equipment
from app.models.service_order import ServiceOrder, ServiceWorkOrder
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


def _active_equipment_for_work_order(work_order: ServiceWorkOrder) -> list[Equipment]:
    return [
        equipment
        for equipment in work_order.equipment
        if equipment.is_active
    ]


def _build_equipment_lines(equipment_list: list[Equipment]) -> list[WorkOrderEquipmentLine]:
    lines: list[WorkOrderEquipmentLine] = []

    for index, equipment in enumerate(equipment_list, start=1):
        certificate = next(
            (
                item
                for item in equipment.certificates
                if item.is_active
            ),
            None,
        )

        lines.append(
            WorkOrderEquipmentLine(
                index=index,
                quantity=1,
                description=equipment.name or "Equipo",
                brand=equipment.brand or "",
                internal_id=equipment.internal_id or "",
                serial_number=equipment.serial_number or "",
                certificate_folio=(
                    (certificate.expected_folio or certificate.folio)
                    if certificate
                    else ""
                ),
            )
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


def _get_service_work_order(db, work_order_id: int) -> ServiceWorkOrder:
    work_order = db.scalar(
        select(ServiceWorkOrder)
        .where(
            ServiceWorkOrder.id == work_order_id,
            ServiceWorkOrder.is_active.is_(True),
        )
        .options(
            selectinload(ServiceWorkOrder.service_order)
            .selectinload(ServiceOrder.client)
            .selectinload(Client.contacts),
            selectinload(ServiceWorkOrder.service_order)
            .selectinload(ServiceOrder.quotation),
            selectinload(ServiceWorkOrder.equipment)
            .selectinload(Equipment.certificates),
        )
    )

    if work_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden de trabajo no encontrada",
        )

    return work_order


def _render_html(
    service_order: ServiceOrder,
    *,
    work_order: ServiceWorkOrder | None = None,
    equipment_list: list[Equipment] | None = None,
) -> str:
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
        work_order=work_order,
        client=client,
        contact=contact,
        equipment_lines=_build_equipment_lines(equipment_list or service_order.equipment),
        client_address=_client_address(client),
        logo_uri=LOGO_PATH.as_uri() if LOGO_PATH.exists() else None,
    )


def generate_work_order_pdf(db, service_order_id: int) -> tuple[bytes, str]:
    """
    Compatibilidad legacy:
    genera el PDF de la OT principal del servicio.
    """
    service_order = get_service_order(db, service_order_id)

    primary_work_order = None
    if service_order.work_orders:
        primary_work_order = sorted(
            [item for item in service_order.work_orders if item.is_active],
            key=lambda item: item.sequence,
        )[0]

    if primary_work_order is not None:
        equipment_list = _active_equipment_for_work_order(primary_work_order)
        work_order_number = primary_work_order.work_order_number
    else:
        equipment_list = [
            item for item in service_order.equipment if item.is_active
        ]
        work_order_number = service_order.work_order_number

    html = _render_html(
        service_order,
        work_order=primary_work_order,
        equipment_list=equipment_list,
    )

    pdf = HTML(string=html, base_url=str(APP_DIR)).write_pdf()

    client_name = (
        service_order.client.commercial_name
        or service_order.client.legal_name
        or service_order.client.rfc
    )

    return (
        pdf,
        f"Orden_Trabajo_{work_order_number}_{_filename(client_name)}.pdf",
    )


def generate_service_work_order_pdf(db, work_order_id: int) -> tuple[bytes, str]:
    """
    Genera el PDF de una Orden de Trabajo específica.
    Este es el flujo correcto para ETS con múltiples OT.
    """
    work_order = _get_service_work_order(db, work_order_id)
    service_order = work_order.service_order
    equipment_list = _active_equipment_for_work_order(work_order)

    html = _render_html(
        service_order,
        work_order=work_order,
        equipment_list=equipment_list,
    )

    pdf = HTML(string=html, base_url=str(APP_DIR)).write_pdf()

    client_name = (
        service_order.client.commercial_name
        or service_order.client.legal_name
        or service_order.client.rfc
    )

    return (
        pdf,
        f"Orden_Trabajo_{work_order.work_order_number}_{_filename(client_name)}.pdf",
    )