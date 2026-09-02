import unittest
from datetime import datetime
from types import SimpleNamespace

from app.schemas.field_sheet import FieldSheetCreate, FieldSheetRead, FieldSheetResultUpdate
from app.schemas.client import ClientCertificateProfileCreate
from app.models.client import ClientCertificateProfile
from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.services.institutional_configurations import DEFAULT_INSTITUTIONAL_VALUES
from app.services.field_sheets import _apply_results_updates, _client_address


OFFICIAL_TEMPLATE_KEYS = {
    "anemometro", "angulimetro", "bascula", "calibradores", "cronometro",
    "detector_gases", "dimensional", "electrica", "flujo", "general",
    "maestro_altura", "par_torsional", "pesas", "presion", "reglas",
    "sonido", "tacometro", "temperatura", "tld_6_canales", "tld",
    "valvula_seguridad", "verificacion_equipos", "copa",
}


class FieldSheetOperationalContractTests(unittest.TestCase):
    def test_client_certificate_profile_contract_keeps_reusable_certificate_data(self):
        payload = ClientCertificateProfileCreate(
            label="Planta Guadalajara",
            company="Empresa Demo",
            address="Domicilio alterno 123",
            attention="Atención Manual",
            is_default=True,
        )
        self.assertEqual(payload.company, "Empresa Demo")
        self.assertTrue(payload.is_default)
        self.assertIn("client_id", ClientCertificateProfile.__table__.columns)
        self.assertIn("deleted_at", ClientCertificateProfile.__table__.columns)

    def test_create_contract_accepts_the_23_official_snapshots(self):
        for key in OFFICIAL_TEMPLATE_KEYS:
            payload = FieldSheetCreate(
                equipment_id=1,
                template_key=key,
                template_version=1,
                template_snapshot={"key": key, "template_key": key, "version": 1, "blocks": []},
            )
            self.assertEqual(payload.template_key, key)
            self.assertEqual(payload.template_snapshot["template_key"], key)

    def test_capture_values_are_part_of_the_persistence_contract(self):
        payload = FieldSheetCreate(
            equipment_id=1,
            template_key="electrica",
            capture_values={"instrument": "Multímetro capturado", "electrical_unit_1": "V"},
        )
        self.assertEqual(payload.capture_values["instrument"], "Multímetro capturado")
        self.assertEqual(payload.capture_values["electrical_unit_1"], "V")

    def test_legacy_null_capture_values_are_serialized_as_an_empty_object(self):
        sheet = FieldSheet(
            id=1,
            equipment_id=1,
            template_key="anemometro",
            status="draft",
            is_active=True,
            consider_equipment_deviations=False,
            certificate_client_mode="billing",
            apply_certificate_client_to_order=False,
            capture_values=None,
            # Fase 6: revision_number/is_current son NOT NULL con default a
            # nivel Python (aplican al INSERT real, no a un objeto en memoria
            # nunca persistido) -- mismo motivo por el que is_active ya se
            # pasaba explícito arriba.
            revision_number=1,
            is_current=True,
        )
        sheet.created_at = datetime.now()
        sheet.updated_at = datetime.now()
        serialized = FieldSheetRead.model_validate(sheet)
        self.assertEqual(serialized.capture_values, {})

    def test_result_row_without_id_updates_by_section_and_row(self):
        sheet = FieldSheet(equipment_id=1, template_key="anemometro")
        existing = FieldSheetResult(id=10, section_key="measurements", row_number=1, row_data={})
        sheet.results_rows = [existing]
        _apply_results_updates(
            sheet,
            [FieldSheetResultUpdate(section_key="measurements", row_number=1, row_data={"ibc_1": "12.3"})],
        )
        self.assertIs(sheet.results_rows[0], existing)
        self.assertEqual(existing.row_data["ibc_1"], "12.3")

    def test_default_institution_is_complete_and_not_simulated(self):
        serialized = " ".join(str(value or "") for value in DEFAULT_INSTITUTIONAL_VALUES.values()).lower()
        for field in ("legal_name", "address", "phone", "email", "logo_path", "document_code", "initial_revision"):
            self.assertTrue(DEFAULT_INSTITUTIONAL_VALUES[field])
        self.assertNotIn("simulad", serialized)
        self.assertNotIn("myc.test", serialized)
        self.assertNotIn("33 0000 0000", serialized)

    def test_billing_client_address_is_built_from_master_data(self):
        client = SimpleNamespace(
            street="Puerto Ensenada",
            exterior_number="1075",
            interior_number=None,
            neighborhood="Col. Miramar",
            locality=None,
            municipality="Zapopan",
            city="Zapopan",
            state="Jalisco",
            postal_code="45060",
            country="México",
        )
        self.assertEqual(
            _client_address(client),
            "Puerto Ensenada, 1075, Col. Miramar, Zapopan, Zapopan, Jalisco, 45060, México",
        )


if __name__ == "__main__":
    unittest.main()
