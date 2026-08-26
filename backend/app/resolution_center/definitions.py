"""Registro institucional de presentación e integración del Centro."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping

from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.domain.definitions import ResolutionDefinition
from app.resolution_integrations.additional_equipment import (
    ADDITIONAL_EQUIPMENT_RESOLUTION_TYPE,
)
from app.resolution_integrations.certificates import CERTIFICATE_RESOLUTION_TYPE
from app.resolution_integrations.installed import (
    build_installed_resolution_integrations,
)


RequestFactory = Callable[[str, Mapping[str, Any]], object]
ContextHydrator = Callable[[Mapping[str, Any]], object]
SnapshotFactory = Callable[[object], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class ResolutionPresentation:
    """Metadata versionada que permite construir la consola sin condicionales."""

    name: str
    family: str
    description: str
    domain: str
    object_type: str
    object_route: str | None
    risk_level: str
    capabilities: tuple[str, ...]
    required_permissions: tuple[str, ...]
    supports_simulation: bool
    supports_compensation: bool
    parameter_schema: Mapping[str, Any]
    labels: Mapping[str, str]
    warnings: tuple[str, ...] = ()
    strategy_keys: tuple[str, ...] = ()
    plan_summary: str = ""
    expected_impacts: tuple[str, ...] = ()
    preserved_entities: tuple[str, ...] = ()
    step_description: str = ""

    def __post_init__(self) -> None:
        if self.risk_level not in {"low", "medium", "high", "critical"}:
            raise ValueError("invalid resolution presentation risk level")
        object.__setattr__(
            self,
            "parameter_schema",
            MappingProxyType(dict(self.parameter_schema)),
        )
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))


@dataclass(frozen=True, slots=True)
class ResolutionCenterDefinition:
    """Vincula definición canónica, presentación y fábrica de solicitud."""

    definition: ResolutionDefinition
    presentation: ResolutionPresentation
    request_factory: RequestFactory
    context_hydrator: ContextHydrator
    request_snapshot: SnapshotFactory

    @property
    def key(self) -> tuple[str, str]:
        return (
            str(self.definition.resolution_type),
            str(self.definition.version),
        )


class ResolutionCenterDefinitionRegistry:
    """Registro explícito y congelable para integraciones presentes y futuras."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], ResolutionCenterDefinition] = {}
        self._frozen = False

    def register(
        self,
        entry: ResolutionCenterDefinition,
        *,
        engine_registry: ResolutionRegistry,
    ) -> None:
        if self._frozen:
            raise RuntimeError("resolution center definition registry is frozen")
        if entry.key in self._entries:
            raise ValueError(f"duplicate center definition: {entry.key}")
        engine_registry.register(entry.definition)
        self._entries[entry.key] = entry

    def resolve(
        self,
        resolution_type: str,
        version: str,
    ) -> ResolutionCenterDefinition:
        try:
            return self._entries[(resolution_type, version)]
        except KeyError:
            raise LookupError(
                f"resolution center definition not found: "
                f"{resolution_type}@{version}"
            ) from None

    def list(self) -> tuple[ResolutionCenterDefinition, ...]:
        return tuple(self._entries[key] for key in sorted(self._entries))

    def freeze(self) -> None:
        self._frozen = True


class ResolutionCenterComponentResolver:
    """Despacha componentes por el manifiesto registrado, no por dominio."""

    def __init__(self, integrations: tuple[object, ...]) -> None:
        self._resolvers = {
            str(reference.key): integration.component_resolver
            for integration in integrations
            for reference in integration.definition.components.values()
        }

    def resolve(self, reference, /):
        try:
            resolver = self._resolvers[str(reference.key)]
        except KeyError:
            raise LookupError(
                f"resolution component not registered: {reference.key}"
            ) from None
        return resolver.resolve(reference)


def build_resolution_center_registry(
    session_factory,
    *,
    engine_registry: ResolutionRegistry,
    certificate_integration=None,
    additional_equipment_integration=None,
) -> tuple[ResolutionCenterDefinitionRegistry, tuple[object, ...]]:
    """Compone integraciones sin enseñar dominios concretos al Centro."""

    installed = build_installed_resolution_integrations(
        session_factory,
        certificate_integration=certificate_integration,
        additional_equipment_integration=additional_equipment_integration,
    )
    registry = ResolutionCenterDefinitionRegistry()
    for item in installed:
        registry.register(
            ResolutionCenterDefinition(
                definition=item.definition,
                presentation=ResolutionPresentation(**item.presentation),
                request_factory=item.request_factory,
                context_hydrator=item.context_hydrator,
                request_snapshot=item.request_snapshot,
            ),
            engine_registry=engine_registry,
        )
    registry.freeze()
    engine_registry.freeze()
    return registry, tuple(item.integration for item in installed)


__all__ = [
    "ADDITIONAL_EQUIPMENT_RESOLUTION_TYPE",
    "CERTIFICATE_RESOLUTION_TYPE",
    "ResolutionCenterDefinition",
    "ResolutionCenterDefinitionRegistry",
    "ResolutionCenterComponentResolver",
    "ResolutionPresentation",
    "build_resolution_center_registry",
]
