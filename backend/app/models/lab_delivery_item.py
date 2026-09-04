from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class LabDeliveryItem(IntegerPkMixin, TimestampMixin, Base):
    """Un equipo entregado en una exhibición (LabWorkOrderDelivery).

    work_order_id/equipment_id son referencias operativas de conveniencia
    (SET NULL): sólo válidas mientras la OT/equipo vivo exista, y quedan en
    NULL si se elimina -- nunca se reasignan a otra OT/equipo. La autoridad
    histórica real es *_snapshot (instrument/brand/identification/serial/
    certificate_folio, más work_order_id_snapshot/work_order_folio_snapshot/
    equipment_id_snapshot): se congelan al crear el registro y nunca se
    recalculan ni se vuelven a escribir, así que sobreviven intactas aunque
    la OT o el equipo original se eliminen."""

    __tablename__ = "lab_delivery_items"
    __table_args__ = (
        UniqueConstraint("delivery_id", "equipment_id", name="uq_lab_delivery_item_equipment"),
    )

    delivery_id: Mapped[int] = mapped_column(
        ForeignKey("lab_work_order_deliveries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_work_orders.id", ondelete="SET NULL"), index=True
    )
    equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_work_order_equipment.id", ondelete="SET NULL"), index=True
    )
    work_order_id_snapshot: Mapped[int] = mapped_column(nullable=False)
    work_order_folio_snapshot: Mapped[int] = mapped_column(nullable=False)
    equipment_id_snapshot: Mapped[int] = mapped_column(nullable=False)
    position_snapshot: Mapped[int | None] = mapped_column()
    instrument_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    identification_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    serial_number_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    certificate_folio_snapshot: Mapped[str | None] = mapped_column(String(160))

    delivery: Mapped["LabWorkOrderDelivery"] = relationship(back_populates="items")
    work_order: Mapped["LabWorkOrder | None"] = relationship(foreign_keys=[work_order_id])
    equipment: Mapped["LabWorkOrderEquipment | None"] = relationship(foreign_keys=[equipment_id])


from app.models.lab_work_order_delivery import LabWorkOrderDelivery  # noqa: E402
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment  # noqa: E402
