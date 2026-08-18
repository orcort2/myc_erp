from decimal import Decimal
from pathlib import Path
import subprocess

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.catalog_item import CatalogItem, CatalogItemComponent
from app.models.client import Client
from app.models.quotation import Quotation, QuotationItem
from app.models.service_order import ServiceOrder, ServiceOrderItem, ServiceWorkOrder
from app.models.user import User
from app.schemas.quotation import QuotationItemUpdate, QuotationUpdate
from app.schemas.catalog_item import CatalogItemCreate, CatalogItemUpdate
from app.schemas.service_execution import ServiceStageCreate, ServiceUnitBatchCreate, ServiceUnitCreate
from app.schemas.service_order import ServiceOrderCreate
from app.services.quotations import (
    _build_operational_snapshot,
    _write_snapshot,
    restore_quotation_snapshot,
    update_quotation,
    update_quotation_item,
)
from app.services.catalog_items import create_catalog_item, update_catalog_item
from app.services.service_execution import create_service_units
from app.services.service_orders import create_service_order


def _service(name: str, category: str, operational_category: str, **extra) -> CatalogItem:
    return CatalogItem(
        item_type="service",
        service_kind="simple",
        commodity=operational_category,
        category=category,
        operational_category=operational_category,
        name=name,
        origin_price=Decimal("100"),
        origin_currency="MXN",
        exchange_rate=Decimal("1"),
        margin_percent=Decimal("0"),
        final_price_mxn=Decimal("100"),
        tax_object="iva_16",
        tax_rate=Decimal("16"),
        **extra,
    )


def _context():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    user = User(
        username="identity-actor",
        email="identity@example.test",
        full_name="Identity Actor",
        hashed_password="unused",
    )
    client = Client(legal_name="Cliente identidad")
    db.add_all([user, client])
    db.flush()
    return engine, db, user, client


def test_quotation_snapshot_is_frozen_when_catalog_changes_and_quote_reopens():
    engine, db, user, client = _context()
    try:
        service = _service("Validación inicial", "Validacion", "validation")
        db.add(service)
        db.flush()
        frozen = _build_operational_snapshot(db, service)
        quotation = Quotation(folio="COT-FROZEN-1", client_id=client.id, status="draft")
        item = QuotationItem(
            catalog_item_id=service.id,
            service_name=service.name,
            operational_category="validation",
            commodity="validation",
            quantity=1,
            unit_price=Decimal("100"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("16"),
            tax_total=Decimal("16"),
            total=Decimal("100"),
            operational_snapshot=frozen,
        )
        quotation.items = [item]
        db.add(quotation)
        db.flush()
        historical_version = _write_snapshot(db, quotation, reason="created", user_id=user.id)
        db.commit()

        service.name = "Servicio General renombrado"
        service.category = "Servicio general"
        service.commodity = "general_service"
        service.operational_category = "general_service"
        db.commit()

        reopened = update_quotation(
            db, quotation.id, QuotationUpdate(notes="Reabierta para revisión"), user_id=user.id
        )
        assert reopened.items[0].operational_snapshot == frozen

        edited = update_quotation_item(
            db,
            quotation.id,
            item.id,
            QuotationItemUpdate(
                catalog_item_id=service.id,
                service_name="Texto comercial editado",
                unit_price=Decimal("120"),
            ),
            user_id=user.id,
        )
        assert edited.items[0].operational_snapshot == frozen
        assert edited.items[0].operational_category == "validation"

        restored = restore_quotation_snapshot(
            db, quotation.id, historical_version.id, user_id=user.id
        )
        assert restored.items[0].operational_snapshot == frozen
    finally:
        db.close()
        engine.dispose()


def test_catalog_persists_known_category_without_general_service_fallback():
    engine, db, _, _ = _context()
    try:
        item = create_catalog_item(
            db,
            CatalogItemCreate(
                item_type="service",
                commodity="general_service",
                category="Validacion",
                operational_category="validation",
                name="Validación de proceso",
                origin_currency="MXN",
                calibration_scope="documentary",
            ),
        )
        assert item.commodity == "validation"
        assert item.operational_category == "validation"
    finally:
        db.close()
        engine.dispose()


def test_catalog_type_and_operational_category_are_independent():
    engine, db, _, _ = _context()
    try:
        shared = {
            "service_kind": "simple",
            "origin_currency": "MXN",
        }
        product_sale = create_catalog_item(db, CatalogItemCreate(
            item_type="product", commodity="sale", category="Venta",
            operational_category="sale", name="Producto vendido", **shared,
        ))
        service_sale = create_catalog_item(db, CatalogItemCreate(
            item_type="service", commodity="sale", category="Venta",
            operational_category="sale", name="Servicio vendido", **shared,
        ))
        product_other = create_catalog_item(db, CatalogItemCreate(
            item_type="product", commodity="other", category="Otro",
            operational_category="other", name="Producto no Venta", **shared,
        ))
        service_maintenance = create_catalog_item(db, CatalogItemCreate(
            item_type="service", commodity="maintenance", category="Mantenimiento",
            operational_category="maintenance", name="Mantenimiento",
            calibration_scope="preventive", maintenance_type="preventive",
            maintenance_location="laboratory", **shared,
        ))

        assert product_sale.operational_category == "sale"
        assert service_sale.operational_category == "sale"
        assert product_other.operational_category == "other"
        assert service_maintenance.operational_category == "maintenance"
    finally:
        db.close()
        engine.dispose()


def test_catalog_edit_preserves_explicit_operational_category():
    engine, db, _, _ = _context()
    try:
        item = create_catalog_item(db, CatalogItemCreate(
            item_type="product", service_kind="simple", commodity="verification",
            category="Verificacion", operational_category="verification",
            name="Producto verificable", origin_currency="MXN",
        ))
        edited = update_catalog_item(
            db,
            item.id,
            CatalogItemUpdate(name="Producto verificable editado"),
        )
        assert edited.item_type == "product"
        assert edited.operational_category == "verification"
    finally:
        db.close()
        engine.dispose()


def test_explicit_catalog_replacement_rebuilds_only_the_selected_snapshot():
    engine, db, user, client = _context()
    try:
        original = _service("Validación original", "Validacion", "validation")
        replacement = _service("Reparación sustituta", "Reparacion", "repair")
        db.add_all([original, replacement])
        db.flush()
        frozen = _build_operational_snapshot(db, original)
        quotation = Quotation(folio="COT-REPLACE-1", client_id=client.id, status="draft")
        item = QuotationItem(
            catalog_item_id=original.id, service_name=original.name,
            operational_category="validation", commodity="validation", quantity=1,
            unit_price=Decimal("100"), discount_percent=Decimal("0"),
            tax_rate=Decimal("16"), tax_total=Decimal("16"), total=Decimal("100"),
            operational_snapshot=frozen,
        )
        quotation.items = [item]
        db.add(quotation)
        db.commit()

        updated = update_quotation_item(
            db,
            quotation.id,
            item.id,
            QuotationItemUpdate(catalog_item_id=replacement.id),
            user_id=user.id,
        )
        updated_item = updated.items[0]
        assert updated_item.operational_category == "repair"
        assert updated_item.operational_snapshot["operational_category"] == "repair"
        assert updated_item.operational_snapshot != frozen
    finally:
        db.close()
        engine.dispose()


def test_known_category_does_not_enter_general_service_but_general_service_evolves():
    engine, db, user, client = _context()
    try:
        validation = _service("Servicio General escrito en el nombre", "Validacion", "validation")
        general = _service("Diagnóstico especial", "Servicio general", "general_service")
        db.add_all([validation, general])
        db.flush()
        order = ServiceOrder(
            folio="ETS-IDENTITY-1", work_order_number=9100, client_id=client.id,
            status="in_progress", requires_payment=True,
        )
        db.add(order)
        db.flush()
        work_order = ServiceWorkOrder(
            service_order_id=order.id, work_order_number=9100, sequence=1,
            status="pending", equipment_limit=10,
        )
        validation_item = ServiceOrderItem(
            service_order_id=order.id, catalog_item_id=validation.id,
            service_name=validation.name, operational_category="validation",
            service_snapshot={"operational_category_snapshot": "validation"},
            quantity=1, status="pending",
        )
        general_item = ServiceOrderItem(
            service_order_id=order.id, catalog_item_id=general.id,
            service_name=general.name, operational_category="general_service",
            service_snapshot={"operational_category_snapshot": "general_service"},
            quantity=1, status="pending",
        )
        db.add_all([work_order, validation_item, general_item])
        db.commit()

        units = create_service_units(
            db,
            order.id,
            ServiceUnitBatchCreate(units=[
                ServiceUnitCreate(
                    work_order_id=work_order.id,
                    origin_service_order_item_id=validation_item.id,
                    name="Unidad validación",
                    initial_stages=[ServiceStageCreate(category="validation")],
                ),
                ServiceUnitCreate(
                    work_order_id=work_order.id,
                    origin_service_order_item_id=general_item.id,
                    name="Unidad general",
                    initial_stages=[ServiceStageCreate(category="diagnosis")],
                ),
            ]),
            user_id=user.id,
        )
        assert units[0].initial_category == "validation"
        assert units[0].evolution_enabled is False
        assert units[1].initial_category == "general_service"
        assert units[1].evolution_enabled is True
        assert units[1].stages[0].status == "authorized"
    finally:
        db.close()
        engine.dispose()


def test_composite_components_and_calibration_keep_frozen_identity_and_scope():
    engine, db, user, client = _context()
    try:
        calibration = _service(
            "Calibración componente", "Calibracion", "calibration",
            calibration_scope="traceable", service_type="traceable",
        )
        qualification = _service("Calificación componente", "Calificacion", "qualification")
        parent = _service("Paquete comercial", "Servicio general", "general_service")
        parent.service_kind = "composite"
        db.add_all([calibration, qualification, parent])
        db.flush()
        parent.components = [
            CatalogItemComponent(component_catalog_item_id=calibration.id, quantity=1),
            CatalogItemComponent(component_catalog_item_id=qualification.id, quantity=2),
        ]
        db.flush()
        snapshot = _build_operational_snapshot(db, parent)
        identities = {
            row["service_name"]: row["operational_category"]
            for row in snapshot["operational_items"]
        }
        assert identities == {
            "Calibración componente": "calibration",
            "Calificación componente": "qualification",
        }
        quotation = Quotation(folio="COT-COMP-ID", client_id=client.id, status="accepted")
        quotation.items = [QuotationItem(
            catalog_item_id=parent.id,
            service_name=parent.name,
            operational_category="general_service",
            quantity=1,
            unit_price=Decimal("100"), discount_percent=Decimal("0"),
            tax_rate=Decimal("16"), tax_total=Decimal("16"), total=Decimal("100"),
            operational_snapshot=snapshot,
        )]
        db.add(quotation)
        db.commit()
        order = create_service_order(
            db,
            ServiceOrderCreate(client_id=client.id, quotation_id=quotation.id),
            user_id=user.id,
        )
        by_name = {row.service_name: row for row in order.items}
        assert by_name["Calibración componente"].operational_category == "calibration"
        assert by_name["Calibración componente"].calibration_scope == "traceable"
        assert by_name["Calificación componente"].operational_category == "qualification"
        assert by_name["Calificación componente"].quantity == 2
    finally:
        db.close()
        engine.dispose()


def test_field_sheet_template_proposal_keeps_existing_resolver_behavior():
    repository = Path(__file__).resolve().parents[2]
    script = """
      import { suggestOfficialFieldSheetTemplate as suggest } from './frontend/src/utils/fieldSheetTemplateResolver.js';
      const pressure = suggest({ equipmentName: 'Manómetro digital' });
      const scale = suggest({ instrumentType: 'Báscula de plataforma' });
      const unknown = suggest({ equipmentName: 'Equipo sin familia' });
      if (pressure.templateKey !== 'presion' || pressure.matchedBy !== 'manometro') process.exit(1);
      if (scale.templateKey !== 'bascula' || scale.matchedBy !== 'bascula') process.exit(2);
      if (unknown.templateKey !== '' || unknown.matchedBy !== '') process.exit(3);
    """
    subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=repository,
        check=True,
    )
