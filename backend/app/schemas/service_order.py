from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ServiceOrderStatus = Literal[
    "scheduled",
    "confirmed",
    "called",
    "in_progress",
    "technical_review",
    "capture",
    "quality_review",
    "pending_payment",
    "released",
    "closed",
    "cancelled",
]


class ServiceOrderItemBase(BaseModel):
    quotation_item_id: int | None = None
    service_name: str = Field(min_length=1, max_length=180)
    quantity: int = Field(default=1, ge=1)
    status: str = Field(default="pending", max_length=60)


class ServiceOrderItemCreate(ServiceOrderItemBase):
    pass


class ServiceOrderItemRead(ServiceOrderItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServiceOrderBase(BaseModel):
    client_id: int
    quotation_id: int | None = None
    advisor_id: int | None = None
    technician_id: int | None = None
    agenda_date: date | None = None
    service_date: date | None = None
    total_equipment: int = Field(default=0, ge=0)
    completed_equipment: int = Field(default=0, ge=0)
    requires_payment: bool = True
    notes: str | None = None


class ServiceOrderCreate(ServiceOrderBase):
    items: list[ServiceOrderItemCreate] = Field(default_factory=list)


class ServiceOrderUpdate(BaseModel):
    advisor_id: int | None = None
    technician_id: int | None = None
    agenda_date: date | None = None
    service_date: date | None = None
    total_equipment: int | None = Field(default=None, ge=0)
    completed_equipment: int | None = Field(default=None, ge=0)
    requires_payment: bool | None = None
    notes: str | None = None


class ServiceOrderStatusChange(BaseModel):
    comment: str | None = None


class ServiceOrderRead(ServiceOrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: str
    status: ServiceOrderStatus
    closed_at: date | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: list[ServiceOrderItemRead] = Field(default_factory=list)
