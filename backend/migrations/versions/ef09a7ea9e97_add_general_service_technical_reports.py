"""add general service technical reports

Revision ID: ef09a7ea9e97
Revises: c3e6a9b2d4f8
Create Date: 2026-10-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ef09a7ea9e97"
down_revision: Union[str, None] = "c3e6a9b2d4f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Categoría operacional de la OT LAB.
    #
    # Todo histórico anterior a esta migración es calibración. Se conserva
    # también el server_default para que callers antiguos que todavía no
    # envían operational_category sigan creando OTs de calibración.
    # ------------------------------------------------------------------
    op.add_column(
        "lab_work_orders",
        sa.Column(
            "operational_category",
            sa.String(length=40),
            nullable=False,
            server_default="calibration",
        ),
    )

    op.create_index(
        "ix_lab_work_orders_operational_category",
        "lab_work_orders",
        ["operational_category"],
        unique=False,
    )

    op.create_check_constraint(
        "ck_lab_work_order_operational_category",
        "lab_work_orders",
        "operational_category IN ('calibration', 'general_service')",
    )

    # ------------------------------------------------------------------
    # 2. Reportes técnicos.
    #
    # Son documentos paralelos a FieldSheet. Nunca reutilizan FieldSheet ni
    # LabWorkOrderEquipment.certificate_folio.
    #
    # Una reapertura crea una revisión nueva y preserva la anterior.
    # ------------------------------------------------------------------
    op.create_table(
        "technical_reports",
        sa.Column("id", sa.Integer(), nullable=False),

        sa.Column(
            "lab_equipment_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "report_type",
            sa.String(length=40),
            nullable=False,
        ),

        # Autoridad documental del reporte. Para installation:
        # MYC-INMM-AA-XXXX
        sa.Column(
            "folio",
            sa.String(length=40),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="draft",
        ),

        # Datos específicos del tipo de reporte. Para instalación contendrá
        # ubicación, condición inicial, actividades, incidencias, prueba
        # funcional, resultado de efectividad, observaciones, etc.
        sa.Column(
            "capture_values",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),

        # Snapshot documental del contexto que dio origen a esta revisión:
        # OT, cliente y equipo. Evita reinterpretar históricos desde datos
        # maestros modificados posteriormente.
        sa.Column(
            "document_snapshot",
            sa.JSON(),
            nullable=True,
        ),

        # Versión del contrato de captura. Permite evolucionar Installation
        # sin reinterpretar reportes históricos.
        sa.Column(
            "report_schema_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),

        # Usuario que confirmó/completó la CAPTURA técnica.
        sa.Column(
            "performed_by_user_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "performed_by_name_snapshot",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "performed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        # Texto exacto que el cliente acepta al firmar. Debe congelarse para
        # que cambiar la redacción futura de la app no cambie el significado
        # de una firma histórica.
        sa.Column(
            "client_conformity_text_snapshot",
            sa.Text(),
            nullable=True,
        ),

        # Sesión Cliente + Técnico ya existente en LAB.
        sa.Column(
            "signature_session_id",
            sa.Integer(),
            nullable=True,
        ),

        # Revisión documental.
        sa.Column(
            "revision_number",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "supersedes_report_id",
            sa.Integer(),
            nullable=True,
        ),

        # PDF final congelado.
        sa.Column(
            "pdf_renderer_version",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "final_pdf_path",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "final_pdf_sha256",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "final_pdf_generated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        # "completed" significa documento ya firmado y PDF final congelado.
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),

        sa.CheckConstraint(
            "report_type IN "
            "('installation', 'verification', 'repair', 'maintenance', 'sale')",
            name="ck_technical_report_type",
        ),
        sa.CheckConstraint(
            "status IN "
            "('draft', 'in_progress', 'ready_for_signatures', 'completed', 'cancelled')",
            name="ck_technical_report_status",
        ),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="ck_technical_report_revision_number",
        ),
        sa.CheckConstraint(
            "report_schema_version >= 1",
            name="ck_technical_report_schema_version",
        ),

        sa.ForeignKeyConstraint(
            ["lab_equipment_id"],
            ["lab_work_order_equipment.id"],
            name="fk_technical_reports_lab_equipment_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["performed_by_user_id"],
            ["users.id"],
            name="fk_technical_reports_performed_by_user_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["signature_session_id"],
            ["lab_work_order_signature_sessions.id"],
            name="fk_technical_reports_signature_session_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_report_id"],
            ["technical_reports.id"],
            name="fk_technical_reports_supersedes_report_id",
            ondelete="RESTRICT",
        ),

        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "folio",
            name="uq_technical_reports_folio",
        ),
        sa.UniqueConstraint(
            "supersedes_report_id",
            name="uq_technical_reports_supersedes_report_id",
        ),
    )

    op.create_index(
        "ix_technical_reports_lab_equipment_id",
        "technical_reports",
        ["lab_equipment_id"],
        unique=False,
    )
    op.create_index(
        "ix_technical_reports_report_type",
        "technical_reports",
        ["report_type"],
        unique=False,
    )
    op.create_index(
        "ix_technical_reports_status",
        "technical_reports",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_technical_reports_signature_session_id",
        "technical_reports",
        ["signature_session_id"],
        unique=False,
    )
    op.create_index(
        "ix_technical_reports_performed_by_user_id",
        "technical_reports",
        ["performed_by_user_id"],
        unique=False,
    )

    # Exactamente una revisión vigente por equipo, pero todas las revisiones
    # anteriores permanecen consultables e inmutables.
    op.create_index(
        "uq_technical_reports_current_lab_equipment",
        "technical_reports",
        ["lab_equipment_id"],
        unique=True,
        postgresql_where=sa.text("is_current IS TRUE"),
    )

    # ------------------------------------------------------------------
    # 3. Evidencia fotográfica.
    #
    # Los bytes NO viven en PostgreSQL. storage_path referencia el storage
    # administrado del backend; SHA-256 protege integridad documental.
    # ------------------------------------------------------------------
    op.create_table(
        "technical_report_evidence",
        sa.Column("id", sa.Integer(), nullable=False),

        sa.Column(
            "technical_report_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "evidence_type",
            sa.String(length=30),
            nullable=False,
        ),

        sa.Column(
            "storage_path",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "mime_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "size_bytes",
            sa.Integer(),
            nullable=False,
        ),

        # Orden global de aparición dentro de la revisión.
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "caption",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),

        sa.CheckConstraint(
            "evidence_type IN ('before', 'during', 'incident', 'after')",
            name="ck_technical_report_evidence_type",
        ),
        sa.CheckConstraint(
            "size_bytes > 0",
            name="ck_technical_report_evidence_size",
        ),
        sa.CheckConstraint(
            "position >= 1",
            name="ck_technical_report_evidence_position",
        ),

        sa.ForeignKeyConstraint(
            ["technical_report_id"],
            ["technical_reports.id"],
            name="fk_technical_report_evidence_report_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_technical_report_evidence_created_by_user_id",
            ondelete="RESTRICT",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "technical_report_id",
            "position",
            name="uq_technical_report_evidence_position",
        ),
    )

    op.create_index(
        "ix_technical_report_evidence_report_id",
        "technical_report_evidence",
        ["technical_report_id"],
        unique=False,
    )
    op.create_index(
        "ix_technical_report_evidence_type",
        "technical_report_evidence",
        ["evidence_type"],
        unique=False,
    )
    op.create_index(
        "ix_technical_report_evidence_created_by_user_id",
        "technical_report_evidence",
        ["created_by_user_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # 4. Secuencia institucional de instalación.
    #
    # Scope actual de InstitutionalFolioSequence:
    # document_type + prefix + year.
    #
    # En octubre de 2026:
    # next_value=1 -> MYC-IN10-26-0001
    #
    # El consecutivo es anual. El mes forma parte del folio visible pero NO
    # reinicia la secuencia.
    # ------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO institutional_folio_sequences
            (document_type, prefix, year, next_value, created_at, updated_at)
        VALUES
            ('technical_report', 'MYC-IN', 2026, 1, NOW(), NOW())
        ON CONFLICT (document_type, prefix, year)
        DO NOTHING
        """
    )


def downgrade() -> None:
    # No reutilizar una secuencia que ya haya consumido folios. Sólo puede
    # retirarse la fila inicial si jamás avanzó de 1.
    op.execute(
        """
        DELETE FROM institutional_folio_sequences
        WHERE document_type = 'technical_report'
          AND prefix = 'MYC-IN'
          AND year = 2026
          AND next_value = 1
        """
    )

    op.drop_index(
        "ix_technical_report_evidence_created_by_user_id",
        table_name="technical_report_evidence",
    )
    op.drop_index(
        "ix_technical_report_evidence_type",
        table_name="technical_report_evidence",
    )
    op.drop_index(
        "ix_technical_report_evidence_report_id",
        table_name="technical_report_evidence",
    )
    op.drop_table("technical_report_evidence")

    op.drop_index(
        "uq_technical_reports_current_lab_equipment",
        table_name="technical_reports",
    )
    op.drop_index(
        "ix_technical_reports_performed_by_user_id",
        table_name="technical_reports",
    )
    op.drop_index(
        "ix_technical_reports_signature_session_id",
        table_name="technical_reports",
    )
    op.drop_index(
        "ix_technical_reports_status",
        table_name="technical_reports",
    )
    op.drop_index(
        "ix_technical_reports_report_type",
        table_name="technical_reports",
    )
    op.drop_index(
        "ix_technical_reports_lab_equipment_id",
        table_name="technical_reports",
    )
    op.drop_table("technical_reports")

    op.drop_constraint(
        "ck_lab_work_order_operational_category",
        "lab_work_orders",
        type_="check",
    )
    op.drop_index(
        "ix_lab_work_orders_operational_category",
        table_name="lab_work_orders",
    )
    op.drop_column(
        "lab_work_orders",
        "operational_category",
    )
