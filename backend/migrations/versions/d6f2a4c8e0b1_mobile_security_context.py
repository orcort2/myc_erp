"""Add Mobile organizational scope and unique active membership.

Revision ID: d6f2a4c8e0b1
Revises: c4e0ead1af28
"""

from alembic import op
import sqlalchemy as sa


revision = "d6f2a4c8e0b1"
down_revision = "c4e0ead1af28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lab_work_orders", sa.Column("client_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_lab_work_orders_client_id",
        "lab_work_orders",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_lab_work_orders_client_id",
        "lab_work_orders",
        ["client_id"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM client_portal_memberships
                        WHERE status = 'active'
                        GROUP BY user_id
                        HAVING COUNT(*) > 1
                    ) THEN
                        RAISE EXCEPTION
                            'No se puede activar la regla Mobile: existen usuarios con más de una membresía activa';
                    END IF;
                END
                $$;
                """
            )
        )
    op.create_index(
        "uq_client_portal_memberships_active_user",
        "client_portal_memberships",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_client_portal_memberships_active_user",
        table_name="client_portal_memberships",
    )
    op.drop_index("ix_lab_work_orders_client_id", table_name="lab_work_orders")
    op.drop_constraint(
        "fk_lab_work_orders_client_id",
        "lab_work_orders",
        type_="foreignkey",
    )
    op.drop_column("lab_work_orders", "client_id")
