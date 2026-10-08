from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class TechnicalReport(IntegerPkMixin, TimestampMixin, Base):
    """Documento técnico no metrológico asociado a un equipo de una OT LAB.

    Vive en paralelo a FieldSheet. Una OT de calibración usa FieldSheet;
    una OT de servicio general usa TechnicalReport.
    """

    __tablename__ = "technical_reports"
    __table_args__ = (
        CheckConstraint(
            "report_type IN "
            "('installation', 'verification', 'repair', 'maintenance', 'sale')",
            name="ck_technical_report_type",
        ),
        CheckConstraint(
            "status IN "
            "('draft', 'in_progress', 'ready_for_signatures', 'completed', 'cancelled')",
            name="ck_technical_report_status",
        ),
        CheckConstraint(
            "revision_number >= 1",
            name="ck_technical_report_revision_number",
        ),
        CheckConstraint(
            "report_schema_version >= 1",
            name="ck_technical_report_schema_version",
        ),
        UniqueConstraint(
            "folio",
            name="uq_technical_reports_folio",
        ),
        UniqueConstraint(
            "supersedes_report_id",
            name="uq_technical_reports_supersedes_report_id",
        ),
        Index(
            "uq_technical_reports_current_lab_equipment",
            "lab_equipment_id",
            unique=True,
            postgresql_where=text("is_current IS TRUE"),
        ),
        # SG-4J-A1: unicidad futura por intervención. Conviven con las
        # restricciones heredadas (folio único, un vigente por equipo), que NO
        # se retiran hasta que todos los consumidores migren.
        UniqueConstraint(
            "intervention_id",
            "revision_number",
            name="uq_technical_reports_intervention_revision",
        ),
        Index(
            "uq_technical_reports_current_intervention",
            "intervention_id",
            unique=True,
            postgresql_where=text("is_current IS TRUE"),
        ),
    )

    lab_equipment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "lab_work_order_equipment.id",
            name="fk_technical_reports_lab_equipment_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # Identidad estable del trabajo técnico (SG-4J-A1). Nullable en base de
    # datos durante la transición: el servicio siempre la asigna y la
    # migración la rellena para todo el histórico; NOT NULL llega después.
    intervention_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "technical_interventions.id",
            name="fk_technical_reports_intervention_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    report_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )

    # Folio documental propio del reporte.
    # Installation: MYC-INMM-AA-XXXX.
    folio: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="draft",
        server_default="draft",
        index=True,
    )

    capture_values: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )

    # Snapshot de OT + cliente + equipo usado por esta revisión.
    document_snapshot: Mapped[dict | None] = mapped_column(JSON)

    report_schema_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    # Técnico que confirma la captura antes de pasar a firmas.
    performed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_technical_reports_performed_by_user_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )
    performed_by_name_snapshot: Mapped[str | None] = mapped_column(
        String(255)
    )
    performed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Texto exacto aceptado por el cliente en esta revisión.
    client_conformity_text_snapshot: Mapped[str | None] = mapped_column(Text)

    signature_session_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "lab_work_order_signature_sessions.id",
            name="fk_technical_reports_signature_session_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    supersedes_report_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "technical_reports.id",
            name="fk_technical_reports_supersedes_report_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    pdf_renderer_version: Mapped[int | None] = mapped_column(Integer)
    final_pdf_path: Mapped[str | None] = mapped_column(Text)
    final_pdf_sha256: Mapped[str | None] = mapped_column(String(64))
    final_pdf_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    lab_equipment: Mapped["LabWorkOrderEquipment"] = relationship(
        back_populates="technical_reports",
    )

    intervention: Mapped["TechnicalIntervention | None"] = relationship(
        back_populates="reports",
        foreign_keys=[intervention_id],
    )

    performed_by: Mapped["User | None"] = relationship(
        foreign_keys=[performed_by_user_id],
    )

    signature_session: Mapped["LabWorkOrderSignatureSession | None"] = relationship(
        foreign_keys=[signature_session_id],
    )

    supersedes_report: Mapped["TechnicalReport | None"] = relationship(
        remote_side="TechnicalReport.id",
        foreign_keys=[supersedes_report_id],
        uselist=False,
    )

    evidence: Mapped[list["TechnicalReportEvidence"]] = relationship(
        back_populates="technical_report",
        cascade="all, delete-orphan",
        order_by="TechnicalReportEvidence.position",
    )


class TechnicalReportEvidence(IntegerPkMixin, TimestampMixin, Base):
    """Evidencia fotográfica perteneciente a una revisión de reporte."""

    __tablename__ = "technical_report_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ('before', 'during', 'incident', 'after')",
            name="ck_technical_report_evidence_type",
        ),
        CheckConstraint(
            "size_bytes > 0",
            name="ck_technical_report_evidence_size",
        ),
        CheckConstraint(
            "position >= 1",
            name="ck_technical_report_evidence_position",
        ),
        UniqueConstraint(
            "technical_report_id",
            "position",
            name="uq_technical_report_evidence_position",
        ),
        # Nombres explícitos: son los que crea la migración ef09a7ea9e97
        # (index=True generaría ix_<tabla>_<columna> y produciría drift).
        Index("ix_technical_report_evidence_report_id", "technical_report_id"),
        Index("ix_technical_report_evidence_type", "evidence_type"),
    )

    technical_report_id: Mapped[int] = mapped_column(
        ForeignKey(
            "technical_reports.id",
            name="fk_technical_report_evidence_report_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    evidence_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    caption: Mapped[str | None] = mapped_column(Text)

    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_technical_report_evidence_created_by_user_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    technical_report: Mapped["TechnicalReport"] = relationship(
        back_populates="evidence",
    )

    created_by: Mapped["User"] = relationship(
        foreign_keys=[created_by_user_id],
    )
