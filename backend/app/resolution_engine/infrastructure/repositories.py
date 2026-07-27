"""Repositorio de lectura y persistencia del agregado de resolución."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionAnalysis,
    ResolutionAuditEvent,
    ResolutionAuthorizationDecision,
    ResolutionAuthorizationRequest,
    ResolutionContextSnapshot,
    ResolutionCompensationExecution,
    ResolutionCompensationPlan,
    ResolutionCompensationPlanStep,
    ResolutionCompensationStepExecution,
    ResolutionEntityReference,
    ResolutionEvidenceReference,
    ResolutionExecution,
    ResolutionIdempotencyRecord,
    ResolutionLock,
    ResolutionOutboxEvent,
    ResolutionSecurityDecision,
    ResolutionPlan,
    ResolutionPlanStep,
    ResolutionPlanStepDependency,
    ResolutionProblem,
    ResolutionResult,
    ResolutionRevalidation,
    ResolutionSimulation,
    ResolutionStepExecution,
    ResolutionStrategySelection,
)


@dataclass(frozen=True, slots=True)
class ResolutionRecord:
    """Snapshot completo de filas necesarias para reconstruir una resolución."""

    resolution: Resolution
    problem: ResolutionProblem | None
    context_snapshots: tuple[ResolutionContextSnapshot, ...]
    analyses: tuple[ResolutionAnalysis, ...]
    strategy_selections: tuple[ResolutionStrategySelection, ...]
    plans: tuple[ResolutionPlan, ...]
    plan_steps: tuple[ResolutionPlanStep, ...]
    plan_step_dependencies: tuple[ResolutionPlanStepDependency, ...]
    simulations: tuple[ResolutionSimulation, ...]
    authorization_requests: tuple[ResolutionAuthorizationRequest, ...]
    authorization_decisions: tuple[ResolutionAuthorizationDecision, ...]
    revalidations: tuple[ResolutionRevalidation, ...]
    executions: tuple[ResolutionExecution, ...]
    step_executions: tuple[ResolutionStepExecution, ...]
    entity_references: tuple[ResolutionEntityReference, ...]
    result: ResolutionResult | None
    audit_events: tuple[ResolutionAuditEvent, ...]
    security_decisions: tuple[ResolutionSecurityDecision, ...]
    idempotency_records: tuple[ResolutionIdempotencyRecord, ...]
    locks: tuple[ResolutionLock, ...]
    outbox_events: tuple[ResolutionOutboxEvent, ...]
    evidence_references: tuple[ResolutionEvidenceReference, ...]
    compensation_plans: tuple[ResolutionCompensationPlan, ...]
    compensation_plan_steps: tuple[ResolutionCompensationPlanStep, ...]
    compensation_executions: tuple[ResolutionCompensationExecution, ...]
    compensation_step_executions: tuple[
        ResolutionCompensationStepExecution, ...
    ]


class ResolutionRepository:
    """Persistencia explícita sin administrar transacciones ni lifecycle."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, record: Any) -> None:
        """Agrega una fila; la unidad de trabajo conserva commit/rollback."""

        self._session.add(record)

    def get(
        self,
        resolution_id: int,
        *,
        for_update: bool = False,
    ) -> Resolution | None:
        statement = select(Resolution).where(Resolution.id == resolution_id)
        if for_update:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def get_by_public_id(self, public_id: str) -> Resolution | None:
        return self._session.scalar(
            select(Resolution).where(Resolution.public_id == public_id)
        )

    def get_by_request_key(self, request_key: str) -> Resolution | None:
        return self._session.scalar(
            select(Resolution).where(Resolution.request_key == request_key)
        )

    def load_record(self, resolution_id: int) -> ResolutionRecord | None:
        """Carga evidencia completa con consultas explícitas y deterministas."""

        resolution = self.get(resolution_id)
        if resolution is None:
            return None

        plans = self._all(
            ResolutionPlan,
            ResolutionPlan.resolution_id == resolution_id,
            ResolutionPlan.version,
        )
        plan_ids = [plan.id for plan in plans]
        plan_steps = self._all_for_ids(
            ResolutionPlanStep,
            ResolutionPlanStep.plan_id,
            plan_ids,
            ResolutionPlanStep.sequence,
        )
        plan_step_ids = [step.id for step in plan_steps]
        authorization_requests = self._all(
            ResolutionAuthorizationRequest,
            ResolutionAuthorizationRequest.resolution_id == resolution_id,
            ResolutionAuthorizationRequest.id,
        )
        authorization_request_ids = [
            request.id for request in authorization_requests
        ]
        executions = self._all(
            ResolutionExecution,
            ResolutionExecution.resolution_id == resolution_id,
            ResolutionExecution.attempt_number,
        )
        execution_ids = [execution.id for execution in executions]
        compensation_plans = self._all(
            ResolutionCompensationPlan,
            ResolutionCompensationPlan.resolution_id == resolution_id,
            ResolutionCompensationPlan.id,
        )
        compensation_plan_ids = [
            plan.id for plan in compensation_plans
        ]
        compensation_executions = self._all(
            ResolutionCompensationExecution,
            ResolutionCompensationExecution.resolution_id == resolution_id,
            ResolutionCompensationExecution.id,
        )
        compensation_execution_ids = [
            execution.id for execution in compensation_executions
        ]

        return ResolutionRecord(
            resolution=resolution,
            problem=self._session.scalar(
                select(ResolutionProblem).where(
                    ResolutionProblem.resolution_id == resolution_id
                )
            ),
            context_snapshots=self._all(
                ResolutionContextSnapshot,
                ResolutionContextSnapshot.resolution_id == resolution_id,
                ResolutionContextSnapshot.sequence,
            ),
            analyses=self._all(
                ResolutionAnalysis,
                ResolutionAnalysis.resolution_id == resolution_id,
                ResolutionAnalysis.analysis_version,
            ),
            strategy_selections=self._all(
                ResolutionStrategySelection,
                ResolutionStrategySelection.resolution_id == resolution_id,
                ResolutionStrategySelection.id,
            ),
            plans=plans,
            plan_steps=plan_steps,
            plan_step_dependencies=self._all_for_ids(
                ResolutionPlanStepDependency,
                ResolutionPlanStepDependency.plan_id,
                plan_ids,
                ResolutionPlanStepDependency.id,
            ),
            simulations=self._all(
                ResolutionSimulation,
                ResolutionSimulation.resolution_id == resolution_id,
                ResolutionSimulation.id,
            ),
            authorization_requests=authorization_requests,
            authorization_decisions=self._all_for_ids(
                ResolutionAuthorizationDecision,
                ResolutionAuthorizationDecision.authorization_request_id,
                authorization_request_ids,
                ResolutionAuthorizationDecision.id,
            ),
            revalidations=self._all(
                ResolutionRevalidation,
                ResolutionRevalidation.resolution_id == resolution_id,
                ResolutionRevalidation.id,
            ),
            executions=executions,
            step_executions=self._all_for_ids(
                ResolutionStepExecution,
                ResolutionStepExecution.execution_id,
                execution_ids,
                ResolutionStepExecution.id,
            ),
            entity_references=self._all(
                ResolutionEntityReference,
                ResolutionEntityReference.resolution_id == resolution_id,
                ResolutionEntityReference.id,
            ),
            result=self._session.scalar(
                select(ResolutionResult).where(
                    ResolutionResult.resolution_id == resolution_id
                )
            ),
            audit_events=self._all(
                ResolutionAuditEvent,
                ResolutionAuditEvent.resolution_id == resolution_id,
                ResolutionAuditEvent.sequence,
            ),
            security_decisions=self._all(
                ResolutionSecurityDecision,
                ResolutionSecurityDecision.resolution_id == resolution_id,
                ResolutionSecurityDecision.id,
            ),
            idempotency_records=self._all(
                ResolutionIdempotencyRecord,
                ResolutionIdempotencyRecord.resolution_id == resolution_id,
                ResolutionIdempotencyRecord.id,
            ),
            locks=self._all(
                ResolutionLock,
                ResolutionLock.resolution_id == resolution_id,
                ResolutionLock.id,
            ),
            outbox_events=self._all(
                ResolutionOutboxEvent,
                ResolutionOutboxEvent.resolution_id == resolution_id,
                ResolutionOutboxEvent.id,
            ),
            evidence_references=self._all(
                ResolutionEvidenceReference,
                ResolutionEvidenceReference.resolution_id == resolution_id,
                ResolutionEvidenceReference.id,
            ),
            compensation_plans=compensation_plans,
            compensation_plan_steps=self._all_for_ids(
                ResolutionCompensationPlanStep,
                ResolutionCompensationPlanStep.plan_id,
                compensation_plan_ids,
                ResolutionCompensationPlanStep.sequence,
            ),
            compensation_executions=compensation_executions,
            compensation_step_executions=self._all_for_ids(
                ResolutionCompensationStepExecution,
                ResolutionCompensationStepExecution.execution_id,
                compensation_execution_ids,
                ResolutionCompensationStepExecution.id,
            ),
        )

    def _all(
        self,
        model: type[Any],
        predicate: Any,
        order_by: Any,
    ) -> tuple[Any, ...]:
        return tuple(
            self._session.scalars(
                select(model).where(predicate).order_by(order_by)
            )
        )

    def _all_for_ids(
        self,
        model: type[Any],
        column: Any,
        identifiers: list[int],
        order_by: Any,
    ) -> tuple[Any, ...]:
        if not identifiers:
            return ()
        return tuple(
            self._session.scalars(
                select(model)
                .where(column.in_(identifiers))
                .order_by(order_by)
            )
        )
