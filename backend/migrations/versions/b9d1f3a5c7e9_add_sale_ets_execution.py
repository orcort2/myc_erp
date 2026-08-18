"""add sale ETS execution

Revision ID: b9d1f3a5c7e9
Revises: a8c0e2f4b6d8
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa


revision = "b9d1f3a5c7e9"
down_revision = "a8c0e2f4b6d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("catalog_items", sa.Column("requires_individual_identification", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("catalog_items", sa.Column("sale_brand", sa.String(120)))
    op.add_column("catalog_items", sa.Column("sale_model", sa.String(120)))
    op.add_column("catalog_items", sa.Column("sale_specification", sa.Text()))
    op.add_column("catalog_items", sa.Column("included_calibration_catalog_item_id", sa.Integer()))
    op.create_foreign_key("fk_catalog_items_included_calibration", "catalog_items", "catalog_items", ["included_calibration_catalog_item_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_catalog_items_included_calibration_catalog_item_id", "catalog_items", ["included_calibration_catalog_item_id"])

    with op.batch_alter_table("service_stages") as batch:
        batch.drop_constraint("ck_service_stages_category", type_="check")
        batch.create_check_constraint(
            "ck_service_stages_category",
            "category IN ('diagnosis','repair','maintenance','calibration','verification','qualification','validation','training','consulting','sale','other')",
        )

    op.create_table(
        "sale_order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_order_id", sa.Integer(), sa.ForeignKey("service_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_order_item_id", sa.Integer(), sa.ForeignKey("service_order_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requires_individual_identification", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("included_calibration_catalog_item_id", sa.Integer(), sa.ForeignKey("catalog_items.id", ondelete="RESTRICT")),
        sa.Column("frozen_configuration", sa.JSON(), nullable=False),
        sa.Column("ordered_quantity", sa.Integer(), nullable=False),
        sa.Column("arrived_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivered_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolved_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending_arrival"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ordered_quantity > 0", name="ck_sale_order_items_ordered_quantity"),
        sa.CheckConstraint("arrived_quantity >= 0 AND delivered_quantity >= 0 AND resolved_quantity >= 0", name="ck_sale_order_items_nonnegative_quantities"),
        sa.UniqueConstraint("service_order_item_id", name="uq_sale_order_items_service_order_item"),
    )
    op.create_index("ix_sale_order_items_service_order_id", "sale_order_items", ["service_order_id"])
    op.create_index("ix_sale_order_items_service_order_item_id", "sale_order_items", ["service_order_item_id"])
    op.create_index("ix_sale_order_items_included_calibration_catalog_item_id", "sale_order_items", ["included_calibration_catalog_item_id"])
    op.create_index("ix_sale_order_items_status", "sale_order_items", ["status"])
    op.create_index("ix_sale_order_items_order_status", "sale_order_items", ["service_order_id", "status"])

    op.create_table(
        "sale_unit_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sale_order_item_id", sa.Integer(), sa.ForeignKey("sale_order_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_unit_id", sa.Integer(), sa.ForeignKey("service_units.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("equipment_id", sa.Integer(), sa.ForeignKey("equipment.id", ondelete="RESTRICT")),
        sa.Column("calibration_stage_id", sa.Integer(), sa.ForeignKey("service_stages.id", ondelete="RESTRICT")),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending_arrival"),
        sa.Column("serial_number", sa.String(120)),
        sa.Column("brand", sa.String(120)),
        sa.Column("model", sa.String(120)),
        sa.Column("specification", sa.Text()),
        sa.Column("discrepancy_reason", sa.Text()),
        sa.Column("arrived_at", sa.DateTime(timezone=True)),
        sa.Column("warranty_returned_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("service_unit_id", name="uq_sale_unit_states_service_unit"),
        sa.UniqueConstraint("equipment_id", name="uq_sale_unit_states_equipment"),
        sa.UniqueConstraint("calibration_stage_id", name="uq_sale_unit_states_calibration_stage"),
    )
    for column in ("sale_order_item_id", "service_unit_id", "equipment_id", "calibration_stage_id", "status", "serial_number"):
        op.create_index(f"ix_sale_unit_states_{column}", "sale_unit_states", [column])
    op.create_index("ix_sale_unit_states_item_status", "sale_unit_states", ["sale_order_item_id", "status"])

    op.create_table(
        "sale_authorizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_order_id", sa.Integer(), sa.ForeignKey("service_orders.id"), nullable=False),
        sa.Column("sale_order_item_id", sa.Integer(), sa.ForeignKey("sale_order_items.id")),
        sa.Column("sale_unit_state_id", sa.Integer(), sa.ForeignKey("sale_unit_states.id")),
        sa.Column("authorization_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="requested"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("authorized_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("consumed_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("resolution_comment", sa.Text()),
        sa.Column("authorized_at", sa.DateTime(timezone=True)),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("authorization_type IN ('individual_identification','zero_cost_calibration','substitution')", name="ck_sale_authorizations_type"),
        sa.CheckConstraint("status IN ('requested','authorized','rejected','consumed')", name="ck_sale_authorizations_status"),
    )
    for column in ("service_order_id", "sale_order_item_id", "sale_unit_state_id", "authorization_type", "status", "requested_by_id", "authorized_by_id", "consumed_by_id"):
        op.create_index(f"ix_sale_authorizations_{column}", "sale_authorizations", [column])
    op.create_index("ix_sale_authorizations_order_status", "sale_authorizations", ["service_order_id", "status"])

    op.create_table(
        "sale_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_order_id", sa.Integer(), sa.ForeignKey("service_orders.id"), nullable=False),
        sa.Column("mode", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="prepared"),
        sa.Column("courier_name", sa.String(120)), sa.Column("tracking_number", sa.String(160)),
        sa.Column("shipped_on", sa.Date()), sa.Column("estimated_arrival_on", sa.Date()),
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("address_source", sa.String(30)), sa.Column("delivery_address", sa.JSON()),
        sa.Column("accepted_at", sa.DateTime(timezone=True)), sa.Column("scheduled_for", sa.DateTime(timezone=True)),
        sa.Column("receiver_name", sa.String(180)), sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("received_by_user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("signature_data_url", sa.Text()), sa.Column("evidence", sa.JSON()),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("confirmed_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mode IN ('courier','client_pickup','myc_technician')", name="ck_sale_deliveries_mode"),
        sa.CheckConstraint("status IN ('prepared','pickup_notified','technician_requested','technician_accepted','scheduled','sent','delivery_reported','delivered','cancelled')", name="ck_sale_deliveries_status"),
    )
    for column in ("service_order_id", "mode", "status", "tracking_number", "technician_id", "received_by_user_id", "created_by_id", "confirmed_by_id"):
        op.create_index(f"ix_sale_deliveries_{column}", "sale_deliveries", [column])
    op.create_index("ix_sale_deliveries_order_status", "sale_deliveries", ["service_order_id", "status"])

    op.create_table(
        "sale_delivery_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("delivery_id", sa.Integer(), sa.ForeignKey("sale_deliveries.id"), nullable=False),
        sa.Column("sale_order_item_id", sa.Integer(), sa.ForeignKey("sale_order_items.id"), nullable=False),
        sa.Column("sale_unit_state_id", sa.Integer(), sa.ForeignKey("sale_unit_states.id")),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_sale_delivery_lines_quantity"),
        sa.UniqueConstraint("delivery_id", "sale_unit_state_id", name="uq_sale_delivery_unit"),
    )
    for column in ("delivery_id", "sale_order_item_id", "sale_unit_state_id"):
        op.create_index(f"ix_sale_delivery_lines_{column}", "sale_delivery_lines", [column])


def downgrade() -> None:
    op.drop_table("sale_delivery_lines")
    op.drop_table("sale_deliveries")
    op.drop_table("sale_authorizations")
    op.drop_table("sale_unit_states")
    op.drop_table("sale_order_items")
    with op.batch_alter_table("service_stages") as batch:
        batch.drop_constraint("ck_service_stages_category", type_="check")
        batch.create_check_constraint(
            "ck_service_stages_category",
            "category IN ('diagnosis','repair','maintenance','calibration','verification','qualification','validation','training','consulting','other')",
        )
    op.drop_index("ix_catalog_items_included_calibration_catalog_item_id", table_name="catalog_items")
    op.drop_constraint("fk_catalog_items_included_calibration", "catalog_items", type_="foreignkey")
    op.drop_column("catalog_items", "included_calibration_catalog_item_id")
    op.drop_column("catalog_items", "sale_specification")
    op.drop_column("catalog_items", "sale_model")
    op.drop_column("catalog_items", "sale_brand")
    op.drop_column("catalog_items", "requires_individual_identification")
