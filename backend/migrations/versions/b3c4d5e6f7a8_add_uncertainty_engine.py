"""add uncertainty engine

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-06-29 00:00:00.000000
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "uncertainty_models",
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("magnitude", sa.String(length=80), nullable=False),
        sa.Column("equipment_family", sa.String(length=120), nullable=True),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("default_coverage_factor", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "version", name="uq_uncertainty_models_code_version"),
    )
    op.create_index(op.f("ix_uncertainty_models_code"), "uncertainty_models", ["code"], unique=False)
    op.create_index(op.f("ix_uncertainty_models_equipment_family"), "uncertainty_models", ["equipment_family"], unique=False)
    op.create_index(op.f("ix_uncertainty_models_magnitude"), "uncertainty_models", ["magnitude"], unique=False)
    op.create_index(op.f("ix_uncertainty_models_name"), "uncertainty_models", ["name"], unique=False)
    op.create_index(op.f("ix_uncertainty_models_status"), "uncertainty_models", ["status"], unique=False)
    op.create_index(op.f("ix_uncertainty_models_version"), "uncertainty_models", ["version"], unique=False)

    op.create_table(
        "uncertainty_components",
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=60), nullable=False),
        sa.Column("distribution", sa.String(length=60), nullable=True),
        sa.Column("divisor", sa.Float(), nullable=True),
        sa.Column("sensitivity_coefficient", sa.Float(), nullable=False),
        sa.Column("value_expression", sa.Text(), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["model_id"], ["uncertainty_models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_uncertainty_components_key"), "uncertainty_components", ["key"], unique=False)
    op.create_index(op.f("ix_uncertainty_components_model_id"), "uncertainty_components", ["model_id"], unique=False)
    op.create_index(op.f("ix_uncertainty_components_source_type"), "uncertainty_components", ["source_type"], unique=False)

    op.create_table(
        "uncertainty_formulas",
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("result_key", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active_formula", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["uncertainty_models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_uncertainty_formulas_is_active_formula"), "uncertainty_formulas", ["is_active_formula"], unique=False)
    op.create_index(op.f("ix_uncertainty_formulas_key"), "uncertainty_formulas", ["key"], unique=False)
    op.create_index(op.f("ix_uncertainty_formulas_model_id"), "uncertainty_formulas", ["model_id"], unique=False)
    op.create_index(op.f("ix_uncertainty_formulas_result_key"), "uncertainty_formulas", ["result_key"], unique=False)

    op.add_column("calibration_procedures", sa.Column("uncertainty_model_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_calibration_procedures_uncertainty_model_id"), "calibration_procedures", ["uncertainty_model_id"], unique=False)
    op.create_foreign_key(
        "fk_calibration_procedures_uncertainty_model_id",
        "calibration_procedures",
        "uncertainty_models",
        ["uncertainty_model_id"],
        ["id"],
    )

    op.create_table(
        "uncertainty_model_exceptions",
        sa.Column("base_model_id", sa.Integer(), nullable=True),
        sa.Column("alternate_model_id", sa.Integer(), nullable=False),
        sa.Column("magnitude", sa.String(length=80), nullable=True),
        sa.Column("equipment_type", sa.String(length=180), nullable=True),
        sa.Column("equipment_model", sa.String(length=120), nullable=True),
        sa.Column("procedure_id", sa.Integer(), nullable=True),
        sa.Column("profile_key", sa.String(length=80), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("authorized_by_id", sa.Integer(), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["alternate_model_id"], ["uncertainty_models.id"]),
        sa.ForeignKeyConstraint(["authorized_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["base_model_id"], ["uncertainty_models.id"]),
        sa.ForeignKeyConstraint(["procedure_id"], ["calibration_procedures.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_uncertainty_model_exceptions_alternate_model_id"), "uncertainty_model_exceptions", ["alternate_model_id"], unique=False)
    op.create_index(op.f("ix_uncertainty_model_exceptions_base_model_id"), "uncertainty_model_exceptions", ["base_model_id"], unique=False)
    op.create_index(op.f("ix_uncertainty_model_exceptions_equipment_model"), "uncertainty_model_exceptions", ["equipment_model"], unique=False)
    op.create_index(op.f("ix_uncertainty_model_exceptions_equipment_type"), "uncertainty_model_exceptions", ["equipment_type"], unique=False)
    op.create_index(op.f("ix_uncertainty_model_exceptions_magnitude"), "uncertainty_model_exceptions", ["magnitude"], unique=False)
    op.create_index(op.f("ix_uncertainty_model_exceptions_procedure_id"), "uncertainty_model_exceptions", ["procedure_id"], unique=False)
    op.create_index(op.f("ix_uncertainty_model_exceptions_profile_key"), "uncertainty_model_exceptions", ["profile_key"], unique=False)
    op.create_index(op.f("ix_uncertainty_model_exceptions_status"), "uncertainty_model_exceptions", ["status"], unique=False)

    op.create_table(
        "uncertainty_calculations",
        sa.Column("field_sheet_id", sa.Integer(), nullable=False),
        sa.Column("uncertainty_model_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("calculation_snapshot", sa.JSON(), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("component_results", sa.JSON(), nullable=False),
        sa.Column("formula_results", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["field_sheet_id"], ["field_sheets.id"]),
        sa.ForeignKeyConstraint(["uncertainty_model_id"], ["uncertainty_models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_uncertainty_calculations_field_sheet_id"), "uncertainty_calculations", ["field_sheet_id"], unique=False)
    op.create_index(op.f("ix_uncertainty_calculations_status"), "uncertainty_calculations", ["status"], unique=False)
    op.create_index(op.f("ix_uncertainty_calculations_uncertainty_model_id"), "uncertainty_calculations", ["uncertainty_model_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_uncertainty_calculations_uncertainty_model_id"), table_name="uncertainty_calculations")
    op.drop_index(op.f("ix_uncertainty_calculations_status"), table_name="uncertainty_calculations")
    op.drop_index(op.f("ix_uncertainty_calculations_field_sheet_id"), table_name="uncertainty_calculations")
    op.drop_table("uncertainty_calculations")
    op.drop_index(op.f("ix_uncertainty_model_exceptions_status"), table_name="uncertainty_model_exceptions")
    op.drop_index(op.f("ix_uncertainty_model_exceptions_profile_key"), table_name="uncertainty_model_exceptions")
    op.drop_index(op.f("ix_uncertainty_model_exceptions_procedure_id"), table_name="uncertainty_model_exceptions")
    op.drop_index(op.f("ix_uncertainty_model_exceptions_magnitude"), table_name="uncertainty_model_exceptions")
    op.drop_index(op.f("ix_uncertainty_model_exceptions_equipment_type"), table_name="uncertainty_model_exceptions")
    op.drop_index(op.f("ix_uncertainty_model_exceptions_equipment_model"), table_name="uncertainty_model_exceptions")
    op.drop_index(op.f("ix_uncertainty_model_exceptions_base_model_id"), table_name="uncertainty_model_exceptions")
    op.drop_index(op.f("ix_uncertainty_model_exceptions_alternate_model_id"), table_name="uncertainty_model_exceptions")
    op.drop_table("uncertainty_model_exceptions")
    op.drop_constraint("fk_calibration_procedures_uncertainty_model_id", "calibration_procedures", type_="foreignkey")
    op.drop_index(op.f("ix_calibration_procedures_uncertainty_model_id"), table_name="calibration_procedures")
    op.drop_column("calibration_procedures", "uncertainty_model_id")
    op.drop_index(op.f("ix_uncertainty_formulas_result_key"), table_name="uncertainty_formulas")
    op.drop_index(op.f("ix_uncertainty_formulas_model_id"), table_name="uncertainty_formulas")
    op.drop_index(op.f("ix_uncertainty_formulas_key"), table_name="uncertainty_formulas")
    op.drop_index(op.f("ix_uncertainty_formulas_is_active_formula"), table_name="uncertainty_formulas")
    op.drop_table("uncertainty_formulas")
    op.drop_index(op.f("ix_uncertainty_components_source_type"), table_name="uncertainty_components")
    op.drop_index(op.f("ix_uncertainty_components_model_id"), table_name="uncertainty_components")
    op.drop_index(op.f("ix_uncertainty_components_key"), table_name="uncertainty_components")
    op.drop_table("uncertainty_components")
    op.drop_index(op.f("ix_uncertainty_models_version"), table_name="uncertainty_models")
    op.drop_index(op.f("ix_uncertainty_models_status"), table_name="uncertainty_models")
    op.drop_index(op.f("ix_uncertainty_models_name"), table_name="uncertainty_models")
    op.drop_index(op.f("ix_uncertainty_models_magnitude"), table_name="uncertainty_models")
    op.drop_index(op.f("ix_uncertainty_models_equipment_family"), table_name="uncertainty_models")
    op.drop_index(op.f("ix_uncertainty_models_code"), table_name="uncertainty_models")
    op.drop_table("uncertainty_models")
