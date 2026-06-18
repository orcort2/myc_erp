"""add document templates

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_templates",
        sa.Column("template_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("company_name", sa.String(length=180), nullable=False),
        sa.Column("company_tagline", sa.String(length=255), nullable=True),
        sa.Column("company_rfc", sa.String(length=20), nullable=True),
        sa.Column("company_email", sa.String(length=255), nullable=True),
        sa.Column("company_website", sa.String(length=255), nullable=True),
        sa.Column("company_address", sa.Text(), nullable=True),
        sa.Column("company_phone", sa.String(length=60), nullable=True),
        sa.Column("document_title", sa.String(length=120), nullable=False),
        sa.Column("document_subtitle", sa.String(length=255), nullable=True),
        sa.Column("document_code", sa.String(length=80), nullable=True),
        sa.Column("document_revision", sa.String(length=80), nullable=True),
        sa.Column("document_issued_on", sa.Date(), nullable=True),
        sa.Column("terms_version", sa.String(length=80), nullable=True),
        sa.Column("commercial_terms", sa.Text(), nullable=True),
        sa.Column("metrological_terms", sa.Text(), nullable=True),
        sa.Column("legal_terms", sa.Text(), nullable=True),
        sa.Column("privacy_notice", sa.Text(), nullable=True),
        sa.Column("acceptance_text", sa.Text(), nullable=True),
        sa.Column("show_summary_terms", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_full_terms", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_acceptance_signature", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_key"),
    )
    op.create_index(op.f("ix_document_templates_id"), "document_templates", ["id"], unique=False)
    op.create_index(
        op.f("ix_document_templates_template_key"),
        "document_templates",
        ["template_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_document_templates_template_key"), table_name="document_templates")
    op.drop_index(op.f("ix_document_templates_id"), table_name="document_templates")
    op.drop_table("document_templates")
