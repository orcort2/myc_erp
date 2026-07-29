from sqlalchemy import CheckConstraint, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class InstitutionalFolioSequence(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "institutional_folio_sequences"
    __table_args__ = (
        UniqueConstraint(
            "document_type",
            "prefix",
            "year",
            name="uq_institutional_folio_sequence_scope",
        ),
        CheckConstraint("next_value >= 0", name="ck_institutional_folio_next_value"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    next_value: Mapped[int] = mapped_column(Integer, nullable=False)
