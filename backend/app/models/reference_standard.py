from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class ReferenceStandard(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "reference_standards"

    internal_code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    owner_company: Mapped[str] = mapped_column(String(40), index=True, default="MYC")
    magnitude: Mapped[str] = mapped_column(String(80), index=True)
    brand: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    serial_number: Mapped[str | None] = mapped_column(String(120))
    identification: Mapped[str | None] = mapped_column(String(120))
    unit: Mapped[str | None] = mapped_column(String(40))
    range_min: Mapped[float | None] = mapped_column(Numeric(18, 6))
    range_max: Mapped[float | None] = mapped_column(Numeric(18, 6))
    resolution: Mapped[float | None] = mapped_column(Numeric(18, 6))
    coverage_factor_k: Mapped[float | None] = mapped_column(Numeric(12, 6))
    provider: Mapped[str | None] = mapped_column(String(180))
    calibration_laboratory: Mapped[str | None] = mapped_column(String(180))
    certificate_number: Mapped[str | None] = mapped_column(String(120))
    certificate_file_path: Mapped[str | None] = mapped_column(String(255))
    calibrated_on: Mapped[date | None] = mapped_column(Date)
    next_calibration_on: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    uncertainties: Mapped[list["ReferenceStandardUncertainty"]] = relationship(
        back_populates="reference_standard",
        cascade="all, delete-orphan",
        order_by="ReferenceStandardUncertainty.range_min.asc()",
    )
    field_sheet_links: Mapped[list["FieldSheetReferenceStandard"]] = relationship(
        back_populates="reference_standard"
    )
    certificates: Mapped[list["ReferenceStandardCertificate"]] = relationship(
        back_populates="reference_standard",
        cascade="all, delete-orphan",
        order_by="ReferenceStandardCertificate.created_at.desc()",
    )

    @property
    def current_certificate(self):
        current = [
            certificate
            for certificate in self.certificates
            if certificate.is_current and certificate.status == "active"
        ]
        return current[0] if current else None

    @property
    def current_certificate_id(self) -> int | None:
        certificate = self.current_certificate
        return certificate.id if certificate else None

    @property
    def current_certificate_number(self) -> str | None:
        certificate = self.current_certificate
        return certificate.certificate_number if certificate else None

    @property
    def current_certificate_expiration_date(self) -> date | None:
        certificate = self.current_certificate
        return certificate.expiration_date if certificate else None

    @property
    def current_certificate_status(self) -> str | None:
        certificate = self.current_certificate
        return certificate.effective_status if certificate else None

    @property
    def effective_status(self) -> str:
        if self.status == "active" and self.next_calibration_on and self.next_calibration_on < date.today():
            return "expired"
        return self.status

    @property
    def is_overdue(self) -> bool:
        return self.effective_status == "expired"


class ReferenceStandardUncertainty(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "reference_standard_uncertainties"

    reference_standard_id: Mapped[int] = mapped_column(
        ForeignKey("reference_standards.id"), index=True
    )
    range_min: Mapped[float | None] = mapped_column(Numeric(18, 6))
    range_max: Mapped[float | None] = mapped_column(Numeric(18, 6))
    unit: Mapped[str | None] = mapped_column(String(40))
    uncertainty_value: Mapped[float] = mapped_column(Numeric(18, 6))
    coverage_factor_k: Mapped[float | None] = mapped_column(Numeric(12, 6))
    distribution: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)

    reference_standard: Mapped["ReferenceStandard"] = relationship(back_populates="uncertainties")


class FieldSheetReferenceStandard(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "field_sheet_reference_standards"
    __table_args__ = (
        UniqueConstraint(
            "field_sheet_id",
            "reference_standard_id",
            "usage_role",
            "measurement_section",
            name="uq_field_sheet_reference_standard_usage",
        ),
    )

    field_sheet_id: Mapped[int] = mapped_column(ForeignKey("field_sheets.id"), index=True)
    reference_standard_id: Mapped[int] = mapped_column(
        ForeignKey("reference_standards.id"), index=True
    )
    reference_standard_certificate_id: Mapped[int | None] = mapped_column(
        ForeignKey("reference_standard_certificates.id"), index=True
    )
    selected_uncertainty_id: Mapped[int | None] = mapped_column(
        ForeignKey("reference_standard_certificate_uncertainties.id"), index=True
    )
    usage_role: Mapped[str] = mapped_column(String(40), default="primary")
    measurement_section: Mapped[str | None] = mapped_column(String(80))
    selection_status: Mapped[str | None] = mapped_column(String(40))
    selection_notes: Mapped[str | None] = mapped_column(Text)
    validation_snapshot: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)

    field_sheet: Mapped["FieldSheet"] = relationship(back_populates="reference_standard_links")
    reference_standard: Mapped["ReferenceStandard"] = relationship(back_populates="field_sheet_links")
    reference_standard_certificate: Mapped["ReferenceStandardCertificate | None"] = relationship()
    selected_uncertainty: Mapped["ReferenceStandardCertificateUncertainty | None"] = relationship()
