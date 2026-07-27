"""Selección versionada y coordinación sin efectos de componentes puros."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.contracts.lifecycle import ComponentResolver
from app.resolution_engine.domain.definitions import ComponentReference
from app.resolution_engine.domain.enums import ComponentKind
from app.resolution_engine.domain.exceptions import ComponentBindingError


@dataclass(frozen=True, slots=True)
class WorkflowSelection:
    """Definición exacta seleccionada para reproducir un flujo."""

    resolution_type: str
    definition_version: str
    definition_fingerprint: str


class ResolutionOrchestrator:
    """Coordina únicamente etapas puras hasta revalidación."""

    def __init__(
        self,
        *,
        registry: ResolutionRegistry,
        components: ComponentResolver,
    ) -> None:
        self._registry = registry
        self._components = components

    def selection(
        self,
        resolution_type: str,
        definition_version: str,
    ) -> WorkflowSelection:
        definition = self._registry.resolve(
            resolution_type,
            definition_version,
        )
        return WorkflowSelection(
            resolution_type=str(definition.resolution_type),
            definition_version=str(definition.version),
            definition_fingerprint=definition.fingerprint,
        )

    def build_context(
        self,
        *,
        resolution_type: str,
        definition_version: str,
        request: Any,
    ) -> Any:
        component = self._component(
            resolution_type,
            definition_version,
            ComponentKind.CONTEXT_PROVIDER,
            "build_context",
        )
        return component.build_context(request)

    def analyze(
        self,
        *,
        resolution_type: str,
        definition_version: str,
        context: Any,
    ) -> Any:
        component = self._component(
            resolution_type,
            definition_version,
            ComponentKind.ANALYZER,
            "analyze",
        )
        return component.analyze(context)

    def build_plan(
        self,
        *,
        resolution_type: str,
        definition_version: str,
        context: Any,
        analysis: Any,
    ) -> tuple[Any, Any]:
        selector = self._component(
            resolution_type,
            definition_version,
            ComponentKind.STRATEGY_SELECTOR,
            "select_strategy",
        )
        strategy = selector.select_strategy(
            context=context,
            analysis=analysis,
        )
        builder = self._component(
            resolution_type,
            definition_version,
            ComponentKind.PLAN_BUILDER,
            "build_plan",
        )
        plan = builder.build_plan(
            context=context,
            analysis=analysis,
            strategy=strategy,
        )
        return strategy, plan

    def simulate(
        self,
        *,
        resolution_type: str,
        definition_version: str,
        context: Any,
        plan: Any,
    ) -> Any:
        simulator = self._component(
            resolution_type,
            definition_version,
            ComponentKind.SIMULATOR,
            "simulate",
        )
        return simulator.simulate(context=context, plan=plan)

    def authorization_requirements(
        self,
        *,
        resolution_type: str,
        definition_version: str,
        context: Any,
        plan: Any,
        simulation: Any,
    ) -> Any:
        policy = self._component(
            resolution_type,
            definition_version,
            ComponentKind.AUTHORIZATION_POLICY,
            "authorization_requirements",
        )
        return policy.authorization_requirements(
            context=context,
            plan=plan,
            simulation=simulation,
        )

    def revalidate(
        self,
        *,
        resolution_type: str,
        definition_version: str,
        authorized_context: Any,
        current_context: Any,
        plan: Any,
        simulation: Any,
    ) -> Any:
        revalidator = self._component(
            resolution_type,
            definition_version,
            ComponentKind.REVALIDATOR,
            "revalidate",
        )
        return revalidator.revalidate(
            authorized_context=authorized_context,
            current_context=current_context,
            plan=plan,
            simulation=simulation,
        )

    def _component(
        self,
        resolution_type: str,
        definition_version: str,
        kind: ComponentKind,
        required_method: str,
    ) -> Any:
        definition = self._registry.resolve(
            resolution_type,
            definition_version,
        )
        reference = definition.component(kind)
        if reference is None:
            raise ComponentBindingError(
                f"Definition {resolution_type}@{definition_version} "
                f"does not declare {kind.value}"
            )
        component = self._components.resolve(reference)
        self._validate_binding(reference, component, required_method)
        return component

    @staticmethod
    def _validate_binding(
        reference: ComponentReference,
        component: object,
        required_method: str,
    ) -> None:
        if not isinstance(component, reference.implementation):
            raise ComponentBindingError(
                f"Component {reference.key}@{reference.version} has an "
                "unexpected implementation"
            )
        if (
            getattr(component, "component_key", None) != reference.key
            or getattr(component, "component_version", None)
            != reference.version
            or not callable(getattr(component, required_method, None))
        ):
            raise ComponentBindingError(
                f"Component {reference.key}@{reference.version} does not "
                f"satisfy {reference.kind.value}"
            )
