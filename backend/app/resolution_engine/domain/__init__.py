"""Tipos de dominio puros del Motor de Resoluciones hasta Fase 4."""

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

__all__ = [
    "ComponentKey",
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
    "ActorIdentity",
    "ActorStatus",
    "ActorType",
    "AuthenticationContext",
    "PermissionGrant",
    "PolicyResult",
    "SecurityDecision",
    "SecurityDecisionOutcome",
    "SecurityRequest",
    "SecurityResource",
]
