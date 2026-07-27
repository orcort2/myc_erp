"""Tipos de dominio puros del Motor de Resoluciones hasta Fase 6."""

from app.resolution_engine.domain.definitions import (
    ComponentReference,
    ResolutionDefinition,
)
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
    ResolutionType,
)
from app.resolution_engine.domain.security import (
    ActorContext,
    ActorIdentity,
    ActorStatus,
    ActorType,
    AuthenticationContext,
    PermissionGrant,
    PolicyResult,
    SecurityDecision,
    SecurityDecisionOutcome,
    SecurityRequest,
    SecurityResource,
)
from app.resolution_engine.domain.lifecycle import (
    LifecycleAction,
    LifecycleEvidence,
    LifecycleTransition,
    ResolutionLifecycle,
    ResolutionStateMachine,
)
from app.resolution_engine.domain.execution import (
    ActionCertainty,
    DomainActionRequest,
    DomainActionResult,
    ExecutionCandidate,
    ExecutionEngine,
    ExecutionEntityEffect,
    ExecutionOutcome,
    ExecutionPlanStep,
)
from app.resolution_engine.domain.compensation import (
    CompensableAction,
    CompensationActionRequest,
    CompensationEngine,
    CompensationOutcome,
    CompensationPlan,
    CompensationPlanStep,
    CompensationSource,
)

__all__ = [
    "ComponentKey",
    "CompensableAction",
    "CompensationActionRequest",
    "CompensationEngine",
    "CompensationOutcome",
    "CompensationPlan",
    "CompensationPlanStep",
    "CompensationSource",
    "ComponentReference",
    "DefinitionVersion",
    "LifecycleAction",
    "LifecycleEvidence",
    "LifecycleTransition",
    "ResolutionDefinition",
    "ResolutionLifecycle",
    "ResolutionStateMachine",
    "ResolutionType",
    "ActorContext",
    "ActionCertainty",
    "ActorIdentity",
    "ActorStatus",
    "ActorType",
    "AuthenticationContext",
    "DomainActionRequest",
    "DomainActionResult",
    "ExecutionCandidate",
    "ExecutionEngine",
    "ExecutionEntityEffect",
    "ExecutionOutcome",
    "ExecutionPlanStep",
    "PermissionGrant",
    "PolicyResult",
    "SecurityDecision",
    "SecurityDecisionOutcome",
    "SecurityRequest",
    "SecurityResource",
]
