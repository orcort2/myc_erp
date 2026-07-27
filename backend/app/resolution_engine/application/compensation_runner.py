"""Selección exclusiva de adaptadores de compensación."""

from app.resolution_engine.contracts.compensation import CompensationHandler
from app.resolution_engine.domain.compensation import CompensationActionRequest
from app.resolution_engine.domain.exceptions import (
    CompensationHandlerNotFoundError,
    CompensationInvocationUncertainError,
    DuplicateCompensationHandlerError,
)
from app.resolution_engine.domain.execution import DomainActionResult


class CompensationRunner:
    """Único punto que invoca operaciones compensatorias propietarias."""

    def __init__(self, handlers: tuple[CompensationHandler, ...]) -> None:
        self._handlers: dict[str, CompensationHandler] = {}
        for handler in handlers:
            key = str(handler.operation_key)
            if key in self._handlers:
                raise DuplicateCompensationHandlerError(
                    f"Duplicate compensation handler: {key}"
                )
            self._handlers[key] = handler

    def run(
        self,
        request: CompensationActionRequest,
        /,
    ) -> DomainActionResult:
        key = request.step.operation_key
        handler = self._handlers.get(key)
        if handler is None:
            raise CompensationHandlerNotFoundError(
                f"Compensation handler not found: {key}"
            )
        try:
            result = handler.execute(request)
        except Exception as exc:
            raise CompensationInvocationUncertainError(
                f"Compensation {key} ended without a confirmed result"
            ) from exc
        if not isinstance(result, DomainActionResult):
            raise CompensationInvocationUncertainError(
                f"Compensation {key} returned an invalid result"
            )
        return result
