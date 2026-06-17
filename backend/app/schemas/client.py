from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ClientContactBase(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    position: str | None = Field(default=None, max_length=120)


class ClientContactCreate(ClientContactBase):
    pass


class ClientContactRead(ClientContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClientBase(BaseModel):
    legal_name: str = Field(min_length=1, max_length=255)
    commercial_name: str | None = Field(default=None, max_length=255)
    rfc: str | None = Field(default=None, max_length=13)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    tax_regime: str | None = Field(default=None, max_length=120)
    payment_terms: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class ClientCreate(ClientBase):
    contacts: list[ClientContactCreate] = Field(default_factory=list)


class ClientUpdate(BaseModel):
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    commercial_name: str | None = Field(default=None, max_length=255)
    rfc: str | None = Field(default=None, max_length=13)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    tax_regime: str | None = Field(default=None, max_length=120)
    payment_terms: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class ClientRead(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    contacts: list[ClientContactRead] = Field(default_factory=list)
