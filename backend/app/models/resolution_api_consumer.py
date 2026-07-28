"""Credenciales institucionales de consumidores de la API del Motor."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IntegerPkMixin, TimestampMixin
from app.resolution_engine.infrastructure.persistence.base import JSON_DOCUMENT


class ResolutionApiConsumer(IntegerPkMixin, TimestampMixin, Base):
    __tablename__ = "resolution_api_consumers"

    consumer_key: Mapped[str] = mapped_column(
        String(80), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    organization_id: Mapped[str] = mapped_column(
        String(160), index=True, nullable=False
    )
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    permissions: Mapped[list[Any]] = mapped_column(
        JSON_DOCUMENT, server_default=text("'[]'"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
