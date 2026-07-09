"""add_service_order_signatures

Revision ID: 27dad4c7a6c8
Revises: 9d2e3f4a5b6c
Create Date: 2026-07-08 18:05:13.740510
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "27dad4c7a6c8"
down_revision: Union[str, None] = "9d2e3f4a5b6c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("service_orders", sa.Column("technician_signature_data_url", sa.Text(), nullable=True))
    op.add_column("service_orders", sa.Column("client_received_signature_data_url", sa.Text(), nullable=True))
    op.add_column("service_orders", sa.Column("client_acceptance_signature_data_url", sa.Text(), nullable=True))

    op.add_column("service_orders", sa.Column("technician_signed_name", sa.String(length=180), nullable=True))
    op.add_column("service_orders", sa.Column("client_received_signed_name", sa.String(length=180), nullable=True))
    op.add_column("service_orders", sa.Column("client_acceptance_signed_name", sa.String(length=180), nullable=True))

    op.add_column("service_orders", sa.Column("technician_signed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("service_orders", sa.Column("client_received_signed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("service_orders", sa.Column("client_acceptance_signed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("service_orders", "client_acceptance_signed_at")
    op.drop_column("service_orders", "client_received_signed_at")
    op.drop_column("service_orders", "technician_signed_at")

    op.drop_column("service_orders", "client_acceptance_signed_name")
    op.drop_column("service_orders", "client_received_signed_name")
    op.drop_column("service_orders", "technician_signed_name")

    op.drop_column("service_orders", "client_acceptance_signature_data_url")
    op.drop_column("service_orders", "client_received_signature_data_url")
    op.drop_column("service_orders", "technician_signature_data_url")