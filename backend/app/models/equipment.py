from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class Equipment(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "equipment"

    service_order_id: Mapped[int] = mapped_column(
        ForeignKey("service_orders.id"),
        index=True,
    )

    work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_work_orders.id"),
        index=True,
    )

    service_order_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_order_items.id"),
        index=True,
    )

    calibration_scope: Mapped[str | None] = mapped_column(
        String(60),
        index=True,
    )
    certificate_master_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("controlled_documents.id"), index=True
    )
    certificate_master_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("controlled_document_versions.id"), index=True
    )
    certificate_template_path_snapshot: Mapped[str | None] = mapped_column(String(255))
    certificate_template_filename_snapshot: Mapped[str | None] = mapped_column(String(255))
    certificate_template_checksum_snapshot: Mapped[str | None] = mapped_column(String(128))
    certificate_template_effective_date_snapshot: Mapped[date | None] = mapped_column(Date)
    certificate_template_expires_on_snapshot: Mapped[date | None] = mapped_column(Date)

    status: Mapped[str] = mapped_column(
        String(60),
        default="registered",
        index=True,
    )

    name: Mapped[str] = mapped_column(String(180))
    brand: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    serial_number: Mapped[str | None] = mapped_column(
        String(120),
        index=True,
    )
    internal_id: Mapped[str | None] = mapped_column(
        String(120),
        index=True,
    )
    range_or_capacity: Mapped[str | None] = mapped_column(String(180))
    initial_condition: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    service_order: Mapped["ServiceOrder"] = relationship(
        back_populates="equipment"
    )

    work_order: Mapped["ServiceWorkOrder | None"] = relationship(
        back_populates="equipment"
    )

    field_sheets: Mapped[list["FieldSheet"]] = relationship(
        back_populates="equipment",
        cascade="all, delete-orphan",
    )

    certificates: Mapped[list["Certificate"]] = relationship(
        back_populates="equipment"
    )

    @property
    def work_order_number(self) -> int | None:
        if self.work_order is None:
            return None
        return self.work_order.work_order_number
