from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InstitutionalConfigurationUpdate(BaseModel):
    legal_name: str | None = Field(default=None, min_length=1, max_length=180)
    document_code: str | None = Field(default=None, min_length=1, max_length=40)
    initial_revision: str | None = Field(default=None, min_length=1, max_length=40)
    address: str | None = None
    phone: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=255)
    logo_path: str | None = Field(default=None, max_length=500)


class InstitutionalConfigurationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    configuration_key: str
    legal_name: str
    document_code: str
    initial_revision: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    logo_path: str | None = None
    created_at: datetime
    updated_at: datetime

