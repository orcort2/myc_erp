from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session
from weasyprint import HTML

from app.services.invoices import get_invoice, get_invoice_payment, get_invoice_settings


APP_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = APP_DIR / "templates"

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def _filename(value: str | None) -> str:
    raw = (value or "documento").strip()
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in raw) or "documento"


def generate_invoice_pdf(db: Session, invoice_id: int) -> tuple[bytes, str]:
    invoice = get_invoice(db, invoice_id)
    settings = get_invoice_settings(db)
    template = env.get_template("invoice_pdf.html")
    html = template.render(invoice=invoice, settings=settings)
    pdf = HTML(string=html, base_url=str(APP_DIR)).write_pdf()
    client_name = getattr(invoice.fiscal_client or invoice.client, "legal_name", None) or getattr(invoice.client, "commercial_name", None)
    return pdf, f"Factura_{_filename(invoice.series)}_{_filename(invoice.folio)}_{_filename(client_name)}.pdf"


def generate_invoice_payment_receipt_pdf(db: Session, payment_id: int) -> tuple[bytes, str]:
    payment = get_invoice_payment(db, payment_id)
    settings = get_invoice_settings(db)
    template = env.get_template("invoice_payment_receipt_pdf.html")
    html = template.render(payment=payment, invoice=payment.invoice, settings=settings)
    pdf = HTML(string=html, base_url=str(APP_DIR)).write_pdf()
    return pdf, f"Recibo_Pago_{_filename(payment.invoice.folio)}_{payment.id}.pdf"
