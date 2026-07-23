from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.service_scope import AccreditationScope


DocumentType = Literal[
    "manual",
    "procedure",
    "format",
    "record",
    "policy",
    "uncertainty_calculation",
    "certificate_master",
    "field_sheet_template",
    "work_order_template",
    "quotation_template",
    "external_standard",
    "other",
]
DocumentStatus = Literal["draft", "active", "obsolete", "suspended"]
VersionStatus = Literal["draft", "active", "obsolete"]
InterpretationType = Literal[
    "procedure_interpretation",
    "uncertainty_model_source",
    "certificate_template_source",
    "field_sheet_template_source",
    "work_order_template_source",
    "general",
]
InterpretationStatus = Literal["draft", "in_review", "approved", "obsolete"]
TechnicalProfileStatus = Literal["draft", "active", "obsolete", "suspended"]


class ControlledDocumentBase(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=255)
    document_type: DocumentType = "other"
    quality_level: str | None = Field(default=None, max_length=80)
    current_revision: str | None = Field(default=None, max_length=80)
    issue_date: date | None = None
    last_review_date: date | None = None
    effective_date: date | None = None
    retention_time: str | None = Field(default=None, max_length=120)
    digital_location: str | None = Field(default=None, max_length=255)
    status: DocumentStatus = "draft"
    description: str | None = None


class ControlledDocumentCreate(ControlledDocumentBase):
    pass


class ControlledDocumentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    document_type: DocumentType | None = None
    quality_level: str | None = Field(default=None, max_length=80)
    current_revision: str | None = Field(default=None, max_length=80)
    issue_date: date | None = None
    last_review_date: date | None = None
    effective_date: date | None = None
    retention_time: str | None = Field(default=None, max_length=120)
    digital_location: str | None = Field(default=None, max_length=255)
    status: DocumentStatus | None = None
    description: str | None = None


class ControlledDocumentArchive(BaseModel):
    status: Literal["obsolete", "suspended"] = "obsolete"
    comment: str | None = None


class ControlledDocumentVersionBase(BaseModel):
    revision: str = Field(min_length=1, max_length=80)
    file_path: str | None = Field(default=None, max_length=255)
    original_filename: str | None = Field(default=None, max_length=255)
    mime_type: str | None = Field(default=None, max_length=120)
    checksum: str | None = Field(default=None, max_length=128)
    change_summary: str | None = None
    reviewed_by_id: int | None = None
    effective_date: date | None = None
    expires_on: date | None = None
    file_size_bytes: int | None = None


class ControlledDocumentVersionCreate(ControlledDocumentVersionBase):
    status: VersionStatus = "draft"


class ControlledDocumentVersionRead(ControlledDocumentVersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    uploaded_by_id: int | None = None
    approved_by_id: int | None = None
    status: VersionStatus
    uploaded_at: datetime
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ControlledDocumentRead(ControlledDocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by_id: int | None = None
    created_at: datetime
    updated_at: datetime
    versions: list[ControlledDocumentVersionRead] = Field(default_factory=list)


class DocumentInterpretationBase(BaseModel):
    document_id: int
    document_version_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    interpretation_type: InterpretationType = "general"
    magnitude: str | None = Field(default=None, max_length=80)
    equipment_type: str | None = Field(default=None, max_length=120)
    service_type: str | None = Field(default=None, max_length=80)
    calibration_scope: AccreditationScope | None = None
    data: dict | None = None
    status: InterpretationStatus = "draft"
    version: int = Field(default=1, ge=1)


class DocumentInterpretationCreate(DocumentInterpretationBase):
    pass


class DocumentInterpretationUpdate(BaseModel):
    document_version_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    interpretation_type: InterpretationType | None = None
    magnitude: str | None = Field(default=None, max_length=80)
    equipment_type: str | None = Field(default=None, max_length=120)
    service_type: str | None = Field(default=None, max_length=80)
    calibration_scope: AccreditationScope | None = None
    data: dict | None = None
    status: InterpretationStatus | None = None


class DocumentInterpretationRead(DocumentInterpretationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by_id: int | None = None
    approved_by_id: int | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TechnicalProfileAllowedPatternBase(BaseModel):
    pattern_id: int | None = None
    pattern_code: str | None = Field(default=None, max_length=120)
    min_range: float | None = None
    max_range: float | None = None
    unit: str | None = Field(default=None, max_length=40)
    priority: int | None = None
    is_preferred: bool = False
    notes: str | None = None


class TechnicalProfileAllowedPatternCreate(TechnicalProfileAllowedPatternBase):
    pass


class TechnicalProfileAllowedPatternRead(TechnicalProfileAllowedPatternBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    technical_profile_id: int
    created_at: datetime


class TechnicalProfileBase(BaseModel):
    code: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=255)
    magnitude: str = Field(min_length=1, max_length=80)
    equipment_type: str = Field(min_length=1, max_length=120)
    service_type: str = Field(default="calibration", min_length=1, max_length=80)
    calibration_scope: AccreditationScope
    procedure_document_id: int | None = None
    procedure_interpretation_id: int | None = None
    field_sheet_template_document_id: int | None = None
    certificate_template_document_id: int | None = None
    uncertainty_source_document_id: int | None = None
    status: TechnicalProfileStatus = "draft"
    version: int = Field(default=1, ge=1)
    rules: dict | None = None
    notes: str | None = None


class TechnicalProfileCreate(TechnicalProfileBase):
    allowed_patterns: list[TechnicalProfileAllowedPatternCreate] = Field(default_factory=list)


class TechnicalProfileUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=120)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    magnitude: str | None = Field(default=None, min_length=1, max_length=80)
    equipment_type: str | None = Field(default=None, min_length=1, max_length=120)
    service_type: str | None = Field(default=None, min_length=1, max_length=80)
    calibration_scope: AccreditationScope | None = None
    procedure_document_id: int | None = None
    procedure_interpretation_id: int | None = None
    field_sheet_template_document_id: int | None = None
    certificate_template_document_id: int | None = None
    uncertainty_source_document_id: int | None = None
    status: TechnicalProfileStatus | None = None
    rules: dict | None = None
    notes: str | None = None
    allowed_patterns: list[TechnicalProfileAllowedPatternCreate] | None = None


class TechnicalProfileRead(TechnicalProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by_id: int | None = None
    approved_by_id: int | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    allowed_patterns: list[TechnicalProfileAllowedPatternRead] = Field(default_factory=list)
