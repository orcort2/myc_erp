"""add reference standard certificates

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a2b3c4d5e6f7"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reference_standard_certificates",
        sa.Column("reference_standard_id", sa.Integer(), nullable=False),
        sa.Column("controlled_document_id", sa.Integer(), nullable=True),
        sa.Column("controlled_document_version_id", sa.Integer(), nullable=True),
        sa.Column("certificate_number", sa.String(length=120), nullable=False),
        sa.Column("issuing_laboratory", sa.String(length=180), nullable=True),
        sa.Column("accreditation_body", sa.String(length=180), nullable=True),
        sa.Column("accreditation_number", sa.String(length=120), nullable=True),
        sa.Column("calibration_date", sa.Date(), nullable=True),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("traceability_statement", sa.Text(), nullable=True),
        sa.Column("environmental_conditions", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["reference_standard_id"], ["reference_standards.id"]),
        sa.ForeignKeyConstraint(["controlled_document_id"], ["controlled_documents.id"]),
        sa.ForeignKeyConstraint(["controlled_document_version_id"], ["controlled_document_versions.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in [
        "id",
        "reference_standard_id",
        "controlled_document_id",
        "controlled_document_version_id",
        "certificate_number",
        "expiration_date",
        "status",
        "is_current",
        "created_by_id",
        "approved_by_id",
    ]:
        op.create_index(
            op.f(f"ix_reference_standard_certificates_{column}"),
            "reference_standard_certificates",
            [column],
            unique=False,
        )
    op.create_index(
        "uq_reference_standard_current_certificate",
        "reference_standard_certificates",
        ["reference_standard_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )

    op.create_table(
        "reference_standard_certificate_uncertainties",
        sa.Column("certificate_id", sa.Integer(), nullable=False),
        sa.Column("magnitude", sa.String(length=80), nullable=True),
        sa.Column("measurement_type", sa.String(length=120), nullable=True),
        sa.Column("range_min", sa.Numeric(18, 6), nullable=True),
        sa.Column("range_max", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("uncertainty_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("uncertainty_unit", sa.String(length=40), nullable=True),
        sa.Column("k_factor", sa.Numeric(12, 6), nullable=True, server_default="2"),
        sa.Column("confidence_level", sa.String(length=80), nullable=True),
        sa.Column("distribution", sa.String(length=80), nullable=True),
        sa.Column("formula_reference", sa.String(length=180), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["certificate_id"], ["reference_standard_certificates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in [
        "id",
        "certificate_id",
        "magnitude",
        "measurement_type",
        "range_min",
        "range_max",
        "unit",
        "is_active",
    ]:
        op.create_index(
            op.f(f"ix_reference_standard_certificate_uncertainties_{column}"),
            "reference_standard_certificate_uncertainties",
            [column],
            unique=False,
        )

    op.add_column(
        "field_sheet_reference_standards",
        sa.Column("reference_standard_certificate_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "field_sheet_reference_standards",
        sa.Column("selected_uncertainty_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "field_sheet_reference_standards",
        sa.Column("selection_status", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "field_sheet_reference_standards",
        sa.Column("selection_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "field_sheet_reference_standards",
        sa.Column("validation_snapshot", sa.JSON(), nullable=True),
    )
    op.create_index(
        op.f("ix_field_sheet_reference_standards_reference_standard_certificate_id"),
        "field_sheet_reference_standards",
        ["reference_standard_certificate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_field_sheet_reference_standards_selected_uncertainty_id"),
        "field_sheet_reference_standards",
        ["selected_uncertainty_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_field_sheet_reference_standards_certificate_id",
        "field_sheet_reference_standards",
        "reference_standard_certificates",
        ["reference_standard_certificate_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_field_sheet_reference_standards_uncertainty_id",
        "field_sheet_reference_standards",
        "reference_standard_certificate_uncertainties",
        ["selected_uncertainty_id"],
        ["id"],
    )

    op.alter_column("reference_standard_certificates", "status", server_default=None)
    op.alter_column("reference_standard_certificates", "is_current", server_default=None)
    op.alter_column("reference_standard_certificate_uncertainties", "k_factor", server_default=None)
    op.alter_column("reference_standard_certificate_uncertainties", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_field_sheet_reference_standards_uncertainty_id", "field_sheet_reference_standards", type_="foreignkey")
    op.drop_constraint("fk_field_sheet_reference_standards_certificate_id", "field_sheet_reference_standards", type_="foreignkey")
    op.drop_index(op.f("ix_field_sheet_reference_standards_selected_uncertainty_id"), table_name="field_sheet_reference_standards")
    op.drop_index(op.f("ix_field_sheet_reference_standards_reference_standard_certificate_id"), table_name="field_sheet_reference_standards")
    op.drop_column("field_sheet_reference_standards", "validation_snapshot")
    op.drop_column("field_sheet_reference_standards", "selection_notes")
    op.drop_column("field_sheet_reference_standards", "selection_status")
    op.drop_column("field_sheet_reference_standards", "selected_uncertainty_id")
    op.drop_column("field_sheet_reference_standards", "reference_standard_certificate_id")
    for column in [
        "is_active",
        "unit",
        "range_max",
        "range_min",
        "measurement_type",
        "magnitude",
        "certificate_id",
        "id",
    ]:
        op.drop_index(
            op.f(f"ix_reference_standard_certificate_uncertainties_{column}"),
            table_name="reference_standard_certificate_uncertainties",
        )
    op.drop_table("reference_standard_certificate_uncertainties")
    op.drop_index("uq_reference_standard_current_certificate", table_name="reference_standard_certificates")
    for column in [
        "approved_by_id",
        "created_by_id",
        "is_current",
        "status",
        "expiration_date",
        "certificate_number",
        "controlled_document_version_id",
        "controlled_document_id",
        "reference_standard_id",
        "id",
    ]:
        op.drop_index(
            op.f(f"ix_reference_standard_certificates_{column}"),
            table_name="reference_standard_certificates",
        )
    op.drop_table("reference_standard_certificates")
