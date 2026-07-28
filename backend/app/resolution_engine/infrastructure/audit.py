"""Adaptadores SQLAlchemy read-only para auditoría y autorización."""

from __future__ import annotations

from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from app.resolution_engine.contracts.audit import (
    AUDIT_READ_ACTION,
    AuditQuery,
    audit_security_operation_payload,
)
from app.resolution_engine.domain.audit import ResolutionAuditSnapshot
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_engine.domain.security import SecurityDecisionUseMode
from app.resolution_engine.infrastructure.audit_projection import (
    AuditProjector,
)
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
)
from app.resolution_engine.infrastructure.repositories import (
    ResolutionRepository,
)
from app.resolution_engine.infrastructure.security_decisions import (
    SecurityDecisionExpectation,
    SqlAlchemySecurityDecisionVerifier,
)


class SqlAlchemyAuditRecordStore:
    """Carga y proyecta el expediente sobre un único snapshot SQL."""

    def __init__(self, session: Session) -> None:
        bind = session.get_bind()
        self._engine = bind.engine if isinstance(bind, Connection) else bind

    def load_audit_snapshot(
        self,
        resolution_id: int,
        /,
    ) -> ResolutionAuditSnapshot | None:
        isolation_level = _audit_snapshot_isolation(self._engine)
        with self._engine.connect().execution_options(
            isolation_level=isolation_level,
            resolution_audit_snapshot=True,
        ) as connection:
            with connection.begin():
                if connection.dialect.name == "sqlite":
                    connection.exec_driver_sql("BEGIN")
                with Session(bind=connection) as snapshot_session:
                    record = ResolutionRepository(
                        snapshot_session
                    ).load_record(resolution_id)
                    if record is None:
                        return None
                    return AuditProjector(record).project()


class SqlAlchemyAuditAccessVerifier:
    """Exige una decisión allowed exacta antes de exponer el expediente."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._security = SqlAlchemySecurityDecisionVerifier()

    def verify(self, query: AuditQuery, /) -> tuple[str, ...]:
        resolution = self._session.get(Resolution, query.resolution_id)
        if resolution is None:
            return ("resolution_missing",)
        return self._security.verify(
            self._session,
            SecurityDecisionExpectation(
                decision_id=query.security_decision_id,
                action=AUDIT_READ_ACTION,
                resource_type="resolution",
                resource_id=str(query.resolution_id),
                actor=query.actor,
                required_permissions=(
                    ComponentKey(AUDIT_READ_ACTION),
                ),
                occurred_at=query.requested_at,
                use_mode=SecurityDecisionUseMode.REUSABLE_READ,
                operation_id=query.operation_id,
                operation_payload=audit_security_operation_payload(
                    resolution_id=query.resolution_id,
                    context=query.context,
                ),
                resolution_id=query.resolution_id,
                context=query.context,
            ),
        )


def _audit_snapshot_isolation(engine: Engine) -> str:
    """Selecciona un aislamiento que conserve el corte entre consultas."""

    dialect = engine.dialect.name
    if dialect == "postgresql":
        return "REPEATABLE READ"
    if dialect == "sqlite":
        return "SERIALIZABLE"
    raise RuntimeError(
        f"audit snapshots are not configured for dialect {dialect!r}"
    )
