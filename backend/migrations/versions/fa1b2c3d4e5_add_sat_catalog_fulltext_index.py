"""add SAT catalog full-text index

Revision ID: fa1b2c3d4e5
Revises: f9b0c1d2e3f4
Create Date: 2026-07-14 15:00:00.000000
"""

from alembic import op


revision = "fa1b2c3d4e5"
down_revision = "f9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX ix_sat_catalog_records_search_text_fts ON sat_catalog_records USING gin (to_tsvector('simple', search_text))")


def downgrade() -> None:
    op.execute("DROP INDEX ix_sat_catalog_records_search_text_fts")
