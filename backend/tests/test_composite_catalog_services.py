import unittest
from decimal import Decimal

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.catalog_item import CatalogItem
from app.models.client import Client
from app.models.quotation import Quotation, QuotationItem
from app.models.user import User
from app.schemas.catalog_item import CatalogItemCreate, CatalogItemOut, CatalogItemUpdate
from app.schemas.service_order import ServiceOrderCreate
from app.services.catalog_items import create_catalog_item, update_catalog_item
from app.services.service_orders import create_service_order


class CompositeCatalogServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.actor = User(
            username="composite-actor",
            email="composite-actor@example.test",
            full_name="Composite Actor",
            hashed_password="unused",
        )
        self.db.add(self.actor)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    @staticmethod
    def service_payload(name: str, scope: str = "traceable") -> dict:
        return {
            "item_type": "service",
            "service_kind": "simple",
            "commodity": "calibration",
            "category": "Calibracion",
            "name": name,
            "origin_currency": "MXN",
            "calibration_scope": scope,
        }

    def create_simple_service(self, name: str, scope: str = "traceable") -> CatalogItem:
        return create_catalog_item(
            self.db,
            CatalogItemCreate.model_validate(self.service_payload(name, scope)),
        )

    def test_existing_and_omitted_services_default_to_simple(self):
        payload = self.service_payload("Servicio existente")
        payload.pop("service_kind")
        schema = CatalogItemCreate.model_validate(payload)
        self.assertEqual(schema.service_kind, "simple")
        self.assertEqual(schema.components, [])

    def test_composite_requires_components_and_positive_quantities(self):
        payload = self.service_payload("Paquete") | {
            "service_kind": "composite",
            "components": [],
        }
        with self.assertRaises(ValidationError):
            CatalogItemCreate.model_validate(payload)

        payload["components"] = [
            {"component_catalog_item_id": 1, "quantity": 0}
        ]
        with self.assertRaises(ValidationError):
            CatalogItemCreate.model_validate(payload)

    def test_self_reference_and_indirect_cycle_are_rejected(self):
        first = self.create_simple_service("Servicio A")
        second = self.create_simple_service("Servicio B")

        first = update_catalog_item(
            self.db,
            first.id,
            CatalogItemUpdate(
                service_kind="composite",
                components=[
                    {"component_catalog_item_id": second.id, "quantity": 1}
                ],
            ),
        )
        with self.assertRaises(HTTPException) as self_reference:
            update_catalog_item(
                self.db,
                first.id,
                CatalogItemUpdate(
                    components=[
                        {"component_catalog_item_id": first.id, "quantity": 1}
                    ]
                ),
            )
        self.assertEqual(self_reference.exception.status_code, 422)

        with self.assertRaises(HTTPException) as cycle:
            update_catalog_item(
                self.db,
                second.id,
                CatalogItemUpdate(
                    service_kind="composite",
                    components=[
                        {"component_catalog_item_id": first.id, "quantity": 1}
                    ],
                ),
            )
        self.assertEqual(cycle.exception.status_code, 422)
        self.assertIn("circular", str(cycle.exception.detail).lower())

    def test_editing_composite_reuses_links_and_updates_quantity(self):
        component = self.create_simple_service("Servicio componente")
        composite = create_catalog_item(
            self.db,
            CatalogItemCreate.model_validate(
                {
                    "item_type": "service",
                    "service_kind": "composite",
                    "commodity": "general_service",
                    "category": "Servicio general",
                    "name": "Servicio padre",
                    "origin_currency": "MXN",
                    "components": [
                        {"component_catalog_item_id": component.id, "quantity": 1}
                    ],
                }
            ),
        )
        link_id = composite.components[0].id
        updated = update_catalog_item(
            self.db,
            composite.id,
            CatalogItemUpdate(
                components=[
                    {"component_catalog_item_id": component.id, "quantity": 4}
                ]
            ),
        )
        self.assertEqual(updated.components[0].id, link_id)
        self.assertEqual(updated.components[0].quantity, 4)

    def test_ets_expands_composite_but_keeps_one_commercial_quotation_item(self):
        manometer = self.create_simple_service("Calibración de Manómetro")
        thermometer = self.create_simple_service(
            "Calibración de Termómetro", "accredited_iso_17025"
        )
        scale = self.create_simple_service("Calibración de Báscula")
        composite = create_catalog_item(
            self.db,
            CatalogItemCreate.model_validate(
                {
                    "item_type": "service",
                    "service_kind": "composite",
                    "commodity": "general_service",
                    "category": "Servicio general",
                    "name": "Equipo Especial",
                    "origin_currency": "MXN",
                    "components": [
                        {"component_catalog_item_id": manometer.id, "quantity": 2},
                        {"component_catalog_item_id": thermometer.id, "quantity": 3},
                        {"component_catalog_item_id": scale.id, "quantity": 1},
                    ],
                }
            ),
        )
        response = CatalogItemOut.model_validate(composite)
        self.assertEqual(response.service_kind, "composite")
        self.assertEqual(len(response.components), 3)
        self.assertEqual(response.components[0].component_name, "Calibración de Manómetro")

        client = Client(
            client_type="persona_moral",
            legal_name="Cliente compuesto",
            commercial_name="Cliente compuesto",
        )
        self.db.add(client)
        self.db.flush()
        quotation = Quotation(
            folio="COT-COMP-001",
            client_id=client.id,
            status="accepted",
        )
        quotation.items = [
            QuotationItem(
                catalog_item_id=composite.id,
                service_name="Equipo Especial",
                quantity=2,
                unit_price=Decimal("1000.00"),
                discount_percent=Decimal("0.00"),
                tax_rate=Decimal("16.00"),
                tax_total=Decimal("320.00"),
                total=Decimal("2000.00"),
            )
        ]
        self.db.add(quotation)
        self.db.commit()

        service_order = create_service_order(
            self.db,
            ServiceOrderCreate(client_id=client.id, quotation_id=quotation.id),
            user_id=self.actor.id,
        )

        self.assertEqual(len(quotation.items), 1)
        self.assertEqual(quotation.items[0].service_name, "Equipo Especial")
        expanded = {
            item.service_name: (item.quantity, item.catalog_item_id, item.quotation_item_id)
            for item in service_order.items
        }
        self.assertEqual(
            expanded,
            {
                "Calibración de Manómetro": (4, manometer.id, quotation.items[0].id),
                "Calibración de Termómetro": (6, thermometer.id, quotation.items[0].id),
                "Calibración de Báscula": (2, scale.id, quotation.items[0].id),
            },
        )
        self.assertEqual(len(service_order.work_orders), 2)

    def test_simple_quotation_item_preserves_existing_behavior(self):
        simple = self.create_simple_service("Servicio simple")
        client = Client(
            client_type="persona_moral",
            legal_name="Cliente simple",
            commercial_name="Cliente simple",
        )
        self.db.add(client)
        self.db.flush()
        quotation = Quotation(
            folio="COT-SIMPLE-001",
            client_id=client.id,
            status="accepted",
        )
        quotation.items = [
            QuotationItem(
                catalog_item_id=simple.id,
                service_name="Nombre congelado en cotización",
                calibration_scope="traceable",
                quantity=3,
                unit_price=Decimal("100.00"),
                discount_percent=Decimal("0.00"),
                tax_rate=Decimal("16.00"),
                tax_total=Decimal("48.00"),
                total=Decimal("300.00"),
            )
        ]
        self.db.add(quotation)
        self.db.commit()

        service_order = create_service_order(
            self.db,
            ServiceOrderCreate(client_id=client.id, quotation_id=quotation.id),
            user_id=self.actor.id,
        )
        self.assertEqual(len(service_order.items), 1)
        self.assertEqual(service_order.items[0].service_name, "Nombre congelado en cotización")
        self.assertEqual(service_order.items[0].quantity, 3)
        self.assertEqual(service_order.items[0].catalog_item_id, simple.id)


if __name__ == "__main__":
    unittest.main()
