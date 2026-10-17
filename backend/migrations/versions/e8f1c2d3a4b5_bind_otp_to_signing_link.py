"""Bind quotation OTP challenges to revocable signing links.

Revision ID: e8f1c2d3a4b5
Revises: c7e1a4b9026d
"""
from alembic import op
import sqlalchemy as sa

revision = "e8f1c2d3a4b5"
down_revision = "c7e1a4b9026d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "quotation_signing_challenges",
        sa.Column(
            "signing_link_id", sa.Integer(),
            sa.ForeignKey("quotation_signing_links.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_quotation_signing_challenges_signing_link_id",
        "quotation_signing_challenges",
        ["signing_link_id"],
    )


def downgrade():
    op.drop_index(
        "ix_quotation_signing_challenges_signing_link_id",
        table_name="quotation_signing_challenges",
    )
    op.drop_column("quotation_signing_challenges", "signing_link_id")
