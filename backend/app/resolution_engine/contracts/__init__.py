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

__all__ = [
    "ActorContextProvider",
    "Analyzer",
    "AuthorizationPolicy",
    "Clock",
    "ComponentResolver",
    "ContextProvider",
    "CreateResolutionCommand",
    "Executor",
    "IdentifierFactory",
    "LifecycleStore",
    "PermissionPolicy",
    "PlanBuilder",
    "ResolutionComponent",
    "ResolutionProblemInput",
    "Revalidator",
    "SecurityEvidenceStore",
    "SecurityResourceVerifier",
    "Simulator",
    "StrategySelector",
]
