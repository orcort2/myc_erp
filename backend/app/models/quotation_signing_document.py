"""Frozen quotation PDF and revocable customer access capabilities."""
from datetime import datetime

from sqlalchemy import (
    DateTime, ForeignKey, Index, Integer, LargeBinary,
    String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin


class QuotationSigningDocument(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "quotation_signing_documents"
    __table_args__ = (
        UniqueConstraint(
            "quotation_id", "snapshot_id",
            name="uq_quotation_signing_document_version",
        ),
    )

    quotation_id: Mapped[int] = mapped_column(
        ForeignKey("quotations.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("quotation_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    pdf_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    pdf_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class QuotationSigningLink(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "quotation_signing_links"
    __table_args__ = (
        Index("ix_quotation_signing_links_document", "document_id"),
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey("quotation_signing_documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    token_id_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False,
    )
    recipient_email: Mapped[str] = mapped_column(
        String(254), nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_deliveries.id", ondelete="RESTRICT"), nullable=True, index=True,
    )
