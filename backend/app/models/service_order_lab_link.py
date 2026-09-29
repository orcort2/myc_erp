"""Historical ERP association; LAB remains the technical authority."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class ServiceOrderLabLink(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "service_order_lab_links"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'unlinked', 'replaced')",
            name="ck_service_order_lab_link_status",
        ),
        CheckConstraint(
            "(status = 'active' AND unlinked_at IS NULL "
            "AND unlinked_by_user_id IS NULL AND unlink_reason IS NULL "
            "AND replaced_by_link_id IS NULL) OR "
            "(status IN ('unlinked', 'replaced') AND unlinked_at IS NOT NULL "
            "AND unlinked_by_user_id IS NOT NULL AND unlink_reason IS NOT NULL "
            "AND length(trim(unlink_reason)) > 0)",
            name="ck_service_order_lab_link_lifecycle",
        ),
        CheckConstraint(
            "replaced_by_link_id IS NULL OR "
            "(status = 'replaced' AND replaced_by_link_id <> id)",
            name="ck_service_order_lab_link_replacement",
        ),
        Index(
            "uq_service_order_lab_link_active_ets", "service_order_id",
            unique=True, postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        Index(
            "uq_service_order_lab_link_active_root", "lab_root_work_order_id",
            unique=True, postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id", ondelete="RESTRICT"), index=True,
    )
    lab_root_work_order_id: Mapped[int] = mapped_column(
        ForeignKey("lab_work_orders.id", ondelete="RESTRICT"), index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    linked_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False,
    )
    unlinked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unlinked_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    unlink_reason: Mapped[str | None] = mapped_column(Text)
    replaced_by_link_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_order_lab_links.id", ondelete="RESTRICT"),
    )

    service_order: Mapped["ServiceOrder"] = relationship(back_populates="lab_links")
    lab_root_work_order: Mapped["LabWorkOrder"] = relationship()
    linked_by: Mapped["User"] = relationship(foreign_keys=[linked_by_user_id])
    unlinked_by: Mapped["User | None"] = relationship(foreign_keys=[unlinked_by_user_id])
    replaced_by_link: Mapped["ServiceOrderLabLink | None"] = relationship(
        remote_side="ServiceOrderLabLink.id", foreign_keys=[replaced_by_link_id],
    )

    @property
    def root_folio(self) -> int:
        return self.lab_root_work_order.folio

    @property
    def linked_by_name(self) -> str:
        return self.linked_by.full_name or self.linked_by.email

    @property
    def unlinked_by_name(self) -> str | None:
        if self.unlinked_by is None:
            return None
        return self.unlinked_by.full_name or self.unlinked_by.email
