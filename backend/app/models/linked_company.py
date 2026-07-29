from sqlalchemy import Boolean, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class LinkedCompany(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "linked_companies"
    __table_args__ = (
        UniqueConstraint("name", name="linked_companies_name_key"),
        UniqueConstraint(
            "abbreviation", name="linked_companies_abbreviation_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    legal_name: Mapped[str | None] = mapped_column(String(240))
    abbreviation: Mapped[str] = mapped_column(String(40), index=True)
    default_certificate_prefix: Mapped[str] = mapped_column(String(12))
    notes: Mapped[str | None] = mapped_column(Text)
    document_configuration: Mapped[dict | None] = mapped_column(JSON)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, index=True
    )
