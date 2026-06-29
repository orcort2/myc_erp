from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CalibrationProcedureIssuerCompany = Literal["MYC", "Capimet", "Otro"]
CalibrationProcedureCertificateType = Literal[
    "acreditado",
    "trazable",
    "verificacion",
    "inspeccion",
    "otro",
]
CalibrationProcedureStatus = Literal["active", "inactive", "draft", "obsolete"]


class CalibrationProcedureBase(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    magnitude: str = Field(min_length=1, max_length=80)
    profile_key: str | None = Field(default=None, max_length=80)
    version: str = Field(min_length=1, max_length=40)
    issuer_company: CalibrationProcedureIssuerCompany = "MYC"
    certificate_type: CalibrationProcedureCertificateType = "trazable"
    uncertainty_model_id: int | None = None
    uncertainty_model_version_id: int | None = None
    required_readings: int | None = Field(default=None, ge=1)
    decision_rule: str | None = None
    acceptance_criteria: str | None = None
    notes: str | None = None
    status: CalibrationProcedureStatus = "draft"


class CalibrationProcedureCreate(CalibrationProcedureBase):
    pass


class CalibrationProcedureUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    magnitude: str | None = Field(default=None, min_length=1, max_length=80)
    profile_key: str | None = Field(default=None, max_length=80)
    version: str | None = Field(default=None, min_length=1, max_length=40)
    issuer_company: CalibrationProcedureIssuerCompany | None = None
    certificate_type: CalibrationProcedureCertificateType | None = None
    uncertainty_model_id: int | None = None
    uncertainty_model_version_id: int | None = None
    required_readings: int | None = Field(default=None, ge=1)
    decision_rule: str | None = None
    acceptance_criteria: str | None = None
    notes: str | None = None
    status: CalibrationProcedureStatus | None = None


class CalibrationProcedureRead(CalibrationProcedureBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
