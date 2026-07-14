from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CertificateStatus = Literal[
    "draft",
    "expected",
    "field_sheet_ready",
    "capture_pending",
    "capture_in_progress",
    "ready_for_quality",
    "generated",
    "quality_review",
    "match_validated",
    "quality_rejected",
    "correction_requested",
    "returned_to_technician",
    "quality_approved",
    "approved",
    "pdf_pending",
    "pdf_uploaded",
    "authenticated",
    "released_to_client",
    "released",
    "cancelled",
    "suspended",
]

CertificateType = Literal["acreditado", "trazable", "vinculado"]
CertificateMatchStatus = Literal["pending", "matched", "warning", "mismatch", "manual_accepted"]


class CertificateBase(BaseModel):
    service_order_id: int
    equipment_id: int
    field_sheet_id: int | None = None
    certificate_type: CertificateType = "trazable"
    expected_folio: str | None = Field(default=None, max_length=40)
    issued_on: date | None = None
    title: str | None = Field(default=None, max_length=180)
    notes: str | None = None


class CertificateCreate(CertificateBase):
    pass


class CertificateUpdate(BaseModel):
    expected_folio: str | None = Field(default=None, max_length=40)
    issued_on: date | None = None
    title: str | None = Field(default=None, max_length=180)
    notes: str | None = None


class CertificateStatusChange(BaseModel):
    comment: str | None = None
    reason: str | None = None


class CertificatePdfUploadRead(BaseModel):
    certificate_id: int
    filename: str
    match_status: CertificateMatchStatus
    match_details: dict


class CertificateBulkUploadRead(BaseModel):
    service_order_id: int
    expected: int
    uploaded: int
    matched: int
    warnings: int
    mismatches: int
    missing: int
    results: list[CertificatePdfUploadRead] = Field(default_factory=list)


class CertificateBatchActionItemRead(BaseModel):
    certificate_id: int
    folio: str | None = None
    status: str
    authenticated_pdf_path: str | None = None
    error: str | None = None


class CertificateBatchActionRead(BaseModel):
    service_order_id: int
    authenticated: int = 0
    released: int = 0
    skipped: int = 0
    errors: int = 0
    results: list[CertificateBatchActionItemRead] = Field(default_factory=list)


class CertificatePdfVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_number: int
    file_path: str
    original_filename: str | None = None
    uploaded_at: datetime
    uploaded_by_id: int | None = None
    source_status: str | None = None
    change_reason: str | None = None
    is_current: bool


class CertificateRead(CertificateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: str
    expected_folio: str | None = None
    status: CertificateStatus
    released_on: date | None = None
    final_pdf_path: str | None = None
    final_pdf_original_filename: str | None = None
    final_pdf_uploaded_at: datetime | None = None
    final_pdf_uploaded_by_id: int | None = None
    capture_started_at: datetime | None = None
    capture_started_by_id: int | None = None
    sent_to_quality_at: datetime | None = None
    sent_to_quality_by_id: int | None = None
    quality_reviewed_at: datetime | None = None
    quality_reviewed_by_id: int | None = None
    quality_rejection_reason: str | None = None
    released_to_client_at: datetime | None = None
    released_to_client_by_id: int | None = None
    authentication_code: str | None = None
    authentication_hash: str | None = None
    authenticated_pdf_path: str | None = None
    authenticated_pdf_generated_at: datetime | None = None
    authenticated_by_id: int | None = None
    verification_url: str | None = None
    external_source: str = "excel"
    match_status: CertificateMatchStatus = "pending"
    match_details: dict | None = None
    client_visible: bool = False
    is_active: bool
    created_at: datetime
    updated_at: datetime
    pdf_versions: list[CertificatePdfVersionRead] = Field(default_factory=list)


class CertificateVerificationRead(BaseModel):
    valid: bool
    authentication_code: str
    folio: str | None = None
    client: str | None = None
    equipment: str | None = None
    serial_number: str | None = None
    status: str | None = None
    authenticated_at: datetime | None = None
    authenticated_by: str = "MYC SYSTEM"
    document_hash: str | None = None
