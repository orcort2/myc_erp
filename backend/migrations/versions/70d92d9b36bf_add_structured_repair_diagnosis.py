"""add structured repair diagnosis

Revision ID: 70d92d9b36bf
Revises: 600367248362
Create Date: 2026-08-20 15:48:26.526689
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "70d92d9b36bf"
down_revision: Union[str, None] = "600367248362"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "repair_executions",
        sa.Column(
            "diagnosis_data",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )

    op.alter_column(
        "repair_executions",
        "diagnosis_data",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column(
        "repair_executions",
        "diagnosis_data",
    )
    