"""Adaptadores SQLAlchemy read-only para auditoría y autorización."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.resolution_engine.contracts.audit import (
    AUDIT_READ_ACTION,
    AuditQuery,
)
from app.resolution_engine.domain.audit import ResolutionAuditSnapshot
from app.resolution_engine.infrastructure.audit_projection import (
    AuditProjector,
)
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionSecurityDecision,
)
from app.resolution_engine.infrastructure.repositories import (
    ResolutionRepository,
)


class SqlAlchemyAuditRecordStore:
    """Carga y proyecta el expediente sin alterar filas."""

    def __init__(self, session: Session) -> None:
        self._repository = ResolutionRepository(session)

    def load_audit_snapshot(
        self,
        resolution_id: int,
        /,
    ) -> ResolutionAuditSnapshot | None:
        record = self._repository.load_record(resolution_id)
        if record is None:
            return None
        return AuditProjector(record).project()


class SqlAlchemyAuditAccessVerifier:
    """Exige una decisión allowed exacta antes de exponer el expediente."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def verify(self, query: AuditQuery, /) -> tuple[str, ...]:
        reasons: list[str] = []
        decision = self._session.scalar(
            select(ResolutionSecurityDecision).where(
                ResolutionSecurityDecision.id
                == query.security_decision_id,
                ResolutionSecurityDecision.resolution_id
                == query.resolution_id,
            )
        )
        if decision is None:
            return ("security_decision_missing_or_foreign",)
        if decision.outcome != "allowed":
            reasons.append("security_decision_denied")
        if decision.action != AUDIT_READ_ACTION:
            reasons.append("security_action_mismatch")
        if decision.actor_id != query.actor_id:
            reasons.append("security_actor_mismatch")
        if decision.correlation_id != query.correlation_id:
            reasons.append("security_correlation_mismatch")
        if decision.resource_type != "resolution":
            reasons.append("security_resource_type_mismatch")
        resolution = self._session.get(Resolution, query.resolution_id)
        if resolution is None:
            reasons.append("resolution_missing")
        elif decision.resource_id not in {
            str(query.resolution_id),
            resolution.public_id,
        }:
            reasons.append("security_resource_id_mismatch")
        if (
            resolution is not None
            and resolution.organization_id is not None
            and decision.organization_id != resolution.organization_id
        ):
            reasons.append("security_organization_mismatch")
        return tuple(reasons)
