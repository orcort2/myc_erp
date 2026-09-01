from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


TICKET_TYPES = (
    "reopen_work_order",
    "manual_myc_folio",
    "linked_folio",
    "partial_close",
    "certificate_folio_block",
    "field_sheet_template_request",
)
TICKET_STATUSES = (
    "pending",
    "approved",
    "rejected",
    "in_progress",
    "resolved",
    "cancelled",
)
SIGNATURE_POLICIES = ("preserve", "invalidate")


class OperationalTicket(IntegerPkMixin, TimestampMixin, Base):
    """Solicitud operativa extensible; inicialmente soporta reaperturas LAB."""

    __tablename__ = "operational_tickets"
    __table_args__ = (
        CheckConstraint(
            "type IN ('reopen_work_order', 'manual_myc_folio', 'linked_folio', "
            "'partial_close', 'certificate_folio_block', 'field_sheet_template_request')",
            name="ck_operational_ticket_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'in_progress', 'resolved', 'cancelled')",
            name="ck_operational_ticket_status",
        ),
        CheckConstraint(
            "requested_signature_policy IS NULL OR requested_signature_policy IN ('preserve', 'invalidate')",
            name="ck_operational_ticket_requested_signature_policy",
        ),
        CheckConstraint(
            "final_signature_policy IS NULL OR final_signature_policy IN ('preserve', 'invalidate')",
            name="ck_operational_ticket_final_signature_policy",
        ),
    )

    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_work_orders.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_work_order_equipment.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    operator_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    linked_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("linked_companies.id", ondelete="RESTRICT"), nullable=True
    )
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("communication_conversations.id", ondelete="SET NULL"), nullable=True
    )
    requested_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requested_signature_policy: Mapped[str | None] = mapped_column(String(20), nullable=True)
    final_signature_policy: Mapped[str | None] = mapped_column(String(20))
    automatic_folio: Mapped[str | None] = mapped_column(String(120))
    requested_folio: Mapped[str | None] = mapped_column(String(120))
    authorized_folio: Mapped[str | None] = mapped_column(String(120))
    accredited_quantity: Mapped[int | None] = mapped_column(Integer)
    traceable_quantity: Mapped[int | None] = mapped_column(Integer)
    resolution_snapshot: Mapped[dict | None] = mapped_column(JSON)
    decision_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    work_order: Mapped["LabWorkOrder | None"] = relationship(foreign_keys=[work_order_id])
    equipment: Mapped["LabWorkOrderEquipment | None"] = relationship(foreign_keys=[equipment_id])
    requested_by: Mapped["User"] = relationship(foreign_keys=[requested_by_user_id])
    reviewed_by: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by_user_id])


from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment  # noqa: E402
from app.models.user import User  # noqa: E402
