"""add field sheet template definitions and snapshots

Revision ID: 9a8b7c6d5e4f
Revises: 7c9e1f2a3b4c
Create Date: 2026-07-03 10:10:00.000000
"""

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, None] = "7c9e1f2a3b4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "field_sheet_template_definitions",
        sa.Column("template_key", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_key", "version", name="uq_field_sheet_template_key_version"),
    )
    op.create_index(op.f("ix_field_sheet_template_definitions_id"), "field_sheet_template_definitions", ["id"], unique=False)
    op.create_index(op.f("ix_field_sheet_template_definitions_template_key"), "field_sheet_template_definitions", ["template_key"], unique=False)
    op.create_index(op.f("ix_field_sheet_template_definitions_status"), "field_sheet_template_definitions", ["status"], unique=False)

    op.add_column("field_sheets", sa.Column("template_definition_json", sa.JSON(), nullable=True))
    op.add_column("field_sheets", sa.Column("template_definition_version", sa.Integer(), nullable=True))
    op.add_column("field_sheet_results", sa.Column("row_data", sa.JSON(), nullable=True))

    bind = op.get_bind()
    from app.services.field_sheet_templates import TEMPLATE_BLOCK_ASSIGNMENTS, build_fallback_template_definition

    template_table = sa.table(
        "field_sheet_template_definitions",
        sa.column("template_key", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("status", sa.String),
        sa.column("version", sa.Integer),
        sa.column("definition_json", sa.JSON),
        sa.column("is_active", sa.Boolean),
    )
    for template_key in TEMPLATE_BLOCK_ASSIGNMENTS:
        definition = build_fallback_template_definition(template_key)
        bind.execute(
            template_table.insert().values(
                template_key=template_key,
                name=definition["name"],
                description=None,
                status="active",
                version=1,
                definition_json=definition,
                is_active=True,
            )
        )

    result_rows = bind.execute(
        sa.text(
            """
            SELECT id, pattern_value, ibc_value_1, ibc_value_2, ibc_value_3, unit, notes
            FROM field_sheet_results
            """
        )
    ).mappings()
    for row in result_rows:
        row_data = {
            "pattern_value": row["pattern_value"],
            "ibc_value_1": row["ibc_value_1"],
            "ibc_value_2": row["ibc_value_2"],
            "ibc_value_3": row["ibc_value_3"],
            "unit": row["unit"],
            "notes": row["notes"],
        }
        bind.execute(
            sa.text(
                "UPDATE field_sheet_results SET row_data = :row_data WHERE id = :id"
            ),
            {"id": row["id"], "row_data": json.dumps(row_data)},
        )

    field_sheets = bind.execute(
        sa.text("SELECT id, template_key FROM field_sheets")
    ).mappings()
    for row in field_sheets:
        definition = build_fallback_template_definition(row["template_key"])
        bind.execute(
            sa.text(
                """
                UPDATE field_sheets
                SET template_definition_json = :definition,
                    template_definition_version = 1
                WHERE id = :id
                """
            ),
            {"id": row["id"], "definition": json.dumps(definition)},
        )


def downgrade() -> None:
    op.drop_column("field_sheet_results", "row_data")
    op.drop_column("field_sheets", "template_definition_version")
    op.drop_column("field_sheets", "template_definition_json")
    op.drop_index(op.f("ix_field_sheet_template_definitions_status"), table_name="field_sheet_template_definitions")
    op.drop_index(op.f("ix_field_sheet_template_definitions_template_key"), table_name="field_sheet_template_definitions")
    op.drop_index(op.f("ix_field_sheet_template_definitions_id"), table_name="field_sheet_template_definitions")
    op.drop_table("field_sheet_template_definitions")
