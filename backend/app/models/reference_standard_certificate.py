from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class ReferenceStandardCertificate(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "reference_standard_certificates"

    reference_standard_id: Mapped[int] = mapped_column(ForeignKey("reference_standards.id"), index=True)
    controlled_document_id: Mapped[int | None] = mapped_column(ForeignKey("controlled_documents.id"), index=True)
    controlled_document_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("controlled_document_versions.id"), index=True
    )
    certificate_number: Mapped[str] = mapped_column(String(120), index=True)
    issuing_laboratory: Mapped[str | None] = mapped_column(String(180))
    accreditation_body: Mapped[str | None] = mapped_column(String(180))
    accreditation_number: Mapped[str | None] = mapped_column(String(120))
    calibration_date: Mapped[date | None] = mapped_column(Date)
    expiration_date: Mapped[date | None] = mapped_column(Date, index=True)
    received_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    traceability_statement: Mapped[str | None] = mapped_column(Text)
    environmental_conditions: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    reference_standard: Mapped["ReferenceStandard"] = relationship(back_populates="certificates")
    uncertainties: Mapped[list["ReferenceStandardCertificateUncertainty"]] = relationship(
        back_populates="certificate",
        cascade="all, delete-orphan",
        order_by="ReferenceStandardCertificateUncertainty.range_min.asc()",
    )

    @property
    def effective_status(self) -> str:
        if self.status == "active" and self.expiration_date and self.expiration_date < date.today():
            return "expired"
        return self.status


class ReferenceStandardCertificateUncertainty(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "reference_standard_certificate_uncertainties"

    certificate_id: Mapped[int] = mapped_column(ForeignKey("reference_standard_certificates.id"), index=True)
    magnitude: Mapped[str | None] = mapped_column(String(80), index=True)
    measurement_type: Mapped[str | None] = mapped_column(String(120), index=True)
    range_min: Mapped[float | None] = mapped_column(Numeric(18, 6), index=True)
    range_max: Mapped[float | None] = mapped_column(Numeric(18, 6), index=True)
    unit: Mapped[str | None] = mapped_column(String(40), index=True)
    uncertainty_value: Mapped[float] = mapped_column(Numeric(18, 6))
    uncertainty_unit: Mapped[str | None] = mapped_column(String(40))
    k_factor: Mapped[float | None] = mapped_column(Numeric(12, 6), default=2)
    confidence_level: Mapped[str | None] = mapped_column(String(80))
    distribution: Mapped[str | None] = mapped_column(String(80))
    formula_reference: Mapped[str | None] = mapped_column(String(180))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    certificate: Mapped["ReferenceStandardCertificate"] = relationship(back_populates="uncertainties")
