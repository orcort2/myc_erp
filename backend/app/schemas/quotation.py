from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.service_scope import ServiceScope


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
    catalog_item_id: int | None = None
    service_name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    quantity: int = Field(default=1, ge=1)
    unit: str | None = Field(default=None, max_length=80)
    sat_key: str | None = Field(default=None, max_length=40)
    sat_unit: str | None = Field(default=None, max_length=40)
    internal_unit: str | None = Field(default=None, max_length=80)
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    discount_percent: Decimal = Field(default=Decimal("0.00"), ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    commodity: str | None = Field(default=None, max_length=40)
    calibration_scope: ServiceScope | None = None
    quotation_legend: str | None = None
    tax_object: str | None = Field(default=None, max_length=20)
    tax_rate: Decimal = Field(default=Decimal("16.00"), ge=0)


class QuotationItemCreate(QuotationItemBase):
    pass


class QuotationItemUpdate(BaseModel):
    catalog_item_id: int | None = None
    service_name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    unit: str | None = Field(default=None, max_length=80)
    sat_key: str | None = Field(default=None, max_length=40)
    sat_unit: str | None = Field(default=None, max_length=40)
    internal_unit: str | None = Field(default=None, max_length=80)
    unit_price: Decimal | None = Field(default=None, ge=0)
    discount_percent: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    commodity: str | None = Field(default=None, max_length=40)
    calibration_scope: ServiceScope | None = None
    quotation_legend: str | None = None
    tax_object: str | None = Field(default=None, max_length=20)
    tax_rate: Decimal | None = Field(default=None, ge=0)


class QuotationItemRead(QuotationItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operational_snapshot: dict | None = None
    tax_total: Decimal
    total: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

class QuotationBase(BaseModel):
    client_id: int
    advisor_id: int | None = None
    issued_on: date | None = None
    valid_until: date | None = None
    payment_terms: str | None = None
    notes: str | None = None


class QuotationCreate(QuotationBase):
    items: list[QuotationItemCreate] = Field(default_factory=list)


class QuotationUpdate(BaseModel):
    client_id: int | None = None
    advisor_id: int | None = None
    issued_on: date | None = None
    valid_until: date | None = None
    payment_terms: str | None = None
    notes: str | None = None


class QuotationStatusChange(BaseModel):
    comment: str | None = None


class QuotationSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quotation_id: int
    snapshot_number: int
    reason: str | None = None
    created_by_id: int | None = None
    snapshot_data: dict
    created_at: datetime
    updated_at: datetime


class QuotationRestoreSnapshot(BaseModel):
    snapshot_id: int


class QuotationRead(QuotationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: str
    advisor_name: str | None = None
    status: str
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: list[QuotationItemRead] = Field(default_factory=list)
