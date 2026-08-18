from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class ServiceOrder(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "service_orders"
    __table_args__ = {"sqlite_autoincrement": True}

    folio: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        index=True,
    )

    # Legacy / compatibilidad:
    # Se conserva como OT principal para no romper pantallas, PDFs o datos previos.
    # La operación nueva usará ServiceWorkOrder.
    work_order_number: Mapped[int] = mapped_column(
        unique=True,
        index=True,
    )

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id"),
        index=True,
    )

    quotation_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotations.id"),
        index=True,
    )

    advisor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    technician_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(60),
        default="scheduled",
        index=True,
    )

    agenda_date: Mapped[date | None] = mapped_column(Date)

    service_date: Mapped[date | None] = mapped_column(Date)

    closed_at: Mapped[date | None] = mapped_column(Date)

    total_equipment: Mapped[int] = mapped_column(
        default=0,
    )

    completed_equipment: Mapped[int] = mapped_column(
        default=0,
    )

    requires_payment: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(Text)

    source_snapshot: Mapped[dict | None] = mapped_column(JSON)

    technician_signature_data_url: Mapped[str | None] = mapped_column(Text)

    client_received_signature_data_url: Mapped[str | None] = mapped_column(Text)

    client_acceptance_signature_data_url: Mapped[str | None] = mapped_column(Text)

    technician_signed_name: Mapped[str | None] = mapped_column(
        String(180),
    )

    client_received_signed_name: Mapped[str | None] = mapped_column(
        String(180),
    )

    client_acceptance_signed_name: Mapped[str | None] = mapped_column(
        String(180),
    )

    technician_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    client_received_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    client_acceptance_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    signature_status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        server_default="pending",
        nullable=False,
        index=True,
    )

    signature_cycle_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )

    signatures_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    signature_reopen_available: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    signature_reopened_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    signature_reopened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    signature_reopen_source: Mapped[str | None] = mapped_column(
        String(50),
    )

    client: Mapped["Client"] = relationship(
        back_populates="service_orders",
    )

    quotation: Mapped["Quotation | None"] = relationship(
        back_populates="service_orders",
    )

    advisor: Mapped["User | None"] = relationship(
        foreign_keys=[advisor_id],
    )

    technician: Mapped["User | None"] = relationship(
        foreign_keys=[technician_id],
    )

    signature_reopened_by: Mapped["User | None"] = relationship(
        foreign_keys=[signature_reopened_by_id],
    )

    items: Mapped[list["ServiceOrderItem"]] = relationship(
        back_populates="service_order",
        cascade="all, delete-orphan",
    )

    work_orders: Mapped[list["ServiceWorkOrder"]] = relationship(
        back_populates="service_order",
        cascade="all, delete-orphan",
        order_by="ServiceWorkOrder.sequence.asc()",
    )

    signature_cycles: Mapped[list["ServiceOrderSignatureCycle"]] = relationship(
        back_populates="service_order",
        cascade="all, delete-orphan",
        order_by="ServiceOrderSignatureCycle.cycle_number.asc()",
    )

    equipment: Mapped[list["Equipment"]] = relationship(
        back_populates="service_order",
    )

    certificates: Mapped[list["Certificate"]] = relationship(
        back_populates="service_order",
    )

    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="service_order",
    )

    exception_requests: Mapped[list["ServiceOrderExceptionRequest"]] = relationship(
        back_populates="service_order",
        cascade="all, delete-orphan",
        order_by="ServiceOrderExceptionRequest.id.asc()",
    )

    service_units: Mapped[list["ServiceUnit"]] = relationship(
        back_populates="service_order",
        order_by="ServiceUnit.id.asc()",
    )

    @property
    def advisor_name(self) -> str | None:
        if self.advisor is None:
            return None
        return self.advisor.full_name or self.advisor.email

    @property
    def technician_name(self) -> str | None:
        if self.technician is None:
            return None
        return self.technician.full_name or self.technician.email

    @property
    def has_pending_signature_work_orders(self) -> bool:
        active_work_orders = [
            work_order
            for work_order in self.work_orders
            if work_order.is_active and work_order.status != "cancelled"
        ]

        return any(
            not any(link.is_current for link in work_order.signature_cycle_links)
            for work_order in active_work_orders
        )


class ServiceOrderSignatureCycle(
    IntegerPkMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "service_order_signature_cycles"

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id"),
        index=True,
        nullable=False,
    )

    cycle_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    trigger: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="initial",
        server_default="initial",
    )

    comment: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="confirmed",
        server_default="confirmed",
        index=True,
    )

    technician_signature_data_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    client_received_signature_data_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    client_acceptance_signature_data_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    technician_signed_name: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    client_received_signed_name: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    client_acceptance_signed_name: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    technician_signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    client_received_signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    client_acceptance_signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    authorized_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    work_order_links: Mapped[
        list["ServiceOrderSignatureCycleWorkOrder"]
    ] = relationship(
        back_populates="signature_cycle",
        cascade="all, delete-orphan",
        order_by="ServiceOrderSignatureCycleWorkOrder.id.asc()",
    )

    authorization_comment: Mapped[str | None] = mapped_column(Text)

    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    service_order: Mapped["ServiceOrder"] = relationship(
        back_populates="signature_cycles",
    )

    authorized_by: Mapped["User | None"] = relationship(
        foreign_keys=[authorized_by_id],
    )


class ServiceWorkOrder(
    IntegerPkMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "service_work_orders"
    __table_args__ = (
        Index(
            "ix_service_work_orders_work_order_number",
            "work_order_number",
        ),
    )

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id"),
        index=True,
    )

    work_order_number: Mapped[int] = mapped_column(
        unique=True,
    )

    sequence: Mapped[int] = mapped_column(
        Integer,
        default=1,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(60),
        default="pending",
        index=True,
    )

    equipment_limit: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(Text)

    service_order: Mapped["ServiceOrder"] = relationship(
        back_populates="work_orders",
    )

    equipment: Mapped[list["Equipment"]] = relationship(
        back_populates="work_order",
        order_by="Equipment.id.asc()",
    )

    service_units: Mapped[list["ServiceUnit"]] = relationship(
        back_populates="work_order",
        order_by="ServiceUnit.id.asc()",
    )

    signature_cycle_links: Mapped[
        list["ServiceOrderSignatureCycleWorkOrder"]
    ] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="ServiceOrderSignatureCycleWorkOrder.id.asc()",
    )

    @property
    def active_equipment_count(self) -> int:
        return len(
            [
                item
                for item in self.equipment
                if item.is_active
            ]
        )

    @property
    def available_equipment_slots(self) -> int:
        return max(
            self.equipment_limit - self.active_equipment_count,
            0,
        )


class ServiceOrderSignatureCycleWorkOrder(
    IntegerPkMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "service_order_signature_cycle_work_orders"

    __table_args__ = (
        UniqueConstraint(
            "signature_cycle_id",
            "work_order_id",
            name="uq_signature_cycle_work_order",
        ),
    )

    signature_cycle_id: Mapped[int] = mapped_column(
        ForeignKey("service_order_signature_cycles.id"),
        index=True,
        nullable=False,
    )

    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_work_orders.id"),
        index=True,
        nullable=False,
    )

    assignment_type: Mapped[str] = mapped_column(
        String(50),
        default="initial",
        server_default="initial",
        nullable=False,
        index=True,
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        index=True,
    )

    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    signature_cycle: Mapped["ServiceOrderSignatureCycle"] = relationship(
        back_populates="work_order_links",
    )

    work_order: Mapped["ServiceWorkOrder"] = relationship(
        back_populates="signature_cycle_links",
    )


class ServiceOrderItem(
    IntegerPkMixin,
    TimestampMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "service_order_items"

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id"),
        index=True,
    )

    quotation_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotation_items.id"),
    )

    catalog_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_items.id"),
        index=True,
    )

    expected_certificate_master_id: Mapped[int | None] = mapped_column(
        ForeignKey("controlled_documents.id"),
        index=True,
    )

    service_name: Mapped[str] = mapped_column(
        String(180),
    )

    # Identidad operacional heredada de la partida aprobada.
    #
    # Debe provenir de la cotización/snapshot congelado y no inferirse
    # nuevamente desde item_type, commodity, nombre o catálogo vigente.
    operational_category: Mapped[str | None] = mapped_column(
        String(40),
        index=True,
    )

    calibration_scope: Mapped[str | None] = mapped_column(
        String(60),
    )

    service_snapshot: Mapped[dict | None] = mapped_column(
        JSON,
    )

    quantity: Mapped[int] = mapped_column(
        default=1,
    )

    status: Mapped[str] = mapped_column(
        String(60),
        default="pending",
    )

    service_order: Mapped[ServiceOrder] = relationship(
        back_populates="items",
    )