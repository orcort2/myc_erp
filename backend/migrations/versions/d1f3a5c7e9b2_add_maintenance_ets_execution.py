"""add maintenance ETS execution

Revision ID: d1f3a5c7e9b2
Revises: c0e2f4a6b8d1
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa


revision = "d1f3a5c7e9b2"
down_revision = "c0e2f4a6b8d1"
branch_labels = None
depends_on = None


def _timestamps():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.add_column("catalog_items", sa.Column("maintenance_type", sa.String(20)))
    op.add_column("catalog_items", sa.Column("maintenance_location", sa.String(20)))
    op.add_column("catalog_items", sa.Column("maintenance_base_materials", sa.JSON()))
    op.create_index("ix_catalog_items_maintenance_type", "catalog_items", ["maintenance_type"])
    op.create_index("ix_catalog_items_maintenance_location", "catalog_items", ["maintenance_location"])
    op.execute(sa.text("UPDATE catalog_items SET maintenance_type=calibration_scope, maintenance_location='laboratory', maintenance_base_materials='[]' WHERE operational_category='maintenance'"))

    op.create_table(
        "maintenance_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_order_id", sa.Integer(), sa.ForeignKey("service_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_order_item_id", sa.Integer(), sa.ForeignKey("service_order_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_unit_id", sa.Integer(), sa.ForeignKey("service_units.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_stage_id", sa.Integer(), sa.ForeignKey("service_stages.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("maintenance_type", sa.String(20), nullable=False),
        sa.Column("location_mode", sa.String(20), nullable=False),
        sa.Column("configuration_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending_arrival"),
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("field_request_status", sa.String(30)),
        sa.Column("field_address", sa.JSON()),
        sa.Column("scheduled_for", sa.DateTime(timezone=True)),
        sa.Column("initial_condition", sa.String(40)),
        sa.Column("initial_description", sa.Text()),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("final_condition", sa.String(50)),
        sa.Column("functional_result", sa.Text()),
        sa.Column("technical_conclusion", sa.Text()),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("before_photos", sa.JSON(), nullable=False),
        sa.Column("after_photos", sa.JSON(), nullable=False),
        sa.Column("technical_completed_at", sa.DateTime(timezone=True)),
        sa.Column("report_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("report_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("report_generated_at", sa.DateTime(timezone=True)),
        sa.Column("signed_report_version", sa.Integer()),
        sa.Column("signer_name", sa.String(180)),
        sa.Column("signature_data_url", sa.Text()),
        sa.Column("signed_at", sa.DateTime(timezone=True)),
        sa.Column("client_decision", sa.String(30)),
        sa.Column("investigation_status", sa.String(30)),
        sa.Column("linked_investigation_stage_id", sa.Integer(), sa.ForeignKey("service_stages.id", ondelete="RESTRICT")),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("maintenance_type IN ('preventive','corrective')", name="ck_maintenance_type"),
        sa.CheckConstraint("location_mode IN ('laboratory','field')", name="ck_maintenance_location"),
        sa.UniqueConstraint("service_unit_id", name="uq_maintenance_execution_unit"),
        sa.UniqueConstraint("service_stage_id", name="uq_maintenance_execution_stage"),
    )
    for column in ("service_order_id", "service_order_item_id", "service_unit_id", "service_stage_id", "maintenance_type", "location_mode", "status", "technician_id", "field_request_status", "investigation_status", "linked_investigation_stage_id"):
        op.create_index(f"ix_maintenance_executions_{column}", "maintenance_executions", [column])
    op.create_index("ix_maintenance_execution_order_status", "maintenance_executions", ["service_order_id", "status"])

    op.create_table(
        "maintenance_pauses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("maintenance_execution_id", sa.Integer(), sa.ForeignKey("maintenance_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pause_type", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("responsible_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tentative_resume_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("resolution", sa.Text()),
        sa.Column("resolved_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("pause_type IN ('spare_part','authorization','second_intervention','commercial_review','administrative_investigation')", name="ck_maintenance_pause_type"),
        sa.CheckConstraint("status IN ('active','resolved')", name="ck_maintenance_pause_status"),
    )
    for column in ("maintenance_execution_id", "pause_type", "responsible_user_id", "status", "resolved_by_id"):
        op.create_index(f"ix_maintenance_pauses_{column}", "maintenance_pauses", [column])

    op.create_table(
        "maintenance_materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("maintenance_execution_id", sa.Integer(), sa.ForeignKey("maintenance_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("component", sa.String(180)),
        sa.Column("notes", sa.Text()),
        sa.Column("internal_unit_cost", sa.Numeric(12, 2)),
        sa.Column("decision", sa.String(20)),
        sa.Column("source", sa.String(30), nullable=False, server_default="technician"),
        *_timestamps(),
        sa.CheckConstraint("material_type IN ('used','required')", name="ck_maintenance_material_type"),
        sa.CheckConstraint("quantity > 0", name="ck_maintenance_material_quantity"),
    )
    for column in ("maintenance_execution_id", "material_type"):
        op.create_index(f"ix_maintenance_materials_{column}", "maintenance_materials", [column])

    op.create_table(
        "maintenance_change_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("maintenance_execution_id", sa.Integer(), sa.ForeignKey("maintenance_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_type", sa.String(30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="requested"),
        sa.Column("quotation_item_id", sa.Integer(), sa.ForeignKey("quotation_items.id", ondelete="RESTRICT")),
        sa.Column("linked_service_order_id", sa.Integer(), sa.ForeignKey("service_orders.id", ondelete="RESTRICT")),
        sa.Column("decided_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("decision_reason", sa.Text()),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("change_type IN ('corrective','repair','investigation')", name="ck_maintenance_change_type"),
        sa.CheckConstraint("status IN ('requested','approved','rejected','overridden','linked')", name="ck_maintenance_change_status"),
    )
    for column in ("maintenance_execution_id", "change_type", "status", "quotation_item_id", "linked_service_order_id", "decided_by_id"):
        op.create_index(f"ix_maintenance_change_requests_{column}", "maintenance_change_requests", [column])


def downgrade() -> None:
    op.drop_table("maintenance_change_requests")
    op.drop_table("maintenance_materials")
    op.drop_table("maintenance_pauses")
    op.drop_table("maintenance_executions")
    op.drop_index("ix_catalog_items_maintenance_location", table_name="catalog_items")
    op.drop_index("ix_catalog_items_maintenance_type", table_name="catalog_items")
    op.drop_column("catalog_items", "maintenance_base_materials")
    op.drop_column("catalog_items", "maintenance_location")
    op.drop_column("catalog_items", "maintenance_type")
