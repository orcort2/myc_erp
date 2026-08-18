from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from app.models.base import IntegerPkMixin, TimestampMixin


class SaleOrderItem(IntegerPkMixin, TimestampMixin, Base):
    """Proyección de Venta construida exclusivamente desde el snapshot cotizado."""

    __tablename__ = "sale_order_items"
    __table_args__ = (
        UniqueConstraint("service_order_item_id", name="uq_sale_order_items_service_order_item"),
        CheckConstraint("ordered_quantity > 0", name="ck_sale_order_items_ordered_quantity"),
        CheckConstraint(
            "arrived_quantity >= 0 AND delivered_quantity >= 0 AND resolved_quantity >= 0",
            name="ck_sale_order_items_nonnegative_quantities",
        ),
        Index("ix_sale_order_items_order_status", "service_order_id", "status"),
    )

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_order_item_id: Mapped[int] = mapped_column(
        ForeignKey("service_order_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    requires_individual_identification: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    included_calibration_catalog_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="RESTRICT"), index=True
    )
    frozen_configuration: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ordered_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    arrived_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    delivered_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    resolved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_arrival", index=True)

    service_order: Mapped["ServiceOrder"] = relationship()
    service_order_item: Mapped["ServiceOrderItem"] = relationship()
    units: Mapped[list["SaleUnitState"]] = relationship(
        back_populates="sale_order_item", cascade="all, delete-orphan", order_by="SaleUnitState.id"
    )


class SaleUnitState(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "sale_unit_states"
    __table_args__ = (
        UniqueConstraint("service_unit_id", name="uq_sale_unit_states_service_unit"),
        UniqueConstraint("equipment_id", name="uq_sale_unit_states_equipment"),
        UniqueConstraint("calibration_stage_id", name="uq_sale_unit_states_calibration_stage"),
        Index("ix_sale_unit_states_item_status", "sale_order_item_id", "status"),
    )

    sale_order_item_id: Mapped[int] = mapped_column(
        ForeignKey("sale_order_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_unit_id: Mapped[int] = mapped_column(
        ForeignKey("service_units.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), index=True
    )
    calibration_stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_stages.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_arrival", index=True)
    serial_number: Mapped[str | None] = mapped_column(String(120), index=True)
    brand: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    specification: Mapped[str | None] = mapped_column(Text)
    discrepancy_reason: Mapped[str | None] = mapped_column(Text)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    warranty_returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sale_order_item: Mapped[SaleOrderItem] = relationship(back_populates="units")
    service_unit: Mapped["ServiceUnit"] = relationship()
    equipment: Mapped["Equipment | None"] = relationship()
    calibration_stage: Mapped["ServiceStage | None"] = relationship(foreign_keys=[calibration_stage_id])


class SaleAuthorization(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "sale_authorizations"
    __table_args__ = (
        CheckConstraint(
            "authorization_type IN ('individual_identification','zero_cost_calibration','substitution')",
            name="ck_sale_authorizations_type",
        ),
        CheckConstraint(
            "status IN ('requested','authorized','rejected','consumed')",
            name="ck_sale_authorizations_status",
        ),
        Index("ix_sale_authorizations_order_status", "service_order_id", "status"),
    )

    service_order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id"), nullable=False, index=True)
    sale_order_item_id: Mapped[int | None] = mapped_column(ForeignKey("sale_order_items.id"), index=True)
    sale_unit_state_id: Mapped[int | None] = mapped_column(ForeignKey("sale_unit_states.id"), index=True)
    authorization_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="requested", index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    authorized_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    consumed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    resolution_comment: Mapped[str | None] = mapped_column(Text)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SaleDelivery(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "sale_deliveries"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('courier','client_pickup','myc_technician')",
            name="ck_sale_deliveries_mode",
        ),
        CheckConstraint(
            "status IN ('prepared','pickup_notified','technician_requested','technician_accepted',"
            "'scheduled','sent','delivery_reported','delivered','cancelled')",
            name="ck_sale_deliveries_status",
        ),
        Index("ix_sale_deliveries_order_status", "service_order_id", "status"),
    )

    service_order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id"), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="prepared", index=True)
    courier_name: Mapped[str | None] = mapped_column(String(120))
    tracking_number: Mapped[str | None] = mapped_column(String(160), index=True)
    shipped_on: Mapped[date | None] = mapped_column(Date)
    estimated_arrival_on: Mapped[date | None] = mapped_column(Date)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    address_source: Mapped[str | None] = mapped_column(String(30))
    delivery_address: Mapped[dict | None] = mapped_column(JSON)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    receiver_name: Mapped[str | None] = mapped_column(String(180))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    signature_data_url: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict | None] = mapped_column(JSON)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    confirmed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    lines: Mapped[list["SaleDeliveryLine"]] = relationship(
        back_populates="delivery", cascade="all, delete-orphan", order_by="SaleDeliveryLine.id"
    )


class SaleDeliveryLine(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "sale_delivery_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sale_delivery_lines_quantity"),
        UniqueConstraint("delivery_id", "sale_unit_state_id", name="uq_sale_delivery_unit"),
    )

    delivery_id: Mapped[int] = mapped_column(ForeignKey("sale_deliveries.id"), nullable=False, index=True)
    sale_order_item_id: Mapped[int] = mapped_column(ForeignKey("sale_order_items.id"), nullable=False, index=True)
    sale_unit_state_id: Mapped[int | None] = mapped_column(ForeignKey("sale_unit_states.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    delivery: Mapped[SaleDelivery] = relationship(back_populates="lines")
    sale_order_item: Mapped[SaleOrderItem] = relationship()
    sale_unit_state: Mapped["SaleUnitState | None"] = relationship()
