from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QuotationServiceChangeCreate(BaseModel):
    quotation_line_number: int = Field(gt=0)
    requested_service_key: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=3, max_length=2000)
    observation: str | None = Field(default=None, max_length=4000)


class QuotationServiceChangeReview(BaseModel):
    decision: Literal["authorize", "reject", "request_information"]
    comment: str | None = Field(default=None, max_length=4000)
    validity_hours: int = Field(default=72, ge=1, le=168)


class QuotationServiceChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    folio: str
    status: str
    status_label: str
    capability: str
    quotation_folio: str
    service_order_folio: str
    client_name: str
    quotation_line_number: int
    current_service_key: str | None = None
    requested_service_key: str
    current_service_name: str
    requested_service_name: str
    requester_name: str
    reviewer_name: str | None = None
    authorized_apply_user_name: str | None = None
    service_order_status: str
    equipment_count: int
    reason: str
    observation: str | None = None
    review_comment: str | None = None
    block_reason: str | None = None
    impact: dict
    requested_at: datetime
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None
    applied_at: datetime | None = None
    can_apply: bool = False
    can_review: bool = False
    can_request: bool = False
