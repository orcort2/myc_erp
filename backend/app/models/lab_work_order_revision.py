from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class LabWorkOrderRevision(IntegerPkMixin, TimestampMixin, Base):
    """Snapshot inmutable de una revisión documental LAB cerrada."""

    __tablename__ = "lab_work_order_revisions"
    __table_args__ = (
        UniqueConstraint(
            "work_order_id", "revision_number", name="uq_lab_work_order_revision_number"
        ),
    )

    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("lab_work_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Cierre UX 2026-09: nullable -- un Admin con autoridad directa
    # (work_orders.reopen + política) reabre sin crear un ticket artificial
    # (ver reopen_work_order_directly). El snapshot histórico sigue
    # generándose igual; sólo deja de exigir un ticket que no existió.
    reopen_ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("operational_tickets.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    signature_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_work_order_signature_sessions.id", ondelete="RESTRICT"), nullable=True
    )
    signature_preserved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    final_pdf: Mapped[bytes | None] = mapped_column(LargeBinary)
    final_pdf_sha256: Mapped[str | None] = mapped_column(String(64))
    final_pdf_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    work_order: Mapped["LabWorkOrder"] = relationship(back_populates="revisions")


from app.models.lab_work_order import LabWorkOrder  # noqa: E402
