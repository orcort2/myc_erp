"""phase 14 additional equipment reconciliation

Revision ID: 7b8c9d0e1f2a
Revises: 6ae1d4877cdb
Create Date: 2026-07-29 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b8c9d0e1f2a"
down_revision: Union[str, None] = "6ae1d4877cdb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "equipment",
        sa.Column("resolution_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "equipment",
        sa.Column(
            "resolution_reconciliation_id",
            sa.String(length=160),
            nullable=True,
        ),
    )
    op.add_column(
        "equipment",
        sa.Column(
            "resolution_request_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_equipment_resolution_id_resolutions",
        "equipment",
        "resolutions",
        ["resolution_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_equipment_resolution_id",
        "equipment",
        ["resolution_id"],
        unique=False,
    )
    op.create_index(
        "ix_equipment_resolution_reconciliation_id",
        "equipment",
        ["resolution_reconciliation_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_equipment_resolution_reconciliation_id",
        table_name="equipment",
    )
    op.drop_index("ix_equipment_resolution_id", table_name="equipment")
    op.drop_constraint(
        "fk_equipment_resolution_id_resolutions",
        "equipment",
        type_="foreignkey",
    )
    op.drop_column("equipment", "resolution_request_hash")
    op.drop_column("equipment", "resolution_reconciliation_id")
    op.drop_column("equipment", "resolution_id")
