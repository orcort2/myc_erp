"""service order source snapshot and canonical constraints

Revision ID: af2a3b4c5d6e
Revises: ae1f2a3b4c5d
Create Date: 2026-07-30 00:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "af2a3b4c5d6e"
down_revision: Union[str, None] = "ae1f2a3b4c5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("service_orders", sa.Column("source_snapshot", sa.JSON()))
    op.create_check_constraint(
        "ck_catalog_items_service_type",
        "catalog_items",
        "service_type IS NULL OR service_type IN ('accredited', 'traceable', 'linked')",
    )
    op.create_check_constraint(
        "ck_institutional_folio_next_value",
        "institutional_folio_sequences",
        "next_value >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_institutional_folio_next_value",
        "institutional_folio_sequences",
        type_="check",
    )
    op.drop_constraint(
        "ck_catalog_items_service_type",
        "catalog_items",
        type_="check",
    )
    op.drop_column("service_orders", "source_snapshot")
