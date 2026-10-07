from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.technical_report_installation import InstallationCapturePatch


TechnicalReportType = Literal[
    "installation",
    "verification",
    "repair",
    "maintenance",
    "sale",
]

TechnicalReportStatus = Literal[
    "draft",
    "in_progress",
    "ready_for_signatures",
    "completed",
    "cancelled",
]

TechnicalReportEvidenceType = Literal[
    "before",
    "during",
    "incident",
    "after",
]


class TechnicalReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # El modelo ya permite otros tipos, pero en esta primera fase el servicio
    # sólo habilitará installation.
    report_type: TechnicalReportType


class TechnicalReportCaptureUpdate(BaseModel):
    """PATCH del reporte: sólo `capture_values`. Cualquier otro campo
    (folio, report_type, revisión, firma, PDF, responsable...) se rechaza."""

    model_config = ConfigDict(extra="forbid")

    capture_values: InstallationCapturePatch


class TechnicalReportEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    technical_report_id: int
    evidence_type: TechnicalReportEvidenceType
    storage_path: str
    mime_type: str
    sha256: str
    size_bytes: int
    position: int
    caption: str | None
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime


class TechnicalReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lab_equipment_id: int
    report_type: TechnicalReportType
    folio: str
    status: TechnicalReportStatus

    capture_values: dict
    document_snapshot: dict | None
    report_schema_version: int

    performed_by_user_id: int | None
    performed_by_name_snapshot: str | None
    performed_at: datetime | None

    client_conformity_text_snapshot: str | None
    signature_session_id: int | None

    revision_number: int
    is_current: bool
    supersedes_report_id: int | None

    pdf_renderer_version: int | None
    final_pdf_path: str | None
    final_pdf_sha256: str | None
    final_pdf_generated_at: datetime | None

    completed_at: datetime | None

    created_at: datetime
    updated_at: datetime

    evidence: list[TechnicalReportEvidenceRead] = Field(default_factory=list)
