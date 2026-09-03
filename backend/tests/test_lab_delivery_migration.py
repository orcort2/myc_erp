from __future__ import annotations

import importlib.util
from pathlib import Path

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
    assert {column.name for column in LabWorkOrderDelivery.__table__.columns} >= {
        "work_order_id", "delivered_at", "delivered_by_user_id", "recipient_name",
        "recipient_signature_data_url", "status", "voucher_pdf", "voucher_pdf_sha256",
    }
    active_index = next(index for index in LabWorkOrderDelivery.__table__.indexes if index.name == "uq_lab_work_order_delivery_active")
    assert active_index.unique is True
    assert str(active_index.dialect_options["postgresql"]["where"]) == "status = 'completed'"


def test_lab_delivery_downgrade_explicitly_preserves_rows_and_null_departures():
    source = Path(_migration_module().__file__).read_text()
    assert "SELECT count(*) FROM lab_work_order_deliveries" in source
    assert "SELECT count(*) FROM lab_work_orders WHERE departure_date IS NULL" in source
    assert "SELECT count(*) FROM lab_work_order_group_requests WHERE departure_date IS NULL" in source
    assert "raise RuntimeError" in source
