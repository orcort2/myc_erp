from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.enums import (
    AnalysisStatus,
    RevalidationStatus,
    SimulationStatus,
)


RELEASED_STATUSES = frozenset({"released_to_client", "released"})


class CertificateResolutionStrategyKey(StrEnum):
    WITHDRAW_CLIENT_ACCESS = "withdraw_client_access"
    NO_ACTION = "no_action"


@dataclass(frozen=True, slots=True)
class CertificateResolutionRequest:
    certificate_id: int
    reason: str

    def __post_init__(self) -> None:
        if self.certificate_id <= 0:
            raise ValueError("certificate_id must be positive")
        if not self.reason.strip():
            raise ValueError("reason is required")


@dataclass(frozen=True, slots=True)
class CertificateFacts:
    certificate_id: int
    folio: str
    status: str
    client_visible: bool
    authenticated_document_present: bool
    released_on: str | None
    released_to_client_at: str | None
    released_to_client_by_id: int | None
    is_active: bool
    updated_at: str | None

    def snapshot(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "folio": self.folio,
            "status": self.status,
            "client_visible": self.client_visible,
            "authenticated_document_present": (
                self.authenticated_document_present
            ),
            "released_on": self.released_on,
            "released_to_client_at": self.released_to_client_at,
            "released_to_client_by_id": self.released_to_client_by_id,
            "is_active": self.is_active,
            "updated_at": self.updated_at,
        }

    @property
    def snapshot_hash(self) -> str:
        return canonical_sha256(self.snapshot())


@dataclass(frozen=True, slots=True)
class CertificateResolutionContext:
    facts: CertificateFacts
    reason: str

    def snapshot(self) -> dict[str, Any]:
        return {
            "facts": self.facts.snapshot(),
            "reason": self.reason.strip(),
        }

    @property
    def context_hash(self) -> str:
        return canonical_sha256(self.snapshot())


@dataclass(frozen=True, slots=True)
class CertificateResolutionAnalysis:
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
class CertificateResolutionStrategy:
    key: CertificateResolutionStrategyKey
    rationale: str

    def snapshot(self) -> dict[str, str]:
        return {"key": self.key.value, "rationale": self.rationale}


@dataclass(frozen=True, slots=True)
class CertificateResolutionPlanStep:
    step_key: str
    operation_key: str
    owner_module: str
    input_payload: dict[str, Any]
    compensation_operation_key: str
    compensation_payload: dict[str, Any]

    def snapshot(self) -> dict[str, Any]:
        return {
            "step_key": self.step_key,
            "operation_key": self.operation_key,
            "owner_module": self.owner_module,
            "input_payload": dict(self.input_payload),
            "is_compensable": True,
            "compensation_operation_key": (
                self.compensation_operation_key
            ),
            "compensation_payload": dict(self.compensation_payload),
        }


@dataclass(frozen=True, slots=True)
class CertificateResolutionPlan:
    context_hash: str
    strategy: CertificateResolutionStrategy
    steps: tuple[CertificateResolutionPlanStep, ...]
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
class CertificateResolutionSimulation:
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
class CertificateAuthorizationRequirements:
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
class CertificateResolutionRevalidation:
    status: RevalidationStatus
    authorized_context_hash: str
    current_context_hash: str
    reason_codes: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status is RevalidationStatus.VALID

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "authorized_context_hash": self.authorized_context_hash,
            "current_context_hash": self.current_context_hash,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True, slots=True)
class CertificateOperationOutcome:
    certificate_id: int
    folio: str
    operation_key: str
    idempotency_key: str
    before_snapshot: dict[str, Any]
    after_snapshot: dict[str, Any]
    domain_transaction_reference: str
