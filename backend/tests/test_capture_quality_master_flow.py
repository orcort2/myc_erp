import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.services.certificates import capture_master_readiness, quality_approve, send_to_quality


def build_certificate(status="capture_in_progress"):
    return SimpleNamespace(
        id=1,
        service_order_id=1,
        status=status,
        equipment=SimpleNamespace(
            certificate_master_document_id=8,
            certificate_master_version_id=1,
            certificate_template_path_snapshot="certificate-masters/8/master.xlsx",
        ),
        service_order=SimpleNamespace(status="capture"),
        sent_to_quality_at=None,
        sent_to_quality_by_id=None,
        capture_started_at=None,
        capture_started_by_id=None,
        quality_reviewed_at=None,
        quality_reviewed_by_id=None,
        quality_rejection_reason=None,
        match_status="pending",
    )


def capture_file(validation):
    return SimpleNamespace(
        id=7,
        original_filename="Master_MYCA-07-2026-0001.xlsx",
        stored_path="capture/1/7-Master_MYCA-07-2026-0001.xlsx",
        identification_status="identified",
        validation_results=validation,
        uploaded_by_id=1,
        created_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
    )


class CaptureQualityMasterFlowTests(unittest.TestCase):
    def test_identified_master_with_warnings_is_ready(self):
        db = MagicMock()
        db.scalar.return_value = capture_file({
            "cliente": {"status": "no_encontrado"},
            "proxima_calibracion": {"status": "no_encontrado"},
            "servicio": {"status": "no_encontrado"},
        })
        readiness = capture_master_readiness(db, build_certificate())
        self.assertTrue(readiness["ready"])
        self.assertEqual(len(readiness["warnings"]), 3)
        self.assertEqual(readiness["mismatches"], [])

    def test_unidentified_master_is_blocked(self):
        db = MagicMock()
        db.scalar.return_value = None
        readiness = capture_master_readiness(db, build_certificate())
        self.assertFalse(readiness["ready"])
        self.assertIn("no está identificado", readiness["reason"])

    def test_blocking_mismatch_is_blocked(self):
        db = MagicMock()
        db.scalar.return_value = capture_file({"folio": {"status": "mismatch"}})
        readiness = capture_master_readiness(db, build_certificate())
        self.assertFalse(readiness["ready"])
        self.assertEqual(len(readiness["mismatches"]), 1)

    def test_send_to_quality_persists_actor_date_audit_and_master_reference(self):
        db = MagicMock()
        current = build_certificate()
        db.scalar.return_value = capture_file({"cliente": {"status": "no_encontrado"}})
        with (
            patch("app.services.certificates.get_certificate", return_value=current),
            patch("app.services.certificates.write_audit_log") as audit,
        ):
            updated = send_to_quality(db, current.id, user_id=9)
        self.assertEqual(updated.status, "quality_review")
        self.assertEqual(updated.sent_to_quality_by_id, 9)
        self.assertIsNotNone(updated.sent_to_quality_at)
        self.assertEqual(updated.service_order.status, "quality_review")
        self.assertEqual(updated.match_status, "pending")
        audit.assert_called_once()
        call = audit.call_args.kwargs
        self.assertEqual(call["user_id"], 9)
        self.assertEqual(call["previous_values"], {"status": "capture_in_progress"})
        self.assertEqual(call["new_values"]["status"], "quality_review")
        self.assertEqual(call["new_values"]["capture_master_file_id"], 7)

    def test_quality_can_approve_the_ready_master_without_pdf_or_pdf_match(self):
        db = MagicMock()
        current = build_certificate(status="quality_review")
        db.scalar.return_value = capture_file({"cliente": {"status": "no_encontrado"}})
        with (
            patch("app.services.certificates.get_certificate", return_value=current),
            patch("app.services.certificates.write_audit_log") as audit,
        ):
            updated = quality_approve(db, current.id, user_id=4)
        self.assertEqual(updated.status, "quality_approved")
        self.assertEqual(updated.quality_reviewed_by_id, 4)
        self.assertEqual(updated.match_status, "pending")
        self.assertEqual(audit.call_args.kwargs["new_values"]["capture_master_file_id"], 7)

    def test_send_to_quality_rejects_a_blocked_master(self):
        db = MagicMock()
        current = build_certificate()
        db.scalar.return_value = capture_file({"folio": {"status": "mismatch"}})
        with patch("app.services.certificates.get_certificate", return_value=current):
            with self.assertRaisesRegex(HTTPException, "diferencias bloqueantes"):
                send_to_quality(db, current.id, user_id=9)

    def test_historical_capture_pending_with_identified_master_is_normalized_and_sent(self):
        db = MagicMock()
        current = build_certificate(status="capture_pending")
        db.scalar.return_value = capture_file({"cliente": {"status": "no_encontrado"}})
        with (
            patch("app.services.certificates.get_certificate", return_value=current),
            patch("app.services.certificates.write_audit_log") as audit,
        ):
            updated = send_to_quality(db, current.id, user_id=9)
        self.assertEqual(updated.status, "quality_review")
        self.assertEqual(audit.call_count, 2)
        self.assertEqual(audit.call_args_list[0].kwargs["previous_values"], {"status": "capture_pending"})
        self.assertEqual(audit.call_args_list[0].kwargs["new_values"]["status"], "capture_in_progress")
        self.assertEqual(audit.call_args_list[1].kwargs["previous_values"], {"status": "capture_in_progress"})
        self.assertEqual(audit.call_args_list[1].kwargs["new_values"]["status"], "quality_review")


if __name__ == "__main__":
    unittest.main()
