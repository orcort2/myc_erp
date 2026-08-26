"""Definiciones versionadas de restauración, reconstrucción y baja de ETS."""

from __future__ import annotations

from dataclasses import dataclass

from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.domain.definitions import ComponentReference, ResolutionDefinition
from app.resolution_engine.domain.enums import AnalysisStatus, ComponentKind, RevalidationStatus, SimulationStatus
from app.resolution_engine.domain.value_objects import ComponentKey, DefinitionVersion, ResolutionType

from .domain import (
    AdministrationAnalysis,
    AdministrationAuthorizationRequirements,
    AdministrationPlan,
    AdministrationPlanStep,
    AdministrationRevalidation,
    AdministrationSimulation,
    AdministrationStrategy,
    AdministrationStrategyKey,
    ServiceOrderAdministrationContext,
    ServiceOrderAdministrationRequest,
)

VERSION = DefinitionVersion("1.0")
RESTORE_RESOLUTION_TYPE = ResolutionType("service_order.restore_soft_deleted")
REBUILD_RESOLUTION_TYPE = ResolutionType("service_order.rebuild_from_accepted_quotation")
VOID_RESOLUTION_TYPE = ResolutionType("service_order.void_preserving_history")
OPERATION_KEY = "service_orders.execute_administrative_operation"


class AdministrationContextProvider:
    component_key = ComponentKey("service_orders.administration.context")
    component_version = VERSION

    def __init__(self, reader) -> None:
        self._reader = reader

    def build_context(self, request: ServiceOrderAdministrationRequest, /):
        return ServiceOrderAdministrationContext(self._reader.read(request), request)


class AdministrationAnalyzer:
    component_key = ComponentKey("service_orders.administration.analyzer")
    component_version = VERSION

    def analyze(self, context, /):
        status = AnalysisStatus.RESOLVABLE if context.facts.allowed else AnalysisStatus.BLOCKED
        reasons = ("requires_administrative_authorization",) if context.facts.allowed else context.facts.blockers
        return AdministrationAnalysis(status, tuple(reasons), context.context_hash)


class AdministrationStrategySelector:
    component_key = ComponentKey("service_orders.administration.strategy")
    component_version = VERSION

    def select_strategy(self, *, context, analysis):
        return AdministrationStrategy(
            key=(AdministrationStrategyKey(context.request.operation)
                 if analysis.is_resolvable else AdministrationStrategyKey.NO_ACTION),
            rationale=("Ejecutar únicamente la operación administrativa autorizada."
                       if analysis.is_resolvable else "Los bloqueantes impiden modificar el ETS."),
        )


class AdministrationPlanBuilder:
    component_key = ComponentKey("service_orders.administration.plan")
    component_version = VERSION

    def build_plan(self, *, context, analysis, strategy):
        if not analysis.is_resolvable:
            return AdministrationPlan(context.context_hash, strategy, (), context.facts.blockers)
        return AdministrationPlan(
            context.context_hash,
            strategy,
            (AdministrationPlanStep(
                step_key=f"{context.request.operation}_service_order",
                operation_key=OPERATION_KEY,
                owner_module="service_orders",
                input_payload={
                    **context.request.snapshot(),
                    "expected_service_order_id": context.facts.service_order_id,
                    "expected_active_sibling_id": context.facts.active_sibling_id,
                    "expected_updated_at": context.facts.updated_at,
                },
            ),),
        )


class AdministrationSimulator:
    component_key = ComponentKey("service_orders.administration.simulator")
    component_version = VERSION

    def simulate(self, *, context, plan):
        return AdministrationSimulation(
            status=(SimulationStatus.BLOCKED if plan.blockers else
                    (SimulationStatus.VALID_WITH_WARNINGS if context.facts.warnings else SimulationStatus.VALID)),
            plan_hash=plan.plan_hash,
            impacts=context.facts.proposed_changes,
            preserved_evidence=(
                "quotation.frozen_snapshot", "service_order.source_snapshot",
                "service_order.items", "certificates", "invoices", "resolution.audit_events",
            ),
            blockers=plan.blockers,
        )


class AdministrationAuthorizationPolicy:
    component_key = ComponentKey("service_orders.administration.authorization")
    component_version = VERSION

    def authorization_requirements(self, *, context, plan, simulation):
        return AdministrationAuthorizationRequirements(
            required_permissions=(f"service_orders.administration.{context.request.operation}.authorize",),
            required_functions=("administrative_control",),
            plan_hash=plan.plan_hash,
        )


class AdministrationRevalidator:
    component_key = ComponentKey("service_orders.administration.revalidator")
    component_version = VERSION

    def revalidate(self, *, authorized_context, current_context, plan, simulation):
        unchanged = authorized_context.context_hash == current_context.context_hash
        return AdministrationRevalidation(
            RevalidationStatus.VALID if unchanged else RevalidationStatus.REQUIRES_NEW_PLAN,
            authorized_context.context_hash,
            current_context.context_hash,
            ("administrative_context_unchanged",) if unchanged else ("administrative_context_changed",),
        )


COMPONENTS = {
    ComponentKind.CONTEXT_PROVIDER: AdministrationContextProvider,
    ComponentKind.ANALYZER: AdministrationAnalyzer,
    ComponentKind.STRATEGY_SELECTOR: AdministrationStrategySelector,
    ComponentKind.PLAN_BUILDER: AdministrationPlanBuilder,
    ComponentKind.SIMULATOR: AdministrationSimulator,
    ComponentKind.AUTHORIZATION_POLICY: AdministrationAuthorizationPolicy,
    ComponentKind.REVALIDATOR: AdministrationRevalidator,
}


def build_definition(resolution_type: ResolutionType, description: str) -> ResolutionDefinition:
    return ResolutionDefinition(
        resolution_type=resolution_type,
        version=VERSION,
        description=description,
        components={kind: ComponentReference(kind, implementation.component_key, VERSION, implementation)
                    for kind, implementation in COMPONENTS.items()},
    )


@dataclass(frozen=True, slots=True)
class ServiceOrderAdministrationIntegration:
    definition: ResolutionDefinition
    component_resolver: object
    action_handlers: tuple[object, ...]
    compensation_handlers: tuple[object, ...] = ()

    def register(self, registry: ResolutionRegistry) -> None:
        registry.register(self.definition)
