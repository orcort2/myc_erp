from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.calibration_procedure import CalibrationProcedureRead
from app.schemas.reference_standard import (
    FieldSheetReferenceStandardCreate,
    FieldSheetReferenceStandardRead,
)


FieldSheetStatus = Literal[
    "draft",
    "in_progress",
    "completed",
    "under_review",
    "returned_to_technician",
    "approved",
    "rejected",
    "cancelled",
]

FieldSheetTemplateKey = Literal["general", "electrica"]


class FieldSheetResultBase(BaseModel):
    section_key: str = Field(min_length=1, max_length=80)
    row_number: int = Field(ge=1)
    pattern_value: str | None = Field(default=None, max_length=180)
    ibc_value_1: str | None = Field(default=None, max_length=180)
    ibc_value_2: str | None = Field(default=None, max_length=180)
    ibc_value_3: str | None = Field(default=None, max_length=180)
    unit: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class FieldSheetResultCreate(FieldSheetResultBase):
    pass


class FieldSheetResultUpdate(FieldSheetResultBase):
    id: int | None = None


class FieldSheetResultRead(FieldSheetResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class FieldSheetBase(BaseModel):
    equipment_id: int
    template_key: FieldSheetTemplateKey = "general"
    calibration_procedure_id: int | None = None
    calibration_place: str | None = None
    reception_date: date | None = None
    calibration_date: date | None = None
    next_calibration_date: date | None = None
    environment_humidity_start: str | None = None
    environment_humidity_end: str | None = None
    environment_temperature_start: str | None = None
    environment_temperature_end: str | None = None
    equipment_general_condition: bool | None = None
    consider_equipment_deviations: bool = False
    units: str | None = None
    calibrated_by: str | None = None
    reviewed_by: str | None = None
    report_made_by: str | None = None
    purchase_order_or_quotation: str | None = None
    initial_condition: str | None = None
    final_condition: str | None = None
    pattern_used: str | None = None
    results: str | None = None
    observations: str | None = None
    evidence_notes: str | None = None
    method: str | None = None
    environmental_conditions: str | None = None
    technician_notes: str | None = None
    results_rows: list[FieldSheetResultCreate] = Field(default_factory=list)
    reference_standards: list[FieldSheetReferenceStandardCreate] = Field(default_factory=list)


class FieldSheetCreate(FieldSheetBase):
    pass


class FieldSheetUpdate(BaseModel):
    template_key: FieldSheetTemplateKey | None = None
    calibration_procedure_id: int | None = None
    calibration_place: str | None = None
    reception_date: date | None = None
    calibration_date: date | None = None
    next_calibration_date: date | None = None
    environment_humidity_start: str | None = None
    environment_humidity_end: str | None = None
    environment_temperature_start: str | None = None
    environment_temperature_end: str | None = None
    equipment_general_condition: bool | None = None
    consider_equipment_deviations: bool | None = None
    units: str | None = None
    calibrated_by: str | None = None
    reviewed_by: str | None = None
    report_made_by: str | None = None
    purchase_order_or_quotation: str | None = None
    initial_condition: str | None = None
    final_condition: str | None = None
    pattern_used: str | None = None
    results: str | None = None
    observations: str | None = None
    evidence_notes: str | None = None
    method: str | None = None
    environmental_conditions: str | None = None
    technician_notes: str | None = None
    results_rows: list[FieldSheetResultUpdate] | None = None
    reference_standards: list[FieldSheetReferenceStandardCreate] | None = None


class FieldSheetStatusChange(BaseModel):
    comment: str | None = None


class FieldSheetRead(FieldSheetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_order_number: int | None = None
    calibration_procedure_id: int | None = None
    status: FieldSheetStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime
    returned_to_technician_at: datetime | None = None
    returned_to_technician_by_id: int | None = None
    returned_to_technician_reason: str | None = None
    results_rows: list[FieldSheetResultRead] = Field(default_factory=list)
    calibration_procedure: CalibrationProcedureRead | None = None
    reference_standards: list[FieldSheetReferenceStandardRead] = Field(default_factory=list)
