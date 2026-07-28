from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IntegerPkMixin


JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")


class CertificateResolutionOperation(IntegerPkMixin, Base):
    """Evidencia append-only de una mutación solicitada por el Motor."""

    __tablename__ = "certificate_resolution_operations"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_certificate_resolution_operations_idempotency",
        ),
        CheckConstraint(
            "length(request_hash) = 64",
            name="ck_certificate_resolution_operations_request_hash",
        ),
        Index(
            "ix_certificate_resolution_operations_certificate_action",
            "certificate_id",
            "operation_key",
        ),
    )

    certificate_id: Mapped[int] = mapped_column(
        ForeignKey("certificates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_operation_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "certificate_resolution_operations.id",
            ondelete="RESTRICT",
        ),
        index=True,
    )
    operation_key: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(160), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(120), nullable=False)
    request_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT,
        nullable=False,
    )
    before_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT,
        nullable=False,
    )
    after_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT,
        nullable=False,
    )
    result_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_DOCUMENT,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
