"""add declarative field sheet capture values

Revision ID: f1d2e3f4a5b6
Revises: f0c1d2e3f4a5
Create Date: 2026-07-13 16:00:00.000000
"""
from collections.abc import Sequence
from copy import deepcopy
import json

from alembic import op
import sqlalchemy as sa


revision: str = "f1d2e3f4a5b6"
down_revision: str | None = "f0c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("field_sheets", sa.Column("capture_values", sa.JSON(), nullable=True))
    bind = op.get_bind()
    active = bind.execute(
        sa.text(
            """SELECT id, name, description, version, definition_json
               FROM field_sheet_template_definitions
               WHERE template_key = 'bascula' AND status = 'active' AND is_active = true
               ORDER BY version DESC LIMIT 1"""
        )
    ).mappings().first()
    if active is not None:
        definition = deepcopy(active["definition_json"])
        for section in definition.get("result_sections") or []:
            if section.get("key") == "eccentricity_cycle":
                section["columns"] = [column for column in section.get("columns") or [] if column.get("key") != "position"]
        for block in definition.get("blocks") or []:
            for section in block.get("sections") or []:
                if section.get("key") == "eccentricity_cycle":
                    section["columns"] = [column for column in section.get("columns") or [] if column.get("key") != "position"]
        new_version = int(active["version"]) + 1
        definition["version"] = new_version
        bind.execute(
            sa.text("UPDATE field_sheet_template_definitions SET status = 'inactive' WHERE id = :id"),
            {"id": active["id"]},
        )
        bind.execute(
            sa.text(
                """INSERT INTO field_sheet_template_definitions
                   (template_key, name, description, status, version, definition_json, created_at, updated_at, is_active)
                   VALUES ('bascula', :name, :description, 'active', :version,
                           CAST(:definition AS JSON), now(), now(), true)"""
            ),
            {
                "name": active["name"],
                "description": active["description"],
                "version": new_version,
                "definition": json.dumps(definition, ensure_ascii=False),
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    latest = bind.execute(
        sa.text(
            "SELECT id, version FROM field_sheet_template_definitions WHERE template_key = 'bascula' AND status = 'active' ORDER BY version DESC LIMIT 1"
        )
    ).mappings().first()
    if latest is not None:
        bind.execute(sa.text("UPDATE field_sheet_template_definitions SET status = 'inactive', is_active = false WHERE id = :id"), {"id": latest["id"]})
        bind.execute(
            sa.text(
                "UPDATE field_sheet_template_definitions SET status = 'active' WHERE template_key = 'bascula' AND version = :version"
            ),
            {"version": int(latest["version"]) - 1},
        )
    op.drop_column("field_sheets", "capture_values")
