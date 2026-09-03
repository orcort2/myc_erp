from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class LabWorkOrderDelivery(IntegerPkMixin, TimestampMixin, Base):
    """Evento inmutable de entrega física de todos los equipos de una OT LAB."""

    __tablename__ = "lab_work_order_deliveries"
    __table_args__ = (
        CheckConstraint("status IN ('completed', 'voided')", name="ck_lab_work_order_delivery_status"),
        Index(
            "uq_lab_work_order_delivery_active",
            "work_order_id",
            unique=True,
            postgresql_where=text("status = 'completed'"),
            sqlite_where=text("status = 'completed'"),
        ),
    )

    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("lab_work_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    recipient_name: Mapped[str] = mapped_column(String(180), nullable=False)
    recipient_signature_data_url: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed", index=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    void_reason: Mapped[str | None] = mapped_column(Text)
    voucher_pdf: Mapped[bytes | None] = mapped_column(LargeBinary)
    voucher_pdf_sha256: Mapped[str | None] = mapped_column(String(64))
    voucher_pdf_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    work_order: Mapped["LabWorkOrder"] = relationship(back_populates="deliveries")
    delivered_by: Mapped["User"] = relationship(foreign_keys=[delivered_by_user_id])
    voided_by: Mapped["User | None"] = relationship(foreign_keys=[voided_by_user_id])
