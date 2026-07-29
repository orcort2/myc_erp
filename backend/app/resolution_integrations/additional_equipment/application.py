"""Definición versionada del vertical de equipo adicional."""

from __future__ import annotations

from dataclasses import dataclass

from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.domain.definitions import ComponentReference, ResolutionDefinition
from app.resolution_engine.domain.enums import (
    AnalysisStatus,
    ComponentKind,
    RevalidationStatus,
    SimulationStatus,
)
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
    ResolutionType,
)
from app.resolution_integrations.additional_equipment.contracts import (
    AdditionalEquipmentFactsReader,
)
from app.resolution_integrations.additional_equipment.domain import (
    AdditionalEquipmentAnalysis,
    AdditionalEquipmentAuthorizationRequirements,
    AdditionalEquipmentPlan,
    AdditionalEquipmentPlanStep,
    AdditionalEquipmentResolutionContext,
    AdditionalEquipmentResolutionRequest,
    AdditionalEquipmentRevalidation,
    AdditionalEquipmentSimulation,
    AdditionalEquipmentStrategy,
    AdditionalEquipmentStrategyKey,
)


ADDITIONAL_EQUIPMENT_RESOLUTION_TYPE = ResolutionType(
    "service_order.resolve_additional_equipment"
)
ADDITIONAL_EQUIPMENT_RESOLUTION_VERSION = DefinitionVersion("1.0")
REGISTER_OPERATION = "service_orders.register_additional_equipment"
COMPENSATE_OPERATION = "service_orders.compensate_additional_equipment"


class AdditionalEquipmentContextProvider:
    component_key = ComponentKey("service_orders.additional_equipment.context")
    component_version = ADDITIONAL_EQUIPMENT_RESOLUTION_VERSION

    def __init__(self, reader: AdditionalEquipmentFactsReader) -> None:
        self._reader = reader

    def build_context(
        self,
        request: AdditionalEquipmentResolutionRequest,
        /,
    ) -> AdditionalEquipmentResolutionContext:
        return AdditionalEquipmentResolutionContext(
            facts=self._reader.read(request),
            request=request,
        )


class AdditionalEquipmentAnalyzer:
    component_key = ComponentKey("service_orders.additional_equipment.analyzer")
    component_version = ADDITIONAL_EQUIPMENT_RESOLUTION_VERSION

    def analyze(
        self,
        context: AdditionalEquipmentResolutionContext,
        /,
    ) -> AdditionalEquipmentAnalysis:
        facts = context.facts
        reasons: list[str] = []
        if not facts.service_order_active or facts.service_order_status in {
            "closed",
            "cancelled",
        }:
            status = AnalysisStatus.BLOCKED
            reasons.append("blocked_service_state")
        elif facts.duplicate_reconciliation:
            status = AnalysisStatus.ALREADY_RESOLVED
            reasons.append("already_resolved")
        elif facts.duplicate_equipment_id is not None:
            status = AnalysisStatus.ALREADY_RESOLVED
            reasons.extend(("duplicate_equipment", "already_registered"))
        elif not facts.catalog_exists or not facts.catalog_active:
            status = AnalysisStatus.REQUIRES_INFORMATION
            reasons.append("missing_catalog")
        elif not facts.scope_allowed:
            status = AnalysisStatus.BLOCKED
            reasons.append("invalid_classification")
        else:
            status = AnalysisStatus.RESOLVABLE
            reasons.append("requires_authorization")
            if facts.signatures_confirmed:
                reasons.append("requires_signature")
            if facts.commercial_adjustment_required:
                reasons.append("requires_commercial_adjustment")
            if facts.late_stage:
                reasons.extend(("late_stage_warning", "requires_manual_review"))
        return AdditionalEquipmentAnalysis(
            status=status,
            reason_codes=tuple(reasons),
            context_hash=context.context_hash,
        )


class AdditionalEquipmentStrategySelector:
    component_key = ComponentKey("service_orders.additional_equipment.strategy")
    component_version = ADDITIONAL_EQUIPMENT_RESOLUTION_VERSION

    def select_strategy(
        self,
        *,
        context: AdditionalEquipmentResolutionContext,
        analysis: AdditionalEquipmentAnalysis,
    ) -> AdditionalEquipmentStrategy:
        if analysis.status is AnalysisStatus.ALREADY_RESOLVED:
            return AdditionalEquipmentStrategy(
                key=AdditionalEquipmentStrategyKey.NO_ACTION,
                rationale="La propuesta ya fue conciliada o el equipo ya existe.",
            )
        if "requires_signature" in analysis.reason_codes:
            key = AdditionalEquipmentStrategyKey.PENDING_SIGNATURE
            rationale = "Registrar el equipo y abrir el seguimiento de nueva firma."
        elif "requires_commercial_adjustment" in analysis.reason_codes:
            key = AdditionalEquipmentStrategyKey.PENDING_COMMERCIAL_ADJUSTMENT
            rationale = "Registrar el equipo y señalar el ajuste comercial pendiente."
        elif _available_slots(context) >= context.request.quantity:
            key = AdditionalEquipmentStrategyKey.ATTACH_EXISTING_WORK_ORDER
            rationale = "Usar una OT activa con capacidad suficiente."
        else:
            key = AdditionalEquipmentStrategyKey.CREATE_NEW_WORK_ORDER
            rationale = "Crear una OT adicional con el límite institucional."
        return AdditionalEquipmentStrategy(key=key, rationale=rationale)


class AdditionalEquipmentPlanBuilder:
    component_key = ComponentKey("service_orders.additional_equipment.plan")
    component_version = ADDITIONAL_EQUIPMENT_RESOLUTION_VERSION

    def build_plan(
        self,
        *,
        context: AdditionalEquipmentResolutionContext,
        analysis: AdditionalEquipmentAnalysis,
        strategy: AdditionalEquipmentStrategy,
    ) -> AdditionalEquipmentPlan:
        if not analysis.is_resolvable:
            return AdditionalEquipmentPlan(
                context_hash=context.context_hash,
                strategy=strategy,
                steps=(),
                blockers=analysis.reason_codes,
            )
        request = context.request
        steps = []
        for position in range(1, request.quantity + 1):
            reconciliation_id = (
                request.reconciliation_id
                if request.quantity == 1
                else f"{request.reconciliation_id}:{position}"
            )
            payload = {
                **request.snapshot(),
                "quantity": 1,
                "reconciliation_id": reconciliation_id,
                "expected_service_order_status": context.facts.service_order_status,
                "service_order_item_id": context.facts.service_order_item_id,
                "allow_new_work_order": True,
                "requires_signature": context.facts.signatures_confirmed,
                "requires_commercial_adjustment": (
                    context.facts.commercial_adjustment_required
                ),
            }
            steps.append(
                AdditionalEquipmentPlanStep(
                    step_key=f"register_additional_equipment_{position}",
                    operation_key=REGISTER_OPERATION,
                    owner_module="service_orders",
                    input_payload=payload,
                    compensation_operation_key=COMPENSATE_OPERATION,
                    compensation_payload={
                        "service_order_id": request.service_order_id,
                        "reconciliation_id": reconciliation_id,
                    },
                )
            )
        return AdditionalEquipmentPlan(
            context_hash=context.context_hash,
            strategy=strategy,
            steps=tuple(steps),
        )


class AdditionalEquipmentSimulator:
    component_key = ComponentKey("service_orders.additional_equipment.simulator")
    component_version = ADDITIONAL_EQUIPMENT_RESOLUTION_VERSION

    def simulate(
        self,
        *,
        context: AdditionalEquipmentResolutionContext,
        plan: AdditionalEquipmentPlan,
    ) -> AdditionalEquipmentSimulation:
        impacts: list[str] = []
        if not plan.blockers:
            expected_work_order = _expected_work_order_impact(context, plan)
            impacts.extend(
                (
                    f"service_order:{context.request.service_order_id}",
                    f"equipment:{context.request.name.strip()}",
                    f"classification:{context.request.calibration_scope}",
                    f"equipment:+{context.request.quantity}",
                    expected_work_order,
                    "certificate:provisional_reference_only_until_execution",
                    "field_sheet:not_created",
                    "capture:pending",
                    "quality:pending",
                    (
                        "invoice:commercial_review_required"
                        if context.facts.commercial_adjustment_required
                        else "invoice:no_automatic_change"
                    ),
                    "reversible:unprocessed_equipment_and_empty_created_work_order",
                    "irreversible:evidence_signatures_authorized_documents_consumed_folios",
                )
            )
            if context.facts.signatures_confirmed:
                impacts.append("signature:new_cycle_required")
            if context.facts.commercial_adjustment_required:
                impacts.append("commercial:adjustment_required")
        warnings = (
            context.facts.late_stage
            or context.facts.commercial_adjustment_required
        )
        return AdditionalEquipmentSimulation(
            status=(
                SimulationStatus.BLOCKED
                if plan.blockers
                else (
                    SimulationStatus.VALID_WITH_WARNINGS
                    if warnings
                    else SimulationStatus.VALID
                )
            ),
            plan_hash=plan.plan_hash,
            impacts=tuple(impacts),
            preserved_evidence=(
                "service_order.signature_history",
                "service_order.quotation_history",
                "invoice.issued_documents",
                "certificate.authorized_documents",
                "resolution.audit_events",
            ),
            blockers=plan.blockers,
        )


class AdditionalEquipmentAuthorizationPolicy:
    component_key = ComponentKey(
        "service_orders.additional_equipment.authorization"
    )
    component_version = ADDITIONAL_EQUIPMENT_RESOLUTION_VERSION

    def authorization_requirements(
        self,
        *,
        context: AdditionalEquipmentResolutionContext,
        plan: AdditionalEquipmentPlan,
        simulation: AdditionalEquipmentSimulation,
    ) -> AdditionalEquipmentAuthorizationRequirements:
        permissions = [
            "service_orders.additional_equipment.authorize",
        ]
        functions = ["technical_operations"]
        if context.facts.commercial_adjustment_required:
            permissions.append(
                "service_orders.additional_equipment.commercial_review"
            )
            functions.append("commercial")
        return AdditionalEquipmentAuthorizationRequirements(
            required_permissions=tuple(permissions),
            required_functions=tuple(functions),
            plan_hash=plan.plan_hash,
        )


class AdditionalEquipmentRevalidator:
    component_key = ComponentKey("service_orders.additional_equipment.revalidator")
    component_version = ADDITIONAL_EQUIPMENT_RESOLUTION_VERSION

    def revalidate(
        self,
        *,
        authorized_context: AdditionalEquipmentResolutionContext,
        current_context: AdditionalEquipmentResolutionContext,
        plan: AdditionalEquipmentPlan,
        simulation: AdditionalEquipmentSimulation,
    ) -> AdditionalEquipmentRevalidation:
        if authorized_context.context_hash == current_context.context_hash:
            status = RevalidationStatus.VALID
            reasons = ("service_order_context_unchanged",)
        else:
            status = RevalidationStatus.REQUIRES_NEW_PLAN
            reasons = ("critical_service_order_facts_changed",)
        return AdditionalEquipmentRevalidation(
            status=status,
            authorized_context_hash=authorized_context.context_hash,
            current_context_hash=current_context.context_hash,
            reason_codes=reasons,
        )


def _available_slots(context: AdditionalEquipmentResolutionContext) -> int:
    return sum(int(item["available_slots"]) for item in context.facts.active_work_orders)


def _expected_work_order_impact(
    context: AdditionalEquipmentResolutionContext,
    plan: AdditionalEquipmentPlan,
) -> str:
    if (
        plan.strategy.key
        is AdditionalEquipmentStrategyKey.ATTACH_EXISTING_WORK_ORDER
    ):
        candidate = next(
            (
                item
                for item in context.facts.active_work_orders
                if int(item["available_slots"]) >= context.request.quantity
            ),
            None,
        )
        if candidate is not None:
            position = int(candidate["equipment_count"]) + 1
            return (
                f"work_order:existing:{candidate['id']}:"
                f"position:{position}:limit:10"
            )
    return "work_order:new_on_execution:position:1:limit:10"


COMPONENT_IMPLEMENTATIONS = {
    ComponentKind.CONTEXT_PROVIDER: AdditionalEquipmentContextProvider,
    ComponentKind.ANALYZER: AdditionalEquipmentAnalyzer,
    ComponentKind.STRATEGY_SELECTOR: AdditionalEquipmentStrategySelector,
    ComponentKind.PLAN_BUILDER: AdditionalEquipmentPlanBuilder,
    ComponentKind.SIMULATOR: AdditionalEquipmentSimulator,
    ComponentKind.AUTHORIZATION_POLICY: AdditionalEquipmentAuthorizationPolicy,
    ComponentKind.REVALIDATOR: AdditionalEquipmentRevalidator,
}


def build_additional_equipment_resolution_definition() -> ResolutionDefinition:
    return ResolutionDefinition(
        resolution_type=ADDITIONAL_EQUIPMENT_RESOLUTION_TYPE,
        version=ADDITIONAL_EQUIPMENT_RESOLUTION_VERSION,
        description=(
            "Concilia y registra equipo adicional de un ETS mediante "
            "autorización, revalidación y ejecución determinista."
        ),
        components={
            kind: ComponentReference(
                kind=kind,
                key=implementation.component_key,
                version=ADDITIONAL_EQUIPMENT_RESOLUTION_VERSION,
                implementation=implementation,
            )
            for kind, implementation in COMPONENT_IMPLEMENTATIONS.items()
        },
    )


@dataclass(frozen=True, slots=True)
class AdditionalEquipmentResolutionIntegration:
    definition: ResolutionDefinition
    component_resolver: object
    action_handlers: tuple[object, ...]
    compensation_handlers: tuple[object, ...]

    def register(self, registry: ResolutionRegistry) -> None:
        registry.register(self.definition)
