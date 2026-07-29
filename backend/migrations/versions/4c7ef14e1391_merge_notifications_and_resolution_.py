"""merge notifications and resolution center heads

Revision ID: 4c7ef14e1391
Revises: b18ac098c1db, d2f4a6b8c0e3
Create Date: 2026-07-28 14:47:21.084520
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4c7ef14e1391'
down_revision: Union[str, None] = ('b18ac098c1db', 'd2f4a6b8c0e3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
