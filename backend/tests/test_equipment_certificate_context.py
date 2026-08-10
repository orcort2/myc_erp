import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.catalog_item import CatalogItem
from app.models.certificate import Certificate
from app.models.client import Client
from app.models.controlled_document import (
    ControlledDocument,
    ControlledDocumentVersion,
)
from app.models.quotation import Quotation, QuotationItem
from app.models.user import User
from app.schemas.equipment import EquipmentCreate
from app.schemas.service_order import ServiceOrderCreate
from app.services.equipment import FINISHED_STATUSES, create_equipment
from app.services.service_orders import create_service_order


class EquipmentCertificateContextTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.actor = User(
            username="equipment-context-actor",
            email="equipment-context-actor@example.test",
            full_name="Equipment Context Actor",
            hashed_password="unused",
        )
        self.db.add(self.actor)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_equipment_uses_master_frozen_on_service_order_item(self):
        master = ControlledDocument(
            code="MC-EQUIPO-001",
            name="Master equipo",
            document_type="certificate_master",
            status="active",
        )
        master.versions = [
            ControlledDocumentVersion(
                revision="1",
                file_path="certificate-masters/master-equipo.xlsx",
                original_filename="master-equipo.xlsx",
                checksum="abc123",
                status="active",
                effective_date=date(2026, 7, 1),
                expires_on=date(2027, 7, 1),
            )
        ]
        client = Client(
            client_type="persona_moral",
            legal_name="Cliente de contexto",
            commercial_name="Cliente de contexto",
        )
        self.db.add_all([master, client])
        self.db.flush()

        catalog_item = CatalogItem(
            item_type="service",
            service_kind="simple",
            commodity="calibration",
            category="Calibracion",
            name="Calibración original",
            origin_currency="MXN",
            calibration_scope="traceable",
            expected_certificate_master_id=master.id,
        )
        self.db.add(catalog_item)
        self.db.flush()

        quotation = Quotation(
            folio="COT-EQUIPO-CONTEXTO",
            client_id=client.id,
            status="accepted",
        )
        quotation.items = [
            QuotationItem(
                catalog_item_id=catalog_item.id,
                service_name=catalog_item.name,
                calibration_scope="traceable",
                quantity=1,
                unit_price=Decimal("100.00"),
                discount_percent=Decimal("0.00"),
                tax_rate=Decimal("16.00"),
                tax_total=Decimal("16.00"),
                total=Decimal("100.00"),
            )
        ]
        self.db.add(quotation)
        self.db.commit()

        service_order = create_service_order(
            self.db,
            ServiceOrderCreate(
                client_id=client.id,
                quotation_id=quotation.id,
            ),
            user_id=self.actor.id,
        )
        service_order_item = service_order.items[0]
        self.assertEqual(
            service_order_item.expected_certificate_master_id,
            master.id,
        )

        catalog_item.name = "Nombre modificado después del ETS"
        catalog_item.expected_certificate_master_id = None
        self.db.commit()

        equipment = create_equipment(
            self.db,
            EquipmentCreate(
                service_order_id=service_order.id,
                name="Termómetro patrón",
            ),
        )

        self.assertEqual(equipment.certificate_master_document_id, master.id)
        self.assertEqual(
            equipment.certificate_master_version_id,
            master.versions[0].id,
        )
        self.assertEqual(
            equipment.certificate_template_checksum_snapshot,
            "abc123",
        )
        self.assertEqual(
            equipment.certificate_operational_context_snapshot,
            {
                "schema_version": 1,
                "calibration_scope": "traceable",
                "certificate_type": "trazable",
                "expected_certificate_master_id": master.id,
                "service_order_item_id": service_order_item.id,
                "source_catalog_item_id": catalog_item.id,
            },
        )
        certificate = self.db.scalar(
            select(Certificate).where(
                Certificate.equipment_id == equipment.id
            )
        )
        self.assertIsNotNone(certificate)
        self.assertEqual(certificate.certificate_type, "trazable")

    def test_finished_statuses_keep_operational_semantics(self):
        self.assertEqual(
            FINISHED_STATUSES,
            {"calibrated", "labeled", "not_done"},
        )


if __name__ == "__main__":
    unittest.main()
