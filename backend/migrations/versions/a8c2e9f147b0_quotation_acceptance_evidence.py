"""Store version-bound quotation acceptance evidence.

Revision ID: a8c2e9f147b0
Revises: f6b9c3d4e5a7
"""
from alembic import op
import sqlalchemy as sa

revision = "a8c2e9f147b0"
down_revision = "f6b9c3d4e5a7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quotation_acceptances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("quotation_snapshots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("pdf_sha256", sa.String(64), nullable=False),
        sa.Column("pdf_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("signer_name", sa.String(180), nullable=False),
        sa.Column("signer_email", sa.String(254), nullable=False),
        sa.Column("consent_text", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.Column("invalidated_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("invalidation_reason", sa.String(100)),
    )
    op.create_index("ix_quotation_acceptances_quotation_id", "quotation_acceptances", ["quotation_id"])
    op.create_index(
        "uq_quotation_acceptances_current",
        "quotation_acceptances",
        ["quotation_id"],
        unique=True,
        postgresql_where=sa.text("invalidated_at IS NULL"),
        sqlite_where=sa.text("invalidated_at IS NULL"),
    )


def downgrade():
    op.drop_index("uq_quotation_acceptances_current", table_name="quotation_acceptances")
    op.drop_index("ix_quotation_acceptances_quotation_id", table_name="quotation_acceptances")
    op.drop_table("quotation_acceptances")
