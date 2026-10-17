"""Email signing challenge persistence.

Revision ID: b9d3f0a258c1
Revises: a8c2e9f147b0
"""
from alembic import op
import sqlalchemy as sa

revision = "b9d3f0a258c1"
down_revision = "a8c2e9f147b0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quotation_signing_challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("quotation_snapshots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("recipient_email", sa.String(254), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column("nonce", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_quotation_signing_challenges_quotation_id", "quotation_signing_challenges", ["quotation_id"])


def downgrade():
    op.drop_index("ix_quotation_signing_challenges_quotation_id", table_name="quotation_signing_challenges")
    op.drop_table("quotation_signing_challenges")
