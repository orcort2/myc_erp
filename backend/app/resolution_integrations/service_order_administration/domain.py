"""Objetos deterministas de las herramientas administrativas de ETS."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.enums import AnalysisStatus, RevalidationStatus, SimulationStatus


class AdministrationStrategyKey(StrEnum):
    RESTORE = "restore"
    REBUILD = "rebuild"
    VOID = "void"
    NO_ACTION = "no_action"


@dataclass(frozen=True, slots=True)
class ServiceOrderAdministrationRequest:
    operation: str
    subject_id: int
    reason: str

    def __post_init__(self) -> None:
        if self.operation not in {"restore", "rebuild", "void"}:
            raise ValueError("invalid service-order administrative operation")
        if self.subject_id <= 0:
            raise ValueError("subject_id must be positive")
        if not self.reason.strip():
            raise ValueError("reason is required")

    def snapshot(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "subject_id": self.subject_id,
            "reason": self.reason.strip(),
        }


@dataclass(frozen=True, slots=True)
class ServiceOrderAdministrationFacts:
    operation: str
    subject_id: int
    service_order_id: int | None
    service_order_folio: str | None
    quotation_id: int | None
    quotation_status: str | None
    service_order_active: bool | None
    active_sibling_id: int | None
    inactive_order_ids: tuple[int, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    affected_entities: tuple[str, ...]
    proposed_changes: tuple[str, ...]
    updated_at: str | None

    @property
    def allowed(self) -> bool:
        return not self.blockers

    def snapshot(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "subject_id": self.subject_id,
            "service_order_id": self.service_order_id,
            "service_order_folio": self.service_order_folio,
            "quotation_id": self.quotation_id,
            "quotation_status": self.quotation_status,
            "service_order_active": self.service_order_active,
            "active_sibling_id": self.active_sibling_id,
            "inactive_order_ids": list(self.inactive_order_ids),
            "allowed": self.allowed,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "affected_entities": list(self.affected_entities),
            "proposed_changes": list(self.proposed_changes),
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class ServiceOrderAdministrationContext:
    facts: ServiceOrderAdministrationFacts
    request: ServiceOrderAdministrationRequest

    def snapshot(self) -> dict[str, Any]:
        return {"facts": self.facts.snapshot(), "request": self.request.snapshot()}

    @property
    def context_hash(self) -> str:
        return canonical_sha256(self.snapshot())


@dataclass(frozen=True, slots=True)
class AdministrationAnalysis:
    status: AnalysisStatus
    reason_codes: tuple[str, ...]
    context_hash: str

    @property
    def is_resolvable(self) -> bool:
        return self.status is AnalysisStatus.RESOLVABLE

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "reason_codes": list(self.reason_codes),
            "context_hash": self.context_hash,
        }


@dataclass(frozen=True, slots=True)
class AdministrationStrategy:
    key: AdministrationStrategyKey
    rationale: str

    def snapshot(self) -> dict[str, str]:
        return {"key": self.key.value, "rationale": self.rationale}


@dataclass(frozen=True, slots=True)
class AdministrationPlanStep:
    step_key: str
    operation_key: str
    owner_module: str
    input_payload: dict[str, Any]

    def snapshot(self) -> dict[str, Any]:
        return {
            "step_key": self.step_key,
            "operation_key": self.operation_key,
            "owner_module": self.owner_module,
            "input_payload": dict(self.input_payload),
            "is_compensable": False,
        }


@dataclass(frozen=True, slots=True)
class AdministrationPlan:
    context_hash: str
    strategy: AdministrationStrategy
    steps: tuple[AdministrationPlanStep, ...]
    blockers: tuple[str, ...] = ()

    def snapshot(self) -> dict[str, Any]:
        return {
            "context_hash": self.context_hash,
            "strategy": self.strategy.snapshot(),
            "steps": [step.snapshot() for step in self.steps],
            "blockers": list(self.blockers),
        }

    @property
    def plan_hash(self) -> str:
        return canonical_sha256(self.snapshot())


@dataclass(frozen=True, slots=True)
class AdministrationSimulation:
    status: SimulationStatus
    plan_hash: str
    impacts: tuple[str, ...]
    preserved_evidence: tuple[str, ...]
    blockers: tuple[str, ...] = ()

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "plan_hash": self.plan_hash,
            "impacts": list(self.impacts),
            "preserved_evidence": list(self.preserved_evidence),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True, slots=True)
class AdministrationAuthorizationRequirements:
    required_permissions: tuple[str, ...]
    required_functions: tuple[str, ...]
    plan_hash: str

    def snapshot(self) -> dict[str, Any]:
        return {
            "required_permissions": list(self.required_permissions),
            "required_functions": list(self.required_functions),
            "plan_hash": self.plan_hash,
        }


@dataclass(frozen=True, slots=True)
class AdministrationRevalidation:
    status: RevalidationStatus
    authorized_context_hash: str
    current_context_hash: str
    reason_codes: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status in {RevalidationStatus.VALID, RevalidationStatus.VALID_WITH_WARNINGS}

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "authorized_context_hash": self.authorized_context_hash,
            "current_context_hash": self.current_context_hash,
            "reason_codes": list(self.reason_codes),
        }
