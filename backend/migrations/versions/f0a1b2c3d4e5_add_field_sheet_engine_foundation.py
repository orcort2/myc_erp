"""add field sheet engine foundation

Revision ID: f0a1b2c3d4e5
Revises: e9e489637dc8
Create Date: 2026-07-13 12:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f0a1b2c3d4e5"
down_revision: str | None = "e9e489637dc8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "institutional_configurations",
        sa.Column("configuration_key", sa.String(length=60), nullable=False),
        sa.Column("legal_name", sa.String(length=180), nullable=False),
        sa.Column("document_code", sa.String(length=40), nullable=False),
        sa.Column("initial_revision", sa.String(length=40), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=80), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("logo_path", sa.String(length=500), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("configuration_key"),
    )
    op.create_index(
        op.f("ix_institutional_configurations_configuration_key"),
        "institutional_configurations",
        ["configuration_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_institutional_configurations_id"),
        "institutional_configurations",
        ["id"],
        unique=False,
    )
    op.add_column("field_sheets", sa.Column("institutional_snapshot_json", sa.JSON(), nullable=True))

    op.create_table(
        "field_sheet_signatures",
        sa.Column("field_sheet_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False),
        sa.Column("display_label", sa.String(length=180), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=True),
        sa.Column("signature_data", sa.Text(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["field_sheet_id"], ["field_sheets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("field_sheet_id", "role", name="uq_field_sheet_signature_role"),
    )
    op.create_index(op.f("ix_field_sheet_signatures_field_sheet_id"), "field_sheet_signatures", ["field_sheet_id"], unique=False)
    op.create_index(op.f("ix_field_sheet_signatures_id"), "field_sheet_signatures", ["id"], unique=False)
    op.create_index(op.f("ix_field_sheet_signatures_role"), "field_sheet_signatures", ["role"], unique=False)
    op.create_index(op.f("ix_field_sheet_signatures_user_id"), "field_sheet_signatures", ["user_id"], unique=False)

    institution_table = sa.table(
        "institutional_configurations",
        sa.column("configuration_key", sa.String),
        sa.column("legal_name", sa.String),
        sa.column("document_code", sa.String),
        sa.column("initial_revision", sa.String),
        sa.column("address", sa.Text),
        sa.column("phone", sa.String),
        sa.column("email", sa.String),
        sa.column("logo_path", sa.String),
    )
    op.bulk_insert(
        institution_table,
        [
            {
                "configuration_key": "default",
                "legal_name": "METROLOGÍA Y SERVICIOS MYC",
                "document_code": "FCA-30",
                "initial_revision": "R1",
                "address": "Av. Cristóbal Colón 6086, Int. 57, San Pedro Tlaquepaque, Jalisco, C.P. 45601",
                "phone": "33 5009 2659 · Cel. 33 1398 8169",
                "email": "contacto@mycmetrology.com.mx",
                "logo_path": "frontend/src/assets/myc-logo.png",
            }
        ],
    )

    connection = op.get_bind()
    institution = {
        "configuration_key": "default",
        "legal_name": "METROLOGÍA Y SERVICIOS MYC",
        "document_code": "FCA-30",
        "initial_revision": "R1",
        "address": "Av. Cristóbal Colón 6086, Int. 57, San Pedro Tlaquepaque, Jalisco, C.P. 45601",
        "phone": "33 5009 2659 · Cel. 33 1398 8169",
        "email": "contacto@mycmetrology.com.mx",
        "logo_path": "frontend/src/assets/myc-logo.png",
    }
    import json

    connection.execute(
        sa.text(
            "UPDATE field_sheets SET institutional_snapshot_json = :snapshot "
            "WHERE institutional_snapshot_json IS NULL"
        ),
        {"snapshot": json.dumps(institution)},
    )

    legacy_sheets = connection.execute(
        sa.text("SELECT id, calibrated_by, reviewed_by, report_made_by FROM field_sheets")
    ).mappings()
    signature_table = sa.table(
        "field_sheet_signatures",
        sa.column("field_sheet_id", sa.Integer),
        sa.column("role", sa.String),
        sa.column("display_label", sa.String),
        sa.column("name", sa.String),
        sa.column("position", sa.Integer),
    )
    for sheet in legacy_sheets:
        op.bulk_insert(
            signature_table,
            [
                {"field_sheet_id": sheet["id"], "role": "calibrated_by", "display_label": "Calibró", "name": sheet["calibrated_by"], "position": 0},
                {"field_sheet_id": sheet["id"], "role": "reviewed_by", "display_label": "Revisó", "name": sheet["reviewed_by"], "position": 1},
                {"field_sheet_id": sheet["id"], "role": "report_made_by", "display_label": "Elaboró informe", "name": sheet["report_made_by"], "position": 2},
            ],
        )

    from app.services.field_sheet_template_engine import OFFICIAL_PILOT_TEMPLATES
    from app.services.field_sheet_templates import normalize_template_definition

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
    for template_key, source in OFFICIAL_PILOT_TEMPLATES.items():
        previous_version = connection.execute(
            sa.text(
                "SELECT COALESCE(MAX(version), 0) FROM field_sheet_template_definitions "
                "WHERE template_key = :template_key"
            ),
            {"template_key": template_key},
        ).scalar_one()
        version = int(previous_version) + 1
        definition = normalize_template_definition(
            {**source, "version": version, "status": "active", "source": "database"}
        )
        connection.execute(
            sa.text(
                "UPDATE field_sheet_template_definitions SET status = 'inactive' "
                "WHERE template_key = :template_key AND is_active = true"
            ),
            {"template_key": template_key},
        )
        connection.execute(
            template_table.insert().values(
                template_key=template_key,
                name=definition["name"],
                description=definition.get("description"),
                status="active",
                version=version,
                definition_json=definition,
                is_active=True,
            )
        )


def downgrade() -> None:
    connection = op.get_bind()
    for template_key in ("anemometro", "calibradores", "presion", "bascula"):
        latest = connection.execute(
            sa.text(
                "SELECT MAX(version) FROM field_sheet_template_definitions "
                "WHERE template_key = :template_key"
            ),
            {"template_key": template_key},
        ).scalar_one_or_none()
        if latest is None:
            continue
        connection.execute(
            sa.text(
                "DELETE FROM field_sheet_template_definitions "
                "WHERE template_key = :template_key AND version = :version"
            ),
            {"template_key": template_key, "version": latest},
        )
        previous = connection.execute(
            sa.text(
                "SELECT MAX(version) FROM field_sheet_template_definitions "
                "WHERE template_key = :template_key"
            ),
            {"template_key": template_key},
        ).scalar_one_or_none()
        if previous is not None:
            connection.execute(
                sa.text(
                    "UPDATE field_sheet_template_definitions SET status = 'active' "
                    "WHERE template_key = :template_key AND version = :version"
                ),
                {"template_key": template_key, "version": previous},
            )
    op.drop_index(op.f("ix_field_sheet_signatures_user_id"), table_name="field_sheet_signatures")
    op.drop_index(op.f("ix_field_sheet_signatures_role"), table_name="field_sheet_signatures")
    op.drop_index(op.f("ix_field_sheet_signatures_id"), table_name="field_sheet_signatures")
    op.drop_index(op.f("ix_field_sheet_signatures_field_sheet_id"), table_name="field_sheet_signatures")
    op.drop_table("field_sheet_signatures")
    op.drop_column("field_sheets", "institutional_snapshot_json")
    op.drop_index(op.f("ix_institutional_configurations_id"), table_name="institutional_configurations")
    op.drop_index(op.f("ix_institutional_configurations_configuration_key"), table_name="institutional_configurations")
    op.drop_table("institutional_configurations")
