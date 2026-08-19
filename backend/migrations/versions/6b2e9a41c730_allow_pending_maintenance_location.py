"""allow pending maintenance location

Revision ID: 6b2e9a41c730
Revises: 4a8d7c6b5e21
Create Date: 2026-08-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6b2e9a41c730"
down_revision: Union[str, None] = "4a8d7c6b5e21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "maintenance_executions",
        "location_mode",
        existing_type=sa.String(length=20),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE maintenance_executions
        SET location_mode = 'laboratory'
        WHERE location_mode IS NULL
        """
    )

    op.alter_column(
        "maintenance_executions",
        "location_mode",
        existing_type=sa.String(length=20),
        nullable=False,
    )