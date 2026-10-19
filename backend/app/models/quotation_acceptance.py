"""Immutable quotation acceptance evidence with explicit operational invalidation."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, LargeBinary, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class QuotationAcceptance(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "quotation_acceptances"
    __table_args__ = (
        Index(
            "uq_quotation_acceptances_current",
            "quotation_id",
            unique=True,
            postgresql_where=text("invalidated_at IS NULL"),
            sqlite_where=__import__("sqlalchemy").text("invalidated_at IS NULL"),
        ),
    )

    # Folio institucional MYC-AC-AAAA-NNNNNN: único, inmutable y nunca reutilizado.
    confirmation_folio: Mapped[str | None] = mapped_column(String(24), unique=True, index=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id", ondelete="RESTRICT"), index=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("quotation_snapshots.id", ondelete="RESTRICT"))
    pdf_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    pdf_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    signer_name: Mapped[str] = mapped_column(String(180), nullable=False)
    signer_email: Mapped[str] = mapped_column(String(254), nullable=False)
    consent_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    invalidation_reason: Mapped[str | None] = mapped_column(String(100))
