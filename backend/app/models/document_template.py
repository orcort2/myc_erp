from datetime import date

from sqlalchemy import Boolean, Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class DocumentTemplate(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "document_templates"

    template_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    company_name: Mapped[str] = mapped_column(String(180))
    company_tagline: Mapped[str | None] = mapped_column(String(255))
    company_rfc: Mapped[str | None] = mapped_column(String(20))
    company_email: Mapped[str | None] = mapped_column(String(255))
    company_website: Mapped[str | None] = mapped_column(String(255))
    company_address: Mapped[str | None] = mapped_column(Text)
    company_phone: Mapped[str | None] = mapped_column(String(60))
    document_title: Mapped[str] = mapped_column(String(120))
    document_subtitle: Mapped[str | None] = mapped_column(String(255))
    document_code: Mapped[str | None] = mapped_column(String(80))
    document_revision: Mapped[str | None] = mapped_column(String(80))
    document_issued_on: Mapped[date | None] = mapped_column(Date)
    terms_version: Mapped[str | None] = mapped_column(String(80))
    commercial_terms: Mapped[str | None] = mapped_column(Text)
    metrological_terms: Mapped[str | None] = mapped_column(Text)
    legal_terms: Mapped[str | None] = mapped_column(Text)
    privacy_notice: Mapped[str | None] = mapped_column(Text)
    acceptance_text: Mapped[str | None] = mapped_column(Text)
    show_summary_terms: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_full_terms: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_acceptance_signature: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
