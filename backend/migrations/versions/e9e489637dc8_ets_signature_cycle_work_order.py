"""ets signature cycle work order

Revision ID: e9e489637dc8
Revises: 28eed747a29b
Create Date: 2026-07-10 12:45:17.244296
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e9e489637dc8'
down_revision: Union[str, None] = '28eed747a29b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_order_signature_cycles",
        sa.Column("service_order_id", sa.Integer(), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column(
            "trigger",
            sa.String(length=50),
            server_default="initial",
            nullable=False,
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="confirmed",
            nullable=False,
        ),
        sa.Column(
            "technician_signature_data_url",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "client_received_signature_data_url",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "client_acceptance_signature_data_url",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "technician_signed_name",
            sa.String(length=180),
            nullable=False,
        ),
        sa.Column(
            "client_received_signed_name",
            sa.String(length=180),
            nullable=False,
        ),
        sa.Column(
            "client_acceptance_signed_name",
            sa.String(length=180),
            nullable=False,
        ),
        sa.Column(
            "technician_signed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "client_received_signed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "client_acceptance_signed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("authorized_by_id", sa.Integer(), nullable=True),
        sa.Column("authorization_comment", sa.Text(), nullable=True),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["authorized_by_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["service_order_id"],
            ["service_orders.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_service_order_signature_cycles_authorized_by_id",
        "service_order_signature_cycles",
        ["authorized_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_service_order_signature_cycles_cycle_number",
        "service_order_signature_cycles",
        ["cycle_number"],
        unique=False,
    )
    op.create_index(
        "ix_service_order_signature_cycles_service_order_id",
        "service_order_signature_cycles",
        ["service_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_service_order_signature_cycles_status",
        "service_order_signature_cycles",
        ["status"],
        unique=False,
    )

    op.create_table(
        "service_order_signature_cycle_work_orders",
        sa.Column("signature_cycle_id", sa.Integer(), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column(
            "assignment_type",
            sa.String(length=50),
            server_default="initial",
            nullable=False,
        ),
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["signature_cycle_id"],
            ["service_order_signature_cycles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["service_work_orders.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "signature_cycle_id",
            "work_order_id",
            name="uq_signature_cycle_work_order",
        ),
    )

    op.create_index(
        "ix_service_order_signature_cycle_work_orders_assignment_type",
        "service_order_signature_cycle_work_orders",
        ["assignment_type"],
        unique=False,
    )
    op.create_index(
        "ix_service_order_signature_cycle_work_orders_is_current",
        "service_order_signature_cycle_work_orders",
        ["is_current"],
        unique=False,
    )
    op.create_index(
        "ix_service_order_signature_cycle_work_orders_signature_cycle_id",
        "service_order_signature_cycle_work_orders",
        ["signature_cycle_id"],
        unique=False,
    )
    op.create_index(
        "ix_service_order_signature_cycle_work_orders_work_order_id",
        "service_order_signature_cycle_work_orders",
        ["work_order_id"],
        unique=False,
    )

    op.add_column(
        "service_orders",
        sa.Column(
            "signature_status",
            sa.String(length=30),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column(
        "service_orders",
        sa.Column(
            "signature_cycle_number",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
    )
    op.add_column(
        "service_orders",
        sa.Column(
            "signatures_confirmed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "service_orders",
        sa.Column(
            "signature_reopen_available",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "service_orders",
        sa.Column(
            "signature_reopened_by_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.add_column(
        "service_orders",
        sa.Column(
            "signature_reopened_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "service_orders",
        sa.Column(
            "signature_reopen_source",
            sa.String(length=50),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_service_orders_signature_status",
        "service_orders",
        ["signature_status"],
        unique=False,
    )
    op.create_index(
        "ix_service_orders_signature_reopened_by_id",
        "service_orders",
        ["signature_reopened_by_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_service_orders_signature_reopened_by_id_users",
        "service_orders",
        "users",
        ["signature_reopened_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_service_orders_signature_reopened_by_id_users",
        "service_orders",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_service_orders_signature_reopened_by_id",
        table_name="service_orders",
    )
    op.drop_index(
        "ix_service_orders_signature_status",
        table_name="service_orders",
    )

    op.drop_column("service_orders", "signature_reopen_source")
    op.drop_column("service_orders", "signature_reopened_at")
    op.drop_column("service_orders", "signature_reopened_by_id")
    op.drop_column("service_orders", "signature_reopen_available")
    op.drop_column("service_orders", "signatures_confirmed_at")
    op.drop_column("service_orders", "signature_cycle_number")
    op.drop_column("service_orders", "signature_status")

    op.drop_index(
        "ix_service_order_signature_cycle_work_orders_work_order_id",
        table_name="service_order_signature_cycle_work_orders",
    )
    op.drop_index(
        "ix_service_order_signature_cycle_work_orders_signature_cycle_id",
        table_name="service_order_signature_cycle_work_orders",
    )
    op.drop_index(
        "ix_service_order_signature_cycle_work_orders_is_current",
        table_name="service_order_signature_cycle_work_orders",
    )
    op.drop_index(
        "ix_service_order_signature_cycle_work_orders_assignment_type",
        table_name="service_order_signature_cycle_work_orders",
    )

    op.drop_table("service_order_signature_cycle_work_orders")

    op.drop_index(
        "ix_service_order_signature_cycles_status",
        table_name="service_order_signature_cycles",
    )
    op.drop_index(
        "ix_service_order_signature_cycles_service_order_id",
        table_name="service_order_signature_cycles",
    )
    op.drop_index(
        "ix_service_order_signature_cycles_cycle_number",
        table_name="service_order_signature_cycles",
    )
    op.drop_index(
        "ix_service_order_signature_cycles_authorized_by_id",
        table_name="service_order_signature_cycles",
    )

    op.drop_table("service_order_signature_cycles")
