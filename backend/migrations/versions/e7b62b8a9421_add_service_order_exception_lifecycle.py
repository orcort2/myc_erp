"""add service order exception lifecycle

Revision ID: e7b62b8a9421
Revises: c8a51e2d7f40
"""

from alembic import op
import sqlalchemy as sa


revision = "e7b62b8a9421"
down_revision = "c8a51e2d7f40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_order_exception_requests",
        sa.Column("service_order_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_id", sa.Integer(), nullable=False),
        sa.Column("authorized_by_id", sa.Integer(), nullable=True),
        sa.Column("executed_by_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="requested", nullable=False),
        sa.Column("source_stage", sa.String(length=80), nullable=False),
        sa.Column("target_stage", sa.String(length=80), nullable=False),
        sa.Column("target_status", sa.String(length=60), nullable=True),
        sa.Column("service_order_status_at_request", sa.String(length=60), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("authorization_comment", sa.Text(), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('requested', 'authorized', 'executed', 'rejected')",
            name="ck_service_order_exception_requests_status",
        ),
        sa.ForeignKeyConstraint(["authorized_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["executed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_service_order_exception_requests_id"), "service_order_exception_requests", ["id"], unique=False)
    op.create_index(op.f("ix_service_order_exception_requests_service_order_id"), "service_order_exception_requests", ["service_order_id"], unique=False)
    op.create_index(op.f("ix_service_order_exception_requests_requested_by_id"), "service_order_exception_requests", ["requested_by_id"], unique=False)
    op.create_index(op.f("ix_service_order_exception_requests_authorized_by_id"), "service_order_exception_requests", ["authorized_by_id"], unique=False)
    op.create_index(op.f("ix_service_order_exception_requests_executed_by_id"), "service_order_exception_requests", ["executed_by_id"], unique=False)
    op.create_index(op.f("ix_service_order_exception_requests_status"), "service_order_exception_requests", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_service_order_exception_requests_status"), table_name="service_order_exception_requests")
    op.drop_index(op.f("ix_service_order_exception_requests_executed_by_id"), table_name="service_order_exception_requests")
    op.drop_index(op.f("ix_service_order_exception_requests_authorized_by_id"), table_name="service_order_exception_requests")
    op.drop_index(op.f("ix_service_order_exception_requests_requested_by_id"), table_name="service_order_exception_requests")
    op.drop_index(op.f("ix_service_order_exception_requests_service_order_id"), table_name="service_order_exception_requests")
    op.drop_index(op.f("ix_service_order_exception_requests_id"), table_name="service_order_exception_requests")
    op.drop_table("service_order_exception_requests")
