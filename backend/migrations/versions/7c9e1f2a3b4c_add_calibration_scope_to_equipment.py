"""add calibration scope to equipment

Revision ID: 7c9e1f2a3b4c
Revises: 2ffda0c6458f
Create Date: 2026-07-02 09:42:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c9e1f2a3b4c"
down_revision: Union[str, None] = "2ffda0c6458f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "equipment",
        sa.Column("calibration_scope", sa.String(length=60), nullable=True),
    )
    op.create_index(
        op.f("ix_equipment_calibration_scope"),
        "equipment",
        ["calibration_scope"],
        unique=False,
    )
    op.execute(
        """
        UPDATE equipment
        SET calibration_scope = service_order_items.calibration_scope
        FROM service_order_items
        WHERE equipment.service_order_item_id = service_order_items.id
          AND equipment.calibration_scope IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_equipment_calibration_scope"), table_name="equipment")
    op.drop_column("equipment", "calibration_scope")
