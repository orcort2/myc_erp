from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


EngineSeverity = Literal["VALIDO", "ADVERTENCIA", "ERROR"]


class EngineMessage(BaseModel):
    severity: EngineSeverity
    code: str
    message: str


class OperationalFlowResult(BaseModel):
    current_stage: str
    next_stage: str | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    messages: list[EngineMessage] = Field(default_factory=list)


class DocumentSelectionResult(BaseModel):
    field_sheet_template: str
    certificate_template: str
    label_template: str
    criteria: dict
    messages: list[EngineMessage] = Field(default_factory=list)


class StandardsValidationResult(BaseModel):
    status: EngineSeverity
    messages: list[EngineMessage] = Field(default_factory=list)
    blocking_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FolioSuggestionRequest(BaseModel):
    certificate_type: Literal["acreditado", "trazable", "verification"] = "trazable"
    issued_on: date | None = None
    sequence: int | None = Field(default=None, ge=1)
    manual_folio: str | None = Field(default=None, min_length=1, max_length=40)
    reason: str | None = Field(default=None, max_length=255)


class FolioSuggestionResult(BaseModel):
    suggested_folio: str
    reserved_folio: str | None = None
    definitive_folio: str | None = None
    mode: Literal["automatic", "manual"]
    issued_on: date
    messages: list[EngineMessage] = Field(default_factory=list)


class CertificatePreparationResult(BaseModel):
    certificate_id: int
    folio: str
    status: str
    created: bool
    messages: list[EngineMessage] = Field(default_factory=list)


class TechnicalCaptureResult(BaseModel):
    field_sheet_id: int
    procedure_confirmed: bool
    template_confirmed: bool
    standards_confirmed: bool
    folio_confirmed: bool
    ready_for_calculation: bool
    messages: list[EngineMessage] = Field(default_factory=list)


class CalculationPointInput(BaseModel):
    reference_value: float
    indications: list[float] = Field(min_length=1)
    resolution: float = Field(gt=0)
    pattern_uncertainty: float | None = Field(default=None, gt=0)
    tolerance: float | None = Field(default=None, gt=0)
    k: float = Field(default=2.0, gt=0)


class CalculationRequest(BaseModel):
    profile_key: str = Field(min_length=1, max_length=80)
    points: list[CalculationPointInput] = Field(min_length=1)


class CalculationPointResult(BaseModel):
    reference_value: float
    average: float
    error: float
    repeatability_uncertainty: float
    resolution_uncertainty: float
    combined_uncertainty: float
    expanded_uncertainty: float
    tolerance: float | None = None
    accepted: bool | None = None


class CalculationResult(BaseModel):
    profile_key: str
    final_result: Literal["accepted", "rejected", "informative"]
    points: list[CalculationPointResult]
    certificate_tables: list[dict]
    messages: list[EngineMessage] = Field(default_factory=list)


class LabelPreparationResult(BaseModel):
    folio: str
    client_name: str | None = None
    equipment_name: str
    calibration_date: date | None = None
    next_calibration_date: date | None = None
    certificate_type: str
    status: str
    messages: list[EngineMessage] = Field(default_factory=list)
