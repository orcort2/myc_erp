from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class QuotationServiceChangeRequest(TimestampMixin, Base):
    """Expediente y capacidad de un solo uso para corregir un servicio aprobado."""

    __tablename__ = "quotation_service_change_requests"
    __table_args__ = (
        UniqueConstraint("folio", name="uq_quotation_service_change_folio"),
        UniqueConstraint("active_scope_key", name="uq_quotation_service_change_active_scope"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folio: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    quotation_id: Mapped[int] = mapped_column(
        ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quotation_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotation_items.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    current_catalog_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    requested_catalog_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_items.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    requester_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    authorized_apply_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    applied_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotation_snapshots.id", ondelete="RESTRICT"), index=True
    )
    result_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotation_snapshots.id", ondelete="RESTRICT"), index=True
    )

    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="pending_review", index=True
    )
    capability: Mapped[str] = mapped_column(
        String(80), nullable=False, default="quotation.change_service_type"
    )
    active_scope_key: Mapped[str | None] = mapped_column(String(240), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    observation: Mapped[str | None] = mapped_column(Text)
    review_comment: Mapped[str | None] = mapped_column(Text)
    block_reason: Mapped[str | None] = mapped_column(Text)
    current_service_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    requested_service_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    impact_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    service_order_folio_snapshot: Mapped[str | None] = mapped_column(String(40))
    base_quotation_snapshot: Mapped[dict | None] = mapped_column(JSON)
    delta_snapshot: Mapped[dict | None] = mapped_column(JSON)
    rebuild_audit_snapshot: Mapped[dict | None] = mapped_column(JSON)
    quotation_version_at_request: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    quotation: Mapped["Quotation"] = relationship(foreign_keys=[quotation_id])
    service_order: Mapped["ServiceOrder"] = relationship(foreign_keys=[service_order_id])
    quotation_item: Mapped["QuotationItem"] = relationship(foreign_keys=[quotation_item_id])
    current_catalog_item: Mapped["CatalogItem"] = relationship(
        foreign_keys=[current_catalog_item_id]
    )
    requested_catalog_item: Mapped["CatalogItem"] = relationship(
        foreign_keys=[requested_catalog_item_id]
    )
    requester: Mapped["User"] = relationship(foreign_keys=[requester_id])
    reviewer: Mapped["User | None"] = relationship(foreign_keys=[reviewer_id])
    authorized_apply_user: Mapped["User | None"] = relationship(
        foreign_keys=[authorized_apply_user_id]
    )
    applied_by: Mapped["User | None"] = relationship(foreign_keys=[applied_by_id])
    snapshot: Mapped["QuotationSnapshot | None"] = relationship(foreign_keys=[snapshot_id])
    result_snapshot: Mapped["QuotationSnapshot | None"] = relationship(
        foreign_keys=[result_snapshot_id]
    )
