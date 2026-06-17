"""expand service orders

Revision ID: 5d6e7f8a9b10
Revises: 917baf3a5378
Create Date: 2026-06-17 14:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5d6e7f8a9b10"
down_revision: Union[str, None] = "917baf3a5378"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("service_orders", sa.Column("advisor_id", sa.Integer(), nullable=True))
    op.add_column("service_orders", sa.Column("technician_id", sa.Integer(), nullable=True))
    op.alter_column("service_orders", "scheduled_date", new_column_name="agenda_date")
    op.add_column("service_orders", sa.Column("service_date", sa.Date(), nullable=True))
    op.add_column(
        "service_orders",
        sa.Column("total_equipment", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "service_orders",
        sa.Column("completed_equipment", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "service_orders",
        sa.Column("requires_payment", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.execute("UPDATE service_orders SET status = 'scheduled' WHERE status = 'open'")
    op.create_index(op.f("ix_service_orders_advisor_id"), "service_orders", ["advisor_id"], unique=False)
    op.create_index(
        op.f("ix_service_orders_technician_id"),
        "service_orders",
        ["technician_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_service_orders_advisor_id_users",
        "service_orders",
        "users",
        ["advisor_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_service_orders_technician_id_users",
        "service_orders",
        "users",
        ["technician_id"],
        ["id"],
    )
    op.alter_column("service_orders", "total_equipment", server_default=None)
    op.alter_column("service_orders", "completed_equipment", server_default=None)
    op.alter_column("service_orders", "requires_payment", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_service_orders_technician_id_users", "service_orders", type_="foreignkey")
    op.drop_constraint("fk_service_orders_advisor_id_users", "service_orders", type_="foreignkey")
    op.drop_index(op.f("ix_service_orders_technician_id"), table_name="service_orders")
    op.drop_index(op.f("ix_service_orders_advisor_id"), table_name="service_orders")
    op.drop_column("service_orders", "requires_payment")
    op.drop_column("service_orders", "completed_equipment")
    op.drop_column("service_orders", "total_equipment")
    op.drop_column("service_orders", "service_date")
    op.alter_column("service_orders", "agenda_date", new_column_name="scheduled_date")
    op.drop_column("service_orders", "technician_id")
    op.drop_column("service_orders", "advisor_id")
