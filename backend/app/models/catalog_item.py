from decimal import Decimal

from sqlalchemy import Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class CatalogItem(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "catalog_items"

    item_type: Mapped[str] = mapped_column(String(20), index=True)
    commodity: Mapped[str] = mapped_column(String(40), index=True)
    category: Mapped[str] = mapped_column(String(120), index=True)
    internal_key: Mapped[str | None] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    sat_key: Mapped[str | None] = mapped_column(String(40))
    sat_unit: Mapped[str | None] = mapped_column(String(40))
    internal_unit: Mapped[str | None] = mapped_column(String(80))
    custom_internal_unit: Mapped[str | None] = mapped_column(String(80))
    origin_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    origin_currency: Mapped[str] = mapped_column(String(3))
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=1)
    margin_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    final_price_mxn: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    internal_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    cost_currency: Mapped[str | None] = mapped_column(String(3))
    calibration_scope: Mapped[str | None] = mapped_column(String(60))
    quotation_legend: Mapped[str | None] = mapped_column(Text)
    tax_object: Mapped[str] = mapped_column(String(20), default="iva_16", index=True)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=16)
