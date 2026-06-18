"""complete catalog items and quotation item tax fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("catalog_items", sa.Column("custom_internal_unit", sa.String(length=80), nullable=True))
    op.add_column(
        "catalog_items",
        sa.Column("tax_object", sa.String(length=20), server_default="iva_16", nullable=False),
    )
    op.add_column(
        "catalog_items",
        sa.Column("tax_rate", sa.Numeric(5, 2), server_default="16.00", nullable=False),
    )
    op.create_index(op.f("ix_catalog_items_tax_object"), "catalog_items", ["tax_object"], unique=False)
    op.create_index(
        op.f("ix_catalog_items_origin_currency"),
        "catalog_items",
        ["origin_currency"],
        unique=False,
    )

    op.add_column("quotation_items", sa.Column("sat_key", sa.String(length=40), nullable=True))
    op.add_column("quotation_items", sa.Column("sat_unit", sa.String(length=40), nullable=True))
    op.add_column("quotation_items", sa.Column("internal_unit", sa.String(length=80), nullable=True))
    op.add_column(
        "quotation_items",
        sa.Column("discount_percent", sa.Numeric(8, 4), server_default="0.0000", nullable=False),
    )
    op.add_column("quotation_items", sa.Column("tax_object", sa.String(length=20), nullable=True))
    op.add_column(
        "quotation_items",
        sa.Column("tax_rate", sa.Numeric(5, 2), server_default="16.00", nullable=False),
    )
    op.add_column(
        "quotation_items",
        sa.Column("tax_total", sa.Numeric(12, 2), server_default="0.00", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("quotation_items", "tax_total")
    op.drop_column("quotation_items", "tax_rate")
    op.drop_column("quotation_items", "tax_object")
    op.drop_column("quotation_items", "discount_percent")
    op.drop_column("quotation_items", "internal_unit")
    op.drop_column("quotation_items", "sat_unit")
    op.drop_column("quotation_items", "sat_key")

    op.drop_index(op.f("ix_catalog_items_origin_currency"), table_name="catalog_items")
    op.drop_index(op.f("ix_catalog_items_tax_object"), table_name="catalog_items")
    op.drop_column("catalog_items", "tax_rate")
    op.drop_column("catalog_items", "tax_object")
    op.drop_column("catalog_items", "custom_internal_unit")
