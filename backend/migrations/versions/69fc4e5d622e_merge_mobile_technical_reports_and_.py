"""merge mobile technical reports and quotation signing histories

Revision ID: 69fc4e5d622e
Revises: c6d9e2f5a8b1, f9a2b3c4d5e6
Create Date: 2026-10-19 17:20:09.354443
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '69fc4e5d622e'
down_revision: Union[str, None] = ('c6d9e2f5a8b1', 'f9a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
