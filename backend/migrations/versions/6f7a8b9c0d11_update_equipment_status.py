"""update equipment status

Revision ID: 6f7a8b9c0d11
Revises: 5d6e7f8a9b10
Create Date: 2026-06-17 14:45:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "6f7a8b9c0d11"
down_revision: Union[str, None] = "5d6e7f8a9b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE equipment SET status = 'registered' WHERE status = 'pending'")


def downgrade() -> None:
    op.execute("UPDATE equipment SET status = 'pending' WHERE status = 'registered'")
