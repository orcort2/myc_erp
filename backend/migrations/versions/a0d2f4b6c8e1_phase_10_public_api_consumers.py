"""Add institutional Resolution Engine API consumers.

Revision ID: a0d2f4b6c8e1
Revises: f9c1d3e5a7b9
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a0d2f4b6c8e1"
down_revision: str | None = "f9c1d3e5a7b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_document = sa.JSON().with_variant(
        postgresql.JSONB(astext_type=sa.Text()),
        "postgresql",
    )
    op.create_table(
        "resolution_api_consumers",
        sa.Column("consumer_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("organization_id", sa.String(length=160), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "permissions",
            json_document,
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "consumer_key",
            name="uq_resolution_api_consumers_consumer_key",
        ),
    )
    op.create_index(
        "ix_resolution_api_consumers_id",
        "resolution_api_consumers",
        ["id"],
    )
    op.create_index(
        "ix_resolution_api_consumers_organization_id",
        "resolution_api_consumers",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resolution_api_consumers_organization_id",
        table_name="resolution_api_consumers",
    )
    op.drop_index(
        "ix_resolution_api_consumers_id",
        table_name="resolution_api_consumers",
    )
    op.drop_table("resolution_api_consumers")
