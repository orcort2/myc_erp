"""add quotation payment terms and snapshots

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-07-07 17:25:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3c4d5e6f7a8b"
down_revision: Union[str, None] = "2b3c4d5e6f7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("quotations", sa.Column("payment_terms", sa.Text(), nullable=True))
    op.create_table(
        "quotation_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("quotation_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_number", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=80), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("snapshot_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quotation_snapshots_created_by_id"), "quotation_snapshots", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_quotation_snapshots_quotation_id"), "quotation_snapshots", ["quotation_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_quotation_snapshots_quotation_id"), table_name="quotation_snapshots")
    op.drop_index(op.f("ix_quotation_snapshots_created_by_id"), table_name="quotation_snapshots")
    op.drop_table("quotation_snapshots")
    op.drop_column("quotations", "payment_terms")
