from sqlalchemy import JSON, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IntegerPkMixin, SoftDeleteMixin, TimestampMixin


class FieldSheetTemplateDefinition(IntegerPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "field_sheet_template_definitions"
    __table_args__ = (
        UniqueConstraint("template_key", "version", name="uq_field_sheet_template_key_version"),
    )

    template_key: Mapped[str] = mapped_column(String(60), index=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    definition_json: Mapped[dict] = mapped_column(JSON, nullable=False)
