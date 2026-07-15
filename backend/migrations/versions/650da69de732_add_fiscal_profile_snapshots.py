"""add canonical client fiscal country and invoice fiscal snapshots

Revision ID: 650da69de732
Revises: 640da69de732
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "650da69de732"
down_revision: Union[str, None] = "640da69de732"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("fiscal_country_code", sa.String(length=10), nullable=True))
    op.add_column("invoices", sa.Column("fiscal_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "fiscal_snapshot")
    op.drop_column("clients", "fiscal_country_code")
