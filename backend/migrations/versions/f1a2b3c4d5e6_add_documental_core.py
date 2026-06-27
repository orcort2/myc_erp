"""add documental core

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-06-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "controlled_documents",
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=60), nullable=False),
        sa.Column("quality_level", sa.String(length=80), nullable=True),
        sa.Column("current_revision", sa.String(length=80), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("last_review_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("retention_time", sa.String(length=120), nullable=True),
        sa.Column("digital_location", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_controlled_documents_id"), "controlled_documents", ["id"], unique=False)
    op.create_index(op.f("ix_controlled_documents_code"), "controlled_documents", ["code"], unique=True)
    op.create_index(op.f("ix_controlled_documents_name"), "controlled_documents", ["name"], unique=False)
    op.create_index(op.f("ix_controlled_documents_document_type"), "controlled_documents", ["document_type"], unique=False)
    op.create_index(op.f("ix_controlled_documents_quality_level"), "controlled_documents", ["quality_level"], unique=False)
    op.create_index(op.f("ix_controlled_documents_status"), "controlled_documents", ["status"], unique=False)
    op.create_index(op.f("ix_controlled_documents_created_by_id"), "controlled_documents", ["created_by_id"], unique=False)

    op.create_table(
        "controlled_document_versions",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("revision", sa.String(length=80), nullable=False),
        sa.Column("file_path", sa.String(length=255), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["controlled_documents.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_controlled_document_versions_id"), "controlled_document_versions", ["id"], unique=False)
    op.create_index(op.f("ix_controlled_document_versions_document_id"), "controlled_document_versions", ["document_id"], unique=False)
    op.create_index(op.f("ix_controlled_document_versions_revision"), "controlled_document_versions", ["revision"], unique=False)
    op.create_index(op.f("ix_controlled_document_versions_status"), "controlled_document_versions", ["status"], unique=False)
    op.create_index(op.f("ix_controlled_document_versions_uploaded_by_id"), "controlled_document_versions", ["uploaded_by_id"], unique=False)
    op.create_index(op.f("ix_controlled_document_versions_approved_by_id"), "controlled_document_versions", ["approved_by_id"], unique=False)
    op.create_index(op.f("ix_controlled_document_versions_reviewed_by_id"), "controlled_document_versions", ["reviewed_by_id"], unique=False)
    op.create_index(
        "uq_controlled_document_one_active_version",
        "controlled_document_versions",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "document_interpretations",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("document_version_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("interpretation_type", sa.String(length=80), nullable=False),
        sa.Column("magnitude", sa.String(length=80), nullable=True),
        sa.Column("equipment_type", sa.String(length=120), nullable=True),
        sa.Column("service_type", sa.String(length=80), nullable=True),
        sa.Column("calibration_scope", sa.String(length=40), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["controlled_documents.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["controlled_document_versions.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in [
        "id",
        "document_id",
        "document_version_id",
        "name",
        "interpretation_type",
        "magnitude",
        "equipment_type",
        "service_type",
        "calibration_scope",
        "status",
        "created_by_id",
        "approved_by_id",
    ]:
        op.create_index(op.f(f"ix_document_interpretations_{column}"), "document_interpretations", [column], unique=False)

    op.create_table(
        "technical_profiles",
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("magnitude", sa.String(length=80), nullable=False),
        sa.Column("equipment_type", sa.String(length=120), nullable=False),
        sa.Column("service_type", sa.String(length=80), nullable=False, server_default="calibration"),
        sa.Column("calibration_scope", sa.String(length=40), nullable=False),
        sa.Column("procedure_document_id", sa.Integer(), nullable=True),
        sa.Column("procedure_interpretation_id", sa.Integer(), nullable=True),
        sa.Column("field_sheet_template_document_id", sa.Integer(), nullable=True),
        sa.Column("certificate_template_document_id", sa.Integer(), nullable=True),
        sa.Column("uncertainty_source_document_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rules", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["procedure_document_id"], ["controlled_documents.id"]),
        sa.ForeignKeyConstraint(["procedure_interpretation_id"], ["document_interpretations.id"]),
        sa.ForeignKeyConstraint(["field_sheet_template_document_id"], ["controlled_documents.id"]),
        sa.ForeignKeyConstraint(["certificate_template_document_id"], ["controlled_documents.id"]),
        sa.ForeignKeyConstraint(["uncertainty_source_document_id"], ["controlled_documents.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    for column in [
        "id",
        "code",
        "name",
        "magnitude",
        "equipment_type",
        "service_type",
        "calibration_scope",
        "status",
        "procedure_document_id",
        "procedure_interpretation_id",
        "field_sheet_template_document_id",
        "certificate_template_document_id",
        "uncertainty_source_document_id",
        "created_by_id",
        "approved_by_id",
    ]:
        op.create_index(op.f(f"ix_technical_profiles_{column}"), "technical_profiles", [column], unique=column == "code")

    op.create_table(
        "technical_profile_allowed_patterns",
        sa.Column("technical_profile_id", sa.Integer(), nullable=False),
        sa.Column("pattern_id", sa.Integer(), nullable=True),
        sa.Column("pattern_code", sa.String(length=120), nullable=True),
        sa.Column("min_range", sa.Numeric(18, 6), nullable=True),
        sa.Column("max_range", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("is_preferred", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["technical_profile_id"], ["technical_profiles.id"]),
        sa.ForeignKeyConstraint(["pattern_id"], ["reference_standards.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_technical_profile_allowed_patterns_id"), "technical_profile_allowed_patterns", ["id"], unique=False)
    op.create_index(op.f("ix_technical_profile_allowed_patterns_technical_profile_id"), "technical_profile_allowed_patterns", ["technical_profile_id"], unique=False)
    op.create_index(op.f("ix_technical_profile_allowed_patterns_pattern_id"), "technical_profile_allowed_patterns", ["pattern_id"], unique=False)
    op.create_index(op.f("ix_technical_profile_allowed_patterns_pattern_code"), "technical_profile_allowed_patterns", ["pattern_code"], unique=False)

    documents = sa.table(
        "controlled_documents",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("document_type", sa.String),
        sa.column("quality_level", sa.String),
        sa.column("status", sa.String),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        documents,
        [
            {"code": "MDG-01", "name": "Manual de Gestion de la Calidad", "document_type": "manual", "quality_level": "Nivel I", "status": "draft", "description": "Documento semilla del nucleo documental."},
            {"code": "FCA-02", "name": "Lista Maestra de Documentos", "document_type": "record", "quality_level": "Nivel II", "status": "draft", "description": "Lista maestra inicial."},
            {"code": "PMP-01", "name": "Procedimiento de uso y calibracion de manometros y vacuometros", "document_type": "procedure", "quality_level": "Nivel II", "status": "draft", "description": "Procedimiento base para presion."},
            {"code": "FCA-15-7", "name": "Calibracion de manometros", "document_type": "field_sheet_template", "quality_level": "Nivel III", "status": "draft", "description": "Formato semilla de hoja de campo."},
            {"code": "FPV-01", "name": "Orden de trabajo", "document_type": "work_order_template", "quality_level": "Nivel III", "status": "draft", "description": "Formato semilla de orden de trabajo."},
            {"code": "FCA-22", "name": "Cotizacion", "document_type": "quotation_template", "quality_level": "Nivel III", "status": "draft", "description": "Formato semilla de cotizacion."},
            {"code": "FCA-18-1", "name": "Calculo de incertidumbre", "document_type": "uncertainty_calculation", "quality_level": "Nivel III", "status": "draft", "description": "Fuente documental para modelo de incertidumbre futuro."},
        ],
    )

    profiles = sa.table(
        "technical_profiles",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("magnitude", sa.String),
        sa.column("equipment_type", sa.String),
        sa.column("service_type", sa.String),
        sa.column("calibration_scope", sa.String),
        sa.column("status", sa.String),
        sa.column("version", sa.Integer),
        sa.column("notes", sa.Text),
    )
    op.bulk_insert(
        profiles,
        [
            {
                "code": "PT-PRESION-MANOMETRO-ACR-001",
                "name": "Perfil Tecnico Presion - Manometros Acreditado",
                "magnitude": "Presion",
                "equipment_type": "Manometro",
                "service_type": "calibration",
                "calibration_scope": "accredited",
                "status": "draft",
                "version": 1,
                "notes": "Perfil semilla; no contiene calculos metrologicos.",
            }
        ],
    )

    op.alter_column("controlled_documents", "status", server_default=None)
    op.alter_column("controlled_document_versions", "status", server_default=None)
    op.alter_column("document_interpretations", "status", server_default=None)
    op.alter_column("document_interpretations", "version", server_default=None)
    op.alter_column("technical_profiles", "service_type", server_default=None)
    op.alter_column("technical_profiles", "status", server_default=None)
    op.alter_column("technical_profiles", "version", server_default=None)
    op.alter_column("technical_profile_allowed_patterns", "is_preferred", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_technical_profile_allowed_patterns_pattern_code"), table_name="technical_profile_allowed_patterns")
    op.drop_index(op.f("ix_technical_profile_allowed_patterns_pattern_id"), table_name="technical_profile_allowed_patterns")
    op.drop_index(op.f("ix_technical_profile_allowed_patterns_technical_profile_id"), table_name="technical_profile_allowed_patterns")
    op.drop_index(op.f("ix_technical_profile_allowed_patterns_id"), table_name="technical_profile_allowed_patterns")
    op.drop_table("technical_profile_allowed_patterns")
    for column in [
        "approved_by_id",
        "created_by_id",
        "uncertainty_source_document_id",
        "certificate_template_document_id",
        "field_sheet_template_document_id",
        "procedure_interpretation_id",
        "procedure_document_id",
        "status",
        "calibration_scope",
        "service_type",
        "equipment_type",
        "magnitude",
        "name",
        "code",
        "id",
    ]:
        op.drop_index(op.f(f"ix_technical_profiles_{column}"), table_name="technical_profiles")
    op.drop_table("technical_profiles")
    for column in [
        "approved_by_id",
        "created_by_id",
        "status",
        "calibration_scope",
        "service_type",
        "equipment_type",
        "magnitude",
        "interpretation_type",
        "name",
        "document_version_id",
        "document_id",
        "id",
    ]:
        op.drop_index(op.f(f"ix_document_interpretations_{column}"), table_name="document_interpretations")
    op.drop_table("document_interpretations")
    op.drop_index("uq_controlled_document_one_active_version", table_name="controlled_document_versions")
    op.drop_index(op.f("ix_controlled_document_versions_reviewed_by_id"), table_name="controlled_document_versions")
    op.drop_index(op.f("ix_controlled_document_versions_approved_by_id"), table_name="controlled_document_versions")
    op.drop_index(op.f("ix_controlled_document_versions_uploaded_by_id"), table_name="controlled_document_versions")
    op.drop_index(op.f("ix_controlled_document_versions_status"), table_name="controlled_document_versions")
    op.drop_index(op.f("ix_controlled_document_versions_revision"), table_name="controlled_document_versions")
    op.drop_index(op.f("ix_controlled_document_versions_document_id"), table_name="controlled_document_versions")
    op.drop_index(op.f("ix_controlled_document_versions_id"), table_name="controlled_document_versions")
    op.drop_table("controlled_document_versions")
    op.drop_index(op.f("ix_controlled_documents_created_by_id"), table_name="controlled_documents")
    op.drop_index(op.f("ix_controlled_documents_status"), table_name="controlled_documents")
    op.drop_index(op.f("ix_controlled_documents_quality_level"), table_name="controlled_documents")
    op.drop_index(op.f("ix_controlled_documents_document_type"), table_name="controlled_documents")
    op.drop_index(op.f("ix_controlled_documents_name"), table_name="controlled_documents")
    op.drop_index(op.f("ix_controlled_documents_code"), table_name="controlled_documents")
    op.drop_index(op.f("ix_controlled_documents_id"), table_name="controlled_documents")
    op.drop_table("controlled_documents")
