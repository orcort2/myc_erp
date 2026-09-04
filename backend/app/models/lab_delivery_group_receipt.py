from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class LabDeliveryGroupReceipt(IntegerPkMixin, TimestampMixin, Base):
    """Resumen final consolidado de entrega de un grupo/cohorte (root_work_order_id),
    congelado cuando remaining == 0. Nunca se regenera in-place: un void que
    rompe la completitud sólo marca superseded_at; la siguiente entrega
    completa produce una nueva version.

    root_work_order_id es una referencia operativa (SET NULL), igual que en
    LabWorkOrderDelivery; root_work_order_id_snapshot/
    root_work_order_folio_snapshot son la autoridad histórica y nunca se
    reescriben."""

    __tablename__ = "lab_delivery_group_receipts"
    __table_args__ = (
        UniqueConstraint("root_work_order_id", "version", name="uq_lab_delivery_group_receipt_version"),
    )

    root_work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_work_orders.id", ondelete="SET NULL"), index=True
    )
    root_work_order_id_snapshot: Mapped[int] = mapped_column(nullable=False)
    root_work_order_folio_snapshot: Mapped[int] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    exhibitions_count: Mapped[int] = mapped_column(nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pdf: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    pdf_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    root_work_order: Mapped["LabWorkOrder | None"] = relationship(foreign_keys=[root_work_order_id])
    generated_by: Mapped["User"] = relationship(foreign_keys=[generated_by_user_id])


from app.models.lab_work_order import LabWorkOrder  # noqa: E402
from app.models.user import User  # noqa: E402
