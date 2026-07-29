import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import Mock

from fastapi import HTTPException

from app.routers.invoices import (
    institutional_invoice_pdf,
    invoice_fiscal_xml,
    payment_receipt_pdf,
)
from app.services.invoice_pdfs import (
    CATALOG_CANDIDATES,
    _catalog_entry,
    get_invoice_fiscal_xml,
    invoice_document_filename,
)


def invoice(**values):
    payload = {
        "id": 41,
        "series": "MYCF",
        "folio": "000123",
        "facturama_xml_path": "facturama/41/cfdi.xml",
    }
    payload.update(values)
    return SimpleNamespace(**payload)


class InvoiceDocumentTests(unittest.TestCase):
    def test_catalog_candidates_match_the_active_sat_catalog_codes(self):
        self.assertEqual(CATALOG_CANDIDATES["tax_regime"][0], "fiscal_regimes")
        self.assertEqual(CATALOG_CANDIDATES["exportation"][0], "exports")
        self.assertEqual(CATALOG_CANDIDATES["product_service"][0], "products_services")
        self.assertEqual(CATALOG_CANDIDATES["unit"][0], "units")

    def test_catalog_entry_reads_description_from_the_active_version(self):
        database = Mock()
        catalog = SimpleNamespace(id=7)
        active_version = SimpleNamespace(id=19)
        record = SimpleNamespace(
            code="03",
            name="Transferencia electrónica de fondos",
            data={},
            is_active=True,
            valid_from=None,
            valid_until=None,
        )
        database.scalar.side_effect = [catalog, record]

        with patch(
            "app.services.invoice_pdfs.latest_version",
            return_value=active_version,
        ):
            result = _catalog_entry(database, ("payment_forms",), "03")

        self.assertEqual(result, {
            "code": "03",
            "name": "Transferencia electrónica de fondos",
        })

    def test_public_filenames_are_stable_and_do_not_leak_storage_names(self):
        record = invoice(series="A/B", folio="12 3")

        self.assertEqual(
            invoice_document_filename(record, "pdf"),
            "Factura_MYC_A_B-12_3.pdf",
        )
        self.assertEqual(
            invoice_document_filename(record, "xml"),
            "Factura_MYC_A_B-12_3.xml",
        )

    def test_fiscal_xml_reads_existing_valid_document_with_public_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "internal-provider-name.xml"
            source.write_bytes(b'<?xml version="1.0"?><cfdi:Comprobante xmlns:cfdi="urn:cfdi"/>')
            with patch("app.services.invoice_pdfs.get_invoice", return_value=invoice()), patch(
                "app.services.invoice_pdfs.resolve_storage_path", return_value=source
            ):
                content, filename = get_invoice_fiscal_xml(object(), 41)

        self.assertIn(b"Comprobante", content)
        self.assertEqual(filename, "Factura_MYC_MYCF-000123.xml")

    def test_fiscal_xml_reports_missing_or_invalid_documents(self):
        with patch("app.services.invoice_pdfs.get_invoice", return_value=invoice()), patch(
            "app.services.invoice_pdfs.resolve_storage_path", return_value=None
        ):
            with self.assertRaises(HTTPException) as missing:
                get_invoice_fiscal_xml(object(), 41)
        self.assertEqual(missing.exception.status_code, 404)

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "invalid.xml"
            source.write_text("not xml", encoding="utf-8")
            with patch("app.services.invoice_pdfs.get_invoice", return_value=invoice()), patch(
                "app.services.invoice_pdfs.resolve_storage_path", return_value=source
            ):
                with self.assertRaises(HTTPException) as invalid:
                    get_invoice_fiscal_xml(object(), 41)
        self.assertEqual(invalid.exception.status_code, 409)

    def test_document_routes_use_expected_mime_and_attachment_names(self):
        with patch(
            "app.routers.invoices.generate_invoice_pdf",
            return_value=(b"%PDF-test", "Factura_MYC_MYCF-000123.pdf"),
        ):
            pdf = institutional_invoice_pdf(41, object(), object())
        self.assertEqual(pdf.media_type, "application/pdf")
        self.assertEqual(
            pdf.headers["content-disposition"],
            'attachment; filename="Factura_MYC_MYCF-000123.pdf"',
        )

        with patch(
            "app.routers.invoices.get_invoice_fiscal_xml",
            return_value=(b"<cfdi:Comprobante/>", "Factura_MYC_MYCF-000123.xml"),
        ):
            xml = invoice_fiscal_xml(41, object(), object())
        self.assertEqual(xml.media_type, "application/xml")
        self.assertEqual(
            xml.headers["content-disposition"],
            'attachment; filename="Factura_MYC_MYCF-000123.xml"',
        )

        with patch(
            "app.routers.invoices.generate_invoice_payment_receipt_pdf",
            return_value=(b"%PDF-payment", "Recibo_Pago_000123_9.pdf"),
        ):
            receipt = payment_receipt_pdf(9, object(), object())
        self.assertEqual(receipt.media_type, "application/pdf")
        self.assertEqual(
            receipt.headers["content-disposition"],
            'inline; filename="Recibo_Pago_000123_9.pdf"',
        )
