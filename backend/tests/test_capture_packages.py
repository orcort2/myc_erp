import tempfile
import unittest
from datetime import date
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.models.controlled_document import ControlledDocument, ControlledDocumentVersion
from app.services.capture_packages import (
    CAPTURE_PACKAGE_FIELD_SHEET_STATUSES,
    EligibleItem,
    _package_member_prefix,
    _render_pair,
    _is_macos_auxiliary,
    _mark_capture_started,
    _validation_issue_keys,
    eligibility_for_equipment,
)


class FakeDb:
    def __init__(self, master, version):
        self.master = master
        self.version = version
        self.added = []

    def get(self, model, record_id):
        if model is ControlledDocument and record_id == 8:
            return self.master
        if model is ControlledDocumentVersion and record_id == 1:
            return self.version
        return None

    def add(self, item):
        self.added.append(item)


def build_case(status, template_path):
    certificate = SimpleNamespace(id=1, is_active=True, expected_folio="MYCA-07-2026-0001", folio="MYCA-07-2026-0001")
    field_sheet = SimpleNamespace(id=1, is_active=True, status=status, next_calibration_date=date(2027, 9, 28))
    equipment = SimpleNamespace(
        id=1,
        calibration_scope="accredited_iso_17025",
        field_sheets=[field_sheet],
        certificates=[certificate],
        name="TERMÓMETRO",
        internal_id="TER-01",
        certificate_master_document_id=8,
        certificate_master_version_id=1,
        certificate_template_path_snapshot="certificate-masters/8/master.xlsx",
        certificate_template_checksum_snapshot=sha256(template_path.read_bytes()).hexdigest(),
        certificate_template_filename_snapshot="CERTIFICADO MASTER TEMPERATURA.xlsx",
    )
    certificate.equipment = equipment
    return equipment, field_sheet, certificate


class CapturePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.template_path = Path(self.temp_dir.name) / "master.xlsx"
        self.template_path.write_bytes(b"xlsx-test")
        self.db = FakeDb(
            SimpleNamespace(status="active"),
            SimpleNamespace(status="active", expires_on=date(2027, 7, 21)),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_completed_review_and_approved_are_eligible_for_capture_package(self):
        self.assertEqual(CAPTURE_PACKAGE_FIELD_SHEET_STATUSES, {"completed", "under_review", "approved"})
        for status in CAPTURE_PACKAGE_FIELD_SHEET_STATUSES:
            with self.subTest(status=status):
                equipment, _, _ = build_case(status, self.template_path)
                with patch("app.services.capture_packages.resolve_storage_path", return_value=self.template_path):
                    item = eligibility_for_equipment(self.db, equipment)
                self.assertTrue(item.ready)
                self.assertIsNone(item.reason)

    def test_in_progress_sheet_remains_blocked(self):
        equipment, _, _ = build_case("in_progress", self.template_path)
        item = eligibility_for_equipment(self.db, equipment)
        self.assertFalse(item.ready)
        self.assertEqual(item.reason, "La Hoja de Campo no está completada")

    def test_package_uses_ets_ot_certificate_hierarchy_and_institutional_names(self):
        equipment, field_sheet, certificate = build_case("under_review", self.template_path)
        order = SimpleNamespace(id=1, folio="OSMYC-26-07-0001")
        work_order = SimpleNamespace(id=1, work_order_number=7002)
        prefix = _package_member_prefix(order, work_order, certificate, include_ets=True)
        self.assertEqual(prefix, "OSMYC-26-07-0001/OT-7002/MYCA-07-2026-0001")

        item = EligibleItem(equipment, field_sheet, certificate)
        with (
            patch("app.services.capture_packages.resolve_storage_path", return_value=self.template_path),
            patch("app.services.capture_packages.generate_field_sheet_pdf", return_value=(b"pdf-test", "ignored.pdf")),
        ):
            pdf_name, pdf, excel_name, excel = _render_pair(self.db, item)
        self.assertEqual(pdf_name, "Hoja_Campo_MYCA-07-2026-0001.pdf")
        self.assertEqual(excel_name, "Master_MYCA-07-2026-0001.xlsx")
        self.assertEqual(pdf, b"pdf-test")
        self.assertEqual(excel, b"xlsx-test")
        self.assertEqual(equipment.certificate_template_filename_snapshot, "CERTIFICADO MASTER TEMPERATURA.xlsx")

    def test_macos_auxiliary_files_are_ignored(self):
        for filename in ("._Master.xlsx", ".DS_Store", "__MACOSX/OT/Master.xlsx", "OT/__MACOSX/._Master.xlsx"):
            with self.subTest(filename=filename):
                self.assertTrue(_is_macos_auxiliary(filename))
        self.assertFalse(_is_macos_auxiliary("OSMYC/OT-7002/Master_MYCA-07-2026-0001.xlsx"))

    def test_validation_issues_distinguish_warnings_from_mismatches(self):
        warnings, mismatches = _validation_issue_keys({
            "cliente": {"status": "no_encontrado"},
            "servicio": {"status": "mismatch"},
            "folio": {"status": "coincide"},
        })
        self.assertEqual(warnings, ["cliente"])
        self.assertEqual(mismatches, ["servicio"])

    def test_identified_master_starts_capture_with_actor_and_audit(self):
        certificate = SimpleNamespace(
            id=1,
            status="capture_pending",
            capture_started_at=None,
            capture_started_by_id=None,
        )
        _mark_capture_started(self.db, certificate, user_id=7, filename="Master_MYCA-07-2026-0001.xlsx")
        self.assertEqual(certificate.status, "capture_in_progress")
        self.assertEqual(certificate.capture_started_by_id, 7)
        self.assertIsNotNone(certificate.capture_started_at)
        self.assertEqual(len(self.db.added), 1)
        self.assertEqual(self.db.added[0].action, "certificate.capture_started")
        self.assertEqual(self.db.added[0].user_id, 7)


if __name__ == "__main__":
    unittest.main()
