"""expand clients module fields

Revision ID: 1a2c3e4f5a6b
Revises: 0f1e2d3c4b5a
Create Date: 2026-07-06 13:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1a2c3e4f5a6b"
down_revision: Union[str, None] = "0f1e2d3c4b5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("cfdi_use", sa.String(length=40), nullable=True))
    op.add_column("clients", sa.Column("street", sa.String(length=255), nullable=True))
    op.add_column("clients", sa.Column("exterior_number", sa.String(length=40), nullable=True))
    op.add_column("clients", sa.Column("interior_number", sa.String(length=40), nullable=True))
    op.add_column("clients", sa.Column("neighborhood", sa.String(length=180), nullable=True))
    op.add_column("clients", sa.Column("city", sa.String(length=180), nullable=True))
    op.add_column("clients", sa.Column("state", sa.String(length=180), nullable=True))
    op.add_column("clients", sa.Column("postal_code", sa.String(length=20), nullable=True))
    op.add_column("clients", sa.Column("country", sa.String(length=120), nullable=True))
    op.add_column("clients", sa.Column("fiscal_postal_code", sa.String(length=20), nullable=True))
    op.add_column("clients", sa.Column("tax_constancy_filename", sa.String(length=255), nullable=True))
    op.add_column("clients", sa.Column("tax_constancy_path", sa.String(length=500), nullable=True))
    op.add_column("clients", sa.Column("tax_constancy_uploaded_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "tax_constancy_uploaded_at")
    op.drop_column("clients", "tax_constancy_path")
    op.drop_column("clients", "tax_constancy_filename")
    op.drop_column("clients", "fiscal_postal_code")
    op.drop_column("clients", "country")
    op.drop_column("clients", "postal_code")
    op.drop_column("clients", "state")
    op.drop_column("clients", "city")
    op.drop_column("clients", "neighborhood")
    op.drop_column("clients", "interior_number")
    op.drop_column("clients", "exterior_number")
    op.drop_column("clients", "street")
    op.drop_column("clients", "cfdi_use")
