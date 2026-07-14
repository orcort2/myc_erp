"""Make authenticated PDF presence consistent with lifecycle state.

Revision ID: f4c5d6e7f8a9
Revises: f3b4c5d6e7f8
Create Date: 2026-07-13
"""

from alembic import op


revision = "f4c5d6e7f8a9"
down_revision = "f3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE certificates
        SET status = 'authenticated'
        WHERE authenticated_pdf_path IS NOT NULL
          AND is_active = true
          AND status NOT IN ('authenticated', 'released_to_client', 'released', 'cancelled')
        """
    )


def downgrade() -> None:
    pass
