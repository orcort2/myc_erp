"""create isolated temporary LAB work orders

Revision ID: c6e8a1b4d2f9
Revises: a7c2e5f8b1d4, fdc1c503a353
Create Date: 2026-08-13
"""

from alembic import op
import sqlalchemy as sa


revision = "c6e8a1b4d2f9"
down_revision = ("a7c2e5f8b1d4", "fdc1c503a353")
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "lab_work_orders",
        sa.Column("folio", sa.Integer(), nullable=False),
        sa.Column("root_work_order_id", sa.Integer(), nullable=True),
        sa.Column("previous_work_order_id", sa.Integer(), nullable=True),
        sa.Column("signature_session_id", sa.Integer(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("reception_date", sa.Date(), nullable=False),
        sa.Column("departure_date", sa.Date(), nullable=False),
        sa.Column("client_name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=False, server_default=""),
        sa.Column("contact_name", sa.String(length=180), nullable=True),
        sa.Column("contact_phone", sa.String(length=60), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state_name", sa.String(length=120), nullable=True),
        sa.Column("purchase_order", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_pdf", sa.LargeBinary(), nullable=True),
        sa.Column("final_pdf_sha256", sa.String(length=64), nullable=True),
        sa.Column("final_pdf_generated_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("folio BETWEEN 6400 AND 6999", name="ck_lab_work_order_folio_range"),
        sa.CheckConstraint("sequence_number >= 1", name="ck_lab_work_order_sequence"),
        sa.CheckConstraint(
            "status IN ('draft', 'ready_for_signatures', 'completed')",
            name="ck_lab_work_order_status",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["previous_work_order_id"], ["lab_work_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["root_work_order_id"], ["lab_work_orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folio", name="uq_lab_work_order_folio"),
        sa.UniqueConstraint("previous_work_order_id", name="uq_lab_work_order_previous"),
        sa.UniqueConstraint("root_work_order_id", "sequence_number", name="uq_lab_work_order_group_sequence"),
    )
    for column in (
        "folio",
        "root_work_order_id",
        "previous_work_order_id",
        "created_by_user_id",
        "status",
        "completed_at",
    ):
        op.create_index(f"ix_lab_work_orders_{column}", "lab_work_orders", [column])

    op.create_table(
        "lab_work_order_equipment",
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("instrument", sa.String(length=255), nullable=False),
        sa.Column("brand", sa.String(length=160), nullable=False),
        sa.Column("identification", sa.String(length=160), nullable=False),
        sa.Column("serial_number", sa.String(length=160), nullable=False),
        sa.Column("report_number", sa.String(length=160), nullable=True),
        sa.Column("is_good_condition", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("position BETWEEN 1 AND 10", name="ck_lab_equipment_position"),
        sa.ForeignKeyConstraint(["work_order_id"], ["lab_work_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_order_id", "position", name="uq_lab_equipment_position"),
    )
    op.create_index("ix_lab_work_order_equipment_work_order_id", "lab_work_order_equipment", ["work_order_id"])

    op.create_table(
        "lab_work_order_signature_sessions",
        sa.Column("root_work_order_id", sa.Integer(), nullable=False),
        sa.Column("signed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        *_timestamps(),
        sa.ForeignKeyConstraint(["root_work_order_id"], ["lab_work_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["signed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("root_work_order_id", name="uq_lab_signature_session_root"),
    )
    op.create_index(
        "ix_lab_work_order_signature_sessions_root_work_order_id",
        "lab_work_order_signature_sessions",
        ["root_work_order_id"],
    )
    op.create_index(
        "ix_lab_work_order_signature_sessions_signed_by_user_id",
        "lab_work_order_signature_sessions",
        ["signed_by_user_id"],
    )

    op.create_table(
        "lab_work_order_signatures",
        sa.Column("signature_session_id", sa.Integer(), nullable=False),
        sa.Column("signature_type", sa.String(length=20), nullable=False),
        sa.Column("signer_name", sa.String(length=180), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("signature_data_url", sa.Text(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("signature_type IN ('technician', 'client')", name="ck_lab_signature_type"),
        sa.ForeignKeyConstraint(
            ["signature_session_id"],
            ["lab_work_order_signature_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signature_session_id", "signature_type", name="uq_lab_signature_type"),
    )
    op.create_index(
        "ix_lab_work_order_signatures_signature_session_id",
        "lab_work_order_signatures",
        ["signature_session_id"],
    )
    op.create_foreign_key(
        "fk_lab_work_orders_signature_session_id",
        "lab_work_orders",
        "lab_work_order_signature_sessions",
        ["signature_session_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_lab_work_orders_signature_session_id",
        "lab_work_orders",
        ["signature_session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_lab_work_orders_signature_session_id", table_name="lab_work_orders")
    op.drop_constraint(
        "fk_lab_work_orders_signature_session_id",
        "lab_work_orders",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_lab_work_order_signatures_signature_session_id",
        table_name="lab_work_order_signatures",
    )
    op.drop_table("lab_work_order_signatures")
    op.drop_index(
        "ix_lab_work_order_signature_sessions_signed_by_user_id",
        table_name="lab_work_order_signature_sessions",
    )
    op.drop_index(
        "ix_lab_work_order_signature_sessions_root_work_order_id",
        table_name="lab_work_order_signature_sessions",
    )
    op.drop_table("lab_work_order_signature_sessions")
    op.drop_index("ix_lab_work_order_equipment_work_order_id", table_name="lab_work_order_equipment")
    op.drop_table("lab_work_order_equipment")
    for column in (
        "completed_at",
        "status",
        "created_by_user_id",
        "previous_work_order_id",
        "root_work_order_id",
        "folio",
    ):
        op.drop_index(f"ix_lab_work_orders_{column}", table_name="lab_work_orders")
    op.drop_table("lab_work_orders")
