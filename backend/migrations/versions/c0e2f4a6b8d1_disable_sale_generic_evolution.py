"""disable generic evolution for existing sale units

Revision ID: c0e2f4a6b8d1
Revises: b9d1f3a5c7e9
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa


revision = "c0e2f4a6b8d1"
down_revision = "b9d1f3a5c7e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    service_units = sa.table(
        "service_units",
        sa.column("initial_category", sa.String()),
        sa.column("evolution_enabled", sa.Boolean()),
    )
    op.execute(
        service_units.update()
        .where(service_units.c.initial_category == "sale")
        .values(evolution_enabled=False)
    )


def downgrade() -> None:
    service_units = sa.table(
        "service_units",
        sa.column("initial_category", sa.String()),
        sa.column("evolution_enabled", sa.Boolean()),
    )
    op.execute(
        service_units.update()
        .where(service_units.c.initial_category == "sale")
        .values(evolution_enabled=True)
    )
