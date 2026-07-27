"""Consultas de auditoría sobre expedientes reconstruibles."""

from __future__ import annotations

from app.resolution_engine.contracts.audit import (
    AuditAccessVerifier,
    AuditQuery,
    AuditRecordStore,
)
from app.resolution_engine.domain.audit import (
    AuditEngine,
    AuditReport,
    EvidenceNode,
    TimelineEntry,
)
from app.resolution_engine.domain.exceptions import (
    AuditAccessDeniedError,
    AuditRecordNotFoundError,
)


class AuditQueryService:
    """Fachada de aplicación read-only; nunca modifica el expediente."""

    def __init__(
        self,
        *,
        store: AuditRecordStore,
        access_verifier: AuditAccessVerifier,
        engine: AuditEngine | None = None,
    ) -> None:
        self._store = store
        self._access_verifier = access_verifier
        self._engine = engine or AuditEngine()

    def inspect(self, query: AuditQuery, /) -> AuditReport:
        reasons = self._access_verifier.verify(query)
        if reasons:
            raise AuditAccessDeniedError(
                resolution_id=query.resolution_id,
                reasons=reasons,
            )
        snapshot = self._store.load_audit_snapshot(query.resolution_id)
        if snapshot is None:
            raise AuditRecordNotFoundError(
                resolution_id=query.resolution_id
            )
        return self._engine.verify(snapshot)

    def timeline(
        self,
        query: AuditQuery,
        /,
        *,
        correlation_id: str | None = None,
    ) -> tuple[TimelineEntry, ...]:
        report = self.inspect(query)
        return tuple(
            entry
            for entry in report.timeline
            if correlation_id is None
            or entry.correlation_id == correlation_id
        )

    def evidence(
        self,
        query: AuditQuery,
        /,
        *,
        kinds: tuple[str, ...] = (),
        correlation_id: str | None = None,
    ) -> tuple[EvidenceNode, ...]:
        return self.inspect(query).evidence(
            kinds=kinds,
            correlation_id=correlation_id,
        )
