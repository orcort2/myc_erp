"""add catalog items

Revision ID: a1b2c3d4e5f6
Revises: 9c0d1e2f3a14
Create Date: 2026-06-18 11:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9c0d1e2f3a14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalog_items",
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("commodity", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("internal_key", sa.String(length=80), nullable=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sat_key", sa.String(length=40), nullable=True),
        sa.Column("sat_unit", sa.String(length=40), nullable=True),
        sa.Column("internal_unit", sa.String(length=80), nullable=True),
        sa.Column("origin_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("origin_currency", sa.String(length=3), nullable=False),
        sa.Column("exchange_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("margin_percent", sa.Numeric(8, 4), nullable=False),
        sa.Column("final_price_mxn", sa.Numeric(12, 2), nullable=False),
        sa.Column("internal_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("cost_currency", sa.String(length=3), nullable=True),
        sa.Column("calibration_scope", sa.String(length=60), nullable=True),
        sa.Column("quotation_legend", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_catalog_items_id"), "catalog_items", ["id"], unique=False)
    op.create_index(op.f("ix_catalog_items_internal_key"), "catalog_items", ["internal_key"], unique=False)
    op.create_index(op.f("ix_catalog_items_name"), "catalog_items", ["name"], unique=False)
    op.create_index(op.f("ix_catalog_items_item_type"), "catalog_items", ["item_type"], unique=False)
    op.create_index(op.f("ix_catalog_items_commodity"), "catalog_items", ["commodity"], unique=False)
    op.create_index(op.f("ix_catalog_items_category"), "catalog_items", ["category"], unique=False)
    op.create_index(op.f("ix_catalog_items_is_active"), "catalog_items", ["is_active"], unique=False)
    op.create_index(
        "uq_catalog_items_internal_key_active",
        "catalog_items",
        ["internal_key"],
        unique=True,
        postgresql_where=sa.text("is_active = true AND internal_key IS NOT NULL"),
    )

    op.add_column("quotation_items", sa.Column("catalog_item_id", sa.Integer(), nullable=True))
    op.add_column("quotation_items", sa.Column("unit", sa.String(length=80), nullable=True))
    op.add_column("quotation_items", sa.Column("currency", sa.String(length=3), nullable=True))
    op.add_column("quotation_items", sa.Column("commodity", sa.String(length=40), nullable=True))
    op.add_column("quotation_items", sa.Column("calibration_scope", sa.String(length=60), nullable=True))
    op.add_column("quotation_items", sa.Column("quotation_legend", sa.Text(), nullable=True))
    op.create_index(op.f("ix_quotation_items_catalog_item_id"), "quotation_items", ["catalog_item_id"], unique=False)
    op.create_foreign_key(
        "fk_quotation_items_catalog_item_id_catalog_items",
        "quotation_items",
        "catalog_items",
        ["catalog_item_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_quotation_items_catalog_item_id_catalog_items", "quotation_items", type_="foreignkey")
    op.drop_index(op.f("ix_quotation_items_catalog_item_id"), table_name="quotation_items")
    op.drop_column("quotation_items", "quotation_legend")
    op.drop_column("quotation_items", "calibration_scope")
    op.drop_column("quotation_items", "commodity")
    op.drop_column("quotation_items", "currency")
    op.drop_column("quotation_items", "unit")
    op.drop_column("quotation_items", "catalog_item_id")

    op.drop_index("uq_catalog_items_internal_key_active", table_name="catalog_items")
    op.drop_index(op.f("ix_catalog_items_is_active"), table_name="catalog_items")
    op.drop_index(op.f("ix_catalog_items_category"), table_name="catalog_items")
    op.drop_index(op.f("ix_catalog_items_commodity"), table_name="catalog_items")
    op.drop_index(op.f("ix_catalog_items_item_type"), table_name="catalog_items")
    op.drop_index(op.f("ix_catalog_items_name"), table_name="catalog_items")
    op.drop_index(op.f("ix_catalog_items_internal_key"), table_name="catalog_items")
    op.drop_index(op.f("ix_catalog_items_id"), table_name="catalog_items")
    op.drop_table("catalog_items")
