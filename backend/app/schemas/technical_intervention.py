from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.technical_report import TechnicalReportStatus, TechnicalReportType

TechnicalInterventionStatus = str  # open | completed | cancelled


class TechnicalInterventionCreate(BaseModel):
    """Alta explícita de una intervención. Crea la intervención y su primera
    revisión (R1, borrador); nunca crea una R2 ni toca reportes existentes."""

    model_config = ConfigDict(extra="forbid")

    report_type: TechnicalReportType


class TechnicalInterventionCancel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=500)


class TechnicalReportRevisionRead(BaseModel):
    """Metadatos documentales de UNA revisión (sin captura ni evidencias)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    intervention_id: int
    revision_number: int
    is_current: bool
    status: TechnicalReportStatus
    report_type: TechnicalReportType
    folio: str
    supersedes_report_id: int | None
    performed_by_user_id: int | None
    performed_by_name_snapshot: str | None
    performed_at: datetime | None
    completed_at: datetime | None
    pdf_renderer_version: int | None
    final_pdf_generated_at: datetime | None
    final_pdf_sha256: str | None
    pdf_available: bool
    # Entrega física cuyo acuse respalda el PDF de esta revisión (si ya existe).
    delivery_id: int | None
    created_at: datetime
    updated_at: datetime


class TechnicalInterventionRead(BaseModel):
    id: int
    lab_equipment_id: int
    work_order_id: int
    intervention_type: TechnicalReportType
    folio: str
    status: str
    # Obligatoria para el cierre de la OT (open/completed); las canceladas no.
    mandatory: bool
    created_at: datetime
    created_by_user_id: int | None
    revisions_count: int
    current_revision: TechnicalReportRevisionRead | None


class TechnicalInterventionDeliveryRead(BaseModel):
    delivery_id: int
    exhibition_number: int
    delivery_status: str
    delivered_at: datetime
    technical_report_id: int | None


class TechnicalInterventionDetailRead(TechnicalInterventionRead):
    deliveries: list[TechnicalInterventionDeliveryRead]
