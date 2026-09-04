from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class LabWorkOrderDelivery(IntegerPkMixin, TimestampMixin, Base):
    """Evento inmutable de entrega física (una 'exhibición') de un subconjunto
    de equipos del grupo/cohorte histórico de una OT LAB (root_work_order_id).
    Los equipos entregados en este evento viven en LabDeliveryItem.

    root_work_order_id es una referencia operativa (SET NULL): válida
    mientras la OT raíz viva exista, o mientras una OT superviviente del
    grupo la herede al eliminarse la raíz; queda NULL si el grupo entero
    desaparece. root_work_order_id_snapshot/root_work_order_folio_snapshot
    son la autoridad histórica -- se congelan al crear el evento y nunca se
    reescriben, ni siquiera cuando root_work_order_id se reasigna."""

    __tablename__ = "lab_work_order_deliveries"
    __table_args__ = (
        CheckConstraint("status IN ('completed', 'voided')", name="ck_lab_work_order_delivery_status"),
        CheckConstraint("delivery_type IN ('full', 'partial')", name="ck_lab_work_order_delivery_type"),
        CheckConstraint(
            "delivery_method IN ('direct', 'client_pickup')", name="ck_lab_work_order_delivery_method"
        ),
        CheckConstraint(
            "exhibition_number >= 1", name="ck_lab_work_order_delivery_exhibition_number"
        ),
        UniqueConstraint(
            "root_work_order_id", "exhibition_number", name="uq_lab_work_order_delivery_exhibition"
        ),
    )

    root_work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_work_orders.id", ondelete="SET NULL"), index=True
    )
    root_work_order_id_snapshot: Mapped[int] = mapped_column(nullable=False)
    root_work_order_folio_snapshot: Mapped[int] = mapped_column(nullable=False)
    exhibition_number: Mapped[int] = mapped_column(nullable=False)
    delivery_type: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_method: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed", index=True)
    partial_delivery_ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("operational_tickets.id", ondelete="RESTRICT"), index=True
    )
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    delivered_by_signature_data_url: Mapped[str] = mapped_column(Text, nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(180), nullable=False)
    recipient_signature_data_url: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    void_reason: Mapped[str | None] = mapped_column(Text)
    voucher_pdf: Mapped[bytes | None] = mapped_column(LargeBinary)
    voucher_pdf_sha256: Mapped[str | None] = mapped_column(String(64))
    voucher_pdf_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    root_work_order: Mapped["LabWorkOrder | None"] = relationship(foreign_keys=[root_work_order_id])
    delivered_by: Mapped["User"] = relationship(foreign_keys=[delivered_by_user_id])
    voided_by: Mapped["User | None"] = relationship(foreign_keys=[voided_by_user_id])
    partial_delivery_ticket: Mapped["OperationalTicket | None"] = relationship(
        foreign_keys=[partial_delivery_ticket_id]
    )
    items: Mapped[list["LabDeliveryItem"]] = relationship(
        back_populates="delivery",
        cascade="all, delete-orphan",
        order_by="LabDeliveryItem.position_snapshot",
    )


from app.models.lab_delivery_item import LabDeliveryItem  # noqa: E402
from app.models.operational_ticket import OperationalTicket  # noqa: E402
