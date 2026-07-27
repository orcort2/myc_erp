"""Modelo puro para planes y resultados de compensación."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.enums import (
    CompensationStatus,
    CompensationStrategy,
)
from app.resolution_engine.domain.exceptions import (
    InvalidCompensationPlanError,
)
from app.resolution_engine.domain.execution import (
    ActionCertainty,
    DomainActionResult,
)
from app.resolution_engine.domain.lifecycle import ResolutionLifecycle


@dataclass(frozen=True, slots=True)
class CompensableAction:
    """Acción confirmada y su contrato compensatorio declarado."""

    plan_step_id: int
    step_execution_id: int
    step_key: str
    original_sequence: int
    operation_key: str
    compensation_operation_key: str
    owner_module: str
    compensation_payload: Mapping[str, Any]
    dependency_step_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.plan_step_id <= 0 or self.step_execution_id <= 0:
            raise InvalidCompensationPlanError(
                "source step identifiers must be positive"
            )
        if self.original_sequence <= 0:
            raise InvalidCompensationPlanError(
                "source sequence must be positive"
            )
        for name in (
            "step_key",
            "operation_key",
            "compensation_operation_key",
            "owner_module",
        ):
            if not str(getattr(self, name)).strip():
                raise InvalidCompensationPlanError(f"{name} is required")
        object.__setattr__(
            self,
            "compensation_payload",
            MappingProxyType(dict(self.compensation_payload)),
        )
        object.__setattr__(
            self,
            "dependency_step_ids",
            tuple(self.dependency_step_ids),
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "plan_step_id": self.plan_step_id,
            "step_execution_id": self.step_execution_id,
            "step_key": self.step_key,
            "original_sequence": self.original_sequence,
            "operation_key": self.operation_key,
            "compensation_operation_key": self.compensation_operation_key,
            "owner_module": self.owner_module,
            "compensation_payload": dict(self.compensation_payload),
            "dependency_step_ids": list(self.dependency_step_ids),
        }


@dataclass(frozen=True, slots=True)
class CompensationSource:
    lifecycle: ResolutionLifecycle
    execution_id: int
    actions: tuple[CompensableAction, ...]
    completed_step_execution_ids: tuple[int, ...]
    non_compensable_step_execution_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CompensationPlanStep:
    sequence: int
    source_plan_step_id: int
    source_step_execution_id: int
    source_step_key: str
    operation_key: str
    owner_module: str
    input_payload: Mapping[str, Any]
    dependency_source_step_ids: tuple[int, ...] = ()
    id: int | None = None

    def __post_init__(self) -> None:
        if self.sequence <= 0:
            raise InvalidCompensationPlanError(
                "compensation sequence must be positive"
            )
        object.__setattr__(
            self,
            "input_payload",
            MappingProxyType(dict(self.input_payload)),
        )
        object.__setattr__(
            self,
            "dependency_source_step_ids",
            tuple(self.dependency_source_step_ids),
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "source_plan_step_id": self.source_plan_step_id,
            "source_step_execution_id": self.source_step_execution_id,
            "source_step_key": self.source_step_key,
            "operation_key": self.operation_key,
            "owner_module": self.owner_module,
            "input_payload": dict(self.input_payload),
            "dependency_source_step_ids": list(
                self.dependency_source_step_ids
            ),
        }


@dataclass(frozen=True, slots=True)
class CompensationPlan:
    resolution_id: int
    source_execution_id: int
    strategy: CompensationStrategy
    reason: str
    steps: tuple[CompensationPlanStep, ...]
    plan_hash: str
    id: int | None = None
    security_decision_id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "strategy",
            CompensationStrategy(self.strategy),
        )
        object.__setattr__(self, "steps", tuple(self.steps))
        if len(self.plan_hash) != 64:
            raise InvalidCompensationPlanError(
                "compensation plan hash must be SHA-256"
            )


@dataclass(frozen=True, slots=True)
class PreparedCompensation:
    lifecycle: ResolutionLifecycle
    plan: CompensationPlan


@dataclass(frozen=True, slots=True)
class CompensationActionRequest:
    resolution_id: int
    source_execution_id: int
    compensation_execution_id: int
    compensation_step_execution_id: int
    compensation_plan_id: int
    plan_hash: str
    step: CompensationPlanStep
    idempotency_key: str
    actor_id: str
    correlation_id: str

    @property
    def request_hash(self) -> str:
        return canonical_sha256(
            {
                "resolution_id": self.resolution_id,
                "source_execution_id": self.source_execution_id,
                "compensation_execution_id": self.compensation_execution_id,
                "compensation_plan_id": self.compensation_plan_id,
                "plan_hash": self.plan_hash,
                "step": self.step.snapshot(),
                "idempotency_key": self.idempotency_key,
            }
        )


@dataclass(frozen=True, slots=True)
class CompensationReservation:
    plan: CompensationPlan
    execution_id: int
    execution_key: str
    lock_token: str
    lifecycle: ResolutionLifecycle
    step_execution_ids: Mapping[int, int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "step_execution_ids",
            MappingProxyType(dict(self.step_execution_ids)),
        )


@dataclass(frozen=True, slots=True)
class CompensationSummary:
    status: CompensationStatus
    compensated_steps: int
    failed_steps: int
    blocked_steps: int
    total_steps: int


@dataclass(frozen=True, slots=True)
class CompensationOutcome:
    compensation_plan_id: int
    compensation_execution_id: int
    resolution_id: int
    source_execution_id: int
    status: CompensationStatus
    idempotency_key: str
    idempotent_replay: bool
    compensated_steps: int
    failed_steps: int
    blocked_steps: int
    total_steps: int

    def snapshot(self) -> dict[str, Any]:
        return {
            "compensation_plan_id": self.compensation_plan_id,
            "compensation_execution_id": self.compensation_execution_id,
            "resolution_id": self.resolution_id,
            "source_execution_id": self.source_execution_id,
            "status": self.status.value,
            "idempotency_key": self.idempotency_key,
            "compensated_steps": self.compensated_steps,
            "failed_steps": self.failed_steps,
            "blocked_steps": self.blocked_steps,
            "total_steps": self.total_steps,
        }

    @classmethod
    def from_snapshot(
        cls,
        value: Mapping[str, Any],
        *,
        idempotent_replay: bool,
    ) -> CompensationOutcome:
        return cls(
            compensation_plan_id=int(value["compensation_plan_id"]),
            compensation_execution_id=int(
                value["compensation_execution_id"]
            ),
            resolution_id=int(value["resolution_id"]),
            source_execution_id=int(value["source_execution_id"]),
            status=CompensationStatus(value["status"]),
            idempotency_key=str(value["idempotency_key"]),
            idempotent_replay=idempotent_replay,
            compensated_steps=int(value["compensated_steps"]),
            failed_steps=int(value["failed_steps"]),
            blocked_steps=int(value["blocked_steps"]),
            total_steps=int(value["total_steps"]),
        )


class CompensationEngine:
    """Construye orden inverso y consolida resultados sin infraestructura."""

    def build_plan(
        self,
        source: CompensationSource,
        *,
        strategy: CompensationStrategy,
        reason: str,
        selected_step_execution_ids: tuple[int, ...] = (),
    ) -> CompensationPlan:
        strategy = CompensationStrategy(strategy)
        if not reason.strip():
            raise InvalidCompensationPlanError(
                "compensation reason is required"
            )
        available = {
            action.step_execution_id: action for action in source.actions
        }
        selected_ids = (
            set(selected_step_execution_ids)
            if selected_step_execution_ids
            else set(available)
        )
        if not selected_ids or not selected_ids.issubset(available):
            raise InvalidCompensationPlanError(
                "selection contains unavailable compensation actions"
            )
        if strategy is CompensationStrategy.TOTAL:
            if source.non_compensable_step_execution_ids:
                raise InvalidCompensationPlanError(
                    "total compensation crosses a point of no return"
                )
            if selected_ids != set(source.completed_step_execution_ids):
                raise InvalidCompensationPlanError(
                    "total compensation must include every completed step"
                )

        selected = [available[item] for item in selected_ids]
        selected.sort(
            key=lambda item: (item.original_sequence, item.plan_step_id),
            reverse=True,
        )
        selected_plan_ids = {item.plan_step_id for item in selected}
        reverse_dependencies = {
            action.plan_step_id: tuple(
                candidate.plan_step_id
                for candidate in selected
                if action.plan_step_id in candidate.dependency_step_ids
            )
            for action in selected
        }
        steps = tuple(
            CompensationPlanStep(
                sequence=index,
                source_plan_step_id=action.plan_step_id,
                source_step_execution_id=action.step_execution_id,
                source_step_key=action.step_key,
                operation_key=action.compensation_operation_key,
                owner_module=action.owner_module,
                input_payload=action.compensation_payload,
                dependency_source_step_ids=tuple(
                    item
                    for item in reverse_dependencies[action.plan_step_id]
                    if item in selected_plan_ids
                ),
            )
            for index, action in enumerate(selected, start=1)
        )
        payload = {
            "resolution_id": source.lifecycle.resolution_id,
            "source_execution_id": source.execution_id,
            "strategy": strategy.value,
            "reason": reason.strip(),
            "steps": [step.snapshot() for step in steps],
        }
        return CompensationPlan(
            resolution_id=source.lifecycle.resolution_id,
            source_execution_id=source.execution_id,
            strategy=strategy,
            reason=reason.strip(),
            steps=steps,
            plan_hash=canonical_sha256(payload),
        )

    @staticmethod
    def summarize(
        plan: CompensationPlan,
        results: Mapping[int, DomainActionResult],
    ) -> CompensationSummary:
        compensated = sum(
            1 for result in results.values() if result.success
        )
        failed = sum(
            1
            for result in results.values()
            if not result.success
            and result.certainty is ActionCertainty.CONFIRMED
        )
        blocked = sum(
            1
            for result in results.values()
            if result.certainty is ActionCertainty.UNCERTAIN
        )
        if blocked:
            status = CompensationStatus.BLOCKED
        elif failed and compensated:
            status = CompensationStatus.PARTIALLY_COMPENSATED
        elif failed:
            status = CompensationStatus.FAILED
        else:
            status = CompensationStatus.COMPENSATED
        return CompensationSummary(
            status=status,
            compensated_steps=compensated,
            failed_steps=failed,
            blocked_steps=blocked,
            total_steps=len(plan.steps),
        )
