from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class Client(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "clients"

    client_type: Mapped[str] = mapped_column(String(30), default="persona_moral", index=True)
    legal_name: Mapped[str] = mapped_column(String(255), index=True)
    commercial_name: Mapped[str | None] = mapped_column(String(255), index=True)
    rfc: Mapped[str | None] = mapped_column(String(13), index=True)
    curp: Mapped[str | None] = mapped_column(String(18), index=True)
    first_name: Mapped[str | None] = mapped_column(String(120))
    first_last_name: Mapped[str | None] = mapped_column(String(120))
    second_last_name: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    tax_regime: Mapped[str | None] = mapped_column(String(120))
    cfdi_use: Mapped[str | None] = mapped_column(String(40))
    street_type: Mapped[str | None] = mapped_column(String(80))
    street: Mapped[str | None] = mapped_column(String(255))
    exterior_number: Mapped[str | None] = mapped_column(String(40))
    interior_number: Mapped[str | None] = mapped_column(String(40))
    neighborhood: Mapped[str | None] = mapped_column(String(180))
    locality: Mapped[str | None] = mapped_column(String(180))
    municipality: Mapped[str | None] = mapped_column(String(180))
    city: Mapped[str | None] = mapped_column(String(180))
    state: Mapped[str | None] = mapped_column(String(180))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str | None] = mapped_column(String(120))
    fiscal_postal_code: Mapped[str | None] = mapped_column(String(20))
    tax_constancy_filename: Mapped[str | None] = mapped_column(String(255))
    tax_constancy_path: Mapped[str | None] = mapped_column(String(500))
    tax_constancy_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_terms: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)

    contacts: Mapped[list["ClientContact"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    quotations: Mapped[list["Quotation"]] = relationship(back_populates="client")
    service_orders: Mapped[list["ServiceOrder"]] = relationship(back_populates="client")


class ClientContact(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "client_contacts"

    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40))
    position: Mapped[str | None] = mapped_column(String(120))

    client: Mapped[Client] = relationship(back_populates="contacts")
