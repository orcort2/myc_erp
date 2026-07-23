import unittest
from datetime import datetime, timezone

from pydantic import ValidationError

from app.schemas.catalog_item import CatalogItemCreate, CatalogItemOut
from app.schemas.controlled_document import (
    DocumentInterpretationCreate,
    TechnicalProfileCreate,
)
from app.schemas.equipment import EquipmentCreate
from app.schemas.quotation import QuotationItemCreate
from app.schemas.service_order import ServiceOrderItemCreate
from app.schemas.service_scope import ACCREDITATION_SCOPE_VALUES
from app.services.service_order_certificate_capacity import (
    calibration_scope_from_certificate_type,
    certificate_type_from_scope,
)


CANONICAL_SCOPES = (
    "accredited_iso_17025",
    "traceable",
    "accredited_linked_lab",
)
DOCUMENT_LABEL = "Certificado / Certificate: L25-313"


class ServiceScopeContractTests(unittest.TestCase):
    def catalog_payload(self, calibration_scope: str) -> dict:
        return {
            "item_type": "service",
            "commodity": "calibration",
            "category": "Calibracion",
            "name": "Calibración de prueba",
            "origin_currency": "MXN",
            "calibration_scope": calibration_scope,
        }

    def test_accreditation_contract_exposes_only_the_three_business_keys(self):
        self.assertEqual(ACCREDITATION_SCOPE_VALUES, CANONICAL_SCOPES)

    def test_catalog_accepts_each_canonical_accreditation_scope(self):
        for scope in CANONICAL_SCOPES:
            with self.subTest(scope=scope):
                item = CatalogItemCreate.model_validate(self.catalog_payload(scope))
                self.assertEqual(item.calibration_scope, scope)

    def test_catalog_response_accepts_the_canonical_database_value(self):
        now = datetime.now(timezone.utc)
        payload = self.catalog_payload("accredited_iso_17025") | {
            "id": 1,
            "internal_key": "SER-CAL-0001",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        item = CatalogItemOut.model_validate(payload)
        self.assertEqual(item.calibration_scope, "accredited_iso_17025")

    def test_document_label_is_rejected_throughout_the_operational_chain(self):
        payloads = (
            (CatalogItemCreate, self.catalog_payload(DOCUMENT_LABEL)),
            (QuotationItemCreate, {"calibration_scope": DOCUMENT_LABEL}),
            (
                ServiceOrderItemCreate,
                {"service_name": "Calibración", "calibration_scope": DOCUMENT_LABEL},
            ),
            (
                EquipmentCreate,
                {
                    "service_order_id": 1,
                    "name": "Termómetro",
                    "calibration_scope": DOCUMENT_LABEL,
                },
            ),
            (
                DocumentInterpretationCreate,
                {
                    "document_id": 1,
                    "name": "Interpretación",
                    "calibration_scope": DOCUMENT_LABEL,
                },
            ),
            (
                TechnicalProfileCreate,
                {
                    "code": "TP-001",
                    "name": "Perfil",
                    "magnitude": "Temperatura",
                    "equipment_type": "Termómetro",
                    "calibration_scope": DOCUMENT_LABEL,
                },
            ),
        )
        for schema, payload in payloads:
            with self.subTest(schema=schema.__name__):
                with self.assertRaises(ValidationError):
                    schema.model_validate(payload)

    def test_technical_profiles_use_the_same_canonical_accreditation_scope(self):
        profile = TechnicalProfileCreate.model_validate(
            {
                "code": "TP-001",
                "name": "Perfil",
                "magnitude": "Temperatura",
                "equipment_type": "Termómetro",
                "calibration_scope": "accredited_linked_lab",
            }
        )
        self.assertEqual(profile.calibration_scope, "accredited_linked_lab")
        with self.assertRaises(ValidationError):
            TechnicalProfileCreate.model_validate(
                {
                    "code": "TP-002",
                    "name": "Perfil especial",
                    "magnitude": "Temperatura",
                    "equipment_type": "Termómetro",
                    "calibration_scope": "special",
                }
            )

    def test_catalog_rejects_a_scope_from_a_different_service_category(self):
        payload = self.catalog_payload("preventive")
        with self.assertRaisesRegex(ValidationError, "no corresponde"):
            CatalogItemCreate.model_validate(payload)

    def test_non_calibration_service_scope_remains_valid_for_its_category(self):
        payload = self.catalog_payload("preventive") | {
            "commodity": "maintenance",
            "category": "Mantenimiento",
        }
        item = CatalogItemCreate.model_validate(payload)
        self.assertEqual(item.calibration_scope, "preventive")

    def test_certificate_mapping_preserves_the_three_modalities(self):
        expected = {
            "accredited_iso_17025": "acreditado",
            "traceable": "trazable",
            "accredited_linked_lab": "vinculado",
        }
        for scope, certificate_type in expected.items():
            with self.subTest(scope=scope):
                self.assertEqual(certificate_type_from_scope(scope), certificate_type)
                self.assertEqual(
                    calibration_scope_from_certificate_type(certificate_type), scope
                )


if __name__ == "__main__":
    unittest.main()
