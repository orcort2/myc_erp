"""decouple catalog type from operational category

Revision ID: e2a4c6d8f0b1
Revises: d1f3a5c7e9b2
Create Date: 2026-08-18
"""

from alembic import op


revision = "e2a4c6d8f0b1"
down_revision = "d1f3a5c7e9b2"
branch_labels = None
depends_on = None


_EXACT_CATEGORY = """
CASE
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
  WHEN lower(trim(category)) IN ('otro', 'otra') THEN 'other'
  ELSE NULL
END
"""


def upgrade() -> None:
    # Corrige únicamente catálogo vivo con categoría estructurada exacta. No toca
    # QuotationItem, ServiceOrderItem ni snapshots históricos congelados.
    op.execute(
        f"""
        UPDATE catalog_items
        SET operational_category = {_EXACT_CATEGORY}
        WHERE {_EXACT_CATEGORY} IS NOT NULL
          AND operational_category IS DISTINCT FROM {_EXACT_CATEGORY}
        """
    )


def downgrade() -> None:
    # La inferencia histórica por item_type era ambigua y no puede reconstruirse
    # sin volver a introducir el defecto; el downgrade conserva los datos corregidos.
    pass
