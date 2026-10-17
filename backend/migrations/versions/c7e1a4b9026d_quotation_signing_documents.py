"""Frozen quotation signing documents and revocable links.

Revision ID: c7e1a4b9026d
Revises: b9d3f0a258c1
"""
from alembic import op
import sqlalchemy as sa

revision = "c7e1a4b9026d"
down_revision = "b9d3f0a258c1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quotation_signing_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("quotation_id", sa.Integer(),
                  sa.ForeignKey("quotations.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("snapshot_id", sa.Integer(),
                  sa.ForeignKey("quotation_snapshots.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("snapshot_sha256", sa.String(64), nullable=False),
        sa.Column("pdf_sha256", sa.String(64), nullable=False),
        sa.Column("pdf_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "quotation_id", "snapshot_id",
            name="uq_quotation_signing_document_version",
        ),
    )
    op.create_index(
        "ix_quotation_signing_documents_quotation_id",
        "quotation_signing_documents", ["quotation_id"],
    )

    op.create_table(
        "quotation_signing_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("document_id", sa.Integer(),
                  sa.ForeignKey("quotation_signing_documents.id",
                                ondelete="RESTRICT"), nullable=False),
        sa.Column("token_id_hash", sa.String(64),
                  nullable=False, unique=True),
        sa.Column("recipient_email", sa.String(254), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_quotation_signing_links_document",
        "quotation_signing_links", ["document_id"],
    )


def downgrade():
    op.drop_index(
        "ix_quotation_signing_links_document",
        table_name="quotation_signing_links",
    )
    op.drop_table("quotation_signing_links")
    op.drop_index(
        "ix_quotation_signing_documents_quotation_id",
        table_name="quotation_signing_documents",
    )
    op.drop_table("quotation_signing_documents")
