from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ReferenceStandardCertificateStatus = Literal[
    "draft",
    "active",
    "expired",
    "obsolete",
    "rejected",
    "suspended",
]


class ReferenceStandardCertificateUncertaintyBase(BaseModel):
    magnitude: str | None = Field(default=None, max_length=80)
    measurement_type: str | None = Field(default=None, max_length=120)
    range_min: float | None = None
    range_max: float | None = None
    unit: str | None = Field(default=None, max_length=40)
    uncertainty_value: float = Field(gt=0)
    uncertainty_unit: str | None = Field(default=None, max_length=40)
    k_factor: float | None = Field(default=2, gt=0)
    confidence_level: str | None = Field(default=None, max_length=80)
    distribution: str | None = Field(default=None, max_length=80)
    formula_reference: str | None = Field(default=None, max_length=180)
    notes: str | None = None


class ReferenceStandardCertificateUncertaintyCreate(ReferenceStandardCertificateUncertaintyBase):
    pass


class ReferenceStandardCertificateUncertaintyUpdate(BaseModel):
    magnitude: str | None = Field(default=None, max_length=80)
    measurement_type: str | None = Field(default=None, max_length=120)
    range_min: float | None = None
    range_max: float | None = None
    unit: str | None = Field(default=None, max_length=40)
    uncertainty_value: float | None = Field(default=None, gt=0)
    uncertainty_unit: str | None = Field(default=None, max_length=40)
    k_factor: float | None = Field(default=None, gt=0)
    confidence_level: str | None = Field(default=None, max_length=80)
    distribution: str | None = Field(default=None, max_length=80)
    formula_reference: str | None = Field(default=None, max_length=180)
    notes: str | None = None
    is_active: bool | None = None


class ReferenceStandardCertificateUncertaintyRead(ReferenceStandardCertificateUncertaintyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    certificate_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ReferenceStandardCertificateBase(BaseModel):
    controlled_document_id: int | None = None
    controlled_document_version_id: int | None = None
    certificate_number: str = Field(min_length=1, max_length=120)
    issuing_laboratory: str | None = Field(default=None, max_length=180)
    accreditation_body: str | None = Field(default=None, max_length=180)
    accreditation_number: str | None = Field(default=None, max_length=120)
    calibration_date: date | None = None
    expiration_date: date | None = None
    received_date: date | None = None
    status: ReferenceStandardCertificateStatus = "draft"
    traceability_statement: str | None = None
    environmental_conditions: str | None = None
    notes: str | None = None


class ReferenceStandardCertificateCreate(ReferenceStandardCertificateBase):
    uncertainties: list[ReferenceStandardCertificateUncertaintyCreate] = Field(default_factory=list)


class ReferenceStandardCertificateUpdate(BaseModel):
    controlled_document_id: int | None = None
    controlled_document_version_id: int | None = None
    certificate_number: str | None = Field(default=None, min_length=1, max_length=120)
    issuing_laboratory: str | None = Field(default=None, max_length=180)
    accreditation_body: str | None = Field(default=None, max_length=180)
    accreditation_number: str | None = Field(default=None, max_length=120)
    calibration_date: date | None = None
    expiration_date: date | None = None
    received_date: date | None = None
    status: ReferenceStandardCertificateStatus | None = None
    traceability_statement: str | None = None
    environmental_conditions: str | None = None
    notes: str | None = None


class ReferenceStandardCertificateRead(ReferenceStandardCertificateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_standard_id: int
    is_current: bool
    effective_status: str
    created_by_id: int | None = None
    approved_by_id: int | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    uncertainties: list[ReferenceStandardCertificateUncertaintyRead] = Field(default_factory=list)
