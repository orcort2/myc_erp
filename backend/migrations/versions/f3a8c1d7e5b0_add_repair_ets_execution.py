"""add repair ETS execution

Revision ID: f3a8c1d7e5b0
Revises: 6b2e9a41c730
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a8c1d7e5b0"
down_revision: Union[str, None] = "6b2e9a41c730"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "repair_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_order_id", sa.Integer(), sa.ForeignKey("service_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_order_item_id", sa.Integer(), sa.ForeignKey("service_order_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_unit_id", sa.Integer(), sa.ForeignKey("service_units.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_stage_id", sa.Integer(), sa.ForeignKey("service_stages.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("origin", sa.String(30), nullable=False),
        sa.Column("source_maintenance_change_request_id", sa.Integer(), sa.ForeignKey("maintenance_change_requests.id", ondelete="RESTRICT")),
        sa.Column("configuration_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending_arrival"),
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("diagnosis_notes", sa.Text()),
        sa.Column("diagnosis_completed_at", sa.DateTime(timezone=True)),
        sa.Column("conclusion", sa.String(30)),
        sa.Column("conclusion_reason", sa.Text()),
        sa.Column("technical_completed_at", sa.DateTime(timezone=True)),
        sa.Column("report_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("report_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("report_generated_at", sa.DateTime(timezone=True)),
        sa.Column("signed_report_version", sa.Integer()),
        sa.Column("signer_name", sa.String(180)),
        sa.Column("signature_data_url", sa.Text()),
        sa.Column("signed_at", sa.DateTime(timezone=True)),
        sa.Column("client_decision", sa.String(30)),
        sa.Column("sla_due_at", sa.DateTime(timezone=True)),
        sa.Column("warranty_reopened_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("original_closed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_after_intervention", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("cancellation_reason", sa.Text()),
        sa.Column("linked_calibration_stage_id", sa.Integer(), sa.ForeignKey("service_stages.id", ondelete="RESTRICT")),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("origin IN ('quotation','maintenance_linked')", name="ck_repair_origin"),
        sa.CheckConstraint(
            "status IN ('pending_arrival','pending_assignment','assigned','in_evaluation',"
            "'in_repair','testing','technically_completed','equipment_not_suitable',"
            "'pending_release','closed','cancelled')",
            name="ck_repair_status",
        ),
        sa.CheckConstraint(
            "conclusion IS NULL OR conclusion IN ('repaired','equipment_not_suitable')",
            name="ck_repair_conclusion",
        ),
        sa.UniqueConstraint("service_unit_id", name="uq_repair_execution_unit"),
        sa.UniqueConstraint("service_stage_id", name="uq_repair_execution_stage"),
    )
    for column in (
        "service_order_id", "service_order_item_id", "service_unit_id", "service_stage_id",
        "origin", "source_maintenance_change_request_id", "status", "technician_id",
        "linked_calibration_stage_id",
    ):
        op.create_index(f"ix_repair_executions_{column}", "repair_executions", [column])
    op.create_index("ix_repair_execution_order_status", "repair_executions", ["service_order_id", "status"])

    op.create_table(
        "repair_interventions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repair_execution_id", sa.Integer(), sa.ForeignKey("repair_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("removed_components", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.String(20)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("outcome IS NULL OR outcome IN ('effective','partial','ineffective')", name="ck_repair_intervention_outcome"),
        sa.UniqueConstraint("repair_execution_id", "sequence", name="uq_repair_intervention_sequence"),
    )
    for column in ("repair_execution_id", "sequence", "technician_id"):
        op.create_index(f"ix_repair_interventions_{column}", "repair_interventions", [column])

    op.create_table(
        "repair_tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repair_execution_id", sa.Integer(), sa.ForeignKey("repair_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("intervention_id", sa.Integer(), sa.ForeignKey("repair_interventions.id", ondelete="RESTRICT")),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("test_type", sa.String(60), nullable=False),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("performed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("result IN ('pass','fail','inconclusive')", name="ck_repair_test_result"),
        sa.UniqueConstraint("repair_execution_id", "sequence", name="uq_repair_test_sequence"),
    )
    for column in ("repair_execution_id", "intervention_id", "sequence", "result", "performed_by_id"):
        op.create_index(f"ix_repair_tests_{column}", "repair_tests", [column])

    op.create_table(
        "repair_pauses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repair_execution_id", sa.Integer(), sa.ForeignKey("repair_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pause_type", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("responsible_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tentative_resume_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("resolution", sa.Text()),
        sa.Column("resolved_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint(
            "pause_type IN ('spare_part','authorization','client_decision','administrative_investigation')",
            name="ck_repair_pause_type",
        ),
        sa.CheckConstraint("status IN ('active','resolved')", name="ck_repair_pause_status"),
    )
    for column in ("repair_execution_id", "pause_type", "responsible_user_id", "status", "resolved_by_id"):
        op.create_index(f"ix_repair_pauses_{column}", "repair_pauses", [column])

    op.create_table(
        "repair_change_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repair_execution_id", sa.Integer(), sa.ForeignKey("repair_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_type", sa.String(30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="requested"),
        sa.Column("quotation_item_id", sa.Integer(), sa.ForeignKey("quotation_items.id", ondelete="RESTRICT")),
        sa.Column("linked_service_order_id", sa.Integer(), sa.ForeignKey("service_orders.id", ondelete="RESTRICT")),
        sa.Column("decided_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("decision_reason", sa.Text()),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("change_type IN ('additional_scope','investigation')", name="ck_repair_change_type"),
        sa.CheckConstraint("status IN ('requested','approved','rejected','linked')", name="ck_repair_change_status"),
    )
    for column in ("repair_execution_id", "change_type", "status", "quotation_item_id", "linked_service_order_id", "decided_by_id"):
        op.create_index(f"ix_repair_change_requests_{column}", "repair_change_requests", [column])


def downgrade() -> None:
    op.drop_table("repair_change_requests")
    op.drop_table("repair_pauses")
    op.drop_table("repair_tests")
    op.drop_table("repair_interventions")
    op.drop_table("repair_executions")
