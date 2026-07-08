from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class ServiceOrder(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "service_orders"

    folio: Mapped[str] = mapped_column(String(40), unique=True, index=True)

    # Legacy / compatibilidad:
    # Se conserva como OT principal para no romper pantallas, PDFs o datos previos.
    # La operación nueva usará ServiceWorkOrder.
    work_order_number: Mapped[int] = mapped_column(unique=True, index=True)

    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id"), index=True)
    advisor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(60), default="scheduled", index=True)
    agenda_date: Mapped[date | None] = mapped_column(Date)
    service_date: Mapped[date | None] = mapped_column(Date)
    closed_at: Mapped[date | None] = mapped_column(Date)
    total_equipment: Mapped[int] = mapped_column(default=0)
    completed_equipment: Mapped[int] = mapped_column(default=0)
    requires_payment: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    client: Mapped["Client"] = relationship(back_populates="service_orders")
    quotation: Mapped["Quotation | None"] = relationship(back_populates="service_orders")
    advisor: Mapped["User | None"] = relationship(foreign_keys=[advisor_id])
    technician: Mapped["User | None"] = relationship(foreign_keys=[technician_id])

    items: Mapped[list["ServiceOrderItem"]] = relationship(
        back_populates="service_order",
        cascade="all, delete-orphan",
    )

    work_orders: Mapped[list["ServiceWorkOrder"]] = relationship(
        back_populates="service_order",
        cascade="all, delete-orphan",
        order_by="ServiceWorkOrder.sequence.asc()",
    )

    equipment: Mapped[list["Equipment"]] = relationship(back_populates="service_order")
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="service_order")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="service_order")

    @property
    def advisor_name(self) -> str | None:
        if self.advisor is None:
            return None
        return self.advisor.full_name or self.advisor.email

    @property
    def technician_name(self) -> str | None:
        if self.technician is None:
            return None
        return self.technician.full_name or self.technician.email


class ServiceWorkOrder(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "service_work_orders"

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id"),
        index=True,
    )
    work_order_number: Mapped[int] = mapped_column(unique=True, index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1, index=True)
    status: Mapped[str] = mapped_column(String(60), default="pending", index=True)
    equipment_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    service_order: Mapped["ServiceOrder"] = relationship(back_populates="work_orders")

    equipment: Mapped[list["Equipment"]] = relationship(
        back_populates="work_order",
        order_by="Equipment.id.asc()",
    )

    @property
    def active_equipment_count(self) -> int:
        return len([item for item in self.equipment if item.is_active])

    @property
    def available_equipment_slots(self) -> int:
        return max(self.equipment_limit - self.active_equipment_count, 0)


class ServiceOrderItem(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "service_order_items"

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id"),
        index=True,
    )
    quotation_item_id: Mapped[int | None] = mapped_column(ForeignKey("quotation_items.id"))
    service_name: Mapped[str] = mapped_column(String(180))
    calibration_scope: Mapped[str | None] = mapped_column(String(60))
    quantity: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(60), default="pending")

    service_order: Mapped[ServiceOrder] = relationship(back_populates="items")