from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class ServiceOrderExceptionRequest(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "service_order_exception_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('requested', 'authorized', 'executed', 'rejected')",
            name="ck_service_order_exception_requests_status",
        ),
    )

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id"), nullable=False, index=True
    )
    requested_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    authorized_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    executed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="requested",
        server_default="requested",
        index=True,
    )
    source_stage: Mapped[str] = mapped_column(String(80), nullable=False)
    target_stage: Mapped[str] = mapped_column(String(80), nullable=False)
    target_status: Mapped[str | None] = mapped_column(String(60))
    service_order_status_at_request: Mapped[str] = mapped_column(String(60), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    authorization_comment: Mapped[str | None] = mapped_column(Text)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    service_order: Mapped["ServiceOrder"] = relationship(
        back_populates="exception_requests"
    )
    requested_by: Mapped["User"] = relationship(foreign_keys=[requested_by_id])
    authorized_by: Mapped["User | None"] = relationship(foreign_keys=[authorized_by_id])
    executed_by: Mapped["User | None"] = relationship(foreign_keys=[executed_by_id])
