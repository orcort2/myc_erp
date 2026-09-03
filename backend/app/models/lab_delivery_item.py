from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class LabDeliveryItem(IntegerPkMixin, TimestampMixin, Base):
    """Un equipo entregado en una exhibición (LabWorkOrderDelivery). Las FK
    son procedencia; los *_snapshot son la autoridad histórica del voucher --
    nunca se recalculan desde el equipo mutable."""

    __tablename__ = "lab_delivery_items"
    __table_args__ = (
        UniqueConstraint("delivery_id", "equipment_id", name="uq_lab_delivery_item_equipment"),
    )

    delivery_id: Mapped[int] = mapped_column(
        ForeignKey("lab_work_order_deliveries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("lab_work_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("lab_work_order_equipment.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    position_snapshot: Mapped[int | None] = mapped_column()
    instrument_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    identification_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    serial_number_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    certificate_folio_snapshot: Mapped[str | None] = mapped_column(String(160))

    delivery: Mapped["LabWorkOrderDelivery"] = relationship(back_populates="items")
    work_order: Mapped["LabWorkOrder"] = relationship(foreign_keys=[work_order_id])
    equipment: Mapped["LabWorkOrderEquipment"] = relationship(foreign_keys=[equipment_id])


from app.models.lab_work_order_delivery import LabWorkOrderDelivery  # noqa: E402
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment  # noqa: E402
