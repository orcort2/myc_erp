from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class Equipment(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "equipment"

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id"), index=True
    )
    service_order_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_order_items.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(60), default="registered", index=True)
    name: Mapped[str] = mapped_column(String(180))
    brand: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    serial_number: Mapped[str | None] = mapped_column(String(120), index=True)
    internal_id: Mapped[str | None] = mapped_column(String(120), index=True)
    range_or_capacity: Mapped[str | None] = mapped_column(String(180))
    initial_condition: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    service_order: Mapped["ServiceOrder"] = relationship(back_populates="equipment")
