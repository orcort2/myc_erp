from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentTemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    company_name: str = Field(min_length=1, max_length=180)
    company_tagline: str | None = Field(default=None, max_length=255)
    company_rfc: str | None = Field(default=None, max_length=20)
    company_email: str | None = Field(default=None, max_length=255)
    company_website: str | None = Field(default=None, max_length=255)
    company_address: str | None = None
    company_phone: str | None = Field(default=None, max_length=60)
    document_title: str = Field(min_length=1, max_length=120)
    document_subtitle: str | None = Field(default=None, max_length=255)
    document_code: str | None = Field(default=None, max_length=80)
    document_revision: str | None = Field(default=None, max_length=80)
    document_issued_on: date | None = None
    terms_version: str | None = Field(default=None, max_length=80)
    commercial_terms: str | None = None
    metrological_terms: str | None = None
    legal_terms: str | None = None
    privacy_notice: str | None = None
    acceptance_text: str | None = None
    show_summary_terms: bool = True
    show_full_terms: bool = True
    show_acceptance_signature: bool = True


class DocumentTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    company_name: str | None = Field(default=None, min_length=1, max_length=180)
    company_tagline: str | None = Field(default=None, max_length=255)
    company_rfc: str | None = Field(default=None, max_length=20)
    company_email: str | None = Field(default=None, max_length=255)
    company_website: str | None = Field(default=None, max_length=255)
    company_address: str | None = None
    company_phone: str | None = Field(default=None, max_length=60)
    document_title: str | None = Field(default=None, min_length=1, max_length=120)
    document_subtitle: str | None = Field(default=None, max_length=255)
    document_code: str | None = Field(default=None, max_length=80)
    document_revision: str | None = Field(default=None, max_length=80)
    document_issued_on: date | None = None
    terms_version: str | None = Field(default=None, max_length=80)
    commercial_terms: str | None = None
    metrological_terms: str | None = None
    legal_terms: str | None = None
    privacy_notice: str | None = None
    acceptance_text: str | None = None
    show_summary_terms: bool | None = None
    show_full_terms: bool | None = None
    show_acceptance_signature: bool | None = None


class DocumentTemplateOut(DocumentTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_key: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
