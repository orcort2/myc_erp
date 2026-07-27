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


class InvalidLifecycleTransitionError(ResolutionEngineError):
    """La transición solicitada no pertenece al grafo vigente."""

    def __init__(self, *, current_state: str, action: str) -> None:
        super().__init__(
            f"Invalid lifecycle transition: {current_state} + {action}"
        )
        self.current_state = current_state
        self.action = action


class LifecycleInvariantError(ResolutionEngineError):
    """La evidencia persistida no satisface una precondición del Lifecycle."""

    def __init__(self, *, action: str, violations: tuple[str, ...]) -> None:
        super().__init__(
            f"Lifecycle invariants failed for {action}: "
            + ", ".join(violations)
        )
        self.action = action
        self.violations = violations


class LifecycleConcurrencyError(ResolutionEngineError):
    """El expediente cambió después de calcular la transición."""

    def __init__(self, *, resolution_id: int, expected_version: int) -> None:
        super().__init__(
            f"Resolution {resolution_id} no longer has version "
            f"{expected_version}"
        )
        self.resolution_id = resolution_id
        self.expected_version = expected_version


class ResolutionNotFoundError(ResolutionEngineError, LookupError):
    """No existe la resolución solicitada."""

    def __init__(self, *, resolution_id: int) -> None:
        super().__init__(f"Resolution not found: {resolution_id}")
        self.resolution_id = resolution_id


class ComponentBindingError(ResolutionEngineError):
    """Una referencia registrada no tiene una implementación compatible."""


class ExecutionNotReadyError(ResolutionEngineError):
    """La resolución o el plan no satisfacen el gate de ejecución."""


class InvalidExecutionPlanError(ResolutionEngineError):
    """Los pasos o dependencias del plan no forman una ejecución válida."""


class ExecutionIdempotencyConflictError(ResolutionEngineError):
    """Una clave existente fue utilizada para otra solicitud."""


class ExecutionAlreadyInProgressError(ResolutionEngineError):
    """La misma ejecución ya está en curso y no debe duplicarse."""


class ExecutionLockUnavailableError(ResolutionEngineError):
    """Otro propietario conserva el lock exclusivo requerido."""


class ExecutionLockLostError(ResolutionEngineError):
    """El lock expiró, fue liberado o pertenece a otro propietario."""


class DuplicateActionHandlerError(ResolutionEngineError):
    """Más de un handler pretende ejecutar la misma operación."""


class ActionHandlerNotFoundError(ResolutionEngineError):
    """No existe un handler explícito para la operación del paso."""


class ActionInvocationUncertainError(ResolutionEngineError):
    """El handler falló sin confirmar si la operación produjo efectos."""


class CompensationNotAllowedError(ResolutionEngineError):
    """La ejecución o su evidencia no permiten iniciar una compensación."""


class InvalidCompensationPlanError(ResolutionEngineError):
    """La selección declarativa no forma un plan compensatorio válido."""


class CompensationIdempotencyConflictError(ResolutionEngineError):
    """Una clave compensatoria existente representa otra solicitud."""


class DuplicateCompensationHandlerError(ResolutionEngineError):
    """Más de un handler pretende compensar la misma operación."""


class CompensationHandlerNotFoundError(ResolutionEngineError):
    """No existe adaptador compensatorio para la operación declarada."""


class CompensationInvocationUncertainError(ResolutionEngineError):
    """La compensación pudo producir efectos, pero no confirmó resultado."""
