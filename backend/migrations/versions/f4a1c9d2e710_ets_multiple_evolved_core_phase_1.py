"""add ETS multiple/evolved core phase 1

Revision ID: f4a1c9d2e710
Revises: e7b62b8a9421
"""

from alembic import op
import sqlalchemy as sa


revision = "f4a1c9d2e710"
down_revision = "e7b62b8a9421"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "quotation_item_decisions",
        sa.Column("quotation_item_id", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("decided_by_id", sa.Integer(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False, server_default="internal"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("enabled_stage_categories", sa.JSON(), nullable=False, server_default="[]"),
        *_timestamps(),
        sa.CheckConstraint(
            "decision IN ('approved','rejected')",
            name="ck_quotation_item_decisions_decision",
        ),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["quotation_item_id"], ["quotation_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotation_item_decisions_quotation_item_id", "quotation_item_decisions", ["quotation_item_id"])
    op.create_index("ix_quotation_item_decisions_decision", "quotation_item_decisions", ["decision"])
    op.create_index("ix_quotation_item_decisions_decided_by_id", "quotation_item_decisions", ["decided_by_id"])

    op.create_table(
        "service_units",
        sa.Column("service_order_id", sa.Integer(), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=180), nullable=False, server_default="Equipo"),
        sa.Column("brand", sa.String(length=120), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("serial_number", sa.String(length=120), nullable=True),
        sa.Column("identification_status", sa.String(length=30), nullable=False, server_default="partial"),
        sa.Column("identification_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["work_order_id"], ["service_work_orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("equipment_id", name="uq_service_units_equipment_id"),
    )
    op.create_index("ix_service_units_service_order_id", "service_units", ["service_order_id"])
    op.create_index("ix_service_units_work_order_id", "service_units", ["work_order_id"])
    op.create_index("ix_service_units_equipment_id", "service_units", ["equipment_id"])
    op.create_index("ix_service_units_serial_number", "service_units", ["serial_number"])
    op.create_index("ix_service_units_identification_status", "service_units", ["identification_status"])
    op.create_index("ix_service_units_status", "service_units", ["status"])
    op.create_index("ix_service_units_ets_status", "service_units", ["service_order_id", "status"])

    op.create_table(
        "service_stages",
        sa.Column("service_unit_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("origin", sa.String(length=40), nullable=False),
        sa.Column("source_stage_id", sa.Integer(), nullable=True),
        sa.Column("quotation_item_id", sa.Integer(), nullable=True),
        sa.Column("commercial_decision_id", sa.Integer(), nullable=True),
        sa.Column("responsible_user_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_summary", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "category IN ('diagnosis','repair','maintenance','calibration','verification','qualification','validation','training','consulting','other')",
            name="ck_service_stages_category",
        ),
        sa.CheckConstraint(
            "status IN ('planned','pending_quote','pending_approval','authorized','in_progress','paused','completed','client_rejected','not_executable','exception_closed','cancelled')",
            name="ck_service_stages_status",
        ),
        sa.ForeignKeyConstraint(["commercial_decision_id"], ["quotation_item_decisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["quotation_item_id"], ["quotation_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_unit_id"], ["service_units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_stage_id"], ["service_stages.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_unit_id", "sequence", name="uq_service_stage_sequence"),
    )
    for column in ("service_unit_id", "sequence", "category", "status", "origin", "source_stage_id", "quotation_item_id", "commercial_decision_id", "responsible_user_id"):
        op.create_index(f"ix_service_stages_{column}", "service_stages", [column])
    op.create_index("ix_service_stages_unit_status", "service_stages", ["service_unit_id", "status"])
    op.create_index("ix_service_stages_category_status", "service_stages", ["category", "status"])

    op.create_table(
        "technical_service_requests",
        sa.Column("service_order_id", sa.Integer(), nullable=False),
        sa.Column("service_unit_id", sa.Integer(), nullable=False),
        sa.Column("source_stage_id", sa.Integer(), nullable=False),
        sa.Column("source_message_id", sa.Integer(), nullable=True),
        sa.Column("requested_by_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="requested"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("requested_categories", sa.JSON(), nullable=False, server_default="[]"),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('requested','quoting','quoted','partially_approved','approved','rejected','cancelled')",
            name="ck_technical_service_requests_status",
        ),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_unit_id"], ["service_units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_message_id"], ["activity_messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_stage_id"], ["service_stages.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_message_id", name="uq_technical_request_source_message"),
    )
    for column in ("service_order_id", "service_unit_id", "source_stage_id", "source_message_id", "requested_by_id", "status"):
        op.create_index(f"ix_technical_service_requests_{column}", "technical_service_requests", [column])
    op.create_index("ix_technical_requests_ets_status", "technical_service_requests", ["service_order_id", "status"])

    op.add_column("quotation_items", sa.Column("source_service_order_id", sa.Integer(), nullable=True))
    op.add_column("quotation_items", sa.Column("source_service_unit_id", sa.Integer(), nullable=True))
    op.add_column("quotation_items", sa.Column("source_stage_id", sa.Integer(), nullable=True))
    op.add_column("quotation_items", sa.Column("technical_request_id", sa.Integer(), nullable=True))
    op.add_column("quotation_items", sa.Column("equipment_snapshot", sa.JSON(), nullable=True))
    for column, target in (
        ("source_service_order_id", "service_orders.id"),
        ("source_service_unit_id", "service_units.id"),
        ("source_stage_id", "service_stages.id"),
        ("technical_request_id", "technical_service_requests.id"),
    ):
        op.create_index(f"ix_quotation_items_{column}", "quotation_items", [column])
        op.create_foreign_key(
            f"fk_quotation_items_{column}", "quotation_items", target.split(".")[0],
            [column], [target.split(".")[1]], ondelete="RESTRICT",
        )

    op.create_table(
        "service_stage_documents",
        sa.Column("service_stage_id", sa.Integer(), nullable=False),
        sa.Column("controlled_document_id", sa.Integer(), nullable=True),
        sa.Column("document_role", sa.String(length=40), nullable=False, server_default="evidence"),
        sa.Column("external_reference", sa.String(length=255), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["controlled_document_id"], ["controlled_documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_stage_id"], ["service_stages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_stage_id", "controlled_document_id", "document_role", name="uq_service_stage_document_role"),
    )
    op.create_index("ix_service_stage_documents_service_stage_id", "service_stage_documents", ["service_stage_id"])
    op.create_index("ix_service_stage_documents_controlled_document_id", "service_stage_documents", ["controlled_document_id"])

    op.create_table(
        "service_tasks",
        sa.Column("source_message_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("service_order_id", sa.Integer(), nullable=True),
        sa.Column("service_unit_id", sa.Integer(), nullable=True),
        sa.Column("service_stage_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("status IN ('open','in_progress','completed','cancelled')", name="ck_service_tasks_status"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_stage_id"], ["service_stages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_unit_id"], ["service_units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_message_id"], ["activity_messages.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_message_id", name="uq_service_tasks_source_message"),
    )
    for column in ("source_message_id", "created_by_id", "service_order_id", "service_unit_id", "service_stage_id", "status"):
        op.create_index(f"ix_service_tasks_{column}", "service_tasks", [column])
    op.create_index("ix_service_tasks_context", "service_tasks", ["service_order_id", "service_unit_id", "service_stage_id"])

    op.create_table(
        "service_task_assignees",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["task_id"], ["service_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "user_id", name="uq_service_task_assignee"),
    )
    op.create_index("ix_service_task_assignees_task_id", "service_task_assignees", ["task_id"])
    op.create_index("ix_service_task_assignees_user_id", "service_task_assignees", ["user_id"])

    # Compatibilidad: cada equipo de calibración ya ligado a una OT obtiene una
    # unidad estable y una etapa histórica sin alterar Equipment ni su lifecycle.
    op.execute(
        sa.text(
            """
            INSERT INTO service_units (
                service_order_id, work_order_id, equipment_id, name, brand, model,
                serial_number, identification_status, status, created_at, updated_at
            )
            SELECT e.service_order_id, e.work_order_id, e.id, e.name, e.brand, e.model,
                   e.serial_number,
                   CASE WHEN e.brand IS NOT NULL AND e.model IS NOT NULL AND e.serial_number IS NOT NULL
                        THEN 'complete' ELSE 'partial' END,
                   CASE WHEN e.is_active THEN 'active' ELSE 'cancelled' END,
                   e.created_at, e.updated_at
            FROM equipment e
            WHERE e.work_order_id IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO service_stages (
                service_unit_id, sequence, category, status, origin,
                quotation_item_id, started_at, completed_at, created_at, updated_at
            )
            SELECT su.id, 1, 'calibration',
                   CASE
                       WHEN e.status IN ('labeled', 'calibrated') THEN 'completed'
                       WHEN e.status = 'realizing' THEN 'in_progress'
                       WHEN e.status IN ('not_done', 'cancelled') THEN 'not_executable'
                       ELSE 'authorized'
                   END,
                   'legacy_calibration', soi.quotation_item_id,
                   CASE WHEN e.status IN ('realizing','calibrated','labeled') THEN e.updated_at ELSE NULL END,
                   CASE WHEN e.status IN ('calibrated','labeled') THEN e.updated_at ELSE NULL END,
                   e.created_at, e.updated_at
            FROM service_units su
            JOIN equipment e ON e.id = su.equipment_id
            LEFT JOIN service_order_items soi ON soi.id = e.service_order_item_id
            """
        )
    )


def downgrade() -> None:
    op.drop_table("service_task_assignees")
    op.drop_table("service_tasks")
    op.drop_table("service_stage_documents")
    for column in ("technical_request_id", "source_stage_id", "source_service_unit_id", "source_service_order_id"):
        op.drop_constraint(f"fk_quotation_items_{column}", "quotation_items", type_="foreignkey")
        op.drop_index(f"ix_quotation_items_{column}", table_name="quotation_items")
    for column in ("equipment_snapshot", "technical_request_id", "source_stage_id", "source_service_unit_id", "source_service_order_id"):
        op.drop_column("quotation_items", column)
    op.drop_table("technical_service_requests")
    op.drop_table("service_stages")
    op.drop_table("service_units")
    op.drop_table("quotation_item_decisions")
