"""add calibration scope to service order items

Revision ID: 2ffda0c6458f
Revises: c1d2e3f4a5b6
Create Date: 2026-07-01 17:37:38.550996
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2ffda0c6458f'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "service_order_items",
        sa.Column("calibration_scope", sa.String(length=60), nullable=True),
    )



def downgrade() -> None:
    op.drop_column("service_order_items", "calibration_scope")
