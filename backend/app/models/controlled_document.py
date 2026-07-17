from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class ControlledDocument(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "controlled_documents"

    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    document_type: Mapped[str] = mapped_column(String(60), index=True)
    quality_level: Mapped[str | None] = mapped_column(String(80), index=True)
    current_revision: Mapped[str | None] = mapped_column(String(80))
    issue_date: Mapped[date | None] = mapped_column(Date)
    last_review_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date)
    retention_time: Mapped[str | None] = mapped_column(String(120))
    digital_location: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    versions: Mapped[list["ControlledDocumentVersion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ControlledDocumentVersion.created_at.desc()",
    )
    interpretations: Mapped[list["DocumentInterpretation"]] = relationship(
        back_populates="document"
    )


class ControlledDocumentVersion(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "controlled_document_versions"

    document_id: Mapped[int] = mapped_column(ForeignKey("controlled_documents.id"), index=True)
    revision: Mapped[str] = mapped_column(String(80), index=True)
    file_path: Mapped[str | None] = mapped_column(String(255))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(120))
    checksum: Mapped[str | None] = mapped_column(String(128))
    change_summary: Mapped[str | None] = mapped_column(Text)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    effective_date: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document: Mapped["ControlledDocument"] = relationship(back_populates="versions")
    interpretations: Mapped[list["DocumentInterpretation"]] = relationship(
        back_populates="document_version"
    )


class DocumentInterpretation(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "document_interpretations"

    document_id: Mapped[int] = mapped_column(ForeignKey("controlled_documents.id"), index=True)
    document_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("controlled_document_versions.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    interpretation_type: Mapped[str] = mapped_column(String(80), index=True)
    magnitude: Mapped[str | None] = mapped_column(String(80), index=True)
    equipment_type: Mapped[str | None] = mapped_column(String(120), index=True)
    service_type: Mapped[str | None] = mapped_column(String(80), index=True)
    calibration_scope: Mapped[str | None] = mapped_column(String(40), index=True)
    data: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document: Mapped["ControlledDocument"] = relationship(back_populates="interpretations")
    document_version: Mapped["ControlledDocumentVersion | None"] = relationship(
        back_populates="interpretations"
    )


class TechnicalProfile(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "technical_profiles"

    code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    magnitude: Mapped[str] = mapped_column(String(80), index=True)
    equipment_type: Mapped[str] = mapped_column(String(120), index=True)
    service_type: Mapped[str] = mapped_column(String(80), default="calibration", index=True)
    calibration_scope: Mapped[str] = mapped_column(String(40), index=True)
    procedure_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("controlled_documents.id"), index=True
    )
    procedure_interpretation_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_interpretations.id"), index=True
    )
    field_sheet_template_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("controlled_documents.id"), index=True
    )
    certificate_template_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("controlled_documents.id"), index=True
    )
    uncertainty_source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("controlled_documents.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    rules: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    allowed_patterns: Mapped[list["TechnicalProfileAllowedPattern"]] = relationship(
        back_populates="technical_profile",
        cascade="all, delete-orphan",
        order_by="TechnicalProfileAllowedPattern.priority.asc()",
    )


class TechnicalProfileAllowedPattern(IntegerPkMixin, Base):
    __tablename__ = "technical_profile_allowed_patterns"

    technical_profile_id: Mapped[int] = mapped_column(ForeignKey("technical_profiles.id"), index=True)
    # Conecta con reference_standards como tabla formal de patrones del sistema.
    pattern_id: Mapped[int | None] = mapped_column(ForeignKey("reference_standards.id"), index=True)
    pattern_code: Mapped[str | None] = mapped_column(String(120), index=True)
    min_range: Mapped[float | None] = mapped_column(Numeric(18, 6))
    max_range: Mapped[float | None] = mapped_column(Numeric(18, 6))
    unit: Mapped[str | None] = mapped_column(String(40))
    priority: Mapped[int | None] = mapped_column(Integer)
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    technical_profile: Mapped["TechnicalProfile"] = relationship(back_populates="allowed_patterns")
