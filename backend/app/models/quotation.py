from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class Quotation(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "quotations"

    folio: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    advisor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    issued_on: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    payment_terms: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    client: Mapped["Client"] = relationship(back_populates="quotations")
    advisor: Mapped["User | None"] = relationship(foreign_keys=[advisor_id])
    items: Mapped[list["QuotationItem"]] = relationship(
        back_populates="quotation", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["QuotationSnapshot"]] = relationship(
        back_populates="quotation", cascade="all, delete-orphan"
    )
    service_orders: Mapped[list["ServiceOrder"]] = relationship(back_populates="quotation")

    @property
    def advisor_name(self) -> str | None:
        if self.advisor is None or not self.advisor.is_active:
            return None
        return self.advisor.full_name or self.advisor.email


class QuotationItem(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "quotation_items"

    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), index=True)
    catalog_item_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_items.id"), index=True)
    service_name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(default=1)
    unit: Mapped[str | None] = mapped_column(String(80))
    sat_key: Mapped[str | None] = mapped_column(String(40))
    sat_unit: Mapped[str | None] = mapped_column(String(40))
    internal_unit: Mapped[str | None] = mapped_column(String(80))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    currency: Mapped[str | None] = mapped_column(String(3))
    commodity: Mapped[str | None] = mapped_column(String(40))
    calibration_scope: Mapped[str | None] = mapped_column(String(60))
    quotation_legend: Mapped[str | None] = mapped_column(Text)
    operational_snapshot: Mapped[dict | None] = mapped_column(JSON)
    source_service_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_orders.id", ondelete="RESTRICT"), index=True
    )
    source_service_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_units.id", ondelete="RESTRICT"), index=True
    )
    source_stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_stages.id", ondelete="RESTRICT"), index=True
    )
    technical_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("technical_service_requests.id", ondelete="RESTRICT"), index=True
    )
    equipment_snapshot: Mapped[dict | None] = mapped_column(JSON)
    tax_object: Mapped[str | None] = mapped_column(String(20))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=16)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    quotation: Mapped[Quotation] = relationship(back_populates="items")
    decisions: Mapped[list["QuotationItemDecision"]] = relationship(
        back_populates="quotation_item",
        order_by="QuotationItemDecision.created_at.asc()",
    )


class QuotationItemDecision(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "quotation_item_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved','rejected')",
            name="ck_quotation_item_decisions_decision",
        ),
    )

    quotation_item_id: Mapped[int] = mapped_column(
        ForeignKey("quotation_items.id", ondelete="RESTRICT"), index=True
    )
    decision: Mapped[str] = mapped_column(String(20), index=True)
    decided_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(30), default="internal")
    comment: Mapped[str | None] = mapped_column(Text)
    enabled_stage_categories: Mapped[list] = mapped_column(JSON, default=list)

    quotation_item: Mapped[QuotationItem] = relationship(back_populates="decisions")


class QuotationSnapshot(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "quotation_snapshots"

    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"), index=True)
    snapshot_number: Mapped[int] = mapped_column(default=1)
    reason: Mapped[str | None] = mapped_column(String(80))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    snapshot_data: Mapped[dict] = mapped_column(JSON)

    quotation: Mapped[Quotation] = relationship(back_populates="snapshots")
    created_by: Mapped["User | None"] = relationship(foreign_keys=[created_by_id])
