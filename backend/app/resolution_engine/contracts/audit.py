"""Puertos de lectura para auditoría y evidencia institucional."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.resolution_engine.domain.audit import ResolutionAuditSnapshot
from app.resolution_engine.domain.exceptions import InvalidAuditEvidenceError

AUDIT_READ_ACTION = "resolution.audit.inspect"


@dataclass(frozen=True, slots=True)
class AuditQuery:
    """Identidad y autorización exactas requeridas para leer evidencia."""

    resolution_id: int
    actor_id: str
    correlation_id: str
    security_decision_id: int

    def __post_init__(self) -> None:
        if self.resolution_id <= 0 or self.security_decision_id <= 0:
            raise InvalidAuditEvidenceError(
                "audit query identifiers must be positive"
            )
        if not self.actor_id.strip() or not self.correlation_id.strip():
            raise InvalidAuditEvidenceError(
                "audit query requires actor and correlation"
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
