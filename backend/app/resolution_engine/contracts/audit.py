"""Puertos de lectura para auditoría y evidencia institucional."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Protocol

from app.resolution_engine.domain.audit import ResolutionAuditSnapshot
from app.resolution_engine.domain.exceptions import InvalidAuditEvidenceError
from app.resolution_engine.domain.security import ActorContext

AUDIT_READ_ACTION = "resolution.audit.inspect"


def audit_security_operation_payload(
    *,
    resolution_id: int,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Alcance canónico de una concesión de consulta reutilizable."""

    return {
        "resolution_id": resolution_id,
        "context": dict(context),
    }


@dataclass(frozen=True, slots=True)
class AuditQuery:
    """Identidad y autorización exactas requeridas para leer evidencia."""

    resolution_id: int
    security_decision_id: int
    actor: ActorContext
    requested_at: datetime
    operation_id: str
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.resolution_id <= 0 or self.security_decision_id <= 0:
            raise InvalidAuditEvidenceError(
                "audit query identifiers must be positive"
            )
        if self.requested_at.tzinfo is None:
            raise InvalidAuditEvidenceError(
                "audit query time must include timezone"
            )
        if not self.operation_id.strip():
            raise InvalidAuditEvidenceError(
                "audit operation_id is required"
            )


class AuditRecordStore(Protocol):
    """Expone un expediente normalizado desde un único snapshot lógico."""

    def load_audit_snapshot(
        self,
        resolution_id: int,
        /,
    ) -> ResolutionAuditSnapshot | None:
        """Carga y proyecta toda la evidencia en una misma transacción."""


class AuditAccessVerifier(Protocol):
    """Valida una concesión persistida sin incorporar políticas al servicio."""

    def verify(self, query: AuditQuery, /) -> tuple[str, ...]:
        """Devuelve razones estables; vacío significa acceso concedido."""
