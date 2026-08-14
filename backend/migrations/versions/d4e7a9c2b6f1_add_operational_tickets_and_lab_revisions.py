"""add operational tickets and versioned LAB reopening

Revision ID: d4e7a9c2b6f1
Revises: c6e8a1b4d2f9
Create Date: 2026-08-14
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e7a9c2b6f1"
down_revision = "c6e8a1b4d2f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_tickets",
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requested_signature_policy", sa.String(length=20), nullable=False),
        sa.Column("final_signature_policy", sa.String(length=20), nullable=True),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("type IN ('reopen_work_order')", name="ck_operational_ticket_type"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'in_progress', 'resolved', 'cancelled')",
            name="ck_operational_ticket_status",
        ),
        sa.CheckConstraint(
            "requested_signature_policy IN ('preserve', 'invalidate')",
            name="ck_operational_ticket_requested_signature_policy",
        ),
        sa.CheckConstraint(
            "final_signature_policy IS NULL OR final_signature_policy IN ('preserve', 'invalidate')",
            name="ck_operational_ticket_final_signature_policy",
        ),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["work_order_id"], ["lab_work_orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("type", "status", "work_order_id", "requested_by_user_id"):
        op.create_index(f"ix_operational_tickets_{column}", "operational_tickets", [column])

    op.add_column(
        "lab_work_orders",
        sa.Column("revision_number", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "lab_work_orders",
        sa.Column("edit_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column("lab_work_orders", sa.Column("reopened_at", sa.DateTime(timezone=True)))
    op.add_column("lab_work_orders", sa.Column("reopened_by_user_id", sa.Integer()))
    op.add_column("lab_work_orders", sa.Column("reopen_ticket_id", sa.Integer()))
    op.add_column(
        "lab_work_orders",
        sa.Column("signature_required", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "lab_work_orders",
        sa.Column("signature_preserved", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_foreign_key(
        "fk_lab_work_orders_reopened_by_user_id",
        "lab_work_orders", "users", ["reopened_by_user_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_lab_work_orders_reopen_ticket_id",
        "lab_work_orders", "operational_tickets", ["reopen_ticket_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index("ix_lab_work_orders_reopen_ticket_id", "lab_work_orders", ["reopen_ticket_id"])

    op.drop_constraint(
        "uq_lab_signature_session_root", "lab_work_order_signature_sessions", type_="unique"
    )
    op.create_unique_constraint(
        "uq_lab_signature_session_root_version",
        "lab_work_order_signature_sessions",
        ["root_work_order_id", "version"],
    )

    op.create_table(
        "lab_work_order_revisions",
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("reopen_ticket_id", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("signature_session_id", sa.Integer(), nullable=True),
        sa.Column("signature_preserved", sa.Boolean(), nullable=False),
        sa.Column("final_pdf", sa.LargeBinary(), nullable=True),
        sa.Column("final_pdf_sha256", sa.String(length=64), nullable=True),
        sa.Column("final_pdf_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["reopen_ticket_id"], ["operational_tickets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["signature_session_id"], ["lab_work_order_signature_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["work_order_id"], ["lab_work_orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_order_id", "revision_number", name="uq_lab_work_order_revision_number"),
    )
    op.create_index("ix_lab_work_order_revisions_work_order_id", "lab_work_order_revisions", ["work_order_id"])
    op.create_index("ix_lab_work_order_revisions_reopen_ticket_id", "lab_work_order_revisions", ["reopen_ticket_id"])


def downgrade() -> None:
    op.drop_index("ix_lab_work_order_revisions_reopen_ticket_id", table_name="lab_work_order_revisions")
    op.drop_index("ix_lab_work_order_revisions_work_order_id", table_name="lab_work_order_revisions")
    op.drop_table("lab_work_order_revisions")
    op.drop_constraint(
        "uq_lab_signature_session_root_version", "lab_work_order_signature_sessions", type_="unique"
    )
    op.create_unique_constraint(
        "uq_lab_signature_session_root", "lab_work_order_signature_sessions", ["root_work_order_id"]
    )
    op.drop_index("ix_lab_work_orders_reopen_ticket_id", table_name="lab_work_orders")
    op.drop_constraint("fk_lab_work_orders_reopen_ticket_id", "lab_work_orders", type_="foreignkey")
    op.drop_constraint("fk_lab_work_orders_reopened_by_user_id", "lab_work_orders", type_="foreignkey")
    for column in (
        "signature_preserved", "signature_required", "reopen_ticket_id",
        "reopened_by_user_id", "reopened_at", "edit_version", "revision_number",
    ):
        op.drop_column("lab_work_orders", column)
    for column in ("requested_by_user_id", "work_order_id", "status", "type"):
        op.drop_index(f"ix_operational_tickets_{column}", table_name="operational_tickets")
    op.drop_table("operational_tickets")
