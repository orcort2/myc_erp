"""Registro institucional de presentación e integración del Centro."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping

from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.domain.definitions import ResolutionDefinition
from app.resolution_integrations.certificates import (
    CERTIFICATE_RESOLUTION_TYPE,
    build_certificate_resolution_integration,
)
from app.resolution_integrations.certificates.domain import (
    CertificateFacts,
    CertificateResolutionContext,
    CertificateResolutionRequest,
)


RequestFactory = Callable[[str, Mapping[str, Any]], object]
ContextHydrator = Callable[[Mapping[str, Any]], object]
SnapshotFactory = Callable[[object], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class ResolutionPresentation:
    """Metadata versionada que permite construir la consola sin condicionales."""

    name: str
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
) -> tuple[ResolutionCenterDefinitionRegistry, tuple[object, ...]]:
    """Compone integraciones sin enseñar dominios concretos al Centro."""

    integration = (
        certificate_integration
        or build_certificate_resolution_integration(session_factory)
    )
    registry = ResolutionCenterDefinitionRegistry()
    registry.register(
        ResolutionCenterDefinition(
            definition=integration.definition,
            presentation=ResolutionPresentation(
                name="Retiro de certificado liberado incorrectamente",
                description=integration.definition.description,
                domain="certificates",
                object_type="certificate",
                object_route="/dashboard#certificados",
                risk_level="high",
                capabilities=(
                    "context",
                    "analysis",
                    "plan",
                    "simulation",
                    "authorization",
                    "distributed_execution",
                    "compensation",
                ),
                required_permissions=(
                    "certificates.approve",
                    "certificates.release",
                ),
                supports_simulation=True,
                supports_compensation=True,
                parameter_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["reason"],
                    "properties": {
                        "reason": {
                            "type": "string",
                            "title": "Motivo institucional",
                            "description": (
                                "Explique por qué la liberación debe corregirse."
                            ),
                            "minLength": 1,
                            "maxLength": 2000,
                            "ui:widget": "textarea",
                            "ui:rows": 4,
                        }
                    },
                },
                labels={
                    "subject": "Certificado",
                    "subject_placeholder": "ID del certificado",
                    "create_title": "Retiro administrativo de acceso",
                    "analysis": "Validación de liberación y visibilidad",
                    "simulation": "Impacto previsto sobre acceso del cliente",
                    "result": "Resultado del retiro de acceso",
                },
                warnings=(
                    "Retira visibilidad futura sin reescribir la liberación histórica.",
                ),
            ),
            request_factory=lambda subject_id, parameters: (
                CertificateResolutionRequest(
                    certificate_id=int(subject_id),
                    reason=str(parameters["reason"]),
                )
            ),
            context_hydrator=lambda snapshot: CertificateResolutionContext(
                facts=CertificateFacts(**snapshot["facts"]),
                reason=str(snapshot["reason"]),
            ),
            request_snapshot=lambda request: {
                "certificate_id": request.certificate_id,
                "reason": request.reason,
            },
        ),
        engine_registry=engine_registry,
    )
    registry.freeze()
    engine_registry.freeze()
    return registry, (integration,)


__all__ = [
    "CERTIFICATE_RESOLUTION_TYPE",
    "ResolutionCenterDefinition",
    "ResolutionCenterDefinitionRegistry",
    "ResolutionCenterComponentResolver",
    "ResolutionPresentation",
    "build_resolution_center_registry",
]
