"""Contratos tipados y libres de infraestructura del Motor."""

from app.resolution_engine.contracts.components import (
    Analyzer,
    AuthorizationPolicy,
    ContextProvider,
    Executor,
    PermissionPolicy,
    PlanBuilder,
    ResolutionComponent,
    Revalidator,
    Simulator,
    StrategySelector,
)
from app.resolution_engine.contracts.runtime import Clock, IdentifierFactory
from app.resolution_engine.contracts.lifecycle import (
    ComponentResolver,
    CreateResolutionCommand,
    LifecycleStore,
    ResolutionProblemInput,
)
from app.resolution_engine.contracts.security import (
    ActorContextProvider,
    SecurityEvidenceStore,
    SecurityResourceVerifier,
)
from app.resolution_engine.contracts.execution import (
    ActionHandler,
    EventPublisher,
    ExecuteResolutionCommand,
    ExecutionStore,
    OutboxStore,
)
from app.resolution_engine.contracts.compensation import (
    CompensationHandler,
    CompensationStore,
    ExecuteCompensationCommand,
    PrepareCompensationCommand,
)

__all__ = [
    "ActorContextProvider",
    "ActionHandler",
    "Analyzer",
    "AuthorizationPolicy",
    "Clock",
    "CompensationHandler",
    "CompensationStore",
    "ComponentResolver",
    "ContextProvider",
    "CreateResolutionCommand",
    "Executor",
    "EventPublisher",
    "ExecuteResolutionCommand",
    "ExecuteCompensationCommand",
    "ExecutionStore",
    "IdentifierFactory",
    "LifecycleStore",
    "PermissionPolicy",
    "OutboxStore",
    "PlanBuilder",
    "PrepareCompensationCommand",
    "ResolutionComponent",
    "ResolutionProblemInput",
    "Revalidator",
    "SecurityEvidenceStore",
    "SecurityResourceVerifier",
    "Simulator",
    "StrategySelector",
]
