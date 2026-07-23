"""add normalized composite catalog services

Revision ID: ff7a8b9c0d1e
Revises: fe6f7a8b9c0d
Create Date: 2026-07-22 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "ff7a8b9c0d1e"
down_revision = "fe6f7a8b9c0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catalog_items",
        sa.Column(
            "service_kind",
            sa.String(length=20),
            nullable=False,
            server_default="simple",
        ),
    )
    op.create_index(
        "ix_catalog_items_service_kind",
        "catalog_items",
        ["service_kind"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_catalog_items_service_kind",
        "catalog_items",
        "service_kind IN ('simple', 'composite')",
    )

    op.create_table(
        "catalog_item_components",
        sa.Column("parent_catalog_item_id", sa.Integer(), nullable=False),
        sa.Column("component_catalog_item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "parent_catalog_item_id <> component_catalog_item_id",
            name="ck_catalog_item_component_not_self",
        ),
        sa.CheckConstraint(
            "quantity >= 1",
            name="ck_catalog_item_component_quantity_positive",
        ),
        sa.ForeignKeyConstraint(
            ["component_catalog_item_id"],
            ["catalog_items.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_catalog_item_id"],
            ["catalog_items.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "parent_catalog_item_id",
            "component_catalog_item_id",
            name="uq_catalog_item_component_parent_child",
        ),
    )
    op.create_index(
        "ix_catalog_item_components_id",
        "catalog_item_components",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_catalog_item_components_parent_catalog_item_id",
        "catalog_item_components",
        ["parent_catalog_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_catalog_item_components_component_catalog_item_id",
        "catalog_item_components",
        ["component_catalog_item_id"],
        unique=False,
    )

    op.add_column(
        "service_order_items",
        sa.Column("catalog_item_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_service_order_items_catalog_item_id",
        "service_order_items",
        "catalog_items",
        ["catalog_item_id"],
        ["id"],
    )
    op.create_index(
        "ix_service_order_items_catalog_item_id",
        "service_order_items",
        ["catalog_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_service_order_items_catalog_item_id",
        table_name="service_order_items",
    )
    op.drop_constraint(
        "fk_service_order_items_catalog_item_id",
        "service_order_items",
        type_="foreignkey",
    )
    op.drop_column("service_order_items", "catalog_item_id")

    op.drop_index(
        "ix_catalog_item_components_component_catalog_item_id",
        table_name="catalog_item_components",
    )
    op.drop_index(
        "ix_catalog_item_components_parent_catalog_item_id",
        table_name="catalog_item_components",
    )
    op.drop_index(
        "ix_catalog_item_components_id",
        table_name="catalog_item_components",
    )
    op.drop_table("catalog_item_components")

    op.drop_constraint(
        "ck_catalog_items_service_kind",
        "catalog_items",
        type_="check",
    )
    op.drop_index("ix_catalog_items_service_kind", table_name="catalog_items")
    op.drop_column("catalog_items", "service_kind")
