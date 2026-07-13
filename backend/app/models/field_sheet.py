from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class FieldSheet(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "field_sheets"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), index=True)

    work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_work_orders.id"),
        index=True,
    )

    calibration_procedure_id: Mapped[int | None] = mapped_column(
        ForeignKey("calibration_procedures.id"),
        index=True,
    )

    status: Mapped[str] = mapped_column(String(60), default="draft", index=True)
    template_key: Mapped[str] = mapped_column(String(40), default="general", index=True)

    # Compatibilidad / dato congelado para impresión histórica
    work_order_number: Mapped[int | None] = mapped_column(Integer, index=True)

    calibration_place: Mapped[str | None] = mapped_column(String(180))
    minimum_division: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(180))
    attention: Mapped[str | None] = mapped_column(String(180))
    company: Mapped[str | None] = mapped_column(String(180))
    address: Mapped[str | None] = mapped_column(Text)
    reception_date: Mapped[date | None] = mapped_column(Date)
    calibration_date: Mapped[date | None] = mapped_column(Date)
    next_calibration_date: Mapped[date | None] = mapped_column(Date)
    environment_humidity_start: Mapped[str | None] = mapped_column(String(40))
    environment_humidity_end: Mapped[str | None] = mapped_column(String(40))
    environment_temperature_start: Mapped[str | None] = mapped_column(String(40))
    environment_temperature_end: Mapped[str | None] = mapped_column(String(40))
    equipment_general_condition: Mapped[bool | None] = mapped_column(Boolean)
    consider_equipment_deviations: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
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
    returned_to_technician_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_to_technician_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    returned_to_technician_reason: Mapped[str | None] = mapped_column(Text)
    certificate_client_mode: Mapped[str] = mapped_column(String(30), default="billing", nullable=False)
    certificate_client_company: Mapped[str | None] = mapped_column(String(180))
    certificate_client_attention: Mapped[str | None] = mapped_column(String(180))
    certificate_client_address: Mapped[str | None] = mapped_column(Text)
    apply_certificate_client_to_order: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    template_definition_json: Mapped[dict | None] = mapped_column(JSON)
    template_definition_version: Mapped[int | None] = mapped_column(Integer)
    institutional_snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    # Valores editables propios de la hoja que no deben modificar los maestros
    # de cliente/equipo (incluye overrides y campos declarativos por plantilla).
    capture_values: Mapped[dict | None] = mapped_column(JSON)

    equipment: Mapped["Equipment"] = relationship(back_populates="field_sheets")

    work_order: Mapped["ServiceWorkOrder | None"] = relationship()

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

    signatures: Mapped[list["FieldSheetSignature"]] = relationship(
        back_populates="field_sheet",
        cascade="all, delete-orphan",
        order_by="FieldSheetSignature.position.asc()",
    )

    uncertainty_calculations: Mapped[list["UncertaintyCalculation"]] = relationship(
        back_populates="field_sheet",
        cascade="all, delete-orphan",
        order_by="UncertaintyCalculation.created_at.desc()",
    )

    @property
    def reference_standards(self) -> list["FieldSheetReferenceStandard"]:
        return self.reference_standard_links

    @property
    def reserved_certificate_folio(self) -> str | None:
        for certificate in self.certificates:
            if certificate.is_active:
                return certificate.expected_folio or certificate.folio

        equipment = self.equipment
        if equipment is None:
            return None

        for certificate in equipment.certificates:
            if certificate.is_active:
                return certificate.expected_folio or certificate.folio

        return None

    @property
    def template_definition(self) -> dict | None:
        return self.template_definition_json

    @property
    def institutional_snapshot(self) -> dict | None:
        return self.institutional_snapshot_json


class FieldSheetResult(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "field_sheet_results"
    __table_args__ = (
        UniqueConstraint(
            "field_sheet_id",
            "section_key",
            "row_number",
            name="uq_field_sheet_results_row",
        ),
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
    row_data: Mapped[dict | None] = mapped_column(JSON)

    field_sheet: Mapped["FieldSheet"] = relationship(back_populates="results_rows")


class FieldSheetSignature(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "field_sheet_signatures"
    __table_args__ = (
        UniqueConstraint(
            "field_sheet_id",
            "role",
            name="uq_field_sheet_signature_role",
        ),
    )

    field_sheet_id: Mapped[int] = mapped_column(ForeignKey("field_sheets.id"), index=True)
    role: Mapped[str] = mapped_column(String(80), index=True)
    display_label: Mapped[str] = mapped_column(String(180))
    name: Mapped[str | None] = mapped_column(String(180))
    signature_data: Mapped[str | None] = mapped_column(Text)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    field_sheet: Mapped["FieldSheet"] = relationship(back_populates="signatures")
    user: Mapped["User | None"] = relationship()
