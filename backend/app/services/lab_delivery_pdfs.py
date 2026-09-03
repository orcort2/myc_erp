from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.models.lab_work_order import LabWorkOrder
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.services.work_order_pdfs import APP_DIR, TEMPLATE_DIR, _filename


def generate_lab_delivery_receipt(
    work_order: LabWorkOrder,
    delivery: LabWorkOrderDelivery,
    delivered_by_name: str,
) -> tuple[bytes, str]:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html = env.get_template("lab_delivery_receipt.html").render(
        work_order=work_order,
        delivery=delivery,
        delivered_by_name=delivered_by_name,
        delivered_at_display=delivery.delivered_at.astimezone().strftime("%d/%m/%Y · %H:%M"),
    )
    return (
        HTML(string=html, base_url=str(APP_DIR)).write_pdf(),
        f"Acuse-entrega-OT-{work_order.folio}-{_filename(work_order.client_name)}.pdf",
    )
