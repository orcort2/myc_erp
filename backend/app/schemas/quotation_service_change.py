from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QuotationServiceChangeCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)
    observation: str | None = Field(default=None, max_length=4000)


class QuotationServiceChangeReview(BaseModel):
    decision: Literal["authorize", "reject", "request_information"]
    comment: str | None = Field(default=None, max_length=4000)
    validity_hours: int = Field(default=72, ge=1, le=168)


class QuotationUnlockItem(BaseModel):
    service_key: str = Field(min_length=1, max_length=80)
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    discount_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    description: str | None = Field(default=None, max_length=4000)


class QuotationUnlockPreview(BaseModel):
    items: list[QuotationUnlockItem] = Field(min_length=1)


class QuotationUnlockApply(QuotationUnlockPreview):
    expected_snapshot_number: int = Field(gt=0)


class QuotationServiceChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    folio: str
    status: str
    status_label: str
    capability: str
    quotation_folio: str
    service_order_folio: str
    client_name: str
    requester_name: str
    reviewer_name: str | None = None
    authorized_apply_user_name: str | None = None
    service_order_status: str
    reason: str
    observation: str | None = None
    review_comment: str | None = None
    block_reason: str | None = None
    base_snapshot_number: int
    impact: dict
    dependencies: list[dict] = Field(default_factory=list)
    requested_at: datetime
    reviewed_at: datetime | None = None
    expires_at: datetime | None = None
    applied_at: datetime | None = None
    can_apply: bool = False
    can_review: bool = False
    can_request: bool = False
