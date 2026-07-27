"""Persist outbox failure time for Resolution Engine Phase 5.

Revision ID: c5d7e9f1a3b4
Revises: b4c6d8e0f2a3
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5d7e9f1a3b4"
down_revision: str | None = "b4c6d8e0f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "resolution_outbox_events",
        sa.Column(
            "failed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("resolution_outbox_events", "failed_at")
