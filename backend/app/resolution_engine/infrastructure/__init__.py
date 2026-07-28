"""Adaptadores de persistencia y runtime autorizados hasta Fase 11."""

from app.resolution_engine.infrastructure.audit import (
    SqlAlchemyAuditAccessVerifier,
    SqlAlchemyAuditRecordStore,
)
from app.resolution_engine.infrastructure.execution import (
    SqlAlchemyExecutionStore,
)
from app.resolution_engine.infrastructure.execution_control import (
    SqlAlchemyExecutionControl,
)
from app.resolution_engine.infrastructure.lifecycle import (
    SqlAlchemyLifecycleStore,
)
from app.resolution_engine.infrastructure.runtime import (
    SystemClock,
    UuidIdentifierFactory,
)
from app.resolution_engine.infrastructure.repositories import (
    ResolutionRecord,
    ResolutionRepository,
)
from app.resolution_engine.infrastructure.outbox import (
    SqlAlchemyOutboxStore,
)
from app.resolution_engine.infrastructure.compensation import (
    SqlAlchemyCompensationStore,
)
from app.resolution_engine.infrastructure.security_decisions import (
    SecurityDecisionExpectation,
    SqlAlchemySecurityDecisionVerifier,
)
from app.resolution_engine.infrastructure.distribution import (
    SqlAlchemyDistributedWorkStore,
)

__all__ = [
    "SqlAlchemyAuditAccessVerifier",
    "SqlAlchemyAuditRecordStore",
    "ResolutionRecord",
    "ResolutionRepository",
    "SqlAlchemyExecutionControl",
    "SqlAlchemyCompensationStore",
    "SqlAlchemyExecutionStore",
    "SqlAlchemyDistributedWorkStore",
    "SqlAlchemyLifecycleStore",
    "SqlAlchemyOutboxStore",
    "SecurityDecisionExpectation",
    "SqlAlchemySecurityDecisionVerifier",
    "SystemClock",
    "UuidIdentifierFactory",
]
