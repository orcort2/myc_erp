"""fix sale execution timestamp defaults

Revision ID: 3587a5c52827
Revises: e2a4c6d8f0b1
Create Date: 2026-08-18 18:09:48.534726
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3587a5c52827'
down_revision: Union[str, None] = 'e2a4c6d8f0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tables = (
        "sale_order_items",
        "sale_unit_states",
        "sale_authorizations",
        "sale_deliveries",
        "sale_delivery_lines",
    )

    for table_name in tables:
        op.alter_column(
            table_name,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=sa.func.now(),
        )

        op.alter_column(
            table_name,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=sa.func.now(),
        )


def downgrade() -> None:
    tables = (
        "sale_order_items",
        "sale_unit_states",
        "sale_authorizations",
        "sale_deliveries",
        "sale_delivery_lines",
    )

    for table_name in tables:
        op.alter_column(
            table_name,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=None,
        )

        op.alter_column(
            table_name,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=None,
        )