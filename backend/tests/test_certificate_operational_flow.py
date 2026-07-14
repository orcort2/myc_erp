import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.certificates import ALLOWED_TRANSITIONS, get_service_order_release_readiness


class CertificateOperationalFlowTests(unittest.TestCase):
    def _db_with(self, *, requires_payment=True, invoices=()):
        db = MagicMock()
        db.get.return_value = SimpleNamespace(id=7, is_active=True, requires_payment=requires_payment)
        db.scalars.return_value.all.return_value = list(invoices)
        return db

    def test_authenticated_is_a_distinct_state_before_release(self):
        self.assertIn("authenticated", ALLOWED_TRANSITIONS["quality_approved"])
        self.assertEqual(ALLOWED_TRANSITIONS["authenticated"], {"released_to_client", "suspended"})

    def test_quality_sequence_has_no_independent_rejection_branch(self):
        self.assertIn("match_validated", ALLOWED_TRANSITIONS["ready_for_quality"])
        self.assertEqual(
            ALLOWED_TRANSITIONS["match_validated"] & {"quality_approved", "correction_requested"},
            {"quality_approved", "correction_requested"},
        )

    def test_release_is_blocked_when_payment_is_required_without_paid_invoice(self):
        readiness = get_service_order_release_readiness(self._db_with(invoices=[]), 7)
        self.assertFalse(readiness["release_allowed"])
        self.assertEqual(readiness["payment_status"], "pending")
        self.assertIn("factura", readiness["reason"].lower())

    def test_release_is_allowed_when_all_active_invoices_are_paid(self):
        readiness = get_service_order_release_readiness(
            self._db_with(invoices=[SimpleNamespace(status="paid"), SimpleNamespace(status="paid")]),
            7,
        )
        self.assertTrue(readiness["release_allowed"])
        self.assertEqual(readiness["payment_status"], "paid")

    def test_release_does_not_require_payment_when_order_is_exempt(self):
        readiness = get_service_order_release_readiness(self._db_with(requires_payment=False), 7)
        self.assertTrue(readiness["release_allowed"])
        self.assertEqual(readiness["payment_status"], "not_required")


if __name__ == "__main__":
    unittest.main()
