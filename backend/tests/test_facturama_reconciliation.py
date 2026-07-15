import unittest
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.services.facturama.invoices import (
    _confirmed_reconciliation_payload,
    _find_response_value,
    _matches_reconciliation,
)


def invoice_for_match():
    return SimpleNamespace(
        total=Decimal("1.16"),
        fiscal_snapshot={"receiver_rfc": "AECS020326TK6"},
    )


class FacturamaReconciliationTests(unittest.TestCase):
    def test_extracts_identifiers_from_provider_wrappers(self):
        payload = {"Data": {"id": "provider-id", "UUID": "provider-uuid"}}
        self.assertEqual(_find_response_value(payload, "Id", "id"), "provider-id")
        self.assertEqual(_find_response_value(payload, "Uuid", "UUID", "uuid"), "provider-uuid")

    def test_unique_candidate_requires_all_strict_fields(self):
        invoice = invoice_for_match()
        reference = datetime(2026, 7, 15, 19, 46, 21, tzinfo=timezone.utc)
        candidate = {
            "Serie": "MYCF",
            "Folio": "1",
            "Receiver": {"Rfc": "AECS020326TK6"},
            "Total": 1.16,
            "Date": "2026-07-15T19:46:21+00:00",
        }
        self.assertTrue(_matches_reconciliation(invoice, candidate, series="MYCF", folio="1", reference_time=reference))
        candidate["Total"] = 2
        self.assertFalse(_matches_reconciliation(invoice, candidate, series="MYCF", folio="1", reference_time=reference))

    def test_candidate_outside_time_window_is_not_reconciled(self):
        invoice = invoice_for_match()
        reference = datetime(2026, 7, 15, 19, 46, 21, tzinfo=timezone.utc)
        candidate = {
            "Serie": "MYCF",
            "Folio": "1",
            "Rfc": "AECS020326TK6",
            "Total": "1.16",
            "Date": "2026-07-15T20:10:00+00:00",
        }
        self.assertFalse(_matches_reconciliation(invoice, candidate, series="MYCF", folio="1", reference_time=reference))

    def test_confirmed_reconciliation_requires_remote_match_and_marks_payload(self):
        provider = {
            "Id": "provider-id",
            "CfdiType": "ingreso",
            "Folio": "1",
            "Serie": "MYCF",
            "Uuid": "provider-uuid",
            "Date": "2026-07-15T13:46:21",
            "Subtotal": 1,
            "Total": 1.16,
            "Status": "active",
            "Issuer": {"Rfc": "MSM180712686"},
            "Receiver": {"Rfc": "AECS020326TK6"},
        }
        confirmation = {
            "facturama_id": "provider-id",
            "uuid": "provider-uuid",
            "cfdi_type": "I",
            "series": "MYCF",
            "folio": "1",
            "receiver_rfc": "AECS020326TK6",
            "subtotal": Decimal("1.00"),
            "total": Decimal("1.16"),
            "issued_at": datetime(2026, 7, 15, 13, 46, 21, tzinfo=ZoneInfo("America/Mexico_City")),
            "status": "active",
        }
        reconciled = _confirmed_reconciliation_payload(
            invoice_for_match(), provider, confirmation, xml_uuid="provider-uuid"
        )
        self.assertTrue(reconciled["reconciled"])
        self.assertEqual(reconciled["Folio"], "1")
        self.assertEqual(reconciled["Uuid"], "provider-uuid")
