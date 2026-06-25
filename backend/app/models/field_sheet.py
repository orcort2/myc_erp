from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class FieldSheet(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "field_sheets"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), index=True)
    calibration_procedure_id: Mapped[int | None] = mapped_column(
        ForeignKey("calibration_procedures.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(60), default="draft", index=True)
    template_key: Mapped[str] = mapped_column(String(40), default="general", index=True)
    work_order_number: Mapped[int | None] = mapped_column(Integer, index=True)
    calibration_place: Mapped[str | None] = mapped_column(String(180))
    reception_date: Mapped[date | None] = mapped_column(Date)
    calibration_date: Mapped[date | None] = mapped_column(Date)
    next_calibration_date: Mapped[date | None] = mapped_column(Date)
    environment_humidity_start: Mapped[str | None] = mapped_column(String(40))
    environment_humidity_end: Mapped[str | None] = mapped_column(String(40))
    environment_temperature_start: Mapped[str | None] = mapped_column(String(40))
    environment_temperature_end: Mapped[str | None] = mapped_column(String(40))
    equipment_general_condition: Mapped[bool | None] = mapped_column(Boolean)
    consider_equipment_deviations: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    units: Mapped[str | None] = mapped_column(String(80))
    calibrated_by: Mapped[str | None] = mapped_column(String(180))
    reviewed_by: Mapped[str | None] = mapped_column(String(180))
    report_made_by: Mapped[str | None] = mapped_column(String(180))
    purchase_order_or_quotation: Mapped[str | None] = mapped_column(String(180))
    initial_condition: Mapped[str | None] = mapped_column(Text)
    final_condition: Mapped[str | None] = mapped_column(Text)
    pattern_used: Mapped[str | None] = mapped_column(String(180))
    results: Mapped[str | None] = mapped_column(Text)
    observations: Mapped[str | None] = mapped_column(Text)
    evidence_notes: Mapped[str | None] = mapped_column(Text)
    method: Mapped[str | None] = mapped_column(String(180))
    environmental_conditions: Mapped[str | None] = mapped_column(Text)
    technician_notes: Mapped[str | None] = mapped_column(Text)

    equipment: Mapped["Equipment"] = relationship(back_populates="field_sheets")
    calibration_procedure: Mapped["CalibrationProcedure | None"] = relationship(
        back_populates="field_sheets"
    )
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="field_sheet")
    reference_standard_links: Mapped[list["FieldSheetReferenceStandard"]] = relationship(
        back_populates="field_sheet",
        cascade="all, delete-orphan",
        order_by="FieldSheetReferenceStandard.id.asc()",
    )
    results_rows: Mapped[list["FieldSheetResult"]] = relationship(
        back_populates="field_sheet",
        cascade="all, delete-orphan",
        order_by="FieldSheetResult.section_key, FieldSheetResult.row_number",
    )

    @property
    def reference_standards(self) -> list["FieldSheetReferenceStandard"]:
        return self.reference_standard_links


class FieldSheetResult(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "field_sheet_results"
    __table_args__ = (
        UniqueConstraint("field_sheet_id", "section_key", "row_number", name="uq_field_sheet_results_row"),
    )

    field_sheet_id: Mapped[int] = mapped_column(ForeignKey("field_sheets.id"), index=True)
    section_key: Mapped[str] = mapped_column(String(80), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    pattern_value: Mapped[str | None] = mapped_column(String(180))
    ibc_value_1: Mapped[str | None] = mapped_column(String(180))
    ibc_value_2: Mapped[str | None] = mapped_column(String(180))
    ibc_value_3: Mapped[str | None] = mapped_column(String(180))
    unit: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)

    field_sheet: Mapped["FieldSheet"] = relationship(back_populates="results_rows")
