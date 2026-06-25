from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class CalibrationProcedure(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "calibration_procedures"

    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    magnitude: Mapped[str] = mapped_column(String(80), index=True)
    profile_key: Mapped[str | None] = mapped_column(String(80), index=True)
    version: Mapped[str] = mapped_column(String(40), index=True, default="1.0")
    issuer_company: Mapped[str] = mapped_column(String(40), index=True, default="MYC")
    certificate_type: Mapped[str] = mapped_column(String(40), index=True, default="trazable")
    required_readings: Mapped[int | None] = mapped_column()
    decision_rule: Mapped[str | None] = mapped_column(Text)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), index=True, default="draft")

    field_sheets: Mapped[list["FieldSheet"]] = relationship(back_populates="calibration_procedure")
