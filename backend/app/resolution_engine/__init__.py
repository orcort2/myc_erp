"""Superficie interna estable del Motor de Resoluciones hasta Fase 11."""

from app.resolution_engine.application.action_runner import ActionRunner
from app.resolution_engine.application.execution import ResolutionExecutor
from app.resolution_engine.application.compensation import (
    CompensationExecutor,
    CompensationPlanner,
)
from app.resolution_engine.application.compensation_runner import (
    CompensationRunner,
)
from app.resolution_engine.application.distribution import (
    CompensationExecutionWorkHandler,
    DistributedDispatcher,
    DistributedRecoveryService,
    DistributedWorker,
    ResolutionExecutionWorkHandler,
)
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
from app.resolution_engine.contracts.execution import (
    ExecuteResolutionCommand,
    PublishOutboxCommand,
)
from app.resolution_engine.contracts.compensation import (
    ExecuteCompensationCommand,
    PrepareCompensationCommand,
)
from app.resolution_engine.domain.compensation import (
    CompensationEngine,
    CompensationOutcome,
)
from app.resolution_engine.domain.execution import (
    DomainActionRequest,
    DomainActionResult,
    ExecutionOutcome,
)
from app.resolution_engine.domain.distribution import (
    DeterministicRetryPolicy,
    DistributedWorkKind,
    DistributedWorkRequest,
    DistributedWorkResult,
)

__all__ = [
    "ComponentKey",
    "ActionRunner",
    "ComponentReference",
    "CompensationEngine",
    "CompensationExecutionWorkHandler",
    "CompensationExecutor",
    "CompensationOutcome",
    "CompensationPlanner",
    "CompensationRunner",
    "DefinitionVersion",
    "DeterministicRetryPolicy",
    "DistributedDispatcher",
    "DistributedRecoveryService",
    "DistributedWorker",
    "DistributedWorkKind",
    "DistributedWorkRequest",
    "DistributedWorkResult",
    "LifecycleAction",
    "LifecycleActor",
    "DomainActionRequest",
    "DomainActionResult",
    "ExecuteResolutionCommand",
    "ExecuteCompensationCommand",
    "ExecutionOutcome",
    "ResolutionDefinition",
    "ResolutionExecutionWorkHandler",
    "ResolutionExecutor",
    "ResolutionLifecycleService",
    "ResolutionOrchestrator",
    "ResolutionRegistry",
    "ResolutionStateMachine",
    "ResolutionType",
    "PrepareCompensationCommand",
    "PublishOutboxCommand",
]
