"""Normalize legacy authenticated certificates into their explicit workflow state.

Revision ID: f2a3b4c5d6e7
Revises: f1d2e3f4a5b6
Create Date: 2026-07-13
"""

from alembic import op


revision = "f2a3b4c5d6e7"
down_revision = "f1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Prior versions stored the authenticated path but left the certificate in
    # quality_approved/pdf_uploaded. Preserve the document and make its real
    # lifecycle state explicit so release never infers authentication from a file.
    op.execute(
        """
        UPDATE certificates
        SET status = 'authenticated'
        WHERE authenticated_pdf_path IS NOT NULL
          AND is_active = true
          AND status IN ('quality_approved', 'approved', 'pdf_pending', 'pdf_uploaded')
        """
    )


def downgrade() -> None:
    # Keep released documents immutable; only return non-released records to
    # the prior compatible status.
    op.execute(
        """
        UPDATE certificates
        SET status = 'quality_approved'
        WHERE status = 'authenticated'
          AND is_active = true
        """
    )
