"""Registro versionado de definiciones del Motor de Resoluciones."""

from __future__ import annotations

from threading import RLock

from app.resolution_engine.domain.definitions import ResolutionDefinition
from app.resolution_engine.domain.exceptions import (
    DuplicateResolutionDefinitionError,
    NoActiveResolutionDefinitionError,
    ResolutionDefinitionNotFoundError,
    ResolutionRegistryFrozenError,
)
from app.resolution_engine.domain.value_objects import (
    DefinitionVersion,
    ResolutionType,
)


class ResolutionRegistry:
    """Registro explícito, versionado y cerrado a condicionales por dominio.

    Las definiciones se registran fuera del núcleo. Varias versiones pueden
    coexistir y sólo una se marca como activa para nuevas resoluciones. Las
    resoluciones históricas deben solicitar su versión exacta.
    """

    def __init__(self) -> None:
        self._definitions: dict[
            tuple[ResolutionType, DefinitionVersion], ResolutionDefinition
        ] = {}
        self._active_versions: dict[ResolutionType, DefinitionVersion] = {}
        self._frozen = False
        self._lock = RLock()

    @property
    def is_frozen(self) -> bool:
        """Indica si el registro ya no acepta cambios."""

        with self._lock:
            return self._frozen

    def register(
        self,
        definition: ResolutionDefinition,
        *,
        activate: bool = True,
    ) -> None:
        """Registra una definición sin modificar el núcleo.

        ``activate=True`` la convierte en la versión usada para nuevas
        resoluciones. Registrar versiones históricas con ``activate=False``
        permite reconstruir decisiones anteriores sin reactivarlas.
        """

        key = (definition.resolution_type, definition.version)
        with self._lock:
            self._ensure_mutable()
            if key in self._definitions:
                raise DuplicateResolutionDefinitionError(
                    resolution_type=str(definition.resolution_type),
                    version=str(definition.version),
                )
            self._definitions[key] = definition
            if activate:
                self._active_versions[definition.resolution_type] = definition.version

    def activate(
        self,
        resolution_type: ResolutionType | str,
        version: DefinitionVersion | str,
    ) -> None:
        """Marca una versión ya registrada como activa."""

        normalized_type = ResolutionType.parse(resolution_type)
        normalized_version = DefinitionVersion.parse(version)
        key = (normalized_type, normalized_version)
        with self._lock:
            self._ensure_mutable()
            if key not in self._definitions:
                raise ResolutionDefinitionNotFoundError(
                    resolution_type=str(normalized_type),
                    version=str(normalized_version),
                )
            self._active_versions[normalized_type] = normalized_version

    def resolve(
        self,
        resolution_type: ResolutionType | str,
        version: DefinitionVersion | str | None = None,
    ) -> ResolutionDefinition:
        """Obtiene la versión exacta o la versión activa de una definición."""

        normalized_type = ResolutionType.parse(resolution_type)
        with self._lock:
            if version is None:
                active_version = self._active_versions.get(normalized_type)
                if active_version is None:
                    raise NoActiveResolutionDefinitionError(
                        resolution_type=str(normalized_type)
                    )
                normalized_version = active_version
            else:
                normalized_version = DefinitionVersion.parse(version)

            definition = self._definitions.get(
                (normalized_type, normalized_version)
            )
            if definition is None:
                raise ResolutionDefinitionNotFoundError(
                    resolution_type=str(normalized_type),
                    version=str(normalized_version),
                )
            return definition

    def registered_versions(
        self,
        resolution_type: ResolutionType | str,
    ) -> tuple[DefinitionVersion, ...]:
        """Lista las versiones registradas en orden semántico."""

        normalized_type = ResolutionType.parse(resolution_type)
        with self._lock:
            versions = [
                version
                for registered_type, version in self._definitions
                if registered_type == normalized_type
            ]
        return tuple(sorted(versions, key=lambda item: item.sort_key))

    def list_definitions(self) -> tuple[ResolutionDefinition, ...]:
        """Devuelve un snapshot determinista de todas las definiciones."""

        with self._lock:
            definitions = tuple(self._definitions.values())
        return tuple(
            sorted(
                definitions,
                key=lambda item: (
                    str(item.resolution_type),
                    item.version.sort_key,
                ),
            )
        )

    def freeze(self) -> None:
        """Impide registros o activaciones posteriores durante el proceso."""

        with self._lock:
            self._frozen = True

    def _ensure_mutable(self) -> None:
        if self._frozen:
            raise ResolutionRegistryFrozenError()
