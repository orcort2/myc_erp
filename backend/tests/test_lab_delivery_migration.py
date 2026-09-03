from __future__ import annotations

import importlib.util
from pathlib import Path

from app.models.lab_delivery_group_receipt import LabDeliveryGroupReceipt
from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderGroupRequest
from app.models.lab_work_order_delivery import LabWorkOrderDelivery


def _migration_module():
    path = Path(__file__).parents[1] / "migrations/versions/c2d4e6f8a0b1_add_lab_work_order_deliveries.py"
    spec = importlib.util.spec_from_file_location("lab_delivery_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lab_delivery_migration_and_metadata_match():
    migration = _migration_module()
    assert migration.down_revision == "9f3a2c7d1e84"
    assert LabWorkOrder.__table__.c.departure_date.nullable is True
    assert LabWorkOrderGroupRequest.__table__.c.departure_date.nullable is True

    assert LabWorkOrderDelivery.__tablename__ == "lab_work_order_deliveries"
    delivery_columns = {column.name for column in LabWorkOrderDelivery.__table__.columns}
    assert delivery_columns >= {
        "root_work_order_id", "exhibition_number", "delivery_type", "delivery_method",
        "partial_delivery_ticket_id", "delivered_at", "delivered_by_user_id",
        "delivered_by_signature_data_url", "recipient_name", "recipient_signature_data_url",
        "status", "voucher_pdf", "voucher_pdf_sha256",
    }
    # entrega ya no vive keyed 1:1 por OT -- root_work_order_id es la cohorte.
    assert "work_order_id" not in delivery_columns
    exhibition_unique = next(
        constraint
        for constraint in LabWorkOrderDelivery.__table__.constraints
        if constraint.name == "uq_lab_work_order_delivery_exhibition"
    )
    assert {c.name for c in exhibition_unique.columns} == {"root_work_order_id", "exhibition_number"}

    assert LabDeliveryItem.__tablename__ == "lab_delivery_items"
    item_columns = {column.name for column in LabDeliveryItem.__table__.columns}
    assert item_columns >= {
        "delivery_id", "work_order_id", "equipment_id", "position_snapshot",
        "instrument_snapshot", "brand_snapshot", "identification_snapshot",
        "serial_number_snapshot", "certificate_folio_snapshot",
    }
    item_unique = next(
        constraint
        for constraint in LabDeliveryItem.__table__.constraints
        if constraint.name == "uq_lab_delivery_item_equipment"
    )
    assert {c.name for c in item_unique.columns} == {"delivery_id", "equipment_id"}

    assert LabDeliveryGroupReceipt.__tablename__ == "lab_delivery_group_receipts"
    receipt_columns = {column.name for column in LabDeliveryGroupReceipt.__table__.columns}
    assert receipt_columns >= {
        "root_work_order_id", "version", "exhibitions_count", "generated_at",
        "generated_by_user_id", "superseded_at", "pdf", "pdf_sha256",
    }


def test_lab_delivery_migration_adds_partial_delivery_ticket_type():
    source = Path(_migration_module().__file__).read_text()
    assert "partial_delivery" in source
    assert "ck_operational_ticket_type" in source


def test_lab_delivery_downgrade_explicitly_preserves_rows_and_null_departures():
    source = Path(_migration_module().__file__).read_text()
    assert "SELECT count(*) FROM lab_work_order_deliveries" in source
    assert "SELECT count(*) FROM lab_delivery_group_receipts" in source
    assert "SELECT count(*) FROM lab_work_orders WHERE departure_date IS NULL" in source
    assert "SELECT count(*) FROM lab_work_order_group_requests WHERE departure_date IS NULL" in source
    assert "raise RuntimeError" in source
