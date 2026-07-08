"""add field sheet work order id

Revision ID: 9d2e3f4a5b6c
Revises: 9c1d2e3f4a5b
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "9d2e3f4a5b6c"
down_revision = "9c1d2e3f4a5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "field_sheets",
        sa.Column("work_order_id", sa.Integer(), nullable=True),
    )

    op.create_index(
        "ix_field_sheets_work_order_id",
        "field_sheets",
        ["work_order_id"],
    )

    op.create_foreign_key(
        "fk_field_sheets_work_order_id_service_work_orders",
        "field_sheets",
        "service_work_orders",
        ["work_order_id"],
        ["id"],
    )

    # Migrar hojas existentes usando la OT ya asignada al equipo.
    op.execute(
        """
        UPDATE field_sheets
        SET work_order_id = equipment.work_order_id,
            work_order_number = COALESCE(field_sheets.work_order_number, service_work_orders.work_order_number)
        FROM equipment
        LEFT JOIN service_work_orders
            ON service_work_orders.id = equipment.work_order_id
        WHERE field_sheets.equipment_id = equipment.id
          AND field_sheets.work_order_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_field_sheets_work_order_id_service_work_orders",
        "field_sheets",
        type_="foreignkey",
    )
    op.drop_index("ix_field_sheets_work_order_id", table_name="field_sheets")
    op.drop_column("field_sheets", "work_order_id")