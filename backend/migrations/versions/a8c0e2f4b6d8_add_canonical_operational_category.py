"""add canonical operational category

Revision ID: a8c0e2f4b6d8
Revises: f7c9d1e3a5b7
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa


revision = "a8c0e2f4b6d8"
down_revision = "f7c9d1e3a5b7"
branch_labels = None
depends_on = None


_CATEGORY_CASE = """
CASE
  WHEN item_type = 'product' THEN 'sale'
  WHEN lower(trim(category)) IN ('calibracion', 'calibración') THEN 'calibration'
  WHEN lower(trim(category)) = 'mantenimiento' THEN 'maintenance'
  WHEN lower(trim(category)) IN ('reparacion', 'reparación') THEN 'repair'
  WHEN lower(trim(category)) IN ('verificacion', 'verificación') THEN 'verification'
  WHEN lower(trim(category)) IN ('calificacion', 'calificación') THEN 'qualification'
  WHEN lower(trim(category)) IN ('validacion', 'validación') THEN 'validation'
  WHEN lower(trim(category)) IN ('capacitacion', 'capacitación') THEN 'training'
  WHEN lower(trim(category)) IN ('consultoria', 'consultoría') THEN 'consulting'
  WHEN lower(trim(category)) = 'servicio general' THEN 'general_service'
  WHEN lower(trim(category)) IN ('venta', 'patrones', 'equipos', 'accesorios', 'consumibles') THEN 'sale'
  WHEN commodity IN ('calibration','maintenance','repair','verification','qualification',
                     'validation','training','consulting','general_service','sale') THEN commodity
  ELSE NULL
END
"""


def upgrade() -> None:
    op.add_column("catalog_items", sa.Column("operational_category", sa.String(40)))
    op.add_column("quotation_items", sa.Column("operational_category", sa.String(40)))
    op.add_column("service_order_items", sa.Column("operational_category", sa.String(40)))
    op.create_index("ix_catalog_items_operational_category", "catalog_items", ["operational_category"])
    op.create_index("ix_quotation_items_operational_category", "quotation_items", ["operational_category"])
    op.create_index("ix_service_order_items_operational_category", "service_order_items", ["operational_category"])

    op.execute(f"UPDATE catalog_items SET operational_category = {_CATEGORY_CASE}")
    op.execute(
        """
        UPDATE quotation_items AS quotation_item
        SET operational_category = catalog_item.operational_category
        FROM catalog_items AS catalog_item
        WHERE quotation_item.catalog_item_id = catalog_item.id
          AND quotation_item.operational_category IS NULL
        """
    )
    op.execute(
        """
        UPDATE quotation_items
        SET operational_category = commodity
        WHERE operational_category IS NULL
          AND commodity IN ('calibration','maintenance','repair','verification','qualification',
                            'validation','training','consulting','general_service','sale')
        """
    )
    op.execute(
        """
        UPDATE service_order_items AS service_item
        SET operational_category = quotation_item.operational_category
        FROM quotation_items AS quotation_item
        WHERE service_item.quotation_item_id = quotation_item.id
          AND service_item.operational_category IS NULL
        """
    )
    op.execute(
        """
        UPDATE service_order_items AS service_item
        SET operational_category = catalog_item.operational_category
        FROM catalog_items AS catalog_item
        WHERE service_item.catalog_item_id = catalog_item.id
          AND service_item.operational_category IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_service_order_items_operational_category", table_name="service_order_items")
    op.drop_index("ix_quotation_items_operational_category", table_name="quotation_items")
    op.drop_index("ix_catalog_items_operational_category", table_name="catalog_items")
    op.drop_column("service_order_items", "operational_category")
    op.drop_column("quotation_items", "operational_category")
    op.drop_column("catalog_items", "operational_category")
