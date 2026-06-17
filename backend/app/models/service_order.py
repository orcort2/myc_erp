from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class ServiceOrder(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "service_orders"

    folio: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"), index=True)
    status: Mapped[str] = mapped_column(String(60), default="open", index=True)
    scheduled_date: Mapped[date | None] = mapped_column(Date)
    closed_at: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    client: Mapped["Client"] = relationship(back_populates="service_orders")
    quotation: Mapped["Quotation | None"] = relationship(back_populates="service_orders")
    items: Mapped[list["ServiceOrderItem"]] = relationship(
        back_populates="service_order", cascade="all, delete-orphan"
    )
    equipment: Mapped[list["Equipment"]] = relationship(back_populates="service_order")


class ServiceOrderItem(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "service_order_items"

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id"), index=True
    )
    quotation_item_id: Mapped[int | None] = mapped_column(ForeignKey("quotation_items.id"))
    service_name: Mapped[str] = mapped_column(String(180))
    quantity: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(60), default="pending")

    service_order: Mapped[ServiceOrder] = relationship(back_populates="items")

