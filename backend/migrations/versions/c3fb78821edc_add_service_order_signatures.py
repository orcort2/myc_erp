"""add_service_order_signatures

Revision ID: c3fb78821edc
Revises: 27dad4c7a6c8
Create Date: 2026-07-09 11:26:43.957718
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3fb78821edc'
down_revision: Union[str, None] = '27dad4c7a6c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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


def downgrade() -> None:
    # `28eed747a29b` retires this legacy table in its upgrade. During a complete
    # downgrade it has therefore disappeared before this revision is reached.
    # IF EXISTS preserves reversibility both for that canonical chain and for
    # databases that stopped at this historical revision.
    op.execute("DROP INDEX IF EXISTS ix_service_order_signatures_service_order_id")
    op.execute("DROP TABLE IF EXISTS service_order_signatures")
