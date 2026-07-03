"""add missing field sheet capture columns

Revision ID: c1d2e3f4a5b6
Revises: b9c0d1e2f3a4
Create Date: 2026-07-01 15:55:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("field_sheets", sa.Column("minimum_division", sa.String(length=120), nullable=True))
    op.add_column("field_sheets", sa.Column("location", sa.String(length=180), nullable=True))
    op.add_column("field_sheets", sa.Column("attention", sa.String(length=180), nullable=True))
    op.add_column("field_sheets", sa.Column("company", sa.String(length=180), nullable=True))
    op.add_column("field_sheets", sa.Column("address", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("field_sheets", "address")
    op.drop_column("field_sheets", "company")
    op.drop_column("field_sheets", "attention")
    op.drop_column("field_sheets", "location")
    op.drop_column("field_sheets", "minimum_division")
