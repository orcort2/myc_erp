"""Tipos de dominio puros de la Fase 1 del Motor de Resoluciones."""

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

__all__ = [
    "ComponentKey",
    "ComponentReference",
    "DefinitionVersion",
    "ResolutionDefinition",
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
