"""Puertos tipados para componentes registrables de una resolución."""

from __future__ import annotations

from typing import Protocol, TypeVar

from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
)

RequestT = TypeVar("RequestT", contravariant=True)
ContextT = TypeVar("ContextT")
AnalysisT = TypeVar("AnalysisT")
StrategyT = TypeVar("StrategyT")
PlanT = TypeVar("PlanT")
SimulationT = TypeVar("SimulationT")
AuthorizationRequirementsT = TypeVar("AuthorizationRequirementsT", covariant=True)
PermissionRequestT = TypeVar("PermissionRequestT", contravariant=True)
PermissionDecisionT = TypeVar("PermissionDecisionT", covariant=True)
RevalidationT = TypeVar("RevalidationT", covariant=True)
ExecutionT = TypeVar("ExecutionT", covariant=True)


class ResolutionComponent(Protocol):
    """Metadatos estables que toda implementación registrable debe exponer."""

    component_key: ComponentKey
    component_version: DefinitionVersion


class ContextProvider(ResolutionComponent, Protocol[RequestT, ContextT]):
    """Construye un contexto inmutable desde una solicitud tipada."""

    def build_context(self, request: RequestT, /) -> ContextT:
        """Construye el contexto que será persistido por fases posteriores."""


class Analyzer(ResolutionComponent, Protocol[ContextT, AnalysisT]):
    """Analiza un contexto sin producir efectos."""

    def analyze(self, context: ContextT, /) -> AnalysisT:
        """Devuelve un resultado de análisis reproducible."""


class StrategySelector(
    ResolutionComponent,
    Protocol[ContextT, AnalysisT, StrategyT],
):
    """Selecciona una estrategia sin ejecutar acciones de dominio."""

    def select_strategy(
        self,
        *,
        context: ContextT,
        analysis: AnalysisT,
    ) -> StrategyT:
        """Selecciona una estrategia compatible con contexto y análisis."""


class PlanBuilder(
    ResolutionComponent,
    Protocol[ContextT, AnalysisT, StrategyT, PlanT],
):
    """Construye el plan exacto que será simulado y autorizado."""

    def build_plan(
        self,
        *,
        context: ContextT,
        analysis: AnalysisT,
        strategy: StrategyT,
    ) -> PlanT:
        """Construye un plan determinista, todavía sin efectos."""


class Simulator(
    ResolutionComponent,
    Protocol[ContextT, PlanT, SimulationT],
):
    """Simula el plan exacto sin mutaciones ni reservas institucionales."""

    def simulate(self, *, context: ContextT, plan: PlanT) -> SimulationT:
        """Devuelve impactos, advertencias y bloqueos de la simulación."""


class AuthorizationPolicy(
    ResolutionComponent,
    Protocol[ContextT, PlanT, SimulationT, AuthorizationRequirementsT],
):
    """Calcula requisitos de autorización versionados."""

    def authorization_requirements(
        self,
        *,
        context: ContextT,
        plan: PlanT,
        simulation: SimulationT,
    ) -> AuthorizationRequirementsT:
        """Devuelve requisitos; no toma ni persiste decisiones humanas."""


class PermissionPolicy(
    ResolutionComponent,
    Protocol[PermissionRequestT, PermissionDecisionT],
):
    """Evalúa una solicitud de permiso mediante una política tipada."""

    def evaluate_permission(
        self,
        request: PermissionRequestT,
        /,
    ) -> PermissionDecisionT:
        """Devuelve la decisión explicable de la política."""


class Revalidator(
    ResolutionComponent,
    Protocol[ContextT, PlanT, SimulationT, RevalidationT],
):
    """Compara el plan autorizado contra un contexto recién reconstruido."""

    def revalidate(
        self,
        *,
        authorized_context: ContextT,
        current_context: ContextT,
        plan: PlanT,
        simulation: SimulationT,
    ) -> RevalidationT:
        """Determina si el plan exacto conserva vigencia."""


class Executor(
    ResolutionComponent,
    Protocol[ContextT, PlanT, ExecutionT],
):
    """Puerto de ejecución; su implementación y uso pertenecen a Fase 5."""

    def execute(self, *, context: ContextT, plan: PlanT) -> ExecutionT:
        """Ejecuta un plan ya autorizado y revalidado."""
