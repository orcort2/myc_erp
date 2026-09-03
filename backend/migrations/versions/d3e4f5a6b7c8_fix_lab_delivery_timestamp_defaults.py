"""fix lab delivery tables missing timestamp server defaults

Revision ID: d3e4f5a6b7c8
Revises: c2d4e6f8a0b1

c2d4e6f8a0b1 creó created_at/updated_at de lab_work_order_deliveries,
lab_delivery_items y lab_delivery_group_receipts como nullable=False pero
SIN server_default -- un drift respecto a TimestampMixin
(server_default=func.now(), nullable=False), que hoy produce un 500
(NotNullViolation) en cualquier INSERT que no fije esas columnas en Python
(p.ej. vía executemany/bulk o cualquier ruta que no pase por el ORM con
onupdate/default resuelto en memoria). Esta migración sólo agrega el
server_default equivalente; no toca nullability, no toca datos, no toca
c2d4e6f8a0b1.
"""

from alembic import op
import sqlalchemy as sa


revision = "d3e4f5a6b7c8"
down_revision = "c2d4e6f8a0b1"
branch_labels = None
depends_on = None


_TABLES = ("lab_work_order_deliveries", "lab_delivery_items", "lab_delivery_group_receipts")
_COLUMNS = ("created_at", "updated_at")


def upgrade() -> None:
    for table in _TABLES:
        for column in _COLUMNS:
            op.alter_column(
                table,
                column,
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=False,
                server_default=sa.func.now(),
            )


def downgrade() -> None:
    for table in _TABLES:
        for column in _COLUMNS:
            op.alter_column(
                table,
                column,
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=False,
                server_default=None,
            )
