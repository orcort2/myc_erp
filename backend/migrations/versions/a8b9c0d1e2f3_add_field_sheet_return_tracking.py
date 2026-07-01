"""add field sheet return tracking

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-30 17:05:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a8b9c0d1e2f3"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("field_sheets", sa.Column("returned_to_technician_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("field_sheets", sa.Column("returned_to_technician_by_id", sa.Integer(), nullable=True))
    op.add_column("field_sheets", sa.Column("returned_to_technician_reason", sa.Text(), nullable=True))
    op.create_index(op.f("ix_field_sheets_returned_to_technician_by_id"), "field_sheets", ["returned_to_technician_by_id"], unique=False)
    op.create_foreign_key(
        "fk_field_sheets_returned_to_technician_by_id_users",
        "field_sheets",
        "users",
        ["returned_to_technician_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_field_sheets_returned_to_technician_by_id_users", "field_sheets", type_="foreignkey")
    op.drop_index(op.f("ix_field_sheets_returned_to_technician_by_id"), table_name="field_sheets")
    op.drop_column("field_sheets", "returned_to_technician_reason")
    op.drop_column("field_sheets", "returned_to_technician_by_id")
    op.drop_column("field_sheets", "returned_to_technician_at")
