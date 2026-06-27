from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PatternSelectionRequest(BaseModel):
    technical_profile_id: int | None = None
    magnitude: str = Field(min_length=1, max_length=80)
    equipment_type: str | None = Field(default=None, max_length=120)
    calibration_scope: str | None = Field(default=None, max_length=40)
    ibc_range_min: float | None = None
    ibc_range_max: float | None = None
    measured_range_min: float | None = None
    measured_range_max: float | None = None
    unit: str | None = Field(default=None, max_length=40)
    service_date: date | None = None
    allowed_pattern_ids: list[int] | None = None
    selected_pattern_ids: list[int] | None = None


class PatternCandidate(BaseModel):
    pattern_id: int
    pattern_name: str
    pattern_code: str
    magnitude: str
    range_min: float | None = None
    range_max: float | None = None
    unit: str | None = None
    status: str
    current_certificate_id: int | None = None
    current_certificate_number: str | None = None
    current_certificate_expiration_date: date | None = None
    applicable_uncertainty: float | None = None
    uncertainty_unit: str | None = None
    k_factor: float | None = None
    score: float
    validation_status: str
    validation_messages: list[str] = Field(default_factory=list)


class PatternSelectionResult(BaseModel):
    candidates: list[PatternCandidate] = Field(default_factory=list)
    selected_recommendations: list[PatternCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    explanation: str
