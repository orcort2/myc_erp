from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class InstitutionalConfiguration(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "institutional_configurations"

    configuration_key: Mapped[str] = mapped_column(
        String(60), unique=True, index=True, default="default"
    )
    legal_name: Mapped[str] = mapped_column(
        String(180), default="METROLOGÍA Y SERVICIOS MYC"
    )
    document_code: Mapped[str] = mapped_column(String(40), default="FCA-30")
    initial_revision: Mapped[str] = mapped_column(String(40), default="R1")
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(255))
    logo_path: Mapped[str | None] = mapped_column(String(500))

