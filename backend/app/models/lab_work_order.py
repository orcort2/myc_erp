from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class LabWorkOrder(IntegerPkMixin, TimestampMixin, Base):
    """Orden temporal aislada del flujo productivo de ETS/OT."""

    __tablename__ = "lab_work_orders"
    __table_args__ = (
        CheckConstraint("folio BETWEEN 6400 AND 6999", name="ck_lab_work_order_folio_range"),
        CheckConstraint("sequence_number >= 1", name="ck_lab_work_order_sequence"),
        CheckConstraint(
            "status IN ('draft', 'ready_for_signatures', 'completed')",
            name="ck_lab_work_order_status",
        ),
        UniqueConstraint(
            "root_work_order_id",
            "sequence_number",
            name="uq_lab_work_order_group_sequence",
        ),
        UniqueConstraint("folio", name="uq_lab_work_order_folio"),
        UniqueConstraint(
            "previous_work_order_id", name="uq_lab_work_order_previous"
        ),
    )

    folio: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    root_work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_work_orders.id", ondelete="RESTRICT"), index=True
    )
    previous_work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_work_orders.id", ondelete="RESTRICT"), index=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    signature_session_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "lab_work_order_signature_sessions.id",
            ondelete="RESTRICT",
            name="fk_lab_work_orders_signature_session_id",
            use_alter=True,
        ),
        index=True,
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    reception_date: Mapped[date] = mapped_column(Date, nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False, default="")
    contact_name: Mapped[str | None] = mapped_column(String(180))
    contact_phone: Mapped[str | None] = mapped_column(String(60))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(120))
    state_name: Mapped[str | None] = mapped_column(String(120))
    purchase_order: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    final_pdf: Mapped[bytes | None] = mapped_column(LargeBinary)
    final_pdf_sha256: Mapped[str | None] = mapped_column(String(64))
    final_pdf_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    edit_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reopened_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reopen_ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "operational_tickets.id",
            ondelete="RESTRICT",
            name="fk_lab_work_orders_reopen_ticket_id",
            use_alter=True,
        ),
        nullable=True,
        index=True,
    )
    signature_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    signature_preserved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    equipment: Mapped[list["LabWorkOrderEquipment"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="LabWorkOrderEquipment.position",
    )
    signature_session: Mapped["LabWorkOrderSignatureSession | None"] = relationship(
        back_populates="work_orders",
        foreign_keys=[signature_session_id],
    )
    revisions: Mapped[list["LabWorkOrderRevision"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="LabWorkOrderRevision.revision_number",
    )
    client: Mapped["Client | None"] = relationship()


class LabWorkOrderEquipment(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "lab_work_order_equipment"
    __table_args__ = (
        CheckConstraint("position BETWEEN 1 AND 10", name="ck_lab_equipment_position"),
        UniqueConstraint("work_order_id", "position", name="uq_lab_equipment_position"),
    )

    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("lab_work_orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    instrument: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str] = mapped_column(String(160), nullable=False)
    identification: Mapped[str] = mapped_column(String(160), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(160), nullable=False)
    report_number: Mapped[str | None] = mapped_column(String(160))
    is_good_condition: Mapped[bool] = mapped_column(Boolean, nullable=False)

    work_order: Mapped[LabWorkOrder] = relationship(back_populates="equipment")

    @property
    def name(self) -> str:
        return self.instrument

    @property
    def internal_id(self) -> str:
        return self.identification

    @property
    def certificates(self) -> list[object]:
        return []


class LabWorkOrderSignatureSession(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "lab_work_order_signature_sessions"
    __table_args__ = (
        UniqueConstraint(
            "root_work_order_id", "version", name="uq_lab_signature_session_root_version"
        ),
    )

    root_work_order_id: Mapped[int] = mapped_column(
        ForeignKey("lab_work_orders.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    signed_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    signatures: Mapped[list["LabWorkOrderSignature"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    work_orders: Mapped[list[LabWorkOrder]] = relationship(
        back_populates="signature_session", foreign_keys=[LabWorkOrder.signature_session_id]
    )


class LabWorkOrderSignature(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "lab_work_order_signatures"
    __table_args__ = (
        CheckConstraint(
            "signature_type IN ('technician', 'client')",
            name="ck_lab_signature_type",
        ),
        UniqueConstraint("signature_session_id", "signature_type", name="uq_lab_signature_type"),
    )

    signature_session_id: Mapped[int] = mapped_column(
        ForeignKey("lab_work_order_signature_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    signature_type: Mapped[str] = mapped_column(String(20), nullable=False)
    signer_name: Mapped[str] = mapped_column(String(180), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    signature_data_url: Mapped[str] = mapped_column(Text, nullable=False)

    session: Mapped[LabWorkOrderSignatureSession] = relationship(back_populates="signatures")


from app.models.lab_work_order_revision import LabWorkOrderRevision  # noqa: E402
from app.models.client import Client  # noqa: E402
