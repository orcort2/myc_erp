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
        if self.request_key is None or not self.request_key.strip():
            raise ValueError("request_key is required for secure creation")
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

    def security_operation_payload(
        self,
        definition: ResolutionDefinition,
        /,
    ) -> dict[str, Any]:
        """Intención canónica que la concesión de creación debe cubrir."""

        problem = self.problem
        return {
            "definition": {
                "resolution_type": str(definition.resolution_type),
                "version": str(definition.version),
                "fingerprint": definition.fingerprint,
            },
            "source": self.source.value,
            "subject": {
                "type": self.subject_type,
                "id": self.subject_id,
            },
            "title": self.title,
            "description": self.description,
            "reason": self.reason,
            "priority": self.priority.value,
            "request_key": self.request_key,
            "parent_resolution_id": self.parent_resolution_id,
            "requires_authorization": self.requires_authorization,
            "metadata": dict(self.metadata),
            "problem": {
                "problem_code": problem.problem_code,
                "summary": problem.summary,
                "description": problem.description,
                "detected_by": problem.detected_by,
                "detected_at": problem.detected_at.isoformat(),
                "source_payload": dict(problem.source_payload),
                "external_reference": problem.external_reference,
                "severity": problem.severity.value,
                "observed_state": dict(problem.observed_state),
                "evidence": list(problem.evidence),
            },
        }


def lifecycle_transition_operation_payload(
    *,
    resolution_id: int,
    action: str,
    expected_state: str,
    expected_version: int,
    reason: str | None,
    metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Intención exacta de una transición gobernada por Lifecycle."""

    return {
        "resolution_id": resolution_id,
        "action": action,
        "expected_state": expected_state,
        "expected_version": expected_version,
        "reason": reason,
        "metadata": dict(metadata or {}),
    }


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
        operation_id: str,
        reason: str | None,
        metadata: Mapping[str, Any] | None,
    ) -> None:
        """Deniega antes de reconstruir o cambiar el estado raíz."""

    def apply(self, transition: LifecycleTransition, /) -> ResolutionLifecycle:
        """Aplica transición y evento con versión esperada."""


class ComponentResolver(Protocol):
    """Resuelve una referencia exacta sin conocer módulos del ERP."""

    def resolve(self, reference: ComponentReference, /) -> object:
        """Devuelve la instancia enlazada a clave, versión y tipo exactos."""
