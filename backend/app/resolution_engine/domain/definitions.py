"""Definiciones inmutables y registrables de tipos de resolución."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.enums import ComponentKind
from app.resolution_engine.domain.exceptions import (
    InvalidResolutionDefinitionError,
)
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
    ResolutionType,
)


@dataclass(frozen=True, slots=True)
class ComponentReference:
    """Referencia versionada a una clase que satisface un contrato del Motor."""

    kind: ComponentKind
    key: ComponentKey
    version: DefinitionVersion
    implementation: type[Any]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ComponentKind):
            raise InvalidResolutionDefinitionError("invalid component kind")
        if not isinstance(self.key, ComponentKey):
            raise InvalidResolutionDefinitionError("invalid component key")
        if not isinstance(self.version, DefinitionVersion):
            raise InvalidResolutionDefinitionError("invalid component version")
        if not isinstance(self.implementation, type):
            raise InvalidResolutionDefinitionError(
                "component implementation must be a class"
            )

    def manifest(self) -> dict[str, str]:
        return {
            "kind": self.kind.value,
            "key": str(self.key),
            "version": str(self.version),
            "implementation": (
                f"{self.implementation.__module__}."
                f"{self.implementation.__qualname__}"
            ),
        }


@dataclass(frozen=True, slots=True)
class ResolutionDefinition:
    """Manifiesto inmutable de los componentes de un tipo/version."""

    resolution_type: ResolutionType
    version: DefinitionVersion
    components: Mapping[ComponentKind, ComponentReference]
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.resolution_type, ResolutionType):
            raise InvalidResolutionDefinitionError("invalid resolution type")
        if not isinstance(self.version, DefinitionVersion):
            raise InvalidResolutionDefinitionError("invalid definition version")
        if not isinstance(self.description, str):
            raise InvalidResolutionDefinitionError("description must be text")

        normalized: dict[ComponentKind, ComponentReference] = {}
        for kind, reference in self.components.items():
            if not isinstance(kind, ComponentKind):
                raise InvalidResolutionDefinitionError(
                    "component mapping contains an invalid kind"
                )
            if not isinstance(reference, ComponentReference):
                raise InvalidResolutionDefinitionError(
                    "component mapping contains an invalid reference"
                )
            if reference.kind != kind:
                raise InvalidResolutionDefinitionError(
                    f"component key {kind.value} does not match its reference"
                )
            normalized[kind] = reference
        if not normalized:
            raise InvalidResolutionDefinitionError(
                "a resolution definition requires at least one component"
            )
        object.__setattr__(self, "components", MappingProxyType(normalized))

    def component(self, kind: ComponentKind) -> ComponentReference | None:
        return self.components.get(kind)

    def manifest(self) -> dict[str, Any]:
        return {
            "resolution_type": str(self.resolution_type),
            "version": str(self.version),
            "description": self.description,
            "components": [
                self.components[kind].manifest()
                for kind in sorted(self.components, key=lambda item: item.value)
            ],
        }

    @property
    def fingerprint(self) -> str:
        """Hash determinista de identidad y componentes de la definición."""

        return canonical_sha256(self.manifest())
