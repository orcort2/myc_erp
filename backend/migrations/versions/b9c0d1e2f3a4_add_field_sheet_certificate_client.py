"""add field sheet certificate client

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-07-01 10:45:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b9c0d1e2f3a4"
down_revision: str | None = "a8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "field_sheets",
        sa.Column("certificate_client_mode", sa.String(length=30), nullable=False, server_default="billing"),
    )
    op.add_column("field_sheets", sa.Column("certificate_client_company", sa.String(length=180), nullable=True))
    op.add_column("field_sheets", sa.Column("certificate_client_attention", sa.String(length=180), nullable=True))
    op.add_column("field_sheets", sa.Column("certificate_client_address", sa.Text(), nullable=True))
    op.add_column(
        "field_sheets",
        sa.Column("apply_certificate_client_to_order", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("field_sheets", "certificate_client_mode", server_default=None)
    op.alter_column("field_sheets", "apply_certificate_client_to_order", server_default=None)


def downgrade() -> None:
    op.drop_column("field_sheets", "apply_certificate_client_to_order")
    op.drop_column("field_sheets", "certificate_client_address")
    op.drop_column("field_sheets", "certificate_client_attention")
    op.drop_column("field_sheets", "certificate_client_company")
    op.drop_column("field_sheets", "certificate_client_mode")
