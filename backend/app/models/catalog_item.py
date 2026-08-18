from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class CatalogItem(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "catalog_items"
    __table_args__ = (
        CheckConstraint(
            "service_kind IN ('simple', 'composite')",
            name="ck_catalog_items_service_kind",
        ),
        CheckConstraint(
            "service_type IS NULL OR service_type IN ('accredited', 'traceable', 'linked')",
            name="ck_catalog_items_service_type",
        ),
    )

    item_type: Mapped[str] = mapped_column(String(20), index=True)
    service_kind: Mapped[str] = mapped_column(
        String(20), default="simple", server_default="simple", nullable=False, index=True
    )
    commodity: Mapped[str] = mapped_column(String(40), index=True)
    category: Mapped[str] = mapped_column(String(120), index=True)
    operational_category: Mapped[str | None] = mapped_column(String(40), index=True)
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
    service_type: Mapped[str | None] = mapped_column(String(20), index=True)
    linked_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("linked_companies.id"), index=True
    )
    linked_certificate_prefix: Mapped[str | None] = mapped_column(String(12))
    # Sólo aplica a servicios de calibración. El equipo congela la versión activa
    # al momento de crearse, por lo que este vínculo nunca se consulta para
    # reconstruir entregables históricos.
    expected_certificate_master_id: Mapped[int | None] = mapped_column(
        ForeignKey("controlled_documents.id"), index=True
    )
    quotation_legend: Mapped[str | None] = mapped_column(Text)
    tax_object: Mapped[str] = mapped_column(String(20), default="iva_16", index=True)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=16)

    components: Mapped[list["CatalogItemComponent"]] = relationship(
        back_populates="parent_item",
        foreign_keys="CatalogItemComponent.parent_catalog_item_id",
        cascade="all, delete-orphan",
        order_by="CatalogItemComponent.id",
    )
    used_as_component_in: Mapped[list["CatalogItemComponent"]] = relationship(
        back_populates="component_item",
        foreign_keys="CatalogItemComponent.component_catalog_item_id",
    )
    linked_company: Mapped["LinkedCompany | None"] = relationship()


class CatalogItemComponent(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "catalog_item_components"
    __table_args__ = (
        UniqueConstraint(
            "parent_catalog_item_id",
            "component_catalog_item_id",
            name="uq_catalog_item_component_parent_child",
        ),
        CheckConstraint("quantity >= 1", name="ck_catalog_item_component_quantity_positive"),
        CheckConstraint(
            "parent_catalog_item_id <> component_catalog_item_id",
            name="ck_catalog_item_component_not_self",
        ),
    )

    parent_catalog_item_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component_catalog_item_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)

    parent_item: Mapped[CatalogItem] = relationship(
        back_populates="components", foreign_keys=[parent_catalog_item_id]
    )
    component_item: Mapped[CatalogItem] = relationship(
        back_populates="used_as_component_in", foreign_keys=[component_catalog_item_id]
    )

    @property
    def component_name(self) -> str:
        return self.component_item.name

    @property
    def component_internal_key(self) -> str | None:
        return self.component_item.internal_key

    @property
    def component_service_kind(self) -> str:
        return self.component_item.service_kind
