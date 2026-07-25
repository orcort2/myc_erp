"""Adaptadores mínimos autorizados en la Fase 1."""

from app.resolution_engine.infrastructure.runtime import (
    SystemClock,
    UuidIdentifierFactory,
)
from app.resolution_engine.infrastructure.repositories import (
    ResolutionRecord,
    ResolutionRepository,
)

__all__ = [
    "ResolutionRecord",
    "ResolutionRepository",
    "SystemClock",
    "UuidIdentifierFactory",
]
