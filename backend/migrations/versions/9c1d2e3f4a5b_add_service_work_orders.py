"""add service work orders

Revision ID: 9c1d2e3f4a5b
Revises: 3c4d5e6f7a8b
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "9c1d2e3f4a5b"
down_revision = "3c4d5e6f7a8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_work_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("service_order_id", sa.Integer(), nullable=False),
        sa.Column("work_order_number", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=60), nullable=False, server_default="pending"),
        sa.Column("equipment_limit", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_order_number"),
    )

    op.create_index(
        "ix_service_work_orders_service_order_id",
        "service_work_orders",
        ["service_order_id"],
    )
    op.create_index(
        "ix_service_work_orders_work_order_number",
        "service_work_orders",
        ["work_order_number"],
    )
    op.create_index(
        "ix_service_work_orders_sequence",
        "service_work_orders",
        ["sequence"],
    )
    op.create_index(
        "ix_service_work_orders_status",
        "service_work_orders",
        ["status"],
    )

    op.add_column(
        "equipment",
        sa.Column("work_order_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_equipment_work_order_id",
        "equipment",
        ["work_order_id"],
    )
    op.create_foreign_key(
        "fk_equipment_work_order_id_service_work_orders",
        "equipment",
        "service_work_orders",
        ["work_order_id"],
        ["id"],
    )

    # Migrar datos existentes:
    # Cada service_order existente recibe una service_work_order equivalente
    # usando su work_order_number legacy.
    op.execute(
        """
        INSERT INTO service_work_orders (
            created_at,
            updated_at,
            is_active,
            deleted_at,
            deleted_by,
            service_order_id,
            work_order_number,
            sequence,
            status,
            equipment_limit,
            notes
        )
        SELECT
            COALESCE(created_at, now()),
            COALESCE(updated_at, now()),
            is_active,
            deleted_at,
            deleted_by,
            id,
            work_order_number,
            1,
            CASE
                WHEN status IN ('closed', 'cancelled') THEN status
                ELSE 'pending'
            END,
            10,
            NULL
        FROM service_orders
        WHERE work_order_number IS NOT NULL
        """
    )

    # Asignar equipos existentes a la OT migrada de su orden de servicio.
    op.execute(
        """
        UPDATE equipment
        SET work_order_id = service_work_orders.id
        FROM service_work_orders
        WHERE equipment.service_order_id = service_work_orders.service_order_id
          AND service_work_orders.sequence = 1
          AND equipment.work_order_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_equipment_work_order_id_service_work_orders",
        "equipment",
        type_="foreignkey",
    )
    op.drop_index("ix_equipment_work_order_id", table_name="equipment")
    op.drop_column("equipment", "work_order_id")

    op.drop_index("ix_service_work_orders_status", table_name="service_work_orders")
    op.drop_index("ix_service_work_orders_sequence", table_name="service_work_orders")
    op.drop_index("ix_service_work_orders_work_order_number", table_name="service_work_orders")
    op.drop_index("ix_service_work_orders_service_order_id", table_name="service_work_orders")
    op.drop_table("service_work_orders")