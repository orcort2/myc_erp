import unittest
from decimal import Decimal
from types import SimpleNamespace

from app.services.facturama.invoice_mapper import InvoiceValidationError, map_invoice


def valid_invoice():
    return SimpleNamespace(
        id=1, series="F", folio="F-1", payment_form="03", payment_method="PUE", currency="MXN",
        fiscal_snapshot={"receiver_legal_name": "CLIENTE PRUEBA", "receiver_cfdi_use_code": "G03", "receiver_rfc": "XAXX010101000", "receiver_tax_regime_code": "601", "receiver_fiscal_postal_code": "01000"},
        items=[SimpleNamespace(quantity=Decimal("1"), unit_price=Decimal("100"), discount_total=Decimal("0"), tax_rate=Decimal("16"), tax_total=Decimal("16"), line_total=Decimal("116"), sat_key="81141504", sat_unit="E48", unit="Servicio", description="Servicio de prueba")],
    )


class FacturamaInvoiceMapperTests(unittest.TestCase):
    def test_maps_sat_codes_and_tax_to_official_api_web_shape(self):
        payload = map_invoice(valid_invoice(), SimpleNamespace(emitter_data={"rfc": "AAA010101AAA", "expedition_place": "01000"}))
        self.assertEqual(payload["CfdiType"], "I")
        self.assertEqual(payload["Serie"], "MYCF")
        self.assertIsNone(payload["Folio"])
        self.assertEqual(payload["Receiver"]["TaxZipCode"], "01000")
        self.assertEqual(payload["Items"][0]["ProductCode"], "81141504")
        self.assertEqual(payload["Items"][0]["Taxes"][0]["Rate"], "0.16")

    def test_reports_structured_missing_fields_before_pac_call(self):
        invoice = valid_invoice(); invoice.items[0].sat_key = None
        with self.assertRaises(InvoiceValidationError) as raised:
            map_invoice(invoice, SimpleNamespace(emitter_data={}))
        self.assertIn("items[0].sat_product_code", [item["field"] for item in raised.exception.fields])
        self.assertIn("issuer.rfc", [item["field"] for item in raised.exception.fields])
