"""add semantic LAB equipment observations

Revision ID: c91f47a8b2d0
Revises: da6ad5a90e57
"""

from alembic import op
import sqlalchemy as sa


revision = "c91f47a8b2d0"
down_revision = "da6ad5a90e57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lab_work_order_equipment",
        sa.Column("observations", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lab_work_order_equipment", "observations")
