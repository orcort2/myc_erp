"""Modelo persistente completo del Motor de Resoluciones."""

from app.resolution_engine.infrastructure.persistence.core import (
    Resolution,
    ResolutionAnalysis,
    ResolutionContextSnapshot,
    ResolutionProblem,
    ResolutionStrategySelection,
)
from app.resolution_engine.infrastructure.persistence.compensation import (
    ResolutionCompensationExecution,
    ResolutionCompensationPlan,
    ResolutionCompensationPlanStep,
    ResolutionCompensationStepExecution,
)
from app.resolution_engine.infrastructure.persistence.evidence import (
    ResolutionAuditEvent,
    ResolutionEvidenceReference,
    ResolutionIdempotencyRecord,
    ResolutionLock,
    ResolutionOutboxEvent,
    ResolutionSecurityDecision,
    ResolutionSecurityDecisionUse,
)
from app.resolution_engine.infrastructure.persistence.execution import (
    ResolutionEntityReference,
    ResolutionExecution,
    ResolutionResult,
    ResolutionStepExecution,
)
from app.resolution_engine.infrastructure.persistence.governance import (
    ResolutionAuthorizationDecision,
    ResolutionAuthorizationRequest,
    ResolutionRevalidation,
)
from app.resolution_engine.infrastructure.persistence.planning import (
    ResolutionPlan,
    ResolutionPlanStep,
    ResolutionPlanStepDependency,
    ResolutionSimulation,
)

__all__ = [
    "Resolution",
    "ResolutionAnalysis",
    "ResolutionAuditEvent",
    "ResolutionAuthorizationDecision",
    "ResolutionAuthorizationRequest",
    "ResolutionContextSnapshot",
    "ResolutionCompensationExecution",
    "ResolutionCompensationPlan",
    "ResolutionCompensationPlanStep",
    "ResolutionCompensationStepExecution",
    "ResolutionEntityReference",
    "ResolutionEvidenceReference",
    "ResolutionExecution",
    "ResolutionIdempotencyRecord",
    "ResolutionLock",
    "ResolutionOutboxEvent",
    "ResolutionSecurityDecision",
    "ResolutionSecurityDecisionUse",
    "ResolutionPlan",
    "ResolutionPlanStep",
    "ResolutionPlanStepDependency",
    "ResolutionProblem",
    "ResolutionResult",
    "ResolutionRevalidation",
    "ResolutionSimulation",
    "ResolutionStepExecution",
    "ResolutionStrategySelection",
]
