"""Add anticipated LAB group requests and explicit operator ownership.

Revision ID: e7a3c5d9f1b2
Revises: d6f2a4c8e0b1
"""

from alembic import op
import sqlalchemy as sa


revision = "e7a3c5d9f1b2"
down_revision = "d6f2a4c8e0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("lab_work_orders", "client_id", new_column_name="operator_client_id")
    op.drop_index("ix_lab_work_orders_client_id", table_name="lab_work_orders")
    op.create_index("ix_lab_work_orders_operator_client_id", "lab_work_orders", ["operator_client_id"])

    op.create_table(
        "lab_work_order_group_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("operator_client_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("handled_by_user_id", sa.Integer()),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decision_reason", sa.Text()),
        sa.Column("root_work_order_id", sa.Integer(), unique=True),
        sa.Column("conversation_id", sa.Integer(), unique=True),
        sa.Column("reception_date", sa.Date(), nullable=False),
        sa.Column("departure_date", sa.Date(), nullable=False),
        sa.Column("client_name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text(), nullable=False, server_default=""),
        sa.Column("contact_name", sa.String(180)),
        sa.Column("contact_phone", sa.String(60)),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("postal_code", sa.String(20)),
        sa.Column("city", sa.String(120)),
        sa.Column("state_name", sa.String(120)),
        sa.Column("purchase_order", sa.String(120)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("quantity BETWEEN 1 AND 50", name="ck_lab_group_request_quantity"),
        sa.CheckConstraint("status IN ('pending', 'in_review', 'approved', 'rejected')", name="ck_lab_group_request_status"),
        sa.ForeignKeyConstraint(["operator_client_id"], ["clients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["handled_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["root_work_order_id"], ["lab_work_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["conversation_id"], ["communication_conversations.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_lab_work_order_group_requests_operator_client_id", "lab_work_order_group_requests", ["operator_client_id"])
    op.create_index("ix_lab_work_order_group_requests_requested_by_user_id", "lab_work_order_group_requests", ["requested_by_user_id"])
    op.create_index("ix_lab_work_order_group_requests_handled_by_user_id", "lab_work_order_group_requests", ["handled_by_user_id"])
    op.create_index("ix_lab_work_order_group_requests_status", "lab_work_order_group_requests", ["status"])


def downgrade() -> None:
    op.drop_table("lab_work_order_group_requests")
    op.drop_index("ix_lab_work_orders_operator_client_id", table_name="lab_work_orders")
    op.alter_column("lab_work_orders", "operator_client_id", new_column_name="client_id")
    op.create_index("ix_lab_work_orders_client_id", "lab_work_orders", ["client_id"])
