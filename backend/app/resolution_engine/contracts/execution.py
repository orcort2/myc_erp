"""Puertos explícitos para ejecutar acciones y publicar el outbox."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from app.resolution_engine.domain.execution import (
    DomainActionRequest,
    DomainActionResult,
    ExecutionCandidate,
    ExecutionOutcome,
    ExecutionPlanStep,
    ExecutionReservation,
    ExecutionSummary,
)
from app.resolution_engine.domain.lifecycle import LifecycleTransition
from app.resolution_engine.domain.security import ActorContext
from app.resolution_engine.domain.value_objects import ComponentKey


@dataclass(frozen=True, slots=True)
class ExecuteResolutionCommand:
    """Comando interno; la idempotency_key pertenece al namespace global."""

    resolution_id: int
    idempotency_key: str
    security_decision_id: int
    actor: ActorContext
    lock_owner: str
    lock_ttl: timedelta = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class StartExecutionResult:
    reservation: ExecutionReservation | None = None
    previous_outcome: ExecutionOutcome | None = None

    def __post_init__(self) -> None:
        if (self.reservation is None) == (self.previous_outcome is None):
            raise ValueError(
                "start result requires one reservation or previous outcome"
            )


@dataclass(frozen=True, slots=True)
class StepStartResult:
    step_execution_id: int
    previous_result: DomainActionResult | None = None


@dataclass(frozen=True, slots=True)
class OutboxMessage:
    id: int
    event_key: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict
    payload_hash: str
    occurred_at: datetime
    correlation_id: str | None


@dataclass(frozen=True, slots=True)
class OutboxPublicationReport:
    published: int
    failed: int


@dataclass(frozen=True, slots=True)
class PublishOutboxCommand:
    security_decision_id: int
    actor: ActorContext
    organization_id: str
    limit: int = 100


class ActionHandler(Protocol):
    """Adaptador de una operación propietaria; debe honrar idempotency_key."""

    operation_key: ComponentKey

    def execute(
        self,
        request: DomainActionRequest,
        /,
    ) -> DomainActionResult:
        """Ejecuta una única operación mediante el servicio propietario."""


class ExecutionStore(Protocol):
    """Checkpoints durables de ejecución, cada método es transaccional."""

    def find_outcome(
        self,
        *,
        idempotency_key: str,
        request_hash: str,
    ) -> ExecutionOutcome | None:
        """Devuelve el resultado final exacto antes de otra transición."""

    def load_candidate(
        self,
        resolution_id: int,
        /,
    ) -> ExecutionCandidate | None:
        """Reconstruye plan, revalidación y pasos exactos."""

    def verify_security(
        self,
        command: ExecuteResolutionCommand,
        candidate: ExecutionCandidate,
        *,
        occurred_at: datetime,
    ) -> None:
        """Deniega antes de consultar replay o exponer resultados."""

    def start(
        self,
        *,
        command: ExecuteResolutionCommand,
        steps: tuple[ExecutionPlanStep, ...],
        transition: LifecycleTransition,
        execution_key: str,
        lock_token: str,
        request_hash: str,
        occurred_at: datetime,
    ) -> StartExecutionResult:
        """Reserva idempotencia/lock e inicia expediente y lifecycle."""

    def renew_lock(
        self,
        reservation: ExecutionReservation,
        *,
        expires_at: datetime,
        occurred_at: datetime,
    ) -> None:
        """Extiende únicamente el lock vigente del mismo token."""

    def assert_lock(
        self,
        reservation: ExecutionReservation,
        *,
        occurred_at: datetime,
    ) -> None:
        """Comprueba token y vigencia después de una acción propietaria."""

    def start_step(
        self,
        reservation: ExecutionReservation,
        step: ExecutionPlanStep,
        *,
        request_hash: str,
        occurred_at: datetime,
    ) -> StepStartResult:
        """Persiste intención e idempotencia antes de invocar el handler."""

    def record_step_result(
        self,
        reservation: ExecutionReservation,
        step: ExecutionPlanStep,
        result: DomainActionResult,
        *,
        occurred_at: datetime,
    ) -> None:
        """Persiste resultado, entidades, auditoría y outbox del paso."""

    def record_uncertain_lock_loss(
        self,
        reservation: ExecutionReservation,
        step: ExecutionPlanStep,
        result: DomainActionResult,
        *,
        occurred_at: datetime,
    ) -> None:
        """Bloquea el paso cuando ya no puede afirmarse exclusividad."""

    def finish(
        self,
        reservation: ExecutionReservation,
        summary: ExecutionSummary,
        transition: LifecycleTransition,
        *,
        outcome: ExecutionOutcome,
        completed_at: datetime,
        actor: ActorContext,
    ) -> ExecutionOutcome:
        """Cierra ejecución, resultado, lifecycle, idempotencia y lock."""


class OutboxStore(Protocol):
    """Persistencia de publicación explícita, sin scheduler ni worker."""

    def verify_publication(
        self,
        command: PublishOutboxCommand,
        *,
        occurred_at: datetime,
    ) -> None:
        """Valida una decisión institucional antes de leer el outbox."""

    def pending(
        self,
        *,
        organization_id: str,
        available_at: datetime,
        limit: int,
    ) -> tuple[OutboxMessage, ...]:
        """Lista eventos pendientes en orden estable."""

    def mark_published(
        self,
        message_id: int,
        *,
        published_at: datetime,
    ) -> None:
        """Confirma publicación única."""

    def mark_failed(
        self,
        message_id: int,
        *,
        error: str,
        failed_at: datetime,
    ) -> None:
        """Conserva el fallo sin programar reintento."""


class EventPublisher(Protocol):
    """Publicador externo idempotente por event_key."""

    def publish(self, message: OutboxMessage, /) -> None:
        """Publica un evento; no modifica el expediente."""
