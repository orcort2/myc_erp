"""add operational snapshot to quotation items

Revision ID: 7b1c213129ec
Revises: ff7a8b9c0d1e
Create Date: 2026-07-23 11:57:12.501149
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b1c213129ec"
down_revision: Union[str, None] = "ff7a8b9c0d1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "quotation_items",
        sa.Column(
            "operational_snapshot",
            sa.JSON(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "quotation_items",
        "operational_snapshot",
    )