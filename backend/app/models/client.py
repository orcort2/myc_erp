from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class Client(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "clients"

    legal_name: Mapped[str] = mapped_column(String(255), index=True)
    commercial_name: Mapped[str | None] = mapped_column(String(255), index=True)
    rfc: Mapped[str | None] = mapped_column(String(13), index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    tax_regime: Mapped[str | None] = mapped_column(String(120))
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
