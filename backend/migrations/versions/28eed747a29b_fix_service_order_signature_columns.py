"""fix_service_order_signature_columns

Revision ID: 28eed747a29b
Revises: c3fb78821edc
Create Date: 2026-07-09 11:34:05.132290
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '28eed747a29b'
down_revision: Union[str, None] = 'c3fb78821edc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS service_order_signatures CASCADE")

    op.execute("""
        ALTER TABLE service_orders
        ADD COLUMN IF NOT EXISTS technician_signature_data_url TEXT
    """)
    op.execute("""
        ALTER TABLE service_orders
        ADD COLUMN IF NOT EXISTS client_received_signature_data_url TEXT
    """)
    op.execute("""
        ALTER TABLE service_orders
        ADD COLUMN IF NOT EXISTS client_acceptance_signature_data_url TEXT
    """)

    op.execute("""
        ALTER TABLE service_orders
        ADD COLUMN IF NOT EXISTS technician_signed_name VARCHAR(180)
    """)
    op.execute("""
        ALTER TABLE service_orders
        ADD COLUMN IF NOT EXISTS client_received_signed_name VARCHAR(180)
    """)
    op.execute("""
        ALTER TABLE service_orders
        ADD COLUMN IF NOT EXISTS client_acceptance_signed_name VARCHAR(180)
    """)

    op.execute("""
        ALTER TABLE service_orders
        ADD COLUMN IF NOT EXISTS technician_signed_at TIMESTAMP WITH TIME ZONE
    """)
    op.execute("""
        ALTER TABLE service_orders
        ADD COLUMN IF NOT EXISTS client_received_signed_at TIMESTAMP WITH TIME ZONE
    """)
    op.execute("""
        ALTER TABLE service_orders
        ADD COLUMN IF NOT EXISTS client_acceptance_signed_at TIMESTAMP WITH TIME ZONE
    """)

def downgrade() -> None:
    # The direct signature columns belong to `27dad4c7a6c8`; this revision only
    # retires the duplicate table introduced by `c3fb78821edc`. Recreate that
    # table when stepping back so each preceding downgrade can undo exactly
    # the objects it owns.
    op.create_table(
        "service_order_signatures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("service_order_id", sa.Integer(), nullable=False),
        sa.Column("signature_type", sa.String(length=50), nullable=False),
        sa.Column("signer_name", sa.String(length=255), nullable=True),
        sa.Column("signer_role", sa.String(length=100), nullable=True),
        sa.Column("signature_data", sa.Text(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["service_order_id"],
            ["service_orders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_service_order_signatures_service_order_id",
        "service_order_signatures",
        ["service_order_id"],
    )
