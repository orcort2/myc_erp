"""Errores explícitos de la fundación del Motor de Resoluciones."""

from __future__ import annotations


class ResolutionEngineError(Exception):
    """Base de errores propios del Motor."""


class InvalidResolutionValueError(ResolutionEngineError, ValueError):
    """Un value object no cumple su contrato estable."""


class InvalidResolutionDefinitionError(ResolutionEngineError, ValueError):
    """Una definición registrable está incompleta o es inconsistente."""


class CanonicalizationError(ResolutionEngineError, ValueError):
    """Un valor no puede representarse de forma canónica y segura."""


class DuplicateResolutionDefinitionError(ResolutionEngineError):
    """Ya existe la misma combinación tipo/versión."""

    def __init__(self, *, resolution_type: str, version: str) -> None:
        super().__init__(
            f"Resolution definition already registered: "
            f"{resolution_type}@{version}"
        )
        self.resolution_type = resolution_type
        self.version = version


class ResolutionDefinitionNotFoundError(ResolutionEngineError, LookupError):
    """No existe la versión solicitada de una definición."""

    def __init__(self, *, resolution_type: str, version: str) -> None:
        super().__init__(
            f"Resolution definition not found: {resolution_type}@{version}"
        )
        self.resolution_type = resolution_type
        self.version = version


class NoActiveResolutionDefinitionError(ResolutionEngineError, LookupError):
    """El tipo existe o puede existir, pero no tiene versión activa."""

    def __init__(self, *, resolution_type: str) -> None:
        super().__init__(
            f"Resolution type has no active definition: {resolution_type}"
        )
        self.resolution_type = resolution_type


class ResolutionRegistryFrozenError(ResolutionEngineError):
    """El registro ya fue cerrado para el proceso actual."""

    def __init__(self) -> None:
        super().__init__("Resolution registry is frozen")
