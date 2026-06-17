from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class Certificate(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "certificates"

    folio: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    service_order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id"), index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), index=True)
    field_sheet_id: Mapped[int] = mapped_column(ForeignKey("field_sheets.id"), index=True)
    certificate_type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(60), default="draft", index=True)
    issued_on: Mapped[date | None] = mapped_column(Date)
    released_on: Mapped[date | None] = mapped_column(Date)
    title: Mapped[str | None] = mapped_column(String(180))
    notes: Mapped[str | None] = mapped_column(Text)

    service_order: Mapped["ServiceOrder"] = relationship(back_populates="certificates")
    equipment: Mapped["Equipment"] = relationship(back_populates="certificates")
    field_sheet: Mapped["FieldSheet"] = relationship(back_populates="certificates")
