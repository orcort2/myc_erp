from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


FieldSheetStatus = Literal[
    "draft",
    "in_progress",
    "completed",
    "under_review",
    "approved",
    "rejected",
    "cancelled",
]


class FieldSheetBase(BaseModel):
    equipment_id: int
    initial_condition: str | None = None
    final_condition: str | None = None
    pattern_used: str | None = None
    results: str | None = None
    observations: str | None = None
    evidence_notes: str | None = None
    method: str | None = None
    environmental_conditions: str | None = None
    technician_notes: str | None = None


class FieldSheetCreate(FieldSheetBase):
    pass


class FieldSheetUpdate(BaseModel):
    initial_condition: str | None = None
    final_condition: str | None = None
    pattern_used: str | None = None
    results: str | None = None
    observations: str | None = None
    evidence_notes: str | None = None
    method: str | None = None
    environmental_conditions: str | None = None
    technician_notes: str | None = None


class FieldSheetStatusChange(BaseModel):
    comment: str | None = None


class FieldSheetRead(FieldSheetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: FieldSheetStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime
