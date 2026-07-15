from __future__ import annotations

import base64
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import qrcode
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from num2words import num2words
from sqlalchemy import select
from sqlalchemy.orm import Session
from weasyprint import HTML

from app.models.sat_catalog import SatCatalog, SatCatalogRecord
from app.services.document_templates import get_or_create_quotation_template
from app.services.institutional_configurations import (
    get_or_create_institutional_configuration,
)
from app.services.invoices import (
    get_invoice,
    get_invoice_payment,
    get_invoice_settings,
)
from app.services.sat_catalogs.service import is_record_current, latest_version
from app.services.storage_service import resolve_storage_path


APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = APP_DIR.parents[1]
TEMPLATE_DIR = APP_DIR / "templates"

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def _filename(value: str | None) -> str:
    raw = (value or "documento").strip()
    return "".join(
        char if char.isalnum() or char in "._-" else "_"
        for char in raw
    ) or "documento"


def invoice_document_filename(invoice, extension: str) -> str:
    series = _filename(invoice.series)
    folio = _filename(invoice.folio)
    return f"Factura_MYC_{series}-{folio}.{extension}"


def _money(value: Any) -> str:
    try:
        amount = Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0")
    return f"${amount:,.2f}"


def _date(value: Any, with_time: bool = False) -> str:
    if not value:
        return "—"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value

    if isinstance(value, datetime):
        return value.strftime(
            "%d/%m/%Y %H:%M:%S" if with_time else "%d/%m/%Y"
        )

    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    return str(value)


env.filters["money"] = _money
env.filters["date"] = _date


def _amount_in_words(value: Any, currency: str = "MXN") -> str:
    try:
        amount = Decimal(str(value or 0)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0.00")

    integer_part = int(amount)
    cents = int((amount - Decimal(integer_part)) * 100)

    words = num2words(integer_part, lang="es").upper()

    currency_code = (currency or "MXN").upper()
    currency_name = {
        "MXN": "PESOS",
        "USD": "DÓLARES",
        "EUR": "EUROS",
    }.get(currency_code, currency_code)

    return f"{words} {currency_name} {cents:02d}/100 {currency_code}"


def _tag_name(element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _attr(element, *names: str, default: str = "") -> str:
    expected = {name.lower() for name in names}

    for key, value in element.attrib.items():
        if key.lower() in expected and value not in (None, ""):
            return str(value)

    return default


def _find_element(root, name: str):
    for element in root.iter():
        if _tag_name(element).lower() == name.lower():
            return element
    return None


def _find_elements(root, name: str) -> list:
    return [
        element
        for element in root.iter()
        if _tag_name(element).lower() == name.lower()
    ]


def _read_xml_root(invoice):
    if not invoice.facturama_xml_path:
        return None, None

    path = resolve_storage_path(invoice.facturama_xml_path)
    if path is None or not path.is_file():
        return None, None

    content = path.read_bytes()

    try:
        return ElementTree.fromstring(content), content
    except ElementTree.ParseError:
        return None, content


def _logo_data_uri() -> str | None:
    candidates = (
        PROJECT_DIR / "frontend" / "src" / "assets" / "myc-logo.png",
        PROJECT_DIR / "frontend" / "src" / "assets" / "myc-logo.svg",
        PROJECT_DIR / "frontend" / "assets" / "Logo sin fondo MYC.png",
        APP_DIR / "static" / "myc-logo.png",
    )

    for path in candidates:
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        mime = {
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }.get(suffix)

        if not mime:
            continue

        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    return None


def _qr_data_uri(value: str | None) -> str | None:
    if not value:
        return None

    image = qrcode.make(value)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _verification_url(
    *,
    uuid: str,
    emitter_rfc: str,
    receiver_rfc: str,
    total: str,
    seal: str,
) -> str:
    total_value = Decimal(str(total or 0))
    formatted_total = f"{total_value:017.6f}"
    seal_tail = (seal or "")[-8:]

    return (
        "https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx"
        f"?id={uuid}"
        f"&re={emitter_rfc}"
        f"&rr={receiver_rfc}"
        f"&tt={formatted_total}"
        f"&fe={seal_tail}"
    )


def _catalog_entry(
    db: Session,
    candidate_catalog_codes: tuple[str, ...],
    code: str | None,
) -> dict[str, str]:
    normalized_code = str(code or "").strip()

    if not normalized_code:
        return {"code": "", "name": ""}

    for catalog_code in candidate_catalog_codes:
        catalog = db.scalar(
            select(SatCatalog).where(SatCatalog.code == catalog_code)
        )
        if catalog is None:
            continue

        version = latest_version(db, catalog)
        if version is None:
            continue

        record = db.scalar(
            select(SatCatalogRecord).where(
                SatCatalogRecord.catalog_version_id == version.id,
                SatCatalogRecord.code == normalized_code,
            )
        )
        if record is None or not is_record_current(record):
            continue

        return {
            "code": normalized_code,
            "name": (
                str(record.name or "").strip()
                or str((record.data or {}).get("description") or "").strip()
                or str((record.data or {}).get("Descripción") or "").strip()
            ),
        }

    return {"code": normalized_code, "name": ""}


CATALOG_CANDIDATES = {
    "payment_form": (
        "payment_forms",
        "formas_pago",
        "payment_form",
    ),
    "payment_method": (
        "payment_methods",
        "metodos_pago",
        "payment_method",
    ),
    "currency": (
        "currencies",
        "monedas",
        "currency",
    ),
    "cfdi_use": (
        "cfdi_uses",
        "usos_cfdi",
        "usage_cfdi",
    ),
    "tax_regime": (
        "fiscal_regimes",
        "regimenes_fiscales",
        "tax_regime",
    ),
    "voucher_type": (
        "voucher_types",
        "tipos_comprobante",
        "voucher_type",
    ),
    "exportation": (
        "exports",
        "export_codes",
        "exportation",
        "exportaciones",
    ),
    "product_service": (
        "products_services",
        "product_service_keys",
        "productos_servicios",
    ),
    "unit": (
        "units",
        "measurement_units",
        "unidades",
    ),
    "tax_object": (
        "tax_objects",
        "objetos_impuesto",
        "tax_object",
    ),
}


def _extract_fiscal_context(invoice) -> dict[str, Any]:
    root, _ = _read_xml_root(invoice)

    fiscal_snapshot = invoice.fiscal_snapshot or {}

    result = {
        "version": "4.0",
        "cfdi_type": "I",
        "exportation": "01",
        "uuid": invoice.cfdi_uuid or "",
        "stamped_at": invoice.stamped_at,
        "issuer": {
            "rfc": "",
            "name": "",
            "tax_regime": "",
        },
        "receiver": {
            "rfc": fiscal_snapshot.get("receiver_rfc", ""),
            "name": fiscal_snapshot.get("receiver_legal_name", ""),
            "tax_regime": fiscal_snapshot.get("receiver_tax_regime", ""),
            "postal_code": fiscal_snapshot.get("receiver_postal_code", ""),
            "cfdi_use": invoice.usage_cfdi or "",
        },
        "certificate_number": "",
        "sat_certificate_number": "",
        "pac_rfc": "",
        "cfdi_seal": "",
        "sat_seal": "",
        "original_chain": "",
        "expedition_place": "",
        "payment_method": invoice.payment_method or "",
        "payment_form": invoice.payment_form or "",
        "currency": invoice.currency or "MXN",
        "concepts": [],
    }

    if root is None:
        return result

    result.update(
        {
            "version": _attr(root, "Version", default=result["version"]),
            "cfdi_type": _attr(
                root,
                "TipoDeComprobante",
                default=result["cfdi_type"],
            ),
            "exportation": _attr(
                root,
                "Exportacion",
                default=result["exportation"],
            ),
            "certificate_number": _attr(root, "NoCertificado"),
            "cfdi_seal": _attr(root, "Sello"),
            "expedition_place": _attr(root, "LugarExpedicion"),
            "payment_method": _attr(
                root,
                "MetodoPago",
                default=result["payment_method"],
            ),
            "payment_form": _attr(
                root,
                "FormaPago",
                default=result["payment_form"],
            ),
            "currency": _attr(
                root,
                "Moneda",
                default=result["currency"],
            ),
        }
    )

    issuer = _find_element(root, "Emisor")
    if issuer is not None:
        result["issuer"] = {
            "rfc": _attr(issuer, "Rfc"),
            "name": _attr(issuer, "Nombre"),
            "tax_regime": _attr(issuer, "RegimenFiscal"),
        }

    receiver = _find_element(root, "Receptor")
    if receiver is not None:
        result["receiver"] = {
            "rfc": _attr(
                receiver,
                "Rfc",
                default=result["receiver"]["rfc"],
            ),
            "name": _attr(
                receiver,
                "Nombre",
                default=result["receiver"]["name"],
            ),
            "tax_regime": _attr(
                receiver,
                "RegimenFiscalReceptor",
                default=result["receiver"]["tax_regime"],
            ),
            "postal_code": _attr(
                receiver,
                "DomicilioFiscalReceptor",
                default=result["receiver"]["postal_code"],
            ),
            "cfdi_use": _attr(
                receiver,
                "UsoCFDI",
                default=result["receiver"]["cfdi_use"],
            ),
        }

    stamp = _find_element(root, "TimbreFiscalDigital")
    if stamp is not None:
        result.update(
            {
                "uuid": _attr(
                    stamp,
                    "UUID",
                    default=result["uuid"],
                ),
                "stamped_at": _attr(
                    stamp,
                    "FechaTimbrado",
                    default=result["stamped_at"],
                ),
                "sat_certificate_number": _attr(
                    stamp,
                    "NoCertificadoSAT",
                ),
                "pac_rfc": _attr(stamp, "RfcProvCertif"),
                "sat_seal": _attr(stamp, "SelloSAT"),
                "original_chain": (
                    f"||{_attr(stamp, 'Version')}|"
                    f"{_attr(stamp, 'UUID')}|"
                    f"{_attr(stamp, 'FechaTimbrado')}|"
                    f"{_attr(stamp, 'RfcProvCertif')}|"
                    f"{_attr(stamp, 'SelloCFD')}|"
                    f"{_attr(stamp, 'NoCertificadoSAT')}||"
                ),
            }
        )

    result["concepts"] = [
        {
            "product_service": _attr(element, "ClaveProdServ"),
            "unit": _attr(element, "ClaveUnidad"),
            "tax_object": _attr(element, "ObjetoImp"),
        }
        for element in _find_elements(root, "Concepto")
    ]

    return result


def _public_invoice_context(
    db: Session,
    invoice,
    settings,
) -> dict[str, Any]:
    fiscal = _extract_fiscal_context(invoice)
    emitter_data = settings.emitter_data or {}
    quotation_template = get_or_create_quotation_template(db)
    institution = get_or_create_institutional_configuration(db)

    issuer_rfc = fiscal["issuer"]["rfc"] or emitter_data.get("rfc", "")
    issuer_name = (
        fiscal["issuer"]["name"]
        or quotation_template.company_name
        or institution.legal_name
        or emitter_data.get("legal_name")
        or emitter_data.get("commercial_name")
        or "METROLOGÍA Y SERVICIOS MYC"
    )
    issuer_regime_code = (
        fiscal["issuer"]["tax_regime"]
        or emitter_data.get("tax_regime", "")
    )

    receiver = invoice.fiscal_client or invoice.client
    receiver_name = (
        fiscal["receiver"]["name"]
        or getattr(receiver, "legal_name", None)
        or getattr(receiver, "commercial_name", None)
        or "—"
    )
    receiver_rfc = (
        fiscal["receiver"]["rfc"]
        or getattr(receiver, "rfc", None)
        or "—"
    )

    issuer_regime = _catalog_entry(
        db,
        CATALOG_CANDIDATES["tax_regime"],
        issuer_regime_code,
    )
    receiver_regime = _catalog_entry(
        db,
        CATALOG_CANDIDATES["tax_regime"],
        fiscal["receiver"]["tax_regime"],
    )

    fiscal["issuer"] = {
        "rfc": issuer_rfc,
        "name": issuer_name,
        "tax_regime": issuer_regime,
        "address": (
            quotation_template.company_address
            or institution.address
            or emitter_data.get("address", "")
        ),
        "postal_code": (
            emitter_data.get("postal_code", "")
            or fiscal["expedition_place"]
        ),
        "phone": (
            quotation_template.company_phone
            or institution.phone
            or emitter_data.get("phone", "")
        ),
        "email": (
            quotation_template.company_email
            or institution.email
            or emitter_data.get("email", "")
        ),
        "website": quotation_template.company_website or emitter_data.get("website", ""),
    }
    fiscal["receiver"]["name"] = receiver_name
    fiscal["receiver"]["rfc"] = receiver_rfc
    fiscal["receiver"]["tax_regime"] = receiver_regime

    fiscal["payment_form"] = _catalog_entry(
        db,
        CATALOG_CANDIDATES["payment_form"],
        fiscal["payment_form"],
    )
    fiscal["payment_method"] = _catalog_entry(
        db,
        CATALOG_CANDIDATES["payment_method"],
        fiscal["payment_method"],
    )
    fiscal["currency"] = _catalog_entry(
        db,
        CATALOG_CANDIDATES["currency"],
        fiscal["currency"],
    )
    fiscal["receiver"]["cfdi_use"] = _catalog_entry(
        db,
        CATALOG_CANDIDATES["cfdi_use"],
        fiscal["receiver"]["cfdi_use"],
    )
    fiscal["voucher_type"] = _catalog_entry(
        db,
        CATALOG_CANDIDATES["voucher_type"],
        fiscal["cfdi_type"],
    )
    fiscal["exportation"] = _catalog_entry(
        db,
        CATALOG_CANDIDATES["exportation"],
        fiscal["exportation"],
    )

    item_rows = []
    xml_concepts = fiscal.get("concepts") or []

    for index, item in enumerate(invoice.items or []):
        xml_concept = xml_concepts[index] if index < len(xml_concepts) else {}

        product_code = (
            xml_concept.get("product_service")
            or getattr(item, "sat_key", "")
        )
        unit_code = (
            xml_concept.get("unit")
            or getattr(item, "sat_unit", "")
        )
        tax_object_code = (
            xml_concept.get("tax_object")
            or getattr(item, "tax_object", "")
            or "02"
        )

        item_rows.append(
            {
                "item": item,
                "product_service": _catalog_entry(
                    db,
                    CATALOG_CANDIDATES["product_service"],
                    product_code,
                ),
                "unit": _catalog_entry(
                    db,
                    CATALOG_CANDIDATES["unit"],
                    unit_code,
                ),
                "tax_object": _catalog_entry(
                    db,
                    CATALOG_CANDIDATES["tax_object"],
                    tax_object_code,
                ),
            }
        )

    qr_url = None
    if (
        fiscal["uuid"]
        and issuer_rfc
        and receiver_rfc
        and fiscal["cfdi_seal"]
    ):
        qr_url = _verification_url(
            uuid=fiscal["uuid"],
            emitter_rfc=issuer_rfc,
            receiver_rfc=receiver_rfc,
            total=str(invoice.total or 0),
            seal=fiscal["cfdi_seal"],
        )

    return {
        "invoice": invoice,
        "settings": settings,
        "fiscal": fiscal,
        "item_rows": item_rows,
        "total_words": _amount_in_words(
            invoice.total,
            fiscal["currency"]["code"] or invoice.currency or "MXN",
        ),
        "logo_uri": _logo_data_uri(),
        "qr_uri": _qr_data_uri(qr_url),
    }


def generate_invoice_pdf(
    db: Session,
    invoice_id: int,
) -> tuple[bytes, str]:
    invoice = get_invoice(db, invoice_id)
    settings = get_invoice_settings(db)
    template = env.get_template("invoice_pdf.html")
    context = _public_invoice_context(db, invoice, settings)

    html = template.render(**context)
    pdf = HTML(
        string=html,
        base_url=str(PROJECT_DIR),
    ).write_pdf()

    return pdf, invoice_document_filename(invoice, "pdf")


def get_invoice_fiscal_xml(
    db: Session,
    invoice_id: int,
) -> tuple[bytes, str]:
    invoice = get_invoice(db, invoice_id)
    document_path = resolve_storage_path(invoice.facturama_xml_path)

    if document_path is None or not document_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="El XML fiscal aún no está disponible para esta factura.",
        )

    content = document_path.read_bytes()

    try:
        ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise HTTPException(
            status_code=409,
            detail="El XML fiscal almacenado no es válido.",
        ) from exc

    return content, invoice_document_filename(invoice, "xml")


def generate_invoice_payment_receipt_pdf(
    db: Session,
    payment_id: int,
) -> tuple[bytes, str]:
    payment = get_invoice_payment(db, payment_id)
    settings = get_invoice_settings(db)
    template = env.get_template("invoice_payment_receipt_pdf.html")
    html = template.render(
        payment=payment,
        invoice=payment.invoice,
        settings=settings,
    )
    pdf = HTML(string=html, base_url=str(PROJECT_DIR)).write_pdf()

    return (
        pdf,
        f"Recibo_Pago_{_filename(payment.invoice.folio)}_{payment.id}.pdf",
    )
