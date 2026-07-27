"""Adaptadores de persistencia y runtime autorizados hasta Fase 4."""

from app.resolution_engine.infrastructure.lifecycle import (
    SqlAlchemyLifecycleStore,
)
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
    "SqlAlchemyLifecycleStore",
    "SystemClock",
    "UuidIdentifierFactory",
]
