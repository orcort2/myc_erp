"""add client fiscal review flag

Revision ID: 660da69de732
Revises: 650da69de732
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "660da69de732"
down_revision: Union[str, None] = "650da69de732"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("fiscal_review_required", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index(op.f("ix_clients_fiscal_review_required"), "clients", ["fiscal_review_required"], unique=False)
    op.alter_column("clients", "fiscal_review_required", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_clients_fiscal_review_required"), table_name="clients")
    op.drop_column("clients", "fiscal_review_required")
