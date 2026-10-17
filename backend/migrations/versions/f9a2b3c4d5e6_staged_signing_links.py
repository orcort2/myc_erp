"""Stage signing links until their SMTP delivery is confirmed.

Revision ID: f9a2b3c4d5e6
Revises: e8f1c2d3a4b5
"""
from alembic import op
import sqlalchemy as sa

revision = "f9a2b3c4d5e6"
down_revision = "e8f1c2d3a4b5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("quotation_signing_links", sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("quotation_signing_links", sa.Column("delivery_id", sa.Integer(), sa.ForeignKey("email_deliveries.id", ondelete="RESTRICT"), nullable=True))
    op.create_index("ix_quotation_signing_links_delivery_id", "quotation_signing_links", ["delivery_id"])


def downgrade():
    op.drop_index("ix_quotation_signing_links_delivery_id", table_name="quotation_signing_links")
    op.drop_column("quotation_signing_links", "delivery_id")
    op.drop_column("quotation_signing_links", "activated_at")
