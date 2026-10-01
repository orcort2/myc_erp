import asyncio
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.models.invoice import FacturamaInvoiceAttempt
from app.services.facturama import invoices as svc


def make_invoice(**values):
    payload = dict(
        id=7, is_active=True, cfdi_uuid=None, facturama_id=None, status="draft",
        review_required=False, facturama_environment=None, facturama_request_json=None,
        facturama_response_json=None, facturama_http_status=None, facturama_error_message=None,
        facturama_attempted_at=None, stamped_at=None, fiscal_snapshot={"receiver_rfc": "AAA010101AAA"},
        total=Decimal("1.16"), balance_due=Decimal("1.16"), amount_paid=Decimal("0.00"),
    )
    payload.update(values)
    return SimpleNamespace(**payload)


def make_settings(environment):
    return SimpleNamespace(facturama_environment=environment, facturama_enabled=True)


def make_client(environment, uuid="uuid-1"):
    client = MagicMock()
    client.environment = environment
    client.post = AsyncMock(return_value=SimpleNamespace(status_code=200))
    client.get = AsyncMock()
    return client


def run_issue(environment, invoice=None):
    invoice = invoice or make_invoice()
    attempts = []
    db = MagicMock()
    db.scalar.side_effect = [invoice, None, 0]
    db.get.side_effect = lambda model, _id: invoice if model.__name__ == "Invoice" else attempts[0]
    db.add.side_effect = attempts.append
    audits = []
    client = make_client(environment)
    diagnostics = {"status_code": 200, "json": {"Id": "fid", "Uuid": "u-1", "Date": "2026-07-15T10:00:00"}, "text": "", "headers": {}}
    health = SimpleNamespace(status="connected")
    with patch.object(svc, "FacturamaHealthService") as health_cls, \
         patch.object(svc, "map_invoice", return_value={"Serie": "A"}), \
         patch.object(svc, "response_diagnostics", return_value=diagnostics), \
         patch.object(svc, "write_audit_log", side_effect=lambda *a, **k: audits.append(k)), \
         patch.object(svc, "recover_documents", new=AsyncMock(return_value=invoice)):
        health_cls.return_value.check = AsyncMock(return_value=health)
        asyncio.run(svc.issue_invoice(db, 7, user_id=1, client=client, settings=make_settings(environment)))
    return invoice, attempts, audits, client, db


class IssueEnvironmentTests(unittest.TestCase):
    def test_sandbox_still_issues(self):
        invoice, _, audits, _, _ = run_issue("sandbox")
        self.assertEqual(invoice.status, "issued")
        self.assertEqual(invoice.facturama_environment, "sandbox")
        self.assertTrue(all(a["new_values"]["environment"] == "sandbox" for a in audits if "environment" in a["new_values"]))

    def test_production_is_not_blocked_and_persists_real_environment(self):
        invoice, attempts, audits, _, _ = run_issue("production")
        self.assertEqual(invoice.status, "issued")
        self.assertEqual(invoice.facturama_environment, "production")
        environments = [a["new_values"]["environment"] for a in audits if "environment" in a["new_values"]]
        self.assertEqual(sorted(a["action"] for a in audits if "environment" in a["new_values"]), ["facturama.issue_attempt", "facturama.issue_succeeded"])
        self.assertEqual(set(environments), {"production"})
        self.assertIsInstance(attempts[0], FacturamaInvoiceAttempt)


class RejectedRetryEnvironmentTests(unittest.TestCase):
    def _rejected(self):
        return make_invoice(status="issue_rejected", facturama_environment="sandbox")

    def test_rejected_sandbox_retry_in_production_is_blocked(self):
        invoice = self._rejected()
        with self.assertRaises(HTTPException) as ctx:
            run_issue("production", invoice)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail["code"], "facturama_environment_mismatch")
        self.assertEqual(invoice.status, "issue_rejected")
        self.assertEqual(invoice.facturama_environment, "sandbox")
        self.assertIsNone(invoice.facturama_request_json)
        self.assertIsNone(invoice.facturama_attempted_at)

    def test_blocked_retry_makes_no_request_attempt_or_commit(self):
        invoice = self._rejected()
        with patch.object(svc, "FacturamaHealthService") as health_cls, \
             patch.object(svc, "write_audit_log") as audit:
            health_cls.return_value.check = AsyncMock(return_value=SimpleNamespace(status="connected"))
            db = MagicMock()
            db.scalar.side_effect = [invoice]
            client = make_client("production")
            with self.assertRaises(HTTPException):
                asyncio.run(svc.issue_invoice(db, 7, user_id=1, client=client, settings=make_settings("production")))
        client.post.assert_not_called()
        db.add.assert_not_called()
        db.commit.assert_not_called()
        audit.assert_not_called()

    def test_rejected_sandbox_retry_in_sandbox_is_still_allowed(self):
        invoice, attempts, _, client, _ = run_issue("sandbox", self._rejected())
        self.assertEqual(invoice.status, "issued")
        self.assertEqual(invoice.facturama_environment, "sandbox")
        client.post.assert_called_once()
        self.assertEqual(len(attempts), 1)


class ReconcileEnvironmentGuardTests(unittest.TestCase):
    def _reconcile(self, persisted, active):
        invoice = make_invoice(status="issue_unknown", facturama_environment=persisted)
        db = MagicMock()
        db.scalar.return_value = invoice
        client = make_client(active)
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(svc.reconcile_invoice(db, 7, user_id=1, client=client))
        return ctx.exception, invoice, db, client

    def test_mismatch_fails_without_requests_or_changes(self):
        for persisted, active in (("sandbox", "production"), ("production", "sandbox")):
            exc, invoice, db, client = self._reconcile(persisted, active)
            self.assertEqual(exc.detail["code"], "facturama_environment_mismatch")
            self.assertEqual(invoice.status, "issue_unknown")
            self.assertEqual(invoice.facturama_environment, persisted)
            client.get.assert_not_called()
            client.post.assert_not_called()
            db.commit.assert_not_called()

    def test_legacy_row_without_environment_is_treated_as_sandbox(self):
        exc, invoice, _, client = self._reconcile(None, "production")
        self.assertEqual(exc.detail["code"], "facturama_environment_mismatch")
        self.assertIsNone(invoice.facturama_environment)
        client.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
