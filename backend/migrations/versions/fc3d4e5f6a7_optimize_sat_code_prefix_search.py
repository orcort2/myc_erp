"""optimize SAT code and prefix searches

Revision ID: fc3d4e5f6a7
Revises: fb2c3d4e5f6
Create Date: 2026-07-14 14:00:00.000000
"""

from alembic import op


revision = "fc3d4e5f6a7"
down_revision = "fb2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_sat_catalog_records_version_normalized_code_pattern",
        "sat_catalog_records",
        ["catalog_version_id", "normalized_code"],
        unique=False,
        postgresql_ops={"normalized_code": "text_pattern_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_sat_catalog_records_version_normalized_code_pattern", table_name="sat_catalog_records")
