from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class LabWorkOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reception_date: date
    departure_date: date
    client_name: str = Field(min_length=1, max_length=255)
    address: str = Field(default="", max_length=2000)
    contact_name: str | None = Field(default=None, max_length=180)
    contact_phone: str | None = Field(default=None, max_length=60)
    contact_email: EmailStr | None = None
    postal_code: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=120)
    state_name: str | None = Field(default=None, max_length=120)
    purchase_order: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=4000)
    lab_client_id: int | None = Field(default=None, gt=0)

    @field_validator("departure_date")
    @classmethod
    def departure_not_before_reception(cls, value: date, info):
        reception = info.data.get("reception_date")
        if reception and value < reception:
            raise ValueError("La fecha de salida no puede ser anterior a la recepción")
        return value


class LabWorkOrderGroupCreate(LabWorkOrderCreate):
    quantity: int = Field(ge=1, le=50)


class LabWorkOrderGroupRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operator_client_id: int
    lab_client_id: int | None
    operator_client_name: str
    requested_by_user_id: int
    requested_by_name: str
    quantity: int
    status: str
    handled_by_user_id: int | None
    handled_by_name: str | None
    claimed_at: datetime | None
    decided_at: datetime | None
    decision_reason: str | None
    root_work_order_id: int | None
    conversation_id: int | None
    folios: list[int] = Field(default_factory=list)
    reception_date: date
    departure_date: date
    client_name: str
    address: str
    contact_name: str | None
    contact_phone: str | None
    contact_email: str | None
    postal_code: str | None
    city: str | None
    state_name: str | None
    purchase_order: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class LabWorkOrderGroupDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str | None = Field(default=None, max_length=2000)


class LabWorkOrderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reception_date: date | None = None
    departure_date: date | None = None
    client_name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=2000)
    contact_name: str | None = Field(default=None, max_length=180)
    contact_phone: str | None = Field(default=None, max_length=60)
    contact_email: EmailStr | None = None
    postal_code: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=120)
    state_name: str | None = Field(default=None, max_length=120)
    purchase_order: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=4000)
    lab_client_id: int | None = Field(default=None, gt=0)
    expected_edit_version: int | None = Field(default=None, ge=1)


class LabEquipmentBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument: str = Field(min_length=1, max_length=255)
    brand: str = Field(min_length=1, max_length=160)
    identification: str = Field(min_length=1, max_length=160)
    serial_number: str = Field(min_length=1, max_length=160)
    model: str | None = Field(default=None, max_length=160)
    report_number: str | None = Field(default=None, max_length=160)
    is_good_condition: bool


class LabEquipmentWrite(LabEquipmentBase):
    expected_edit_version: int | None = Field(default=None, ge=1)


class LabEquipmentRead(LabEquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    service_type: str | None = None
    linked_company_id: int | None = None
    linked_company_name_snapshot: str | None = None
    linked_company_prefix_snapshot: str | None = None
    certificate_folio: str | None = None
    automatic_certificate_folio: str | None = None
    folio_status: str = "unassigned"
    folio_ticket_id: int | None = None
    field_sheet_id: int | None = None
    field_sheet_status: str | None = None
    certificate_client_mode: str = "order"
    final_lab_client_id: int | None = None
    final_client_company_snapshot: str | None = None
    final_client_address_snapshot: str | None = None
    final_client_attention_snapshot: str | None = None
    created_at: datetime
    updated_at: datetime


class LabEquipmentCertificateClientWrite(BaseModel):
    """Fase 1A/1B: contrato del cliente documental por equipo. Fase 2 lo
    conecta al alta integrada de equipo (create_configured_equipment) y al
    endpoint dedicado de edición.

    Endurecimiento (Fase 2 hardening): cuando se envía final_lab_client_id,
    los tres campos de snapshot son puramente informativos -- el backend
    SIEMPRE los resuelve desde el LabClient autorizado y descarta lo que
    llegue aquí (ver _set_equipment_certificate_client_core). Por eso dejan
    de ser obligatorios en ese caso: sólo son la autoridad cuando NO hay
    final_lab_client_id (cliente final sin referencia de catálogo)."""

    model_config = ConfigDict(extra="forbid")

    certificate_client_mode: str = Field(pattern="^(order|different)$")
    final_lab_client_id: int | None = Field(default=None, gt=0)
    final_client_company_snapshot: str | None = Field(default=None, max_length=255)
    final_client_address_snapshot: str | None = Field(default=None, max_length=2000)
    final_client_attention_snapshot: str | None = Field(default=None, max_length=180)

    @model_validator(mode="after")
    def validate_mode_invariants(self) -> "LabEquipmentCertificateClientWrite":
        if self.certificate_client_mode == "order":
            if (
                self.final_lab_client_id is not None
                or self.final_client_company_snapshot is not None
                or self.final_client_address_snapshot is not None
                or self.final_client_attention_snapshot is not None
            ):
                raise ValueError(
                    "El modo 'order' no admite cliente final ni snapshots: el documento "
                    "hereda cliente/dirección/atención de la OT"
                )
        elif self.final_lab_client_id is None and not (self.final_client_company_snapshot or "").strip():
            raise ValueError(
                "El modo 'different' requiere final_lab_client_id o, en su ausencia, "
                "el snapshot de empresa"
            )
        return self


class LabEquipmentServiceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_type: str = Field(pattern="^(accredited|traceable|linked)$")
    linked_company_id: int | None = Field(default=None, gt=0)


class LabEquipmentConfiguredCreate(BaseModel):
    """Fase 2E: alta integrada (equipo + cliente documental + servicio/folio)
    como una sola operación. Compone los contratos existentes en vez de
    duplicarlos: cada sección se valida con su propio schema de Fase 1/2."""

    model_config = ConfigDict(extra="forbid")

    equipment: LabEquipmentWrite
    certificate_client: LabEquipmentCertificateClientWrite | None = Field(
        default=None,
        description="Si se omite, el equipo queda en certificate_client_mode='order' (default).",
    )
    service: LabEquipmentServiceWrite


class LabManualFolioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested_folio: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=4000)


class LabLinkedFolioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=4000)


class LabCancellationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=2000)


class LabDirectReopenWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested_signature_policy: str = Field(pattern="^(preserve|invalidate)$")
    reason: str = Field(min_length=3, max_length=2000)


class LabPartialCloseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=4000)


class LabFieldSheetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_key: str = Field(min_length=1, max_length=60)


class LabSignatureWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signer_name: str = Field(min_length=1, max_length=180)
    signed_at: datetime
    version: int = Field(default=1, ge=1)
    signature_data_url: str = Field(min_length=32, max_length=1_500_000)

    @field_validator("signature_data_url")
    @classmethod
    def validate_png_data_url(cls, value: str) -> str:
        if not value.startswith("data:image/png;base64,"):
            raise ValueError("La firma debe ser una imagen PNG data URL")
        return value


class LabSignatureGroupWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technician: LabSignatureWrite
    client: LabSignatureWrite


class LabSignatureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    signature_type: str
    signer_name: str
    signed_at: datetime
    version: int


class LabSignatureSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    root_work_order_id: int
    signed_at: datetime
    version: int
    signatures: list[LabSignatureRead]


class LabRelatedWorkOrderRead(BaseModel):
    id: int
    folio: int
    sequence_number: int
    status: str
    signature_session_id: int | None
    equipment_count: int


class LabWorkOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: int
    root_work_order_id: int | None
    previous_work_order_id: int | None
    sequence_number: int
    signature_session_id: int | None
    signature_scope: str | None = None
    created_by_user_id: int
    operator_client_id: int | None
    lab_client_id: int | None
    reception_date: date
    departure_date: date
    client_name: str
    address: str
    contact_name: str | None
    contact_phone: str | None
    contact_email: str | None
    postal_code: str | None
    city: str | None
    state_name: str | None
    purchase_order: str | None
    notes: str | None
    status: str
    completed_at: datetime | None
    partially_closed_at: datetime | None = None
    partial_close_ticket_id: int | None = None
    partial_close_pending_snapshot: dict | None = None
    cancelled_at: datetime | None = None
    cancelled_by_user_id: int | None = None
    cancellation_reason: str | None = None
    previous_status: str | None = None
    final_pdf_sha256: str | None
    final_pdf_generated_at: datetime | None
    revision_number: int
    edit_version: int
    reopen_ticket_id: int | None
    signature_required: bool
    signature_preserved: bool
    created_at: datetime
    updated_at: datetime
    equipment: list[LabEquipmentRead]
    signature_session: LabSignatureSessionRead | None
    related_work_orders: list[LabRelatedWorkOrderRead] = Field(default_factory=list)


class LabWorkOrderListItem(BaseModel):
    id: int
    folio: int
    root_work_order_id: int | None
    sequence_number: int
    client_name: str
    reception_date: date
    status: str
    equipment_count: int
    completed_equipment_count: int = 0
    created_at: datetime
    revision_number: int
    signature_required: bool


class LabFieldSheetTrayItem(BaseModel):
    """Proyección mínima de una hoja operativa para la bandeja Mobile LAB."""

    work_order_id: int
    work_order_folio: int
    work_order_status: str
    equipment_id: int
    instrument: str
    brand: str
    model: str | None
    service_type: str | None
    certificate_folio: str | None
    documentary_client_display: str
    field_sheet_id: int | None
    field_sheet_status: str | None
    template_key: str | None
    template_name: str | None
    revision_number: int | None
    is_current: bool | None
    progress_completed: int
    progress_required: int
    bucket: Literal["pending", "in_progress", "completed"]


class LabFieldSheetTrayPage(BaseModel):
    items: list[LabFieldSheetTrayItem]
    offset: int
    limit: int
    total: int
