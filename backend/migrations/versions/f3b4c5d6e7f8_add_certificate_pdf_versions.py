"""Add immutable certificate PDF version history.

Revision ID: f3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-07-13
"""

import sqlalchemy as sa
from alembic import op


revision = "f3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "certificate_pdf_versions",
        sa.Column("certificate_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("source_status", sa.String(length=60), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["certificate_id"], ["certificates.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("certificate_id", "version_number"),
    )
    op.create_index(op.f("ix_certificate_pdf_versions_certificate_id"), "certificate_pdf_versions", ["certificate_id"])
    op.create_index(op.f("ix_certificate_pdf_versions_uploaded_by_id"), "certificate_pdf_versions", ["uploaded_by_id"])
    op.create_index(op.f("ix_certificate_pdf_versions_is_current"), "certificate_pdf_versions", ["is_current"])
    op.execute(
        """
        INSERT INTO certificate_pdf_versions (
            certificate_id, version_number, file_path, original_filename,
            uploaded_at, uploaded_by_id, source_status, change_reason,
            is_current, created_at, updated_at
        )
        SELECT id, 1, final_pdf_path, final_pdf_original_filename,
               COALESCE(final_pdf_uploaded_at, updated_at), final_pdf_uploaded_by_id,
               status, 'Versión existente migrada al historial', true,
               COALESCE(final_pdf_uploaded_at, updated_at), COALESCE(final_pdf_uploaded_at, updated_at)
        FROM certificates
        WHERE final_pdf_path IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_certificate_pdf_versions_is_current"), table_name="certificate_pdf_versions")
    op.drop_index(op.f("ix_certificate_pdf_versions_uploaded_by_id"), table_name="certificate_pdf_versions")
    op.drop_index(op.f("ix_certificate_pdf_versions_certificate_id"), table_name="certificate_pdf_versions")
    op.drop_table("certificate_pdf_versions")
