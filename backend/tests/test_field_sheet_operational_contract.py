import unittest
from types import SimpleNamespace

from app.schemas.field_sheet import FieldSheetCreate
from app.schemas.client import ClientCertificateProfileCreate
from app.models.client import ClientCertificateProfile
from app.services.institutional_configurations import DEFAULT_INSTITUTIONAL_VALUES
from app.services.field_sheets import _client_address


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
