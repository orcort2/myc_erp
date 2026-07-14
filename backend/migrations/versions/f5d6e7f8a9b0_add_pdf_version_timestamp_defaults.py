"""Add timestamp defaults required by PDF version inserts.

Revision ID: f5d6e7f8a9b0
Revises: f4c5d6e7f8a9
Create Date: 2026-07-13
"""

import sqlalchemy as sa
from alembic import op


revision = "f5d6e7f8a9b0"
down_revision = "f4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("certificate_pdf_versions", "created_at", server_default=sa.func.now())
    op.alter_column("certificate_pdf_versions", "updated_at", server_default=sa.func.now())


def downgrade() -> None:
    op.alter_column("certificate_pdf_versions", "updated_at", server_default=None)
    op.alter_column("certificate_pdf_versions", "created_at", server_default=None)
