"""Puertos de identidad, autoridad y evidencia para integraciones futuras."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from app.resolution_engine.domain.security import (
    ActorContext,
    SecurityDecision,
    SecurityResource,
)


class ActorContextProvider(Protocol):
    """Traduce credenciales del host al contrato canónico del Motor."""

    def build_actor_context(
        self,
        authentication: Any,
        /,
        *,
        correlation_id: str,
    ) -> ActorContext:
        """Autentica y resuelve permisos sin exponer roles internos al Motor."""


class SecurityEvidenceStore(Protocol):
    """Persiste cada concesión o denegación como evidencia append-only."""

    def append(
        self,
        decision: SecurityDecision,
        /,
        *,
        context_snapshot: Mapping[str, Any],
    ) -> None:
        """Agrega evidencia; la unidad de trabajo controla la transacción."""


class SecurityResourceVerifier(Protocol):
    """Comprueba que la evidencia señalada pertenece al agregado exacto."""

    def verify(self, resource: SecurityResource, /) -> tuple[str, ...]:
        """Devuelve códigos explícitos; una tupla vacía significa consistencia."""
