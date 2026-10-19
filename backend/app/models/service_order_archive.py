"""Archivo histórico recuperable de ETS eliminadas por un desbloqueo autorizado.

No es una ETS activa: no hay FK hacia ``service_orders`` (la fila original deja de
existir) y ningún flujo operativo lee esta tabla. Sólo guarda evidencia.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin

ARCHIVE_SCHEMA_VERSION = 1


class ServiceOrderArchive(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "service_order_archives"
    __table_args__ = (
        UniqueConstraint("exception_request_id", name="uq_service_order_archives_exception"),
    )

    original_service_order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    service_order_folio: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    quotation_id: Mapped[int] = mapped_column(
        ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quotation_folio: Mapped[str] = mapped_column(String(40), nullable=False)
    accepted_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotation_snapshots.id", ondelete="RESTRICT"), index=True
    )
    accepted_snapshot_number: Mapped[int | None] = mapped_column(Integer)
    acceptance_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotation_acceptances.id", ondelete="RESTRICT"), index=True
    )
    previous_status: Mapped[str] = mapped_column(String(60), nullable=False)
    source_snapshot: Mapped[dict | None] = mapped_column(JSON)
    archive_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    exception_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotation_service_change_requests.id", ondelete="RESTRICT"), index=True
    )
    exception_folio: Mapped[str | None] = mapped_column(String(40), index=True)
    deleted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=ARCHIVE_SCHEMA_VERSION
    )
    integrity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
