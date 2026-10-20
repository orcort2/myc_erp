"""merge quotation revision cycle and technical reports

Revision ID: ffcd7b40ac46
Revises: 69fc4e5d622e, a1b2c3d4e5f7
Create Date: 2026-10-20 10:21:55.053993
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ffcd7b40ac46'
down_revision: Union[str, None] = ('69fc4e5d622e', 'a1b2c3d4e5f7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
