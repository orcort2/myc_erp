"""add reusable client certificate profiles

Revision ID: f0c1d2e3f4a5
Revises: f0b1c2d3e4f5
Create Date: 2026-07-13 15:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f0c1d2e3f4a5"
down_revision: str | None = "f0b1c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "client_certificate_profiles",
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("attention", sa.String(length=180), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_client_certificate_profiles_client_id"), "client_certificate_profiles", ["client_id"])
    op.create_index(op.f("ix_client_certificate_profiles_id"), "client_certificate_profiles", ["id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_client_certificate_profiles_id"), table_name="client_certificate_profiles")
    op.drop_index(op.f("ix_client_certificate_profiles_client_id"), table_name="client_certificate_profiles")
    op.drop_table("client_certificate_profiles")
