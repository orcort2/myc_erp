from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


QuotationStatus = Literal[
    "draft",
    "sent",
    "waiting",
    "accepted",
    "rejected",
    "expired",
    "cancelled",
]


class QuotationItemBase(BaseModel):
    service_name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0)


class QuotationItemCreate(QuotationItemBase):
    pass


class QuotationItemUpdate(BaseModel):
    service_name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    unit_price: Decimal | None = Field(default=None, ge=0)


class QuotationItemRead(QuotationItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    total: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class QuotationBase(BaseModel):
    client_id: int
    advisor_id: int | None = None
    issued_on: date | None = None
    valid_until: date | None = None
    notes: str | None = None


class QuotationCreate(QuotationBase):
    items: list[QuotationItemCreate] = Field(default_factory=list)


class QuotationUpdate(BaseModel):
    advisor_id: int | None = None
    issued_on: date | None = None
    valid_until: date | None = None
    notes: str | None = None


class QuotationStatusChange(BaseModel):
    comment: str | None = None


class QuotationRead(QuotationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: str
    status: str
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: list[QuotationItemRead] = Field(default_factory=list)
