from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class FieldSheet(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "field_sheets"

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), index=True)
    status: Mapped[str] = mapped_column(String(60), default="draft", index=True)
    initial_condition: Mapped[str | None] = mapped_column(Text)
    final_condition: Mapped[str | None] = mapped_column(Text)
    pattern_used: Mapped[str | None] = mapped_column(String(180))
    results: Mapped[str | None] = mapped_column(Text)
    observations: Mapped[str | None] = mapped_column(Text)
    evidence_notes: Mapped[str | None] = mapped_column(Text)
    method: Mapped[str | None] = mapped_column(String(180))
    environmental_conditions: Mapped[str | None] = mapped_column(Text)
    technician_notes: Mapped[str | None] = mapped_column(Text)

    equipment: Mapped["Equipment"] = relationship(back_populates="field_sheets")
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="field_sheet")
