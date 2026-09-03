"""add lab work order deliveries

Revision ID: c2d4e6f8a0b1
Revises: 9f3a2c7d1e84
"""

from alembic import op
import sqlalchemy as sa


revision = "c2d4e6f8a0b1"
down_revision = "9f3a2c7d1e84"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("lab_work_orders", "departure_date", existing_type=sa.Date(), nullable=True)
    op.alter_column("lab_work_order_group_requests", "departure_date", existing_type=sa.Date(), nullable=True)
    op.create_table(
        "lab_work_order_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_by_user_id", sa.Integer(), nullable=False),
        sa.Column("recipient_name", sa.String(length=180), nullable=False),
        sa.Column("recipient_signature_data_url", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by_user_id", sa.Integer(), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.Column("voucher_pdf", sa.LargeBinary(), nullable=True),
        sa.Column("voucher_pdf_sha256", sa.String(length=64), nullable=True),
        sa.Column("voucher_pdf_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('completed', 'voided')", name="ck_lab_work_order_delivery_status"),
        sa.ForeignKeyConstraint(["delivered_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["voided_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["work_order_id"], ["lab_work_orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lab_work_order_deliveries_id", "lab_work_order_deliveries", ["id"])
    op.create_index("ix_lab_work_order_deliveries_work_order_id", "lab_work_order_deliveries", ["work_order_id"])
    op.create_index("ix_lab_work_order_deliveries_delivered_by_user_id", "lab_work_order_deliveries", ["delivered_by_user_id"])
    op.create_index("ix_lab_work_order_deliveries_status", "lab_work_order_deliveries", ["status"])
    op.create_index(
        "uq_lab_work_order_delivery_active",
        "lab_work_order_deliveries",
        ["work_order_id"],
        unique=True,
        postgresql_where=sa.text("status = 'completed'"),
    )


def downgrade() -> None:
    connection = op.get_bind()
    active = connection.scalar(sa.text("SELECT count(*) FROM lab_work_order_deliveries"))
    if active:
        raise RuntimeError("No se puede revertir: existen acuses de entrega LAB que deben conservarse")
    legacy_nulls = connection.scalar(sa.text("SELECT count(*) FROM lab_work_orders WHERE departure_date IS NULL"))
    request_nulls = connection.scalar(sa.text("SELECT count(*) FROM lab_work_order_group_requests WHERE departure_date IS NULL"))
    if legacy_nulls or request_nulls:
        raise RuntimeError("No se puede revertir: existen OT o solicitudes sin fecha de salida")
    op.drop_table("lab_work_order_deliveries")
    op.alter_column("lab_work_order_group_requests", "departure_date", existing_type=sa.Date(), nullable=False)
    op.alter_column("lab_work_orders", "departure_date", existing_type=sa.Date(), nullable=False)
