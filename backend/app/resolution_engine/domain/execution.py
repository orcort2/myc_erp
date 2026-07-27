"""Modelo puro de ejecución controlada de planes autorizados."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.enums import (
    EntityRelationshipType,
    ExecutionStatus,
    ResolutionResult,
    StepExecutionStatus,
)
from app.resolution_engine.domain.exceptions import (
    InvalidExecutionPlanError,
)
from app.resolution_engine.domain.lifecycle import ResolutionLifecycle


class ActionCertainty(StrEnum):
    """Grado de certeza reportado por el contrato propietario."""

    CONFIRMED = "confirmed"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class ExecutionEntityEffect:
    relationship: EntityRelationshipType
    entity_type: str
    entity_id: str
    module: str
    public_identifier: str | None = None
    before_snapshot: Mapping[str, Any] | None = None
    after_snapshot: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "relationship",
            EntityRelationshipType(self.relationship),
        )
        for name in ("entity_type", "entity_id", "module"):
            if not str(getattr(self, name)).strip():
                raise InvalidExecutionPlanError(f"{name} is required")
        if self.before_snapshot is not None:
            object.__setattr__(
                self,
                "before_snapshot",
                MappingProxyType(dict(self.before_snapshot)),
            )
        if self.after_snapshot is not None:
            object.__setattr__(
                self,
                "after_snapshot",
                MappingProxyType(dict(self.after_snapshot)),
            )
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "relationship": self.relationship.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "module": self.module,
            "public_identifier": self.public_identifier,
            "before_snapshot": (
                dict(self.before_snapshot)
                if self.before_snapshot is not None
                else None
            ),
            "after_snapshot": (
                dict(self.after_snapshot)
                if self.after_snapshot is not None
                else None
            ),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ExecutionPlanStep:
    id: int
    step_key: str
    sequence: int
    operation_key: str
    owner_module: str
    input_payload: Mapping[str, Any]
    preconditions: tuple[Any, ...] = ()
    dependency_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.id <= 0 or self.sequence <= 0:
            raise InvalidExecutionPlanError(
                "step id and sequence must be positive"
            )
        for name in ("step_key", "operation_key", "owner_module"):
            if not str(getattr(self, name)).strip():
                raise InvalidExecutionPlanError(f"{name} is required")
        object.__setattr__(
            self,
            "input_payload",
            MappingProxyType(dict(self.input_payload)),
        )
        object.__setattr__(
            self,
            "preconditions",
            tuple(self.preconditions),
        )
        object.__setattr__(
            self,
            "dependency_ids",
            tuple(self.dependency_ids),
        )

    def request_snapshot(self) -> dict[str, Any]:
        return {
            "step_id": self.id,
            "step_key": self.step_key,
            "sequence": self.sequence,
            "operation_key": self.operation_key,
            "owner_module": self.owner_module,
            "input_payload": dict(self.input_payload),
            "preconditions": list(self.preconditions),
            "dependency_ids": list(self.dependency_ids),
        }


@dataclass(frozen=True, slots=True)
class ExecutionCandidate:
    lifecycle: ResolutionLifecycle
    plan_id: int
    plan_version: int
    plan_hash: str
    revalidation_id: int
    initial_context_hash: str
    steps: tuple[ExecutionPlanStep, ...]


@dataclass(frozen=True, slots=True)
class DomainActionRequest:
    resolution_id: int
    execution_id: int
    step_execution_id: int
    plan_id: int
    plan_version: int
    plan_hash: str
    step: ExecutionPlanStep
    idempotency_key: str
    actor_id: str
    correlation_id: str

    @property
    def request_hash(self) -> str:
        return canonical_sha256(
            {
                "resolution_id": self.resolution_id,
                "execution_id": self.execution_id,
                "plan_id": self.plan_id,
                "plan_version": self.plan_version,
                "plan_hash": self.plan_hash,
                "step": self.step.request_snapshot(),
                "idempotency_key": self.idempotency_key,
            }
        )


@dataclass(frozen=True, slots=True)
class DomainActionResult:
    """Resultado verificable; nunca solicita reintento automático."""

    success: bool
    certainty: ActionCertainty
    response_payload: Mapping[str, Any] = field(default_factory=dict)
    entity_effects: tuple[ExecutionEntityEffect, ...] = ()
    warnings: tuple[str, ...] = ()
    domain_transaction_reference: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    error_details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "certainty", ActionCertainty(self.certainty))
        if self.success and self.certainty is not ActionCertainty.CONFIRMED:
            raise InvalidExecutionPlanError(
                "a successful action must be confirmed"
            )
        if not self.success and not self.error_code:
            raise InvalidExecutionPlanError(
                "an unsuccessful action requires error_code"
            )
        object.__setattr__(
            self,
            "response_payload",
            MappingProxyType(dict(self.response_payload)),
        )
        object.__setattr__(
            self,
            "entity_effects",
            tuple(self.entity_effects),
        )
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(
            self,
            "error_details",
            MappingProxyType(dict(self.error_details)),
        )

    @property
    def step_status(self) -> StepExecutionStatus:
        if self.success:
            return StepExecutionStatus.COMPLETED
        if self.certainty is ActionCertainty.UNCERTAIN:
            return StepExecutionStatus.BLOCKED
        return StepExecutionStatus.FAILED

    def snapshot(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "certainty": self.certainty.value,
            "response_payload": dict(self.response_payload),
            "entity_effects": [
                item.snapshot() for item in self.entity_effects
            ],
            "warnings": list(self.warnings),
            "domain_transaction_reference": (
                self.domain_transaction_reference
            ),
            "error_code": self.error_code,
            "error_message": self.error_message,
            "error_details": dict(self.error_details),
        }

    @classmethod
    def from_snapshot(
        cls,
        value: Mapping[str, Any],
    ) -> DomainActionResult:
        return cls(
            success=bool(value["success"]),
            certainty=ActionCertainty(value["certainty"]),
            response_payload=value.get("response_payload", {}),
            entity_effects=tuple(
                ExecutionEntityEffect(
                    relationship=item["relationship"],
                    entity_type=item["entity_type"],
                    entity_id=item["entity_id"],
                    module=item["module"],
                    public_identifier=item.get("public_identifier"),
                    before_snapshot=item.get("before_snapshot"),
                    after_snapshot=item.get("after_snapshot"),
                    metadata=item.get("metadata", {}),
                )
                for item in value.get("entity_effects", ())
            ),
            warnings=tuple(value.get("warnings", ())),
            domain_transaction_reference=value.get(
                "domain_transaction_reference"
            ),
            error_code=value.get("error_code"),
            error_message=value.get("error_message"),
            error_details=value.get("error_details", {}),
        )


@dataclass(frozen=True, slots=True)
class ExecutionReservation:
    execution_id: int
    resolution_id: int
    plan_id: int
    plan_version: int
    plan_hash: str
    revalidation_id: int
    execution_key: str
    lock_token: str
    actor_id: str
    actor_type: str
    actor_source: str
    correlation_id: str
    lifecycle: ResolutionLifecycle
    steps: tuple[ExecutionPlanStep, ...]
    step_execution_ids: Mapping[int, int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "step_execution_ids",
            MappingProxyType(dict(self.step_execution_ids)),
        )


@dataclass(frozen=True, slots=True)
class ExecutionSummary:
    execution_status: ExecutionStatus
    resolution_result: ResolutionResult | None
    completed_steps: int
    failed_steps: int
    blocked_steps: int
    total_steps: int
    warnings: tuple[str, ...]
    effects: tuple[ExecutionEntityEffect, ...]
    failed_step_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    execution_id: int
    resolution_id: int
    execution_status: ExecutionStatus
    resolution_status: str
    idempotency_key: str
    idempotent_replay: bool
    completed_steps: int
    failed_steps: int
    blocked_steps: int
    total_steps: int
    result_hash: str | None

    def snapshot(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "resolution_id": self.resolution_id,
            "execution_status": self.execution_status.value,
            "resolution_status": self.resolution_status,
            "idempotency_key": self.idempotency_key,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "blocked_steps": self.blocked_steps,
            "total_steps": self.total_steps,
            "result_hash": self.result_hash,
        }

    @classmethod
    def from_snapshot(
        cls,
        value: Mapping[str, Any],
        *,
        idempotent_replay: bool,
    ) -> ExecutionOutcome:
        return cls(
            execution_id=int(value["execution_id"]),
            resolution_id=int(value["resolution_id"]),
            execution_status=ExecutionStatus(value["execution_status"]),
            resolution_status=str(value["resolution_status"]),
            idempotency_key=str(value["idempotency_key"]),
            idempotent_replay=idempotent_replay,
            completed_steps=int(value["completed_steps"]),
            failed_steps=int(value["failed_steps"]),
            blocked_steps=int(value["blocked_steps"]),
            total_steps=int(value["total_steps"]),
            result_hash=value.get("result_hash"),
        )


class ExecutionEngine:
    """Valida el plan y consolida resultados sin infraestructura."""

    def ordered_steps(
        self,
        candidate: ExecutionCandidate,
    ) -> tuple[ExecutionPlanStep, ...]:
        if not candidate.steps:
            raise InvalidExecutionPlanError(
                "an executable plan requires at least one step"
            )
        ordered = tuple(sorted(candidate.steps, key=lambda item: item.sequence))
        ids = {item.id for item in ordered}
        if len(ids) != len(ordered):
            raise InvalidExecutionPlanError("plan step ids must be unique")
        if len({item.sequence for item in ordered}) != len(ordered):
            raise InvalidExecutionPlanError(
                "plan step sequences must be unique"
            )
        positions = {item.id: index for index, item in enumerate(ordered)}
        for item in ordered:
            for dependency_id in item.dependency_ids:
                if dependency_id not in ids:
                    raise InvalidExecutionPlanError(
                        f"step {item.step_key} has an unknown dependency"
                    )
                if positions[dependency_id] >= positions[item.id]:
                    raise InvalidExecutionPlanError(
                        f"step {item.step_key} dependency is not prior"
                    )
        return ordered

    def summarize(
        self,
        *,
        steps: tuple[ExecutionPlanStep, ...],
        results: Mapping[int, DomainActionResult],
    ) -> ExecutionSummary:
        completed = tuple(
            step
            for step in steps
            if step.id in results and results[step.id].success
        )
        failed = tuple(
            step
            for step in steps
            if step.id in results
            and results[step.id].step_status is StepExecutionStatus.FAILED
        )
        blocked = tuple(
            step
            for step in steps
            if step.id in results
            and results[step.id].step_status is StepExecutionStatus.BLOCKED
        )
        warnings = tuple(
            warning
            for step in steps
            if step.id in results
            for warning in results[step.id].warnings
        )
        effects = tuple(
            effect
            for step in steps
            if step.id in results
            for effect in results[step.id].entity_effects
        )
        if blocked:
            execution_status = ExecutionStatus.BLOCKED
            resolution_result = None
        elif failed and completed:
            execution_status = ExecutionStatus.PARTIALLY_COMPLETED
            resolution_result = ResolutionResult.PARTIAL_SUCCESS
        elif failed:
            execution_status = ExecutionStatus.FAILED
            resolution_result = ResolutionResult.FAILED
        elif len(completed) == len(steps):
            execution_status = ExecutionStatus.COMPLETED
            resolution_result = ResolutionResult.SUCCESS
        else:
            raise InvalidExecutionPlanError(
                "execution stopped without a terminal step result"
            )
        return ExecutionSummary(
            execution_status=execution_status,
            resolution_result=resolution_result,
            completed_steps=len(completed),
            failed_steps=len(failed),
            blocked_steps=len(blocked),
            total_steps=len(steps),
            warnings=warnings,
            effects=effects,
            failed_step_keys=tuple(
                item.step_key for item in failed + blocked
            ),
        )

    @staticmethod
    def result_hash(
        *,
        resolution_id: int,
        execution_id: int,
        summary: ExecutionSummary,
        completed_at: datetime,
    ) -> str:
        return canonical_sha256(
            {
                "resolution_id": resolution_id,
                "execution_id": execution_id,
                "execution_status": summary.execution_status.value,
                "resolution_result": (
                    summary.resolution_result.value
                    if summary.resolution_result
                    else None
                ),
                "completed_steps": summary.completed_steps,
                "failed_steps": summary.failed_steps,
                "blocked_steps": summary.blocked_steps,
                "total_steps": summary.total_steps,
                "warnings": list(summary.warnings),
                "effects": [item.snapshot() for item in summary.effects],
                "failed_step_keys": list(summary.failed_step_keys),
                "completed_at": completed_at,
            }
        )
