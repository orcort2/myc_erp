"""Adaptador SQLAlchemy del Lifecycle; no administra commit ni rollback."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.resolution_engine.contracts.lifecycle import CreateResolutionCommand
from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.definitions import ResolutionDefinition
from app.resolution_engine.domain.enums import (
    AnalysisStatus,
    AuthorizationRequestStatus,
    PlanStatus,
    ResolutionStatus,
    RevalidationStatus,
    SimulationStatus,
)
from app.resolution_engine.domain.exceptions import LifecycleConcurrencyError
from app.resolution_engine.domain.lifecycle import (
    AnalysisEvidence,
    AuthorizationEvidence,
    CompensationEvidence,
    ContextEvidence,
    ExecutionEvidence,
    LifecycleEvidence,
    LifecycleTransition,
    PlanEvidence,
    PolicyAuthorizationEvidence,
    ResolutionLifecycle,
    RevalidationEvidence,
    SimulationEvidence,
    StrategyEvidence,
)
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionAuditEvent,
    ResolutionProblem,
)
from app.resolution_engine.infrastructure.repositories import (
    ResolutionRecord,
    ResolutionRepository,
)

_PLAN_AUTHORIZATION_ACTION = "resolution.plan.authorize"


class SqlAlchemyLifecycleStore:
    """Reconstruye evidencia y persiste sólo transiciones ya validadas."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = ResolutionRepository(session)

    def create(
        self,
        command: CreateResolutionCommand,
        *,
        definition: ResolutionDefinition,
        public_id: str,
        occurred_at: datetime,
    ) -> ResolutionLifecycle:
        identity = command.actor.identity
        authentication = command.actor.authentication
        resolution = Resolution(
            public_id=public_id,
            resolution_type=str(definition.resolution_type),
            definition_version=str(definition.version),
            status=ResolutionStatus.DRAFT.value,
            priority=command.priority.value,
            source=command.source.value,
            subject_type=command.subject_type,
            subject_id=command.subject_id,
            parent_resolution_id=command.parent_resolution_id,
            requested_by_actor_id=identity.actor_id,
            organization_id=identity.organization_id,
            branch_id=identity.branch_id,
            correlation_id=authentication.correlation_id,
            request_key=command.request_key,
            title=command.title,
            description=command.description,
            reason=command.reason,
            requires_authorization=command.requires_authorization,
            version=1,
            metadata_json=dict(command.metadata),
        )
        self._repository.add(resolution)
        self._session.flush()
        problem = command.problem
        self._repository.add(
            ResolutionProblem(
                resolution_id=resolution.id,
                problem_code=problem.problem_code,
                summary=problem.summary,
                description=problem.description,
                detected_by=problem.detected_by,
                detected_at=problem.detected_at,
                reported_by_actor_id=identity.actor_id,
                source_payload=dict(problem.source_payload),
                external_reference=problem.external_reference,
                severity=problem.severity.value,
                observed_state=dict(problem.observed_state),
                evidence=list(problem.evidence),
            )
        )
        payload = {
            "definition_fingerprint": definition.fingerprint,
            "definition_version": str(definition.version),
            "problem_code": problem.problem_code,
            "subject": {
                "type": command.subject_type,
                "id": command.subject_id,
            },
        }
        self._repository.add(
            ResolutionAuditEvent(
                resolution_id=resolution.id,
                sequence=1,
                event_type="resolution.lifecycle.created",
                actor_type=identity.actor_type.value,
                actor_id=identity.actor_id,
                occurred_at=occurred_at,
                previous_state=None,
                new_state=ResolutionStatus.DRAFT.value,
                correlation_id=authentication.correlation_id,
                source=authentication.source,
                payload=payload,
                payload_hash=canonical_sha256(payload),
                metadata_json={},
            )
        )
        self._session.flush()
        return self._from_record(
            self._required_record(resolution.id)
        )

    def load(self, resolution_id: int, /) -> ResolutionLifecycle | None:
        record = self._repository.load_record(resolution_id)
        return self._from_record(record) if record is not None else None

    def apply(self, transition: LifecycleTransition, /) -> ResolutionLifecycle:
        values: dict[str, object] = {
            "status": transition.new_state.value,
            "version": transition.new_version,
            "updated_at": transition.event.occurred_at,
        }
        if transition.new_state is ResolutionStatus.CANCELLED:
            values["cancelled_at"] = transition.event.occurred_at
        elif transition.new_state is ResolutionStatus.REJECTED:
            values["rejected_at"] = transition.event.occurred_at
        elif transition.new_state in {
            ResolutionStatus.COMPLETED,
            ResolutionStatus.PARTIALLY_COMPLETED,
            ResolutionStatus.FAILED,
            ResolutionStatus.COMPENSATED,
            ResolutionStatus.PARTIALLY_COMPENSATED,
            ResolutionStatus.COMPENSATION_FAILED,
        }:
            values["completed_at"] = transition.event.occurred_at
        elif transition.new_state is ResolutionStatus.SUPERSEDED:
            values["superseded_by_resolution_id"] = (
                transition.event.payload["metadata"][
                    "superseded_by_resolution_id"
                ]
            )

        result = self._session.execute(
            update(Resolution)
            .where(
                Resolution.id == transition.resolution_id,
                Resolution.version == transition.expected_version,
                Resolution.status == transition.previous_state.value,
            )
            .values(**values)
        )
        if result.rowcount != 1:
            raise LifecycleConcurrencyError(
                resolution_id=transition.resolution_id,
                expected_version=transition.expected_version,
            )

        sequence = self._session.scalar(
            select(func.max(ResolutionAuditEvent.sequence)).where(
                ResolutionAuditEvent.resolution_id
                == transition.resolution_id
            )
        )
        lifecycle = self._from_record(
            self._required_record(transition.resolution_id)
        )
        plan = lifecycle.evidence.plan
        execution = lifecycle.evidence.execution
        self._repository.add(
            ResolutionAuditEvent(
                resolution_id=transition.resolution_id,
                sequence=(sequence or 0) + 1,
                event_type=transition.event.event_type,
                actor_type=transition.event.actor_type,
                actor_id=transition.event.actor_id,
                actor_function=transition.event.actor_function,
                occurred_at=transition.event.occurred_at,
                previous_state=transition.previous_state.value,
                new_state=transition.new_state.value,
                plan_id=plan.id if plan else None,
                plan_version=plan.version if plan else None,
                execution_id=execution.id if execution else None,
                correlation_id=transition.event.correlation_id,
                source=transition.event.source,
                payload=dict(transition.event.payload),
                payload_hash=transition.event.payload_hash,
                metadata_json={},
            )
        )
        self._session.flush()
        return self._from_record(
            self._required_record(transition.resolution_id)
        )

    def _required_record(self, resolution_id: int) -> ResolutionRecord:
        record = self._repository.load_record(resolution_id)
        if record is None:
            raise LifecycleConcurrencyError(
                resolution_id=resolution_id,
                expected_version=0,
            )
        return record

    @staticmethod
    def _from_record(record: ResolutionRecord) -> ResolutionLifecycle:
        root = record.resolution
        context = next(
            (
                item
                for item in record.context_snapshots
                if item.id == root.current_context_snapshot_id
            ),
            None,
        )
        analyses = [
            item
            for item in record.analyses
            if context is not None and item.context_snapshot_id == context.id
        ]
        analysis = analyses[-1] if analyses else None
        strategy = next(
            (
                item
                for item in record.strategy_selections
                if item.id == root.current_strategy_selection_id
            ),
            None,
        )
        plan = next(
            (
                item
                for item in record.plans
                if item.id == root.current_plan_id
            ),
            None,
        )
        simulations = [
            item
            for item in record.simulations
            if plan is not None and item.plan_id == plan.id
        ]
        simulation = simulations[-1] if simulations else None
        authorizations = [
            item
            for item in record.authorization_requests
            if plan is not None
            and simulation is not None
            and item.plan_id == plan.id
            and item.simulation_id == simulation.id
        ]
        authorization = authorizations[-1] if authorizations else None
        authorization_decisions = []
        if authorization is not None:
            latest_by_actor = {}
            for item in record.authorization_decisions:
                if item.authorization_request_id == authorization.id:
                    latest_by_actor[item.approver_actor_id] = item
            authorization_decisions = list(latest_by_actor.values())
        policy_decisions = [
            item
            for item in record.security_decisions
            if plan is not None
            and simulation is not None
            and item.action == _PLAN_AUTHORIZATION_ACTION
            and item.plan_id == plan.id
            and item.simulation_id == simulation.id
        ]
        policy = policy_decisions[-1] if policy_decisions else None
        revalidations = [
            item
            for item in record.revalidations
            if plan is not None and item.plan_id == plan.id
        ]
        revalidation = revalidations[-1] if revalidations else None
        execution = record.executions[-1] if record.executions else None
        execution_steps = [
            item
            for item in record.step_executions
            if execution is not None and item.execution_id == execution.id
        ]
        compensation_plan = (
            record.compensation_plans[-1]
            if record.compensation_plans
            else None
        )
        compensation_execution = next(
            (
                item
                for item in reversed(record.compensation_executions)
                if compensation_plan is not None
                and item.plan_id == compensation_plan.id
            ),
            None,
        )
        compensation_steps = [
            item
            for item in record.compensation_step_executions
            if compensation_execution is not None
            and item.execution_id == compensation_execution.id
        ]

        evidence = LifecycleEvidence(
            context=(
                ContextEvidence(
                    id=context.id,
                    context_hash=context.context_hash,
                )
                if context
                else None
            ),
            analysis=(
                AnalysisEvidence(
                    id=analysis.id,
                    context_id=analysis.context_snapshot_id,
                    status=AnalysisStatus(analysis.status),
                )
                if analysis
                else None
            ),
            strategy=(
                StrategyEvidence(
                    id=strategy.id,
                    analysis_id=strategy.analysis_id,
                    is_active=strategy.is_active,
                )
                if strategy
                else None
            ),
            plan=(
                PlanEvidence(
                    id=plan.id,
                    version=plan.version,
                    plan_hash=plan.plan_hash,
                    context_id=plan.context_snapshot_id,
                    strategy_id=plan.strategy_selection_id,
                    status=PlanStatus(plan.status),
                    is_active=plan.is_active,
                )
                if plan
                else None
            ),
            simulation=(
                SimulationEvidence(
                    id=simulation.id,
                    simulation_hash=simulation.simulation_hash,
                    plan_id=simulation.plan_id,
                    context_id=simulation.context_snapshot_id,
                    status=SimulationStatus(simulation.status),
                )
                if simulation
                else None
            ),
            authorization=(
                AuthorizationEvidence(
                    request_id=authorization.id,
                    plan_id=authorization.plan_id,
                    plan_hash=authorization.plan_hash,
                    simulation_id=authorization.simulation_id,
                    simulation_hash=authorization.simulation_hash,
                    status=AuthorizationRequestStatus(
                        authorization.status
                    ),
                    required_approvals=authorization.required_approvals,
                    approved_decision_count=sum(
                        item.decision == "approved"
                        for item in authorization_decisions
                    ),
                    has_blocking_decision=any(
                        item.decision in {"rejected", "revoked"}
                        for item in authorization_decisions
                    ),
                    expires_at=authorization.expires_at,
                )
                if authorization
                else None
            ),
            policy_authorization=(
                PolicyAuthorizationEvidence(
                    decision_id=policy.id,
                    plan_id=policy.plan_id,
                    plan_version=policy.plan_version,
                    plan_hash=policy.plan_hash,
                    simulation_id=policy.simulation_id,
                    simulation_hash=policy.simulation_hash,
                    outcome=policy.outcome,
                )
                if policy
                else None
            ),
            revalidation=(
                RevalidationEvidence(
                    id=revalidation.id,
                    plan_id=revalidation.plan_id,
                    previous_context_id=(
                        revalidation.previous_context_snapshot_id
                    ),
                    current_context_id=(
                        revalidation.current_context_snapshot_id
                    ),
                    status=RevalidationStatus(revalidation.status),
                )
                if revalidation
                else None
            ),
            execution=(
                ExecutionEvidence(
                    id=execution.id,
                    plan_id=execution.plan_id,
                    revalidation_id=execution.revalidation_id,
                    status=execution.status,
                    total_steps=len(execution_steps),
                    completed_steps=sum(
                        item.status == "completed"
                        for item in execution_steps
                    ),
                    failed_steps=sum(
                        item.status == "failed"
                        for item in execution_steps
                    ),
                    blocked_steps=sum(
                        item.status == "blocked"
                        for item in execution_steps
                    ),
                )
                if execution
                else None
            ),
            compensation=(
                CompensationEvidence(
                    plan_id=compensation_plan.id,
                    execution_id=(
                        compensation_execution.id
                        if compensation_execution
                        else None
                    ),
                    source_execution_id=(
                        compensation_plan.source_execution_id
                    ),
                    status=(
                        compensation_execution.status
                        if compensation_execution
                        else "prepared"
                    ),
                    total_steps=sum(
                        item.plan_id == compensation_plan.id
                        for item in record.compensation_plan_steps
                    ),
                    compensated_steps=sum(
                        item.status == "compensated"
                        for item in compensation_steps
                    ),
                    failed_steps=sum(
                        item.status == "failed"
                        for item in compensation_steps
                    ),
                    blocked_steps=sum(
                        item.status == "blocked"
                        for item in compensation_steps
                    ),
                )
                if compensation_plan
                else None
            ),
        )
        return ResolutionLifecycle(
            resolution_id=root.id,
            public_id=root.public_id,
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            status=ResolutionStatus(root.status),
            version=root.version,
            requires_authorization=root.requires_authorization,
            evidence=evidence,
        )
