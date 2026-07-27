"""API pública del núcleo del Motor de Resoluciones hasta Fase 4."""

from app.resolution_engine.application.lifecycle import (
    LifecycleActor,
    ResolutionLifecycleService,
)
from app.resolution_engine.application.orchestration import (
    ResolutionOrchestrator,
)
from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.domain.definitions import (
    ComponentReference,
    ResolutionDefinition,
)
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
    ResolutionType,
)
from app.resolution_engine.domain.lifecycle import (
    LifecycleAction,
    ResolutionStateMachine,
)

__all__ = [
    "ComponentKey",
    "ComponentReference",
    "DefinitionVersion",
    "LifecycleAction",
    "LifecycleActor",
    "ResolutionDefinition",
    "ResolutionLifecycleService",
    "ResolutionOrchestrator",
    "ResolutionRegistry",
    "ResolutionStateMachine",
    "ResolutionType",
]
