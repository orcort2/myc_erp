"""Contratos de planificación y ejecución compensatoria síncrona."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from app.resolution_engine.domain.compensation import (
    CompensationActionRequest,
    CompensationOutcome,
    CompensationPlan,
    CompensationPlanStep,
    CompensationReservation,
    CompensationSource,
    CompensationSummary,
    PreparedCompensation,
)
from app.resolution_engine.domain.enums import CompensationStrategy
from app.resolution_engine.domain.execution import DomainActionResult
from app.resolution_engine.domain.lifecycle import LifecycleTransition
from app.resolution_engine.domain.security import ActorContext
from app.resolution_engine.domain.value_objects import ComponentKey


def compensation_security_operation_payload(
    *,
    resolution_id: int,
    source_execution_id: int,
    strategy: str,
    reason: str,
    selected_step_execution_ids: tuple[int, ...],
    actor_id: str,
    organization_id: str,
) -> dict:
    """Intención exacta autorizada para preparar una compensación."""

    return {
        "resolution_id": resolution_id,
        "source_execution_id": source_execution_id,
        "strategy": strategy,
        "reason": reason,
        "selected_step_execution_ids": list(selected_step_execution_ids),
        "actor_id": actor_id,
        "organization_id": organization_id,
    }


@dataclass(frozen=True, slots=True)
class PrepareCompensationCommand:
    resolution_id: int
    source_execution_id: int
    strategy: CompensationStrategy
    reason: str
    security_decision_id: int
    idempotency_key: str
    actor: ActorContext
    selected_step_execution_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ExecuteCompensationCommand:
    compensation_plan_id: int
    idempotency_key: str
    actor: ActorContext
    lock_owner: str
    lock_ttl: timedelta = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class StartCompensationResult:
    reservation: CompensationReservation | None = None
    previous_outcome: CompensationOutcome | None = None

    def __post_init__(self) -> None:
        if (self.reservation is None) == (self.previous_outcome is None):
            raise ValueError(
                "start requires one reservation or previous outcome"
            )


class CompensationHandler(Protocol):
    """Adaptador propietario; debe honrar la clave idempotente."""

    operation_key: ComponentKey

    def execute(
        self,
        request: CompensationActionRequest,
        /,
    ) -> DomainActionResult:
        """Ejecuta una única acción compensatoria declarada."""


class CompensationStore(Protocol):
    """Persistencia transaccional de planes y checkpoints compensatorios."""

    def load_source(
        self,
        resolution_id: int,
        source_execution_id: int,
        /,
    ) -> CompensationSource | None:
        """Reconstruye exclusivamente efectos confirmados compensables."""

    def save_plan(
        self,
        command: PrepareCompensationCommand,
        plan: CompensationPlan,
        *,
        created_at: datetime,
    ) -> CompensationPlan:
        """Valida autorización exacta y persiste un plan inmutable."""

    def load_prepared(
        self,
        compensation_plan_id: int,
        actor: ActorContext,
        /,
    ) -> PreparedCompensation | None:
        """Reconstruye plan y Lifecycle sólo para el actor autorizado."""

    def find_outcome(
        self,
        *,
        idempotency_key: str,
        request_hash: str,
    ) -> CompensationOutcome | None:
        """Devuelve únicamente un resultado final con hash idéntico."""

    def start(
        self,
        *,
        command: ExecuteCompensationCommand,
        prepared: PreparedCompensation,
        transition: LifecycleTransition,
        execution_key: str,
        lock_token: str,
        request_hash: str,
        occurred_at: datetime,
    ) -> StartCompensationResult:
        """Reserva lock, crea checkpoints y aplica START_COMPENSATION."""

    def renew_lock(
        self,
        reservation: CompensationReservation,
        *,
        expires_at: datetime,
        occurred_at: datetime,
    ) -> None:
        """Extiende sólo el token compensatorio vigente."""

    def assert_lock(
        self,
        reservation: CompensationReservation,
        *,
        occurred_at: datetime,
    ) -> None:
        """Comprueba exclusividad después del handler."""

    def start_step(
        self,
        reservation: CompensationReservation,
        step: CompensationPlanStep,
        *,
        request_hash: str,
        occurred_at: datetime,
    ) -> DomainActionResult | None:
        """Persiste intención o devuelve el resultado durable del paso."""

    def record_step_result(
        self,
        reservation: CompensationReservation,
        step: CompensationPlanStep,
        result: DomainActionResult,
        *,
        occurred_at: datetime,
        require_active_lock: bool = True,
    ) -> None:
        """Persiste resultado y evidencia sin alterar el hecho original."""

    def finish(
        self,
        reservation: CompensationReservation,
        summary: CompensationSummary,
        transition: LifecycleTransition,
        *,
        outcome: CompensationOutcome,
        completed_at: datetime,
    ) -> CompensationOutcome:
        """Cierra ejecución, Lifecycle, auditoría, outbox y lock."""
