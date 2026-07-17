"""add certificate master file metadata and snapshot validity

Revision ID: fd5e6f7a8b9c
Revises: fc4d5e6f7a8b
Create Date: 2026-07-17 15:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "fd5e6f7a8b9c"
down_revision = "fc4d5e6f7a8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("controlled_document_versions", sa.Column("expires_on", sa.Date(), nullable=True))
    op.add_column("controlled_document_versions", sa.Column("file_size_bytes", sa.Integer(), nullable=True))
    op.add_column("equipment", sa.Column("certificate_template_checksum_snapshot", sa.String(length=128), nullable=True))
    op.add_column("equipment", sa.Column("certificate_template_effective_date_snapshot", sa.Date(), nullable=True))
    op.add_column("equipment", sa.Column("certificate_template_expires_on_snapshot", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("equipment", "certificate_template_expires_on_snapshot")
    op.drop_column("equipment", "certificate_template_effective_date_snapshot")
    op.drop_column("equipment", "certificate_template_checksum_snapshot")
    op.drop_column("controlled_document_versions", "file_size_bytes")
    op.drop_column("controlled_document_versions", "expires_on")
