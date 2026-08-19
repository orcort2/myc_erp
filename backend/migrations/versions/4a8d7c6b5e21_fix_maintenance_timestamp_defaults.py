"""fix maintenance timestamp defaults

Revision ID: 4a8d7c6b5e21
Revises: 3587a5c52827
Create Date: 2026-08-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a8d7c6b5e21"
down_revision: Union[str, None] = "3587a5c52827"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tables = (
        "maintenance_executions",
        "maintenance_pauses",
        "maintenance_materials",
        "maintenance_change_requests",
    )

    for table_name in tables:
        op.alter_column(
            table_name,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=sa.func.now(),
        )

        op.alter_column(
            table_name,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=sa.func.now(),
        )


def downgrade() -> None:
    tables = (
        "maintenance_executions",
        "maintenance_pauses",
        "maintenance_materials",
        "maintenance_change_requests",
    )

    for table_name in tables:
        op.alter_column(
            table_name,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=None,
        )

        op.alter_column(
            table_name,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=None,
        )