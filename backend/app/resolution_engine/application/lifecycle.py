"""Servicios de aplicación para creación y transición del Lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.contracts.lifecycle import (
    CreateResolutionCommand,
    LifecycleStore,
)
from app.resolution_engine.contracts.runtime import Clock, IdentifierFactory
from app.resolution_engine.domain.exceptions import (
    LifecycleInvariantError,
    ResolutionNotFoundError,
)
from app.resolution_engine.domain.lifecycle import (
    LifecycleAction,
    ResolutionLifecycle,
    ResolutionStateMachine,
)
from app.resolution_engine.domain.security import ActorContext


@dataclass(frozen=True, slots=True)
class LifecycleActor:
    context: ActorContext
    security_decision_id: int | None = None
    actor_function: str | None = None

    @property
    def actor_id(self) -> str:
        return self.context.identity.actor_id

    @property
    def actor_type(self) -> str:
        return self.context.identity.actor_type.value

    @property
    def source(self) -> str:
        return self.context.authentication.source

    @property
    def correlation_id(self) -> str:
        return self.context.authentication.correlation_id


class ResolutionLifecycleService:
    """Fachada única para crear y cambiar el estado raíz."""

    def __init__(
        self,
        *,
        registry: ResolutionRegistry,
        store: LifecycleStore,
        state_machine: ResolutionStateMachine,
        clock: Clock,
        identifiers: IdentifierFactory,
    ) -> None:
        self._registry = registry
        self._store = store
        self._state_machine = state_machine
        self._clock = clock
        self._identifiers = identifiers

    def create(
        self,
        command: CreateResolutionCommand,
        /,
    ) -> ResolutionLifecycle:
        occurred_at = self._clock.now()
        violations = list(command.actor.validate_at(occurred_at))
        for name in ("resolution_type", "subject_type", "subject_id", "title"):
            if not str(getattr(command, name)).strip():
                violations.append(f"{name}_required")
        for name in ("problem_code", "summary", "detected_by"):
            if not str(getattr(command.problem, name)).strip():
                violations.append(f"problem_{name}_required")
        if command.problem.detected_at.tzinfo is None:
            violations.append("problem_detected_at_timezone_required")
        if violations:
            raise LifecycleInvariantError(
                action="create",
                violations=tuple(violations),
            )
        definition = self._registry.resolve(
            command.resolution_type,
            command.definition_version,
        )
        return self._store.create(
            command,
            definition=definition,
            public_id=self._identifiers.new_id(),
            occurred_at=occurred_at,
        )

    def transition(
        self,
        resolution_id: int,
        action: LifecycleAction,
        *,
        actor: LifecycleActor,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ResolutionLifecycle:
        occurred_at = self._clock.now()
        violations = actor.context.validate_at(occurred_at)
        if actor.security_decision_id is None or actor.security_decision_id <= 0:
            violations += ("security_decision_required",)
        if violations:
            raise LifecycleInvariantError(
                action=action.value,
                violations=violations,
            )
        self._store.verify_transition_security(
            resolution_id=resolution_id,
            action=action.value,
            security_decision_id=actor.security_decision_id,
            actor=actor.context,
            occurred_at=occurred_at,
        )
        lifecycle = self._store.load(resolution_id)
        if lifecycle is None:
            raise ResolutionNotFoundError(resolution_id=resolution_id)
        transition = self._state_machine.transition(
            lifecycle,
            action,
            occurred_at=occurred_at,
            actor_id=actor.actor_id,
            actor_type=actor.actor_type,
            actor_function=actor.actor_function,
            source=actor.source,
            correlation_id=actor.correlation_id,
            reason=reason,
            metadata={
                **dict(metadata or {}),
                "security_decision_id": actor.security_decision_id,
            },
        )
        return self._store.apply(transition)
