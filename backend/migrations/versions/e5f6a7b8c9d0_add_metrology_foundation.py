"""add metrology foundation tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-25 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reference_standards",
        sa.Column("internal_code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_company", sa.String(length=40), nullable=False),
        sa.Column("magnitude", sa.String(length=80), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("serial_number", sa.String(length=120), nullable=True),
        sa.Column("identification", sa.String(length=120), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("range_min", sa.Numeric(18, 6), nullable=True),
        sa.Column("range_max", sa.Numeric(18, 6), nullable=True),
        sa.Column("resolution", sa.Numeric(18, 6), nullable=True),
        sa.Column("coverage_factor_k", sa.Numeric(12, 6), nullable=True),
        sa.Column("provider", sa.String(length=180), nullable=True),
        sa.Column("calibration_laboratory", sa.String(length=180), nullable=True),
        sa.Column("certificate_number", sa.String(length=120), nullable=True),
        sa.Column("certificate_file_path", sa.String(length=255), nullable=True),
        sa.Column("calibrated_on", sa.Date(), nullable=True),
        sa.Column("next_calibration_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reference_standards_id"), "reference_standards", ["id"], unique=False)
    op.create_index(
        op.f("ix_reference_standards_internal_code"),
        "reference_standards",
        ["internal_code"],
        unique=False,
    )
    op.create_index(op.f("ix_reference_standards_name"), "reference_standards", ["name"], unique=False)
    op.create_index(
        op.f("ix_reference_standards_owner_company"),
        "reference_standards",
        ["owner_company"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reference_standards_magnitude"),
        "reference_standards",
        ["magnitude"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reference_standards_next_calibration_on"),
        "reference_standards",
        ["next_calibration_on"],
        unique=False,
    )
    op.create_index(op.f("ix_reference_standards_status"), "reference_standards", ["status"], unique=False)
    op.create_index(
        "uq_reference_standards_internal_code_active",
        "reference_standards",
        ["internal_code"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    op.create_table(
        "reference_standard_uncertainties",
        sa.Column("reference_standard_id", sa.Integer(), nullable=False),
        sa.Column("range_min", sa.Numeric(18, 6), nullable=True),
        sa.Column("range_max", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("uncertainty_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("coverage_factor_k", sa.Numeric(12, 6), nullable=True),
        sa.Column("distribution", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["reference_standard_id"], ["reference_standards.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reference_standard_uncertainties_id"),
        "reference_standard_uncertainties",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reference_standard_uncertainties_reference_standard_id"),
        "reference_standard_uncertainties",
        ["reference_standard_id"],
        unique=False,
    )

    op.create_table(
        "calibration_procedures",
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("magnitude", sa.String(length=80), nullable=False),
        sa.Column("profile_key", sa.String(length=80), nullable=True),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("issuer_company", sa.String(length=40), nullable=False),
        sa.Column("certificate_type", sa.String(length=40), nullable=False),
        sa.Column("required_readings", sa.Integer(), nullable=True),
        sa.Column("decision_rule", sa.Text(), nullable=True),
        sa.Column("acceptance_criteria", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_calibration_procedures_id"), "calibration_procedures", ["id"], unique=False)
    op.create_index(op.f("ix_calibration_procedures_code"), "calibration_procedures", ["code"], unique=False)
    op.create_index(op.f("ix_calibration_procedures_name"), "calibration_procedures", ["name"], unique=False)
    op.create_index(
        op.f("ix_calibration_procedures_magnitude"),
        "calibration_procedures",
        ["magnitude"],
        unique=False,
    )
    op.create_index(
        op.f("ix_calibration_procedures_profile_key"),
        "calibration_procedures",
        ["profile_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_calibration_procedures_version"),
        "calibration_procedures",
        ["version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_calibration_procedures_issuer_company"),
        "calibration_procedures",
        ["issuer_company"],
        unique=False,
    )
    op.create_index(
        op.f("ix_calibration_procedures_certificate_type"),
        "calibration_procedures",
        ["certificate_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_calibration_procedures_status"),
        "calibration_procedures",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uq_calibration_procedures_code_version_active",
        "calibration_procedures",
        ["code", "version"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    op.add_column(
        "field_sheets",
        sa.Column("calibration_procedure_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_field_sheets_calibration_procedure_id",
        "field_sheets",
        "calibration_procedures",
        ["calibration_procedure_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_field_sheets_calibration_procedure_id"),
        "field_sheets",
        ["calibration_procedure_id"],
        unique=False,
    )

    op.create_table(
        "field_sheet_reference_standards",
        sa.Column("field_sheet_id", sa.Integer(), nullable=False),
        sa.Column("reference_standard_id", sa.Integer(), nullable=False),
        sa.Column("usage_role", sa.String(length=40), nullable=False, server_default="primary"),
        sa.Column("measurement_section", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["field_sheet_id"], ["field_sheets.id"]),
        sa.ForeignKeyConstraint(["reference_standard_id"], ["reference_standards.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "field_sheet_id",
            "reference_standard_id",
            "usage_role",
            "measurement_section",
            name="uq_field_sheet_reference_standard_usage",
        ),
    )
    op.create_index(
        op.f("ix_field_sheet_reference_standards_id"),
        "field_sheet_reference_standards",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_field_sheet_reference_standards_field_sheet_id"),
        "field_sheet_reference_standards",
        ["field_sheet_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_field_sheet_reference_standards_reference_standard_id"),
        "field_sheet_reference_standards",
        ["reference_standard_id"],
        unique=False,
    )

    op.alter_column("reference_standards", "status", server_default=None)
    op.alter_column("reference_standards", "is_active", server_default=None)
    op.alter_column("reference_standard_uncertainties", "is_active", server_default=None)
    op.alter_column("calibration_procedures", "status", server_default=None)
    op.alter_column("calibration_procedures", "is_active", server_default=None)
    op.alter_column("field_sheet_reference_standards", "usage_role", server_default=None)


def downgrade() -> None:
    op.drop_index(
        op.f("ix_field_sheet_reference_standards_reference_standard_id"),
        table_name="field_sheet_reference_standards",
    )
    op.drop_index(
        op.f("ix_field_sheet_reference_standards_field_sheet_id"),
        table_name="field_sheet_reference_standards",
    )
    op.drop_index(op.f("ix_field_sheet_reference_standards_id"), table_name="field_sheet_reference_standards")
    op.drop_table("field_sheet_reference_standards")

    op.drop_index(op.f("ix_field_sheets_calibration_procedure_id"), table_name="field_sheets")
    op.drop_constraint("fk_field_sheets_calibration_procedure_id", "field_sheets", type_="foreignkey")
    op.drop_column("field_sheets", "calibration_procedure_id")

    op.drop_index("uq_calibration_procedures_code_version_active", table_name="calibration_procedures")
    op.drop_index(op.f("ix_calibration_procedures_status"), table_name="calibration_procedures")
    op.drop_index(op.f("ix_calibration_procedures_certificate_type"), table_name="calibration_procedures")
    op.drop_index(op.f("ix_calibration_procedures_issuer_company"), table_name="calibration_procedures")
    op.drop_index(op.f("ix_calibration_procedures_version"), table_name="calibration_procedures")
    op.drop_index(op.f("ix_calibration_procedures_profile_key"), table_name="calibration_procedures")
    op.drop_index(op.f("ix_calibration_procedures_magnitude"), table_name="calibration_procedures")
    op.drop_index(op.f("ix_calibration_procedures_name"), table_name="calibration_procedures")
    op.drop_index(op.f("ix_calibration_procedures_code"), table_name="calibration_procedures")
    op.drop_index(op.f("ix_calibration_procedures_id"), table_name="calibration_procedures")
    op.drop_table("calibration_procedures")

    op.drop_index(
        op.f("ix_reference_standard_uncertainties_reference_standard_id"),
        table_name="reference_standard_uncertainties",
    )
    op.drop_index(op.f("ix_reference_standard_uncertainties_id"), table_name="reference_standard_uncertainties")
    op.drop_table("reference_standard_uncertainties")

    op.drop_index("uq_reference_standards_internal_code_active", table_name="reference_standards")
    op.drop_index(op.f("ix_reference_standards_status"), table_name="reference_standards")
    op.drop_index(op.f("ix_reference_standards_next_calibration_on"), table_name="reference_standards")
    op.drop_index(op.f("ix_reference_standards_magnitude"), table_name="reference_standards")
    op.drop_index(op.f("ix_reference_standards_owner_company"), table_name="reference_standards")
    op.drop_index(op.f("ix_reference_standards_name"), table_name="reference_standards")
    op.drop_index(op.f("ix_reference_standards_internal_code"), table_name="reference_standards")
    op.drop_index(op.f("ix_reference_standards_id"), table_name="reference_standards")
    op.drop_table("reference_standards")
