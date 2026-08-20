"""fix repair timestamp defaults

Revision ID: c4e0ead1af28
Revises: 62f12534fc33
Create Date: 2026-08-20 17:23:40.261761
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4e0ead1af28'
down_revision: Union[str, None] = '62f12534fc33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    for table in (
        "repair_executions",
        "repair_interventions",
        "repair_tests",
        "repair_pauses",
        "repair_change_requests",
    ):
        op.alter_column(
            table,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        )

        op.alter_column(
            table,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        )


def downgrade() -> None:
    for table in (
        "repair_executions",
        "repair_interventions",
        "repair_tests",
        "repair_pauses",
        "repair_change_requests",
    ):
        op.alter_column(
            table,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=None,
        )

        op.alter_column(
            table,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=None,
        )