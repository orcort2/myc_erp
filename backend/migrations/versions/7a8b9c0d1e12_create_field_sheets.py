"""create field sheets

Revision ID: 7a8b9c0d1e12
Revises: 6f7a8b9c0d11
Create Date: 2026-06-17 14:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a8b9c0d1e12"
down_revision: Union[str, None] = "6f7a8b9c0d11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "field_sheets",
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("initial_condition", sa.Text(), nullable=True),
        sa.Column("final_condition", sa.Text(), nullable=True),
        sa.Column("pattern_used", sa.String(length=180), nullable=True),
        sa.Column("results", sa.Text(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("evidence_notes", sa.Text(), nullable=True),
        sa.Column("method", sa.String(length=180), nullable=True),
        sa.Column("environmental_conditions", sa.Text(), nullable=True),
        sa.Column("technician_notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_field_sheets_equipment_id"), "field_sheets", ["equipment_id"], unique=False)
    op.create_index(op.f("ix_field_sheets_id"), "field_sheets", ["id"], unique=False)
    op.create_index(op.f("ix_field_sheets_status"), "field_sheets", ["status"], unique=False)
    op.create_index(
        "uq_field_sheets_active_equipment",
        "field_sheets",
        ["equipment_id"],
        unique=True,
        postgresql_where=sa.text("is_active IS true"),
    )


def downgrade() -> None:
    op.drop_index("uq_field_sheets_active_equipment", table_name="field_sheets")
    op.drop_index(op.f("ix_field_sheets_status"), table_name="field_sheets")
    op.drop_index(op.f("ix_field_sheets_id"), table_name="field_sheets")
    op.drop_index(op.f("ix_field_sheets_equipment_id"), table_name="field_sheets")
    op.drop_table("field_sheets")
