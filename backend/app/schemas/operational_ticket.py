from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReopenTicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_order_id: int
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


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    status: str
    work_order_id: int
    work_order_folio: int
    client_name: str
    requested_by_user_id: int
    requested_by_name: str
    reviewed_by_user_id: int | None
    reason: str
    description: str
    requested_signature_policy: str
    final_signature_policy: str | None
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
