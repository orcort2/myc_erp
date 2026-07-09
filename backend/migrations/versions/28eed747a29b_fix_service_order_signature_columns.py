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
    op.execute("DROP TABLE IF EXISTS service_order_signatures CASCADE")

    op.drop_column("service_orders", "client_acceptance_signed_at")
    op.drop_column("service_orders", "client_received_signed_at")
    op.drop_column("service_orders", "technician_signed_at")

    op.drop_column("service_orders", "client_acceptance_signed_name")
    op.drop_column("service_orders", "client_received_signed_name")
    op.drop_column("service_orders", "technician_signed_name")

    op.drop_column("service_orders", "client_acceptance_signature_data_url")
    op.drop_column("service_orders", "client_received_signature_data_url")
    op.drop_column("service_orders", "technician_signature_data_url")
