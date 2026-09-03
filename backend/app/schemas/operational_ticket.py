from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ReopenTicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_order_id: int
    # Trazabilidad opcional: qué equipo/hoja motivó la solicitud cuando el
    # ticket se origina desde el contexto de una FieldSheet específica (la
    # OT ya cerrada sigue reabriéndose completa -- ver approve_reopen_ticket
    # -- esto sólo identifica la hoja para auditoría y para retirar su
    # revisión vigente en cuanto se aprueba).
    equipment_id: int | None = Field(default=None, gt=0)
    reason: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=4000)
    requested_signature_policy: str = Field(pattern="^(preserve|invalidate)$")


class TicketReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signature_policy: str = Field(pattern="^(preserve|invalidate)$")
    comment: str | None = Field(default=None, max_length=2000)


class TicketReject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment: str = Field(min_length=3, max_length=2000)


class FolioTicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_order_id: int
    equipment_id: int
    type: str = Field(pattern="^(manual_myc_folio|linked_folio)$")
    requested_folio: str | None = Field(default=None, max_length=120)
    reason: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=4000)


class PartialCloseTicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_order_id: int
    reason: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=4000)


class FieldSheetTemplateRequestCreate(BaseModel):
    """Fase 1F: sólo el dominio (crear el ticket como 'pending'). La UI y la
    resolución ('encontramos/creamos la plantilla X') quedan para una fase
    posterior; aquí no se implementa ningún flujo de atención."""

    model_config = ConfigDict(extra="forbid")

    work_order_id: int
    equipment_id: int
    reason: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=4000)


class FieldSheetReopenTicketCreate(BaseModel):
    """Desbloqueo/reapertura de UNA FieldSheet/equipo completed mientras la
    OT sigue abierta (in_progress/ready_to_close) -- distinto de
    ReopenTicketCreate, que reabre la OT completa y sólo aplica cuando ya
    está completed/partially_closed. Misma tabla OperationalTicket, mismo
    patrón que FieldSheetTemplateRequestCreate."""

    model_config = ConfigDict(extra="forbid")

    work_order_id: int
    equipment_id: int
    reason: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=4000)


class ReceptionDateChangeTicketCreate(BaseModel):
    """Solicitud informativa: registra la fecha propuesta sin aplicarla."""

    model_config = ConfigDict(extra="forbid")

    work_order_id: int
    equipment_id: int | None = Field(default=None, gt=0)
    field_sheet_id: int | None = Field(default=None, gt=0)
    requested_date: date
    reason: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=4000)


class CertificateFolioBlockCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accredited_quantity: int = Field(default=0, ge=0, le=100)
    traceable_quantity: int = Field(default=0, ge=0, le=100)
    reason: str = Field(default="Folios certificados", min_length=3, max_length=180)
    description: str = Field(default="Reserva operativa de folios para OT LAB", min_length=3, max_length=4000)


class TicketResolve(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authorized_folio: str | None = Field(default=None, max_length=120)
    comment: str | None = Field(default=None, max_length=2000)


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    status: str
    work_order_id: int | None
    equipment_id: int | None = None
    equipment_position: int | None = None
    equipment_instrument: str | None = None
    equipment_brand: str | None = None
    equipment_model: str | None = None
    equipment_identification: str | None = None
    equipment_serial_number: str | None = None
    equipment_service_type: str | None = None
    equipment_folio_status: str | None = None
    operator_client_id: int | None = None
    work_order_folio: int | None
    client_name: str | None
    requested_by_user_id: int
    requested_by_name: str
    reviewed_by_user_id: int | None
    reason: str
    description: str
    requested_signature_policy: str | None
    final_signature_policy: str | None
    linked_company_id: int | None = None
    conversation_id: int | None = None
    automatic_folio: str | None = None
    requested_folio: str | None = None
    authorized_folio: str | None = None
    accredited_quantity: int | None = None
    traceable_quantity: int | None = None
    resolution_snapshot: dict | None = None
    decision_comment: str | None
    created_at: datetime
    reviewed_at: datetime | None
    resolved_at: datetime | None


class LabRevisionRead(BaseModel):
    id: int | None = None
    revision_number: int
    status: str
    reopen_ticket_id: int | None
    signature_session_id: int | None
    signature_preserved: bool
    final_pdf_sha256: str | None
    final_pdf_generated_at: datetime | None
    created_at: datetime
