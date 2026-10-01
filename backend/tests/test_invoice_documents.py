import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import Mock

from fastapi import HTTPException

from app.routers.invoices import (
    institutional_invoice_pdf,
    facturama_document_route,
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
        "series": "F",
        "folio": "MYCF-2026-0002",
        "cfdi_uuid": "UUID-1234",
        "stamped_at": "2026-10-01",
        "fiscal_snapshot": {},
        "usage_cfdi": "G03",
        "payment_method": "PUE",
        "payment_form": "03",
        "currency": "MXN",
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
        record = invoice(series="A/B", folio="12 3", cfdi_uuid=None, stamped_at=None)

        self.assertEqual(
            invoice_document_filename(record, "pdf"),
            "Factura_MYC_Borrador_12_3.pdf",
        )
        self.assertEqual(
            invoice_document_filename(record, "xml"),
            "Factura_MYC_Borrador_12_3.xml",
        )

    def test_fiscal_xml_reads_existing_valid_document_with_public_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "internal-provider-name.xml"
            source.write_bytes(b'<?xml version="1.0"?><cfdi:Comprobante xmlns:cfdi="urn:cfdi" Serie="MYCF" Folio="3"/>')
            with patch("app.services.invoice_pdfs.get_invoice", return_value=invoice()), patch(
                "app.services.invoice_pdfs.resolve_storage_path", return_value=source
            ):
                content, filename = get_invoice_fiscal_xml(object(), 41)

        self.assertIn(b"Comprobante", content)
        self.assertEqual(filename, "Factura_MYC_MYCF-3.xml")

    def test_provider_document_route_uses_public_xml_identity(self):
        from app.services import invoice_pdfs
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "provider.xml"
            source.write_text(stamped_xml())
            for kind in ("pdf", "xml"):
                with patch("app.routers.invoices.get_invoice", return_value=invoice()), \
                     patch("app.routers.invoices.read_document", return_value=(b"content", "provider-name", "application/" + kind)), \
                     patch.object(invoice_pdfs, "resolve_storage_path", return_value=source):
                    response = facturama_document_route(41, kind, object(), object())
                self.assertEqual(response.headers["content-disposition"], f'attachment; filename="Factura_MYC_MYCF-3.{kind}"')

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


class DraftInvoicePrintTests(unittest.TestCase):
    SNAPSHOT = {
        "receiver_rfc": "AAA010101AAA",
        "receiver_legal_name": "Cliente Congelado SA",
        "receiver_tax_regime_code": "626",
        "receiver_fiscal_postal_code": "44950",
        "receiver_cfdi_use_code": "G03",
    }

    def _render(self, cfdi_uuid=None, stamped_at=None, xml_path=None):
        from app.services import invoice_pdfs

        item = SimpleNamespace(
            id=987654, quotation_item_id=876543, description="Calibración", quantity=1, unit_price=1, subtotal=1, total=1.16,
            sat_key="81141601", sat_unit="E48", tax_object="02",
            tax_rate=16, tax_total=0.16, line_total=1.16, discount_total=0, notes=None,
        )
        inv = invoice(
            facturama_xml_path=xml_path, fiscal_snapshot=self.SNAPSHOT, cfdi_uuid=cfdi_uuid, stamped_at=stamped_at, usage_cfdi=None,
            payment_method="PUE", payment_form="03", currency="MXN", items=[item],
            fiscal_client=None, client=SimpleNamespace(rfc="OTRO", legal_name="Cliente Vivo", commercial_name=None),
            total=1.16, subtotal=1, tax_total=0.16, discount_total=0, withholding_total=0, issued_on=None, observations=None,
        )
        settings = SimpleNamespace(emitter_data={"rfc": "EMI010101AAA", "legal_name": "MYC"})
        tpl = SimpleNamespace(company_name="MYC", company_address="Calle 1", company_phone="", company_email="", company_website="")
        inst = SimpleNamespace(legal_name="MYC", address="", phone="", email="")
        with patch.object(invoice_pdfs, "get_or_create_quotation_template", return_value=tpl), \
             patch.object(invoice_pdfs, "get_or_create_institutional_configuration", return_value=inst), \
             patch.object(invoice_pdfs, "_catalog_entry", side_effect=lambda db, c, code: {"code": code or "", "name": ""}):
            context = invoice_pdfs._public_invoice_context(object(), inv, settings)
        return context, invoice_pdfs.env.get_template("invoice_pdf.html").render(**context)

    def test_draft_uses_snapshot_receiver_values(self):
        context, html = self._render()
        receiver = context["fiscal"]["receiver"]
        self.assertEqual(receiver["rfc"], "AAA010101AAA")
        self.assertEqual(receiver["name"], "Cliente Congelado SA")
        self.assertEqual(receiver["tax_regime"]["code"], "626")
        self.assertEqual(receiver["postal_code"], "44950")
        self.assertEqual(receiver["cfdi_use"]["code"], "G03")
        self.assertIn("44950", html)
        self.assertNotIn("Cliente Vivo", html)

    def test_draft_is_presented_as_unstamped(self):
        context, html = self._render()
        self.assertFalse(context["is_stamped"])
        self.assertIsNone(context["qr_uri"])
        self.assertIn("BORRADOR · SIN TIMBRAR", html)
        self.assertIn("Borrador de factura", html)
        self.assertIn("Documento sin timbrar", html)
        self.assertIn("Documento preliminar. No constituye un CFDI timbrado.", html)
        for forbidden in ("Representación impresa de un CFDI", "Sello digital", "Cadena original", "QR pendiente"):
            self.assertNotIn(forbidden, html)

    def test_stamped_invoice_keeps_cfdi_presentation(self):
        from datetime import datetime, timezone

        context, html = self._render(
            cfdi_uuid="UUID-1234", stamped_at=datetime(2026, 7, 15, tzinfo=timezone.utc)
        )
        self.assertTrue(context["is_stamped"])
        self.assertIn("Factura electrónica", html)
        self.assertIn("Representación impresa de un CFDI", html)
        self.assertIn("UUID-1234", html)
        self.assertIn("Sello digital del CFDI", html)
        self.assertNotIn("BORRADOR", html)


    def test_xml_identity_controls_stamped_pdf_and_filenames(self):
        from app.services import invoice_pdfs
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "provider.xml"
            source.write_text('<cfdi:Comprobante xmlns:cfdi="urn:cfdi" Serie="MYCF" Folio="3"/>')
            with patch.object(invoice_pdfs, "resolve_storage_path", return_value=source):
                context, html = self._render("UUID-1234", "2026-10-01", str(source))
                self.assertEqual(context["fiscal"]["series"], "MYCF")
                self.assertEqual(context["fiscal"]["folio"], "3")
                self.assertIn('<strong>MYCF-3</strong>', html)
                self.assertNotIn('F-MYCF-2026-0002', html)
                for extension in ("pdf", "xml"):
                    self.assertEqual(invoice_document_filename(context["invoice"], extension), f"Factura_MYC_MYCF-3.{extension}")

    def test_draft_has_internal_reference_without_fiscal_identity(self):
        context, html = self._render()
        self.assertEqual(context["fiscal"]["series"], "")
        self.assertEqual(context["fiscal"]["folio"], "")
        self.assertNotIn('Serie / Folio', html)
        self.assertIn('Referencia interna MYC', html)
        self.assertIn('MYCF-2026-0002', html)

    def test_missing_xml_never_substitutes_internal_identity(self):
        context, html = self._render("UUID-1234", "2026-10-01")
        self.assertIn('No disponible en XML', html)
        self.assertEqual(invoice_document_filename(context["invoice"], "pdf"), "Factura_MYC_CFDI_UUID-1234.pdf")


    def test_concept_identification_comes_only_from_xml(self):
        from app.services import invoice_pdfs
        for attribute, expected in [('NoIdentificacion="CAL-001"', 'CAL-001'), ('', '—')]:
            with self.subTest(attribute=attribute), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "cfdi.xml"
                source.write_text(f'<Comprobante Serie="MYCF" Folio="3"><Conceptos><Concepto {attribute}/></Conceptos></Comprobante>')
                with patch.object(invoice_pdfs, "resolve_storage_path", return_value=source):
                    context, html = self._render("UUID-1234", "2026-10-01", str(source))
                self.assertEqual(context["item_rows"][0]["no_identification"], expected if attribute else "")
                self.assertIn(f'<td>{expected}</td>', html)
                self.assertNotIn('<td>987654</td>', html)
                self.assertNotIn('<td>876543</td>', html)
                self.assertNotIn('<td>1</td>\n          <td>1</td>', html)


    def test_rendered_pdf_preserves_identity_stamps_qr_and_repeated_headers(self):
        import io
        from copy import deepcopy
        from pypdf import PdfReader
        from weasyprint import HTML
        from app.services import invoice_pdfs

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "cfdi.xml"
            source.write_text(stamped_xml())
            with patch.object(invoice_pdfs, "resolve_storage_path", return_value=source):
                context, _ = self._render("UUID-1234", "2026-10-01", str(source))
            assert context["fiscal"]["uuid"] == "f6445b4b-3130-4803-adfc-b410494b8a1f"
            assert context["qr_uri"].startswith('data:image/png;base64,')
            for count in (1, 35):
                with self.subTest(concepts=count):
                    context["item_rows"] = [deepcopy(context["item_rows"][0]) for _ in range(count)]
                    for index, row in enumerate(context["item_rows"]):
                        row["item"].description = f'Calibración de instrumento {index + 1:03d}'
                    html = invoice_pdfs.env.get_template("invoice_pdf.html").render(**context)
                    reader = PdfReader(io.BytesIO(HTML(string=html).write_pdf()))
                    pages = [page.extract_text() for page in reader.pages]
                    text = '\n'.join(pages)
                    assert 'MYCF-3' in text
                    assert 'F-MYCF-2026-0002' not in text
                    assert 'f6445b4b-3130-4803-adfc-b410494b8a1f' in text
                    assert 'SELLO DIGITAL DEL CFDI' in text.upper()
                    assert 'SELLO DIGITAL DEL SAT' in text.upper()
                    assert 'CADENA ORIGINAL' in text.upper()
                    assert 'Verificación SAT' in text
                    assert f'instrumento {count:03d}' in text
                    assert 'BORRADOR' not in text
                    for page in pages:
                        if 'Calibración de instrumento' in page:
                            assert 'No. ident.'.upper() in page.upper()
                    assert len(pages) == 1 if count == 1 else len(pages) > 1


def stamped_xml():
    seal = 'AbCdEf0123456789' * 22
    return f'''<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
        xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" Serie="MYCF" Folio="3"
        Sello="{seal}" NoCertificado="30001000000500003416" LugarExpedicion="44950">
      <cfdi:Emisor Rfc="EMI010101AAA" Nombre="METROLOGÍA Y SERVICIOS MYC" RegimenFiscal="601"/>
      <cfdi:Conceptos><cfdi:Concepto ClaveProdServ="81141601" ClaveUnidad="E48" ObjetoImp="02" NoIdentificacion="CAL-001"/></cfdi:Conceptos>
      <cfdi:Complemento><tfd:TimbreFiscalDigital Version="1.1" UUID="f6445b4b-3130-4803-adfc-b410494b8a1f"
        FechaTimbrado="2026-10-01T12:00:00" RfcProvCertif="PAC010101AAA" SelloCFD="{seal}"
        NoCertificadoSAT="30001000000500003417" SelloSAT="{seal}"/></cfdi:Complemento>
    </cfdi:Comprobante>'''
