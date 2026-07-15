"""allow long SAT descriptions

Revision ID: f9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-07-14 14:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f9b0c1d2e3f4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("sat_catalog_records", "name", existing_type=sa.String(length=500), type_=sa.Text(), existing_nullable=True)
    op.alter_column("sat_catalog_records", "normalized_name", existing_type=sa.String(length=600), type_=sa.Text(), existing_nullable=False)


def downgrade() -> None:
    op.alter_column("sat_catalog_records", "normalized_name", existing_type=sa.Text(), type_=sa.String(length=600), existing_nullable=False)
    op.alter_column("sat_catalog_records", "name", existing_type=sa.Text(), type_=sa.String(length=500), existing_nullable=True)
