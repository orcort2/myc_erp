from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CertificateStatus = Literal[
    "draft",
    "generated",
    "quality_review",
    "correction_requested",
    "approved",
    "released",
    "cancelled",
    "suspended",
]

CertificateType = Literal["acreditado", "trazable"]


class CertificateBase(BaseModel):
    service_order_id: int
    equipment_id: int
    field_sheet_id: int
    certificate_type: CertificateType = "trazable"
    issued_on: date | None = None
    title: str | None = Field(default=None, max_length=180)
    notes: str | None = None


class CertificateCreate(CertificateBase):
    pass


class CertificateUpdate(BaseModel):
    issued_on: date | None = None
    title: str | None = Field(default=None, max_length=180)
    notes: str | None = None


class CertificateStatusChange(BaseModel):
    comment: str | None = None


class CertificateRead(CertificateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folio: str
    status: CertificateStatus
    released_on: date | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
