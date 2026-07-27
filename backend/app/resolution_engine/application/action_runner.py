"""Selección explícita de handlers para acciones del plan."""

from __future__ import annotations

from app.resolution_engine.contracts.execution import ActionHandler
from app.resolution_engine.domain.exceptions import (
    ActionHandlerNotFoundError,
    ActionInvocationUncertainError,
    DuplicateActionHandlerError,
)
from app.resolution_engine.domain.execution import (
    DomainActionRequest,
    DomainActionResult,
)


class ActionRunner:
    """Único punto que invoca adaptadores de operaciones propietarias."""

    def __init__(self, handlers: tuple[ActionHandler, ...]) -> None:
        self._handlers: dict[str, ActionHandler] = {}
        for handler in handlers:
            key = str(handler.operation_key)
            if key in self._handlers:
                raise DuplicateActionHandlerError(
                    f"Duplicate action handler: {key}"
                )
            self._handlers[key] = handler

    def run(
        self,
        request: DomainActionRequest,
        /,
    ) -> DomainActionResult:
        key = request.step.operation_key
        handler = self._handlers.get(key)
        if handler is None:
            raise ActionHandlerNotFoundError(
                f"Action handler not found: {key}"
            )
        try:
            result = handler.execute(request)
        except Exception as exc:
            raise ActionInvocationUncertainError(
                f"Action {key} ended without a confirmed result"
            ) from exc
        if not isinstance(result, DomainActionResult):
            raise ActionInvocationUncertainError(
                f"Action {key} returned an invalid result"
            )
        return result
