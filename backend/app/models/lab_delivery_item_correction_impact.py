from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin

IMPACT_TYPES = ("documentation_reissue", "delivery_invalidated")
IMPACT_STATUSES = ("pending", "resolved", "cancelled")


class LabDeliveryItemCorrectionImpact(IntegerPkMixin, TimestampMixin, Base):
    """Consecuencia administrativa de una corrección técnica sobre un
    LabDeliveryItem histórico ya entregado.

    Nunca modifica la Delivery ni su item (snapshots, voucher y hash quedan
    intactos) y nunca se borra: pasa de pending a resolved/cancelled. "none"
    no se persiste. La revisión OT usa SET NULL y la hoja origen RESTRICT;
    work_order_id_snapshot/equipment_id_snapshot conservan la identidad aunque
    el objeto vivo desaparezca."""

    __tablename__ = "lab_delivery_item_correction_impacts"
    __table_args__ = (
        CheckConstraint(
            "impact_type IN ('documentation_reissue', 'delivery_invalidated')",
            name="ck_lab_delivery_item_correction_impact_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'resolved', 'cancelled')",
            name="ck_lab_delivery_item_correction_impact_status",
        ),
        # Guard de concurrencia: una misma corrección (hoja origen) no puede
        # dejar dos impactos pending sobre el mismo item.
        Index(
            "uq_lab_delivery_item_correction_impact_pending",
            "delivery_item_id",
            "source_field_sheet_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )

    delivery_item_id: Mapped[int] = mapped_column(
        ForeignKey("lab_delivery_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    work_order_id_snapshot: Mapped[int] = mapped_column(nullable=False)
    equipment_id_snapshot: Mapped[int] = mapped_column(nullable=False)
    impact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default="pending", index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)
    source_work_order_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_work_order_revisions.id", ondelete="SET NULL")
    )
    # NOT NULL: toda corrección nace de una FieldSheet completed concreta
    # (validada por la autoridad común de reapertura), y es la clave que hace
    # efectivo el índice único parcial. RESTRICT: la hoja origen es histórica.
    source_field_sheet_id: Mapped[int] = mapped_column(
        ForeignKey("field_sheets.id", ondelete="RESTRICT"), nullable=False
    )
    source_field_sheet_revision_number: Mapped[int] = mapped_column(nullable=False)

    delivery_item: Mapped["LabDeliveryItem"] = relationship(back_populates="correction_impacts")


from app.models.lab_delivery_item import LabDeliveryItem  # noqa: E402
