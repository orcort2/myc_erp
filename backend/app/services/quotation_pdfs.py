from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from re import sub
from unicodedata import normalize

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session
from weasyprint import HTML

from app.models.quotation import Quotation, QuotationItem
from app.models.user import User
from app.services.document_templates import get_or_create_quotation_template
from app.services.quotations import get_quotation


APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_DIR.parents[1]
TEMPLATE_DIR = APP_DIR / "templates"
LOGO_PATH = PROJECT_ROOT / "frontend" / "src" / "assets" / "myc-logo.png"

@dataclass(frozen=True)
class PdfLine:
    description: str
    legend: str | None
    quantity: int
    unit: str
    unit_price: Decimal
    discount_percent: Decimal
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    sat_key: str
    sat_unit: str


def _money(value: Decimal | int | float | None) -> Decimal:
    amount = Decimal("0.00") if value is None else Decimal(value)
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_money(value: Decimal | int | float | None) -> str:
    amount = _money(value)
    return f"${amount:,.2f} MXN"


def _format_date(value: date | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%d/%m/%Y")


def _filename(value: str) -> str:
    ascii_value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    safe = sub(r"[^A-Za-z0-9_.-]+", "-", ascii_value).strip("-_.")
    return safe or "cotizacion"


UNITS = (
    "",
    "uno",
    "dos",
    "tres",
    "cuatro",
    "cinco",
    "seis",
    "siete",
    "ocho",
    "nueve",
    "diez",
    "once",
    "doce",
    "trece",
    "catorce",
    "quince",
    "dieciseis",
    "diecisiete",
    "dieciocho",
    "diecinueve",
    "veinte",
    "veintiuno",
    "veintidos",
    "veintitres",
    "veinticuatro",
    "veinticinco",
    "veintiseis",
    "veintisiete",
    "veintiocho",
    "veintinueve",
)

TENS = {
    30: "treinta",
    40: "cuarenta",
    50: "cincuenta",
    60: "sesenta",
    70: "setenta",
    80: "ochenta",
    90: "noventa",
}

HUNDREDS = {
    100: "cien",
    200: "doscientos",
    300: "trescientos",
    400: "cuatrocientos",
    500: "quinientos",
    600: "seiscientos",
    700: "setecientos",
    800: "ochocientos",
    900: "novecientos",
}


def _number_to_words(number: int) -> str:
    if number == 0:
        return "cero"
    if number < 30:
        return UNITS[number]
    if number < 100:
        ten = number // 10 * 10
        unit = number % 10
        return TENS[ten] if unit == 0 else f"{TENS[ten]} y {UNITS[unit]}"
    if number < 1000:
        hundred = number // 100 * 100
        rest = number % 100
        if rest == 0:
            return HUNDREDS[hundred]
        prefix = "ciento" if hundred == 100 else HUNDREDS[hundred]
        return f"{prefix} {_number_to_words(rest)}"
    if number < 1_000_000:
        thousands = number // 1000
        rest = number % 1000
        prefix = "mil" if thousands == 1 else f"{_number_to_words(thousands)} mil"
        return prefix if rest == 0 else f"{prefix} {_number_to_words(rest)}"
    millions = number // 1_000_000
    rest = number % 1_000_000
    prefix = "un millon" if millions == 1 else f"{_number_to_words(millions)} millones"
    return prefix if rest == 0 else f"{prefix} {_number_to_words(rest)}"


def _total_to_words(total: Decimal) -> str:
    amount = _money(total)
    pesos = int(amount)
    cents = int((amount - Decimal(pesos)) * 100)
    return f"{_number_to_words(pesos).upper()} PESOS {cents:02d}/100 MXN"


def _line_from_item(item: QuotationItem) -> PdfLine:
    quantity = int(item.quantity or 0)
    unit_price = _money(item.unit_price)
    discount_percent = _money(item.discount_percent)
    subtotal = _money(item.total)
    tax_total = _money(item.tax_total)
    return PdfLine(
        description=item.service_name or item.description or "Partida sin descripcion",
        legend=item.quotation_legend,
        quantity=quantity,
        unit=item.unit or item.internal_unit or item.sat_unit or "Servicio",
        unit_price=unit_price,
        discount_percent=discount_percent,
        subtotal=subtotal,
        tax_total=tax_total,
        total=_money(subtotal + tax_total),
        sat_key=item.sat_key or "-",
        sat_unit=item.sat_unit or "-",
    )


def _advisor_name(db: Session, advisor_id: int | None) -> str:
    if advisor_id is None:
        return "Por definir"
    advisor = db.get(User, advisor_id)
    if advisor is None or not advisor.is_active:
        return "Por definir"
    return advisor.full_name or advisor.email or "Por definir"


def _render_html(db: Session, quotation: Quotation) -> str:
    client = quotation.client
    template_config = get_or_create_quotation_template(db)
    active_items = [item for item in quotation.items if item.is_active is not False]
    lines = [_line_from_item(item) for item in active_items]
    subtotal = sum((line.subtotal for line in lines), Decimal("0.00"))
    tax_total = sum((line.tax_total for line in lines), Decimal("0.00"))
    total = subtotal + tax_total
    contact = next((contact for contact in client.contacts if contact.is_active), None)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(("html", "xml")),
    )
    env.filters["money"] = _format_money
    env.filters["date"] = _format_date
    template = env.get_template("quotation_pdf.html")
    return template.render(
        quotation=quotation,
        client=client,
        contact=contact,
        lines=lines,
        subtotal=_money(subtotal),
        tax_total=_money(tax_total),
        total=_money(total),
        total_words=_total_to_words(total),
        advisor_name=_advisor_name(db, quotation.advisor_id),
        template_config=template_config,
        logo_uri=LOGO_PATH.as_uri() if LOGO_PATH.exists() else None,
    )


def generate_quotation_pdf(db: Session, quotation_id: int) -> tuple[bytes, str]:
    quotation = get_quotation(db, quotation_id)
    html = _render_html(db, quotation)
    pdf = HTML(string=html, base_url=str(APP_DIR)).write_pdf()
    client_name = quotation.client.commercial_name or quotation.client.legal_name
    return pdf, f"Cotizacion_{_filename(quotation.folio)}_{_filename(client_name)}.pdf"
