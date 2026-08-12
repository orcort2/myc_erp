"""harden ETS multiple/evolved phase 1

Revision ID: a7c2e5f8b1d4
Revises: f4a1c9d2e710
"""

from alembic import op
import sqlalchemy as sa


revision = "a7c2e5f8b1d4"
down_revision = "f4a1c9d2e710"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_units",
        sa.Column("origin_service_order_item_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "service_units",
        sa.Column("initial_category", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "service_units",
        sa.Column(
            "evolution_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_foreign_key(
        "fk_service_units_origin_service_order_item_id",
        "service_units",
        "service_order_items",
        ["origin_service_order_item_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_service_units_origin_service_order_item_id",
        "service_units",
        ["origin_service_order_item_id"],
    )
    op.create_index(
        "ix_service_units_initial_category", "service_units", ["initial_category"]
    )
    op.create_index(
        "ix_service_units_evolution_enabled", "service_units", ["evolution_enabled"]
    )

    op.execute(
        sa.text(
            """
            UPDATE service_units
            SET origin_service_order_item_id = (
                    SELECT COALESCE(
                        (
                            SELECT e.service_order_item_id
                            FROM equipment e
                            WHERE e.id = service_units.equipment_id
                        ),
                        (
                            SELECT soi.id
                            FROM service_stages ss
                            JOIN service_order_items soi
                              ON soi.quotation_item_id = ss.quotation_item_id
                             AND soi.service_order_id = service_units.service_order_id
                            WHERE ss.service_unit_id = service_units.id
                            ORDER BY ss.sequence ASC
                            LIMIT 1
                        )
                    )
                ),
                initial_category = COALESCE(
                    (
                        SELECT ss.category
                        FROM service_stages ss
                        WHERE ss.service_unit_id = service_units.id
                        ORDER BY ss.sequence ASC
                        LIMIT 1
                    ),
                    'other'
                ),
                evolution_enabled = false
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE service_units su
            SET initial_category = 'general_service',
                evolution_enabled = true
            FROM service_order_items soi
            LEFT JOIN catalog_items ci ON ci.id = soi.catalog_item_id
            WHERE soi.id = su.origin_service_order_item_id
              AND (
                  lower(replace(COALESCE(ci.commodity, ''), '_', ' ')) = 'general service'
                  OR lower(COALESCE(ci.category, '')) IN ('servicio general', 'general service')
                  OR lower(COALESCE(soi.service_name, '')) IN ('servicio general', 'general service')
              )
            """
        )
    )
    op.alter_column("service_units", "initial_category", nullable=False)
    op.create_unique_constraint(
        "uq_quotation_item_decisions_item",
        "quotation_item_decisions",
        ["quotation_item_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_quotation_item_decisions_item",
        "quotation_item_decisions",
        type_="unique",
    )
    op.drop_index("ix_service_units_evolution_enabled", table_name="service_units")
    op.drop_index("ix_service_units_initial_category", table_name="service_units")
    op.drop_index(
        "ix_service_units_origin_service_order_item_id", table_name="service_units"
    )
    op.drop_constraint(
        "fk_service_units_origin_service_order_item_id",
        "service_units",
        type_="foreignkey",
    )
    op.drop_column("service_units", "evolution_enabled")
    op.drop_column("service_units", "initial_category")
    op.drop_column("service_units", "origin_service_order_item_id")
