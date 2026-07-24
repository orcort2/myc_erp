"""Fundación del Motor de Resoluciones.

La Fase 1 expone únicamente contratos, tipos de dominio y el registro de
definiciones. No contiene persistencia, ciclo de vida ni ejecución.
"""

from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.domain.definitions import (
    ComponentReference,
    ResolutionDefinition,
)
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
    ResolutionType,
)

__all__ = [
    "ComponentKey",
    "ComponentReference",
    "DefinitionVersion",
    "ResolutionDefinition",
    "ResolutionRegistry",
    "ResolutionType",
]
