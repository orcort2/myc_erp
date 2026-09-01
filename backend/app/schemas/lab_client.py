from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LabClientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1, max_length=255)
    address: str = Field(default="", max_length=2000)
    attention: str = Field(default="", max_length=180)


class LabClientRead(LabClientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operator_client_id: int | None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class LabClientImportSummary(BaseModel):
    new: int
    skipped: int
    invalid: int
    errors: list[dict] = Field(default_factory=list)
