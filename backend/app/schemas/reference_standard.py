from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ReferenceStandardOwnerCompany = Literal["MYC", "Capimet", "Otro"]
ReferenceStandardStatus = Literal["active", "expired", "out_of_service", "inactive"]
ReferenceStandardUsageRole = Literal["primary", "secondary", "auxiliary", "environmental", "other"]


class ReferenceStandardUncertaintyBase(BaseModel):
    range_min: float | None = None
    range_max: float | None = None
    unit: str | None = Field(default=None, max_length=40)
    uncertainty_value: float = Field(gt=0)
    coverage_factor_k: float | None = Field(default=None, gt=0)
    distribution: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class ReferenceStandardUncertaintyCreate(ReferenceStandardUncertaintyBase):
    pass


class ReferenceStandardUncertaintyUpdate(BaseModel):
    range_min: float | None = None
    range_max: float | None = None
    unit: str | None = Field(default=None, max_length=40)
    uncertainty_value: float | None = Field(default=None, gt=0)
    coverage_factor_k: float | None = Field(default=None, gt=0)
    distribution: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    is_active: bool | None = None


class ReferenceStandardUncertaintyRead(ReferenceStandardUncertaintyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_standard_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ReferenceStandardBase(BaseModel):
    internal_code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    owner_company: ReferenceStandardOwnerCompany = "MYC"
    magnitude: str = Field(min_length=1, max_length=80)
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    identification: str | None = Field(default=None, max_length=120)
    unit: str | None = Field(default=None, max_length=40)
    range_min: float | None = None
    range_max: float | None = None
    resolution: float | None = Field(default=None, ge=0)
    coverage_factor_k: float | None = Field(default=None, gt=0)
    provider: str | None = Field(default=None, max_length=180)
    calibration_laboratory: str | None = Field(default=None, max_length=180)
    certificate_number: str | None = Field(default=None, max_length=120)
    certificate_file_path: str | None = Field(default=None, max_length=255)
    calibrated_on: date | None = None
    next_calibration_on: date | None = None
    status: ReferenceStandardStatus = "active"
    notes: str | None = None


class ReferenceStandardCreate(ReferenceStandardBase):
    uncertainties: list[ReferenceStandardUncertaintyCreate] = Field(default_factory=list)


class ReferenceStandardUpdate(BaseModel):
    internal_code: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    owner_company: ReferenceStandardOwnerCompany | None = None
    magnitude: str | None = Field(default=None, min_length=1, max_length=80)
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    identification: str | None = Field(default=None, max_length=120)
    unit: str | None = Field(default=None, max_length=40)
    range_min: float | None = None
    range_max: float | None = None
    resolution: float | None = Field(default=None, ge=0)
    coverage_factor_k: float | None = Field(default=None, gt=0)
    provider: str | None = Field(default=None, max_length=180)
    calibration_laboratory: str | None = Field(default=None, max_length=180)
    certificate_number: str | None = Field(default=None, max_length=120)
    certificate_file_path: str | None = Field(default=None, max_length=255)
    calibrated_on: date | None = None
    next_calibration_on: date | None = None
    status: ReferenceStandardStatus | None = None
    notes: str | None = None


class ReferenceStandardRead(ReferenceStandardBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    effective_status: str
    is_overdue: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    current_certificate_id: int | None = None
    current_certificate_number: str | None = None
    current_certificate_expiration_date: date | None = None
    current_certificate_status: str | None = None
    uncertainties: list[ReferenceStandardUncertaintyRead] = Field(default_factory=list)


class FieldSheetReferenceStandardBase(BaseModel):
    reference_standard_id: int
    usage_role: ReferenceStandardUsageRole = "primary"
    measurement_section: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class FieldSheetReferenceStandardCreate(FieldSheetReferenceStandardBase):
    pass


class FieldSheetReferenceStandardRead(FieldSheetReferenceStandardBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_standard_certificate_id: int | None = None
    selected_uncertainty_id: int | None = None
    selection_status: str | None = None
    selection_notes: str | None = None
    validation_snapshot: dict | None = None
    created_at: datetime
    updated_at: datetime
    reference_standard: ReferenceStandardRead
