from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EquipmentStatus = Literal[
    "registered",
    "realizing",
    "calibrated",
    "labeled",
    "not_done",
    "cancelled",
]


class EquipmentBase(BaseModel):
    service_order_id: int
    work_order_id: int | None = None
    service_order_item_id: int | None = None
    calibration_scope: str | None = Field(default=None, max_length=60)
    certificate_master_document_id: int | None = None
    name: str = Field(min_length=1, max_length=180)
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    internal_id: str | None = Field(default=None, max_length=120)
    range_or_capacity: str | None = Field(default=None, max_length=180)
    initial_condition: str | None = None
    notes: str | None = None


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    work_order_id: int | None = None
    service_order_item_id: int | None = None
    calibration_scope: str | None = Field(default=None, max_length=60)
    certificate_master_document_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=180)
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    internal_id: str | None = Field(default=None, max_length=120)
    range_or_capacity: str | None = Field(default=None, max_length=180)
    initial_condition: str | None = None
    notes: str | None = None


class EquipmentStatusChange(BaseModel):
    comment: str | None = None


class EquipmentRead(EquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_order_number: int | None = None
    status: EquipmentStatus
    certificate_master_document_id: int | None = None
    certificate_master_version_id: int | None = None
    certificate_template_filename_snapshot: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
