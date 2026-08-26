from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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
    expected_edit_version: int | None = Field(default=None, ge=1)


class LabEquipmentBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument: str = Field(min_length=1, max_length=255)
    brand: str = Field(min_length=1, max_length=160)
    identification: str = Field(min_length=1, max_length=160)
    serial_number: str = Field(min_length=1, max_length=160)
    report_number: str | None = Field(default=None, max_length=160)
    is_good_condition: bool


class LabEquipmentWrite(LabEquipmentBase):
    expected_edit_version: int | None = Field(default=None, ge=1)


class LabEquipmentRead(LabEquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    created_at: datetime
    updated_at: datetime


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
    equipment_count: int


class LabWorkOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: int
    root_work_order_id: int | None
    previous_work_order_id: int | None
    sequence_number: int
    signature_session_id: int | None
    created_by_user_id: int
    operator_client_id: int | None
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
    created_at: datetime
    revision_number: int
    signature_required: bool
