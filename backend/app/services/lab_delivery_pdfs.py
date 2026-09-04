from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, select_autoescape

from weasyprint import HTML

from app.models.lab_work_order import LabWorkOrder
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.services.field_sheet_layouts import ORGANIZATION_PRINT_PROFILES
from app.services.work_order_pdfs import APP_DIR, LOGO_PATH, TEMPLATE_DIR, _filename

DELIVERY_METHOD_LABELS = {
    "direct": "Entrega directa",
    "client_pickup": "Recolección por cliente",
}

# El acuse de entrega LAB es exclusivamente MYC (ver AGENTS.md de myc-mobile:
# el flujo de entrega LAB no es multi-organización como las hojas de campo),
# así que su branding institucional toma el perfil MYC directamente -- misma
# autoridad de color que field_sheet_layouts.resolve_organization_print_profile
# usa para el resto de los imprimibles de hojas de campo.
_MYC_PRINT_PROFILE = ORGANIZATION_PRINT_PROFILES["myc"]


def _normalize_recipient_name(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def generate_lab_delivery_receipt(
    root_work_order: LabWorkOrder,
    delivery: LabWorkOrderDelivery,
    delivered_by_name: str,
) -> tuple[bytes, str]:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html = env.get_template("lab_delivery_receipt.html").render(
        root_work_order=root_work_order,
        delivery=delivery,
        delivered_by_name=delivered_by_name,
        delivery_method_label=DELIVERY_METHOD_LABELS.get(delivery.delivery_method, delivery.delivery_method),
        delivered_at_display=delivery.delivered_at.astimezone().strftime("%d/%m/%Y · %H:%M"),
        logo_uri=LOGO_PATH.as_uri() if LOGO_PATH.exists() else None,
        primary_color=_MYC_PRINT_PROFILE["primary_color"],
        header_fill=_MYC_PRINT_PROFILE["header_fill"],
    )
    return (
        HTML(string=html, base_url=str(APP_DIR)).write_pdf(),
        f"Acuse-entrega-OT-{root_work_order.folio}-exhibicion-{delivery.exhibition_number}-{_filename(root_work_order.client_name)}.pdf",
    )


def generate_lab_delivery_final_receipt(
    root_work_order: LabWorkOrder,
    deliveries: list[LabWorkOrderDelivery],
) -> tuple[bytes, str]:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    first_recipient_norm = _normalize_recipient_name(deliveries[0].recipient_name) if deliveries else None
    rows = []
    for item in deliveries:
        same_contact = (
            item is not deliveries[0]
            and first_recipient_norm is not None
            and _normalize_recipient_name(item.recipient_name) == first_recipient_norm
        )
        rows.append(
            {
                "delivery": item,
                "recipient_display": "Mismo contacto" if same_contact else item.recipient_name,
                "delivery_method_label": DELIVERY_METHOD_LABELS.get(
                    item.delivery_method, item.delivery_method
                ),
                "delivered_at_display": item.delivered_at.astimezone().strftime("%d/%m/%Y · %H:%M"),
            }
        )
    html = env.get_template("lab_delivery_final_receipt.html").render(
        root_work_order=root_work_order,
        rows=rows,
        exhibitions_count=len(deliveries),
        logo_uri=LOGO_PATH.as_uri() if LOGO_PATH.exists() else None,
        primary_color=_MYC_PRINT_PROFILE["primary_color"],
        header_fill=_MYC_PRINT_PROFILE["header_fill"],
    )
    return (
        HTML(string=html, base_url=str(APP_DIR)).write_pdf(),
        f"Acuse-final-entrega-OT-{root_work_order.folio}-{_filename(root_work_order.client_name)}.pdf",
    )
