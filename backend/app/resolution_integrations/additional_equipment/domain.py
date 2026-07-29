"""Objetos deterministas del vertical de equipo adicional."""

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


class AdditionalEquipmentStrategyKey(StrEnum):
    ATTACH_EXISTING_WORK_ORDER = "attach_existing_work_order"
    CREATE_NEW_WORK_ORDER = "create_new_work_order"
    PENDING_SIGNATURE = "pending_signature"
    PENDING_COMMERCIAL_ADJUSTMENT = "pending_commercial_adjustment"
    NO_ACTION = "no_action"


@dataclass(frozen=True, slots=True)
class AdditionalEquipmentResolutionRequest:
    service_order_id: int
    reconciliation_id: str
    name: str
    calibration_scope: str
    catalog_item_id: int
    quantity: int = 1
    brand: str | None = None
    model: str | None = None
    serial_number: str | None = None
    internal_id: str | None = None
    range_or_capacity: str | None = None
    notes: str | None = None
    source: str = "resolution_center"
    requested_at: str | None = None
    preferred_work_order_id: int | None = None

    def __post_init__(self) -> None:
        if self.service_order_id <= 0 or self.catalog_item_id <= 0:
            raise ValueError("service_order_id and catalog_item_id must be positive")
        if not self.reconciliation_id.strip():
            raise ValueError("reconciliation_id is required")
        if not self.name.strip():
            raise ValueError("name is required")
        if not 1 <= self.quantity <= 10:
            raise ValueError("quantity must be between 1 and 10")

    def snapshot(self) -> dict[str, Any]:
        return {
            "service_order_id": self.service_order_id,
            "reconciliation_id": self.reconciliation_id.strip(),
            "name": self.name.strip(),
            "calibration_scope": self.calibration_scope,
            "catalog_item_id": self.catalog_item_id,
            "quantity": self.quantity,
            "brand": self.brand,
            "model": self.model,
            "serial_number": self.serial_number,
            "internal_id": self.internal_id,
            "range_or_capacity": self.range_or_capacity,
            "notes": self.notes,
            "source": self.source,
            "requested_at": self.requested_at,
            "preferred_work_order_id": self.preferred_work_order_id,
        }


@dataclass(frozen=True, slots=True)
class AdditionalEquipmentFacts:
    service_order_id: int
    service_order_folio: str
    service_order_status: str
    service_order_active: bool
    technician_id: int | None
    client_id: int
    quotation_id: int | None
    signature_status: str
    signatures_confirmed: bool
    active_work_orders: tuple[dict[str, Any], ...]
    catalog_exists: bool
    catalog_active: bool
    catalog_name: str | None
    scope_allowed: bool
    service_order_item_id: int | None
    commercial_adjustment_required: bool
    duplicate_equipment_id: int | None
    duplicate_reconciliation: bool
    invoice_statuses: tuple[str, ...]
    late_stage: bool
    updated_at: str | None

    def snapshot(self) -> dict[str, Any]:
        return {
            "service_order_id": self.service_order_id,
            "service_order_folio": self.service_order_folio,
            "service_order_status": self.service_order_status,
            "service_order_active": self.service_order_active,
            "technician_id": self.technician_id,
            "client_id": self.client_id,
            "quotation_id": self.quotation_id,
            "signature_status": self.signature_status,
            "signatures_confirmed": self.signatures_confirmed,
            "active_work_orders": [dict(item) for item in self.active_work_orders],
            "catalog_exists": self.catalog_exists,
            "catalog_active": self.catalog_active,
            "catalog_name": self.catalog_name,
            "scope_allowed": self.scope_allowed,
            "service_order_item_id": self.service_order_item_id,
            "commercial_adjustment_required": self.commercial_adjustment_required,
            "duplicate_equipment_id": self.duplicate_equipment_id,
            "duplicate_reconciliation": self.duplicate_reconciliation,
            "invoice_statuses": list(self.invoice_statuses),
            "late_stage": self.late_stage,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class AdditionalEquipmentResolutionContext:
    facts: AdditionalEquipmentFacts
    request: AdditionalEquipmentResolutionRequest

    def snapshot(self) -> dict[str, Any]:
        return {"facts": self.facts.snapshot(), "request": self.request.snapshot()}

    @property
    def context_hash(self) -> str:
        return canonical_sha256(self.snapshot())


@dataclass(frozen=True, slots=True)
class AdditionalEquipmentAnalysis:
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
class AdditionalEquipmentStrategy:
    key: AdditionalEquipmentStrategyKey
    rationale: str

    def snapshot(self) -> dict[str, str]:
        return {"key": self.key.value, "rationale": self.rationale}


@dataclass(frozen=True, slots=True)
class AdditionalEquipmentPlanStep:
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
            "compensation_operation_key": self.compensation_operation_key,
            "compensation_payload": dict(self.compensation_payload),
        }


@dataclass(frozen=True, slots=True)
class AdditionalEquipmentPlan:
    context_hash: str
    strategy: AdditionalEquipmentStrategy
    steps: tuple[AdditionalEquipmentPlanStep, ...]
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
class AdditionalEquipmentSimulation:
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
class AdditionalEquipmentAuthorizationRequirements:
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
class AdditionalEquipmentRevalidation:
    status: RevalidationStatus
    authorized_context_hash: str
    current_context_hash: str
    reason_codes: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status in {
            RevalidationStatus.VALID,
            RevalidationStatus.VALID_WITH_WARNINGS,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "authorized_context_hash": self.authorized_context_hash,
            "current_context_hash": self.current_context_hash,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True, slots=True)
class AdditionalEquipmentOperationOutcome:
    equipment_id: int
    service_order_id: int
    work_order_id: int
    work_order_number: int
    reconciliation_id: str
    created_work_order: bool
    certificate_id: int | None
    before_snapshot: dict[str, Any]
    after_snapshot: dict[str, Any]
    domain_transaction_reference: str
