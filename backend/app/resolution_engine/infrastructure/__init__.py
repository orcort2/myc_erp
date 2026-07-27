"""Adaptadores de persistencia y runtime autorizados hasta Fase 5."""

from app.resolution_engine.infrastructure.execution import (
    SqlAlchemyExecutionStore,
)
from app.resolution_engine.infrastructure.execution_control import (
    SqlAlchemyExecutionControl,
)
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
from app.resolution_engine.infrastructure.outbox import (
    SqlAlchemyOutboxStore,
)

__all__ = [
    "ResolutionRecord",
    "ResolutionRepository",
    "SqlAlchemyExecutionControl",
    "SqlAlchemyExecutionStore",
    "SqlAlchemyLifecycleStore",
    "SqlAlchemyOutboxStore",
    "SystemClock",
    "UuidIdentifierFactory",
]
