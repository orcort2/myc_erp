"""Pure ERP-to-Facturama API Web CFDI 4.0 mapping and validation."""
from decimal import Decimal

from app.models.invoice import Invoice, InvoiceSettings


# Serie fiscal configurada para el perfil Facturama de MYC. El folio interno
# de la factura y `invoice.series` no se envían al PAC.
FACTURAMA_SERIES = "MYCF"


class InvoiceValidationError(Exception):
    def __init__(self, fields: list[dict[str, str]]):
        self.fields = fields


def _value(value: Decimal | int | str | None) -> str:
    return f"{Decimal(value or 0):.2f}"


def map_invoice(invoice: Invoice, settings: InvoiceSettings) -> dict:
    snapshot = invoice.fiscal_snapshot or {}
    emitter = settings.emitter_data or {}
    fields: list[dict[str, str]] = []
    def required(value, field, message):
        if not value: fields.append({"field": field, "message": message})
        return value
    expedition = required(emitter.get("expedition_place"), "issuer.expedition_place", "El lugar de expedición del emisor es obligatorio.")
    required(emitter.get("rfc"), "issuer.rfc", "El RFC del emisor es obligatorio.")
    receiver = {
        "Name": required(snapshot.get("receiver_legal_name"), "receiver.name", "La razón social del receptor es obligatoria."),
        "CfdiUse": required(snapshot.get("receiver_cfdi_use_code") or invoice.usage_cfdi, "receiver.cfdi_use", "El uso CFDI es obligatorio."),
        "Rfc": required(snapshot.get("receiver_rfc"), "receiver.rfc", "El RFC del receptor es obligatorio."),
        "FiscalRegime": required(snapshot.get("receiver_tax_regime_code"), "receiver.tax_regime", "El régimen fiscal del receptor es obligatorio."),
        "TaxZipCode": required(snapshot.get("receiver_fiscal_postal_code"), "receiver.tax_zip_code", "El código postal fiscal del receptor es obligatorio."),
    }
    items = []
    for i, item in enumerate(invoice.items):
        if not item.sat_key: fields.append({"field": f"items[{i}].sat_product_code", "message": "La clave SAT del concepto es obligatoria."})
        if not item.sat_unit: fields.append({"field": f"items[{i}].sat_unit_code", "message": "La clave de unidad SAT es obligatoria."})
        if item.quantity <= 0 or item.unit_price < 0: fields.append({"field": f"items[{i}]", "message": "Cantidad o importe inválido."})
        base = Decimal(item.quantity) * Decimal(item.unit_price) - Decimal(item.discount_total or 0)
        taxes = []
        if Decimal(item.tax_rate or 0):
            taxes.append({"Name": "IVA", "Rate": str(Decimal(item.tax_rate) / 100), "Total": _value(item.tax_total), "Base": _value(base), "IsRetention": "false", "IsFederalTax": "true"})
        items.append({"Quantity": _value(item.quantity), "ProductCode": item.sat_key, "UnitCode": item.sat_unit, "Unit": item.unit or "Servicio", "Description": item.description, "UnitPrice": _value(item.unit_price), "Subtotal": _value(base), "Discount": _value(item.discount_total), "TaxObject": "02" if taxes else "01", "Taxes": taxes, "Total": _value(item.line_total)})
    if not items: fields.append({"field": "items", "message": "La factura requiere al menos un concepto."})
    if not invoice.payment_form: fields.append({"field": "payment_form", "message": "La forma de pago es obligatoria."})
    if not invoice.payment_method: fields.append({"field": "payment_method", "message": "El método de pago es obligatorio."})
    if fields: raise InvoiceValidationError(fields)
    return {"Receiver": receiver, "CfdiType": "I", "NameId": str(invoice.id), "ExpeditionPlace": expedition, "Serie": FACTURAMA_SERIES, "Folio": None, "PaymentForm": invoice.payment_form, "PaymentMethod": invoice.payment_method, "Currency": invoice.currency or "MXN", "Exportation": "01", "Items": items}
