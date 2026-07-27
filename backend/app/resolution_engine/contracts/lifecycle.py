"""Puertos de persistencia y resolución de componentes del Lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from app.resolution_engine.domain.definitions import (
    ComponentReference,
    ResolutionDefinition,
)
from app.resolution_engine.domain.enums import ResolutionPriority, ResolutionSource
from app.resolution_engine.domain.lifecycle import (
    LifecycleTransition,
    ResolutionLifecycle,
)
from app.resolution_engine.domain.security import ActorContext


@dataclass(frozen=True, slots=True)
class ResolutionProblemInput:
    problem_code: str
    summary: str
    detected_by: str
    detected_at: datetime
    description: str | None = None
    source_payload: Mapping[str, Any] = field(default_factory=dict)
    external_reference: str | None = None
    severity: ResolutionPriority = ResolutionPriority.NORMAL
    observed_state: Mapping[str, Any] = field(default_factory=dict)
    evidence: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "severity",
            ResolutionPriority(self.severity),
        )
        object.__setattr__(
            self,
            "source_payload",
            MappingProxyType(dict(self.source_payload)),
        )
        object.__setattr__(
            self,
            "observed_state",
            MappingProxyType(dict(self.observed_state)),
        )
        object.__setattr__(self, "evidence", tuple(self.evidence))


@dataclass(frozen=True, slots=True)
class CreateResolutionCommand:
    resolution_type: str
    source: ResolutionSource
    subject_type: str
    subject_id: str
    title: str
    problem: ResolutionProblemInput
    actor: ActorContext
    security_decision_id: int
    definition_version: str | None = None
    priority: ResolutionPriority = ResolutionPriority.NORMAL
    description: str | None = None
    reason: str | None = None
    request_key: str | None = None
    parent_resolution_id: int | None = None
    requires_authorization: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.security_decision_id <= 0:
            raise ValueError("security_decision_id must be positive")
        object.__setattr__(self, "source", ResolutionSource(self.source))
        object.__setattr__(
            self,
            "priority",
            ResolutionPriority(self.priority),
        )
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )


class LifecycleStore(Protocol):
    """Unidad de persistencia; el commit pertenece al llamador."""

    def create(
        self,
        command: CreateResolutionCommand,
        *,
        definition: ResolutionDefinition,
        public_id: str,
        occurred_at: datetime,
    ) -> ResolutionLifecycle:
        """Persiste raíz, problema y evento inicial."""

    def load(self, resolution_id: int, /) -> ResolutionLifecycle | None:
        """Reconstruye la proyección y su evidencia vigente."""

    def verify_transition_security(
        self,
        *,
        resolution_id: int,
        action: str,
        security_decision_id: int,
        actor: ActorContext,
        occurred_at: datetime,
    ) -> None:
        """Deniega antes de reconstruir o cambiar el estado raíz."""

    def apply(self, transition: LifecycleTransition, /) -> ResolutionLifecycle:
        """Aplica transición y evento con versión esperada."""


class ComponentResolver(Protocol):
    """Resuelve una referencia exacta sin conocer módulos del ERP."""

    def resolve(self, reference: ComponentReference, /) -> object:
        """Devuelve la instancia enlazada a clave, versión y tipo exactos."""
