from datetime import datetime
from typing import Any

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


class ClientCertificateProfileBase(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    company: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1)
    attention: str | None = Field(default=None, max_length=180)
    is_default: bool = False


class ClientCertificateProfileCreate(ClientCertificateProfileBase):
    pass


class ClientCertificateProfileUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    company: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1)
    attention: str | None = Field(default=None, max_length=180)
    is_default: bool | None = None


class ClientCertificateProfileRead(ClientCertificateProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClientBase(BaseModel):
    client_type: str = Field(min_length=1, max_length=30)
    legal_name: str = Field(min_length=1, max_length=255)
    commercial_name: str | None = Field(default=None, max_length=255)
    rfc: str | None = Field(default=None, max_length=13)
    curp: str | None = Field(default=None, max_length=18)
    first_name: str | None = Field(default=None, max_length=120)
    first_last_name: str | None = Field(default=None, max_length=120)
    second_last_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    tax_regime: str | None = Field(default=None, max_length=120)
    cfdi_use: str | None = Field(default=None, max_length=40)
    street_type: str | None = Field(default=None, max_length=80)
    street: str | None = Field(default=None, max_length=255)
    exterior_number: str | None = Field(default=None, max_length=40)
    interior_number: str | None = Field(default=None, max_length=40)
    neighborhood: str | None = Field(default=None, max_length=180)
    locality: str | None = Field(default=None, max_length=180)
    municipality: str | None = Field(default=None, max_length=180)
    city: str | None = Field(default=None, max_length=180)
    state: str | None = Field(default=None, max_length=180)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=120)
    fiscal_postal_code: str | None = Field(default=None, max_length=20)
    payment_terms: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class ClientCreate(ClientBase):
    contacts: list[ClientContactCreate] = Field(default_factory=list)


class ClientUpdate(BaseModel):
    client_type: str | None = Field(default=None, min_length=1, max_length=30)
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    commercial_name: str | None = Field(default=None, max_length=255)
    rfc: str | None = Field(default=None, max_length=13)
    curp: str | None = Field(default=None, max_length=18)
    first_name: str | None = Field(default=None, max_length=120)
    first_last_name: str | None = Field(default=None, max_length=120)
    second_last_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    tax_regime: str | None = Field(default=None, max_length=120)
    cfdi_use: str | None = Field(default=None, max_length=40)
    street_type: str | None = Field(default=None, max_length=80)
    street: str | None = Field(default=None, max_length=255)
    exterior_number: str | None = Field(default=None, max_length=40)
    interior_number: str | None = Field(default=None, max_length=40)
    neighborhood: str | None = Field(default=None, max_length=180)
    locality: str | None = Field(default=None, max_length=180)
    municipality: str | None = Field(default=None, max_length=180)
    city: str | None = Field(default=None, max_length=180)
    state: str | None = Field(default=None, max_length=180)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=120)
    fiscal_postal_code: str | None = Field(default=None, max_length=20)
    payment_terms: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    contacts: list[ClientContactCreate] | None = None


class ClientRead(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    contacts: list[ClientContactRead] = Field(default_factory=list)
    certificate_profiles: list[ClientCertificateProfileRead] = Field(default_factory=list)
    tax_constancy_filename: str | None = None
    tax_constancy_uploaded_at: datetime | None = None


class ClientImportRowRead(BaseModel):
    id: str
    name: str
    rfc: str
    email: str
    status: str
    errors: list[str] = Field(default_factory=list)
    duplicates: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class ClientImportPreviewRead(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[ClientImportRowRead] = Field(default_factory=list)
    valid_count: int = 0
    duplicate_count: int = 0
    error_count: int = 0


class ClientImportConfirm(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)


class ClientImportResultRead(BaseModel):
    imported_count: int
    omitted_count: int
    duplicate_count: int
    error_count: int
    imported_ids: list[int] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ClientTaxConstancyPreviewRead(BaseModel):
    available: bool
    filename: str
    message: str
    extracted_client_type: str | None = None
    extracted_legal_name: str | None = None
    extracted_commercial_name: str | None = None
    extracted_rfc: str | None = None
    extracted_curp: str | None = None
    extracted_first_name: str | None = None
    extracted_first_last_name: str | None = None
    extracted_second_last_name: str | None = None
    extracted_fiscal_postal_code: str | None = None
    extracted_tax_regime: str | None = None
    extracted_tax_regimes: list[str] = Field(default_factory=list)
    extracted_street_type: str | None = None
    extracted_street: str | None = None
    extracted_exterior_number: str | None = None
    extracted_interior_number: str | None = None
    extracted_neighborhood: str | None = None
    extracted_locality: str | None = None
    extracted_municipality: str | None = None
    extracted_state: str | None = None
