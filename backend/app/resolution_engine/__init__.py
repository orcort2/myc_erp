"""API pública del núcleo del Motor de Resoluciones hasta Fase 5."""

from app.resolution_engine.application.action_runner import ActionRunner
from app.resolution_engine.application.execution import ResolutionExecutor
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
from app.resolution_engine.contracts.execution import ExecuteResolutionCommand
from app.resolution_engine.domain.execution import (
    DomainActionRequest,
    DomainActionResult,
    ExecutionOutcome,
)

__all__ = [
    "ComponentKey",
    "ActionRunner",
    "ComponentReference",
    "DefinitionVersion",
    "LifecycleAction",
    "LifecycleActor",
    "DomainActionRequest",
    "DomainActionResult",
    "ExecuteResolutionCommand",
    "ExecutionOutcome",
    "ResolutionDefinition",
    "ResolutionExecutor",
    "ResolutionLifecycleService",
    "ResolutionOrchestrator",
    "ResolutionRegistry",
    "ResolutionStateMachine",
    "ResolutionType",
]
