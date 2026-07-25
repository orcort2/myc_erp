"""Tipos SQL compartidos por el modelo persistente del Motor."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

BIGINT_ID = BigInteger().with_variant(Integer, "sqlite")
JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")


class ResolutionRecordMixin:
    """Identidad técnica común, sin semántica de folio institucional."""

    id: Mapped[int] = mapped_column(
        BIGINT_ID,
        primary_key=True,
        autoincrement=True,
    )


class CreatedAtMixin:
    """Marca temporal para registros append-only."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class MutableTimestampMixin(CreatedAtMixin):
    """Marcas temporales para registros cuyo estado puede avanzar."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
