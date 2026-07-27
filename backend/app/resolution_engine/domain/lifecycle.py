"""Máquina de estados e invariantes puras del Motor de Resoluciones."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.enums import (
    AnalysisStatus,
    AuthorizationRequestStatus,
    PlanStatus,
    ResolutionStatus,
    RevalidationStatus,
    SimulationStatus,
)
from app.resolution_engine.domain.exceptions import (
    InvalidLifecycleTransitionError,
    LifecycleInvariantError,
)


class LifecycleAction(StrEnum):
    """Acciones explícitas que pueden cambiar el estado raíz."""

    RECORD_CONTEXT = "record_context"
    RECORD_ANALYSIS = "record_analysis"
    RECORD_PLAN = "record_plan"
    RECORD_SIMULATION = "record_simulation"
    REQUEST_AUTHORIZATION = "request_authorization"
    CONFIRM_AUTHORIZATION = "confirm_authorization"
    BEGIN_REVALIDATION = "begin_revalidation"
    ACCEPT_REVALIDATION = "accept_revalidation"
    REQUIRE_NEW_PLAN = "require_new_plan"
    MARK_NO_ACTION = "mark_no_action"
    BLOCK = "block"
    REJECT = "reject"
    CANCEL = "cancel"
    SUPERSEDE = "supersede"
    START_EXECUTION = "start_execution"
    COMPLETE_EXECUTION = "complete_execution"
    COMPLETE_PARTIAL_EXECUTION = "complete_partial_execution"
    FAIL_EXECUTION = "fail_execution"
    BLOCK_EXECUTION = "block_execution"
    START_COMPENSATION = "start_compensation"
    COMPLETE_COMPENSATION = "complete_compensation"
    COMPLETE_PARTIAL_COMPENSATION = "complete_partial_compensation"
    FAIL_COMPENSATION = "fail_compensation"


@dataclass(frozen=True, slots=True)
class ContextEvidence:
    id: int
    context_hash: str


@dataclass(frozen=True, slots=True)
class AnalysisEvidence:
    id: int
    context_id: int
    status: AnalysisStatus


@dataclass(frozen=True, slots=True)
class StrategyEvidence:
    id: int
    analysis_id: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class PlanEvidence:
    id: int
    version: int
    plan_hash: str
    context_id: int
    strategy_id: int
    status: PlanStatus
    is_active: bool


@dataclass(frozen=True, slots=True)
class SimulationEvidence:
    id: int
    simulation_hash: str
    plan_id: int
    context_id: int
    status: SimulationStatus


@dataclass(frozen=True, slots=True)
class AuthorizationEvidence:
    request_id: int
    plan_id: int
    plan_hash: str
    simulation_id: int
    simulation_hash: str
    status: AuthorizationRequestStatus
    required_approvals: int
    approved_decision_count: int
    has_blocking_decision: bool
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class PolicyAuthorizationEvidence:
    decision_id: int
    plan_id: int
    plan_version: int
    plan_hash: str
    simulation_id: int
    simulation_hash: str
    outcome: str


@dataclass(frozen=True, slots=True)
class RevalidationEvidence:
    id: int
    plan_id: int
    previous_context_id: int
    current_context_id: int
    status: RevalidationStatus


@dataclass(frozen=True, slots=True)
class ExecutionEvidence:
    id: int
    plan_id: int
    revalidation_id: int
    status: str
    total_steps: int
    completed_steps: int
    failed_steps: int
    blocked_steps: int


@dataclass(frozen=True, slots=True)
class CompensationEvidence:
    plan_id: int
    execution_id: int | None
    source_execution_id: int
    status: str
    total_steps: int
    compensated_steps: int
    failed_steps: int
    blocked_steps: int


@dataclass(frozen=True, slots=True)
class LifecycleEvidence:
    """Referencias exactas reconstruidas desde el expediente persistido."""

    context: ContextEvidence | None = None
    analysis: AnalysisEvidence | None = None
    strategy: StrategyEvidence | None = None
    plan: PlanEvidence | None = None
    simulation: SimulationEvidence | None = None
    authorization: AuthorizationEvidence | None = None
    policy_authorization: PolicyAuthorizationEvidence | None = None
    revalidation: RevalidationEvidence | None = None
    execution: ExecutionEvidence | None = None
    compensation: CompensationEvidence | None = None


@dataclass(frozen=True, slots=True)
class ResolutionLifecycle:
    """Proyección mínima y reproducible de la raíz persistida."""

    resolution_id: int
    public_id: str
    resolution_type: str
    definition_version: str
    status: ResolutionStatus
    version: int
    requires_authorization: bool
    evidence: LifecycleEvidence = field(default_factory=LifecycleEvidence)


@dataclass(frozen=True, slots=True)
class LifecycleDomainEvent:
    """Hecho interno; no es un mensaje de outbox ni se publica."""

    event_type: str
    resolution_id: int
    occurred_at: datetime
    previous_state: ResolutionStatus
    new_state: ResolutionStatus
    action: LifecycleAction
    actor_id: str | None
    actor_type: str
    actor_function: str | None
    source: str
    correlation_id: str | None
    payload: Mapping[str, Any]
    payload_hash: str

    @classmethod
    def build(
        cls,
        *,
        lifecycle: ResolutionLifecycle,
        action: LifecycleAction,
        new_state: ResolutionStatus,
        occurred_at: datetime,
        actor_id: str | None,
        actor_type: str,
        actor_function: str | None,
        source: str,
        correlation_id: str | None,
        reason: str | None,
        metadata: Mapping[str, Any],
    ) -> LifecycleDomainEvent:
        payload = {
            "action": action.value,
            "definition_version": lifecycle.definition_version,
            "from_version": lifecycle.version,
            "reason": reason,
            "metadata": dict(metadata),
        }
        return cls(
            event_type=f"resolution.lifecycle.{action.value}",
            resolution_id=lifecycle.resolution_id,
            occurred_at=occurred_at,
            previous_state=lifecycle.status,
            new_state=new_state,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_function=actor_function,
            source=source,
            correlation_id=correlation_id,
            payload=MappingProxyType(payload),
            payload_hash=canonical_sha256(payload),
        )


@dataclass(frozen=True, slots=True)
class LifecycleTransition:
    resolution_id: int
    expected_version: int
    new_version: int
    previous_state: ResolutionStatus
    new_state: ResolutionStatus
    event: LifecycleDomainEvent


_LINEAR_TRANSITIONS = {
    (ResolutionStatus.DRAFT, LifecycleAction.RECORD_CONTEXT):
        ResolutionStatus.CONTEXT_READY,
    (ResolutionStatus.CONTEXT_READY, LifecycleAction.RECORD_ANALYSIS):
        ResolutionStatus.ANALYZED,
    (ResolutionStatus.ANALYZED, LifecycleAction.RECORD_PLAN):
        ResolutionStatus.PLAN_READY,
    (ResolutionStatus.PLAN_READY, LifecycleAction.RECORD_SIMULATION):
        ResolutionStatus.SIMULATED,
    (ResolutionStatus.SIMULATED, LifecycleAction.REQUEST_AUTHORIZATION):
        ResolutionStatus.PENDING_AUTHORIZATION,
    (
        ResolutionStatus.PENDING_AUTHORIZATION,
        LifecycleAction.CONFIRM_AUTHORIZATION,
    ): ResolutionStatus.AUTHORIZED,
    (ResolutionStatus.SIMULATED, LifecycleAction.CONFIRM_AUTHORIZATION):
        ResolutionStatus.AUTHORIZED,
    (ResolutionStatus.AUTHORIZED, LifecycleAction.BEGIN_REVALIDATION):
        ResolutionStatus.REVALIDATING,
    (ResolutionStatus.REVALIDATING, LifecycleAction.ACCEPT_REVALIDATION):
        ResolutionStatus.READY_FOR_EXECUTION,
    (ResolutionStatus.REVALIDATING, LifecycleAction.REQUIRE_NEW_PLAN):
        ResolutionStatus.PLAN_READY,
    (ResolutionStatus.ANALYZED, LifecycleAction.MARK_NO_ACTION):
        ResolutionStatus.NO_ACTION_REQUIRED,
    (ResolutionStatus.REVALIDATING, LifecycleAction.MARK_NO_ACTION):
        ResolutionStatus.NO_ACTION_REQUIRED,
    (ResolutionStatus.READY_FOR_EXECUTION, LifecycleAction.START_EXECUTION):
        ResolutionStatus.EXECUTING,
    (ResolutionStatus.EXECUTING, LifecycleAction.COMPLETE_EXECUTION):
        ResolutionStatus.COMPLETED,
    (
        ResolutionStatus.EXECUTING,
        LifecycleAction.COMPLETE_PARTIAL_EXECUTION,
    ): ResolutionStatus.PARTIALLY_COMPLETED,
    (ResolutionStatus.EXECUTING, LifecycleAction.FAIL_EXECUTION):
        ResolutionStatus.FAILED,
    (ResolutionStatus.EXECUTING, LifecycleAction.BLOCK_EXECUTION):
        ResolutionStatus.BLOCKED,
    (ResolutionStatus.COMPLETED, LifecycleAction.START_COMPENSATION):
        ResolutionStatus.COMPENSATING,
    (
        ResolutionStatus.PARTIALLY_COMPLETED,
        LifecycleAction.START_COMPENSATION,
    ): ResolutionStatus.COMPENSATING,
    (ResolutionStatus.FAILED, LifecycleAction.START_COMPENSATION):
        ResolutionStatus.COMPENSATING,
    (
        ResolutionStatus.COMPENSATING,
        LifecycleAction.COMPLETE_COMPENSATION,
    ): ResolutionStatus.COMPENSATED,
    (
        ResolutionStatus.COMPENSATING,
        LifecycleAction.COMPLETE_PARTIAL_COMPENSATION,
    ): ResolutionStatus.PARTIALLY_COMPENSATED,
    (
        ResolutionStatus.COMPENSATING,
        LifecycleAction.FAIL_COMPENSATION,
    ): ResolutionStatus.COMPENSATION_FAILED,
}

_CANCELLABLE_STATES = frozenset(
    {
        ResolutionStatus.DRAFT,
        ResolutionStatus.CONTEXT_READY,
        ResolutionStatus.ANALYZED,
        ResolutionStatus.PLAN_READY,
        ResolutionStatus.SIMULATED,
        ResolutionStatus.PENDING_AUTHORIZATION,
        ResolutionStatus.AUTHORIZED,
        ResolutionStatus.REVALIDATING,
        ResolutionStatus.READY_FOR_EXECUTION,
        ResolutionStatus.BLOCKED,
    }
)
_BLOCKABLE_STATES = frozenset(
    {
        ResolutionStatus.CONTEXT_READY,
        ResolutionStatus.ANALYZED,
        ResolutionStatus.PLAN_READY,
        ResolutionStatus.SIMULATED,
        ResolutionStatus.PENDING_AUTHORIZATION,
        ResolutionStatus.AUTHORIZED,
        ResolutionStatus.REVALIDATING,
    }
)
_REJECTABLE_STATES = frozenset(
    {
        ResolutionStatus.ANALYZED,
        ResolutionStatus.SIMULATED,
        ResolutionStatus.PENDING_AUTHORIZATION,
    }
)
_SUPERSEDEABLE_STATES = frozenset(
    {
        ResolutionStatus.DRAFT,
        ResolutionStatus.CONTEXT_READY,
        ResolutionStatus.ANALYZED,
        ResolutionStatus.PLAN_READY,
        ResolutionStatus.SIMULATED,
        ResolutionStatus.PENDING_AUTHORIZATION,
        ResolutionStatus.AUTHORIZED,
        ResolutionStatus.REVALIDATING,
        ResolutionStatus.READY_FOR_EXECUTION,
        ResolutionStatus.BLOCKED,
    }
)


class ResolutionStateMachine:
    """Única autoridad de transiciones de la raíz."""

    def transition(
        self,
        lifecycle: ResolutionLifecycle,
        action: LifecycleAction,
        *,
        occurred_at: datetime,
        actor_id: str | None,
        actor_type: str,
        actor_function: str | None = None,
        source: str = "resolution_engine",
        correlation_id: str | None = None,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> LifecycleTransition:
        action = LifecycleAction(action)
        target = self._target(lifecycle.status, action)
        if occurred_at.tzinfo is None:
            raise LifecycleInvariantError(
                action=action.value,
                violations=("occurred_at_timezone_required",),
            )
        violations = self._violations(
            lifecycle,
            action,
            occurred_at=occurred_at,
        )
        if action in {
            LifecycleAction.BLOCK,
            LifecycleAction.REJECT,
            LifecycleAction.CANCEL,
            LifecycleAction.SUPERSEDE,
        } and not (reason and reason.strip()):
            violations += ("reason_required",)
        if (
            action is LifecycleAction.SUPERSEDE
            and not (metadata or {}).get("superseded_by_resolution_id")
        ):
            violations += ("superseding_resolution_required",)
        if violations:
            raise LifecycleInvariantError(
                action=action.value,
                violations=violations,
            )
        event = LifecycleDomainEvent.build(
            lifecycle=lifecycle,
            action=action,
            new_state=target,
            occurred_at=occurred_at,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_function=actor_function,
            source=source,
            correlation_id=correlation_id,
            reason=reason,
            metadata=metadata or {},
        )
        return LifecycleTransition(
            resolution_id=lifecycle.resolution_id,
            expected_version=lifecycle.version,
            new_version=lifecycle.version + 1,
            previous_state=lifecycle.status,
            new_state=target,
            event=event,
        )

    def _target(
        self,
        state: ResolutionStatus,
        action: LifecycleAction,
    ) -> ResolutionStatus:
        target = _LINEAR_TRANSITIONS.get((state, action))
        if target is not None:
            return target
        if action is LifecycleAction.CANCEL and state in _CANCELLABLE_STATES:
            return ResolutionStatus.CANCELLED
        if action is LifecycleAction.BLOCK and state in _BLOCKABLE_STATES:
            return ResolutionStatus.BLOCKED
        if action is LifecycleAction.REJECT and state in _REJECTABLE_STATES:
            return ResolutionStatus.REJECTED
        if action is LifecycleAction.SUPERSEDE and state in _SUPERSEDEABLE_STATES:
            return ResolutionStatus.SUPERSEDED
        raise InvalidLifecycleTransitionError(
            current_state=state.value,
            action=action.value,
        )

    def _violations(
        self,
        lifecycle: ResolutionLifecycle,
        action: LifecycleAction,
        *,
        occurred_at: datetime,
    ) -> tuple[str, ...]:
        checks = {
            LifecycleAction.RECORD_CONTEXT: self._context_violations,
            LifecycleAction.RECORD_ANALYSIS: self._analysis_violations,
            LifecycleAction.RECORD_PLAN: self._plan_violations,
            LifecycleAction.RECORD_SIMULATION: self._simulation_violations,
            LifecycleAction.REQUEST_AUTHORIZATION:
                self._authorization_request_violations,
            LifecycleAction.CONFIRM_AUTHORIZATION:
                self._authorization_violations,
            LifecycleAction.BEGIN_REVALIDATION:
                self._authorization_violations,
            LifecycleAction.ACCEPT_REVALIDATION:
                self._accepted_revalidation_violations,
            LifecycleAction.REQUIRE_NEW_PLAN:
                self._new_plan_revalidation_violations,
            LifecycleAction.MARK_NO_ACTION:
                self._no_action_violations,
            LifecycleAction.REJECT:
                self._rejection_violations,
            LifecycleAction.START_EXECUTION:
                self._start_execution_violations,
            LifecycleAction.COMPLETE_EXECUTION:
                self._completed_execution_violations,
            LifecycleAction.COMPLETE_PARTIAL_EXECUTION:
                self._partial_execution_violations,
            LifecycleAction.FAIL_EXECUTION:
                self._failed_execution_violations,
            LifecycleAction.BLOCK_EXECUTION:
                self._blocked_execution_violations,
            LifecycleAction.START_COMPENSATION:
                self._start_compensation_violations,
            LifecycleAction.COMPLETE_COMPENSATION:
                self._completed_compensation_violations,
            LifecycleAction.COMPLETE_PARTIAL_COMPENSATION:
                self._partial_compensation_violations,
            LifecycleAction.FAIL_COMPENSATION:
                self._failed_compensation_violations,
        }
        check = checks.get(action)
        violations = list(check(lifecycle) if check is not None else ())
        if action in {
            LifecycleAction.REQUEST_AUTHORIZATION,
            LifecycleAction.CONFIRM_AUTHORIZATION,
            LifecycleAction.BEGIN_REVALIDATION,
            LifecycleAction.ACCEPT_REVALIDATION,
            LifecycleAction.START_EXECUTION,
        }:
            authorization = lifecycle.evidence.authorization
            if (
                authorization
                and authorization.expires_at
            ):
                if authorization.expires_at.tzinfo is None:
                    violations.append(
                        "authorization_expiry_timezone_required"
                    )
                elif occurred_at >= authorization.expires_at:
                    violations.append("authorization_expired")
        return tuple(violations)

    @staticmethod
    def _context_violations(case: ResolutionLifecycle) -> tuple[str, ...]:
        return () if case.evidence.context else ("current_context_missing",)

    @staticmethod
    def _analysis_violations(case: ResolutionLifecycle) -> tuple[str, ...]:
        context = case.evidence.context
        analysis = case.evidence.analysis
        violations = []
        if context is None:
            violations.append("current_context_missing")
        if analysis is None:
            violations.append("analysis_missing")
        elif context is not None and analysis.context_id != context.id:
            violations.append("analysis_context_mismatch")
        return tuple(violations)

    @staticmethod
    def _plan_violations(case: ResolutionLifecycle) -> tuple[str, ...]:
        evidence = case.evidence
        violations = list(ResolutionStateMachine._analysis_violations(case))
        if evidence.analysis and evidence.analysis.status is not AnalysisStatus.RESOLVABLE:
            violations.append("analysis_not_resolvable")
        if evidence.strategy is None:
            violations.append("active_strategy_missing")
        elif not evidence.strategy.is_active:
            violations.append("strategy_not_active")
        elif (
            evidence.analysis
            and evidence.strategy.analysis_id != evidence.analysis.id
        ):
            violations.append("strategy_analysis_mismatch")
        if evidence.plan is None:
            violations.append("active_plan_missing")
        else:
            if not evidence.plan.is_active:
                violations.append("plan_not_active")
            if evidence.plan.status is not PlanStatus.READY:
                violations.append("plan_not_ready")
            if evidence.context and evidence.plan.context_id != evidence.context.id:
                violations.append("plan_context_mismatch")
            if evidence.strategy and evidence.plan.strategy_id != evidence.strategy.id:
                violations.append("plan_strategy_mismatch")
        return tuple(violations)

    @staticmethod
    def _simulation_violations(case: ResolutionLifecycle) -> tuple[str, ...]:
        evidence = case.evidence
        violations = []
        if evidence.plan is None:
            violations.append("active_plan_missing")
        if evidence.simulation is None:
            violations.append("simulation_missing")
        elif evidence.plan is not None:
            if evidence.simulation.plan_id != evidence.plan.id:
                violations.append("simulation_plan_mismatch")
            if evidence.simulation.context_id != evidence.plan.context_id:
                violations.append("simulation_context_mismatch")
            if evidence.simulation.status not in {
                SimulationStatus.VALID,
                SimulationStatus.VALID_WITH_WARNINGS,
            }:
                violations.append("simulation_not_valid")
        return tuple(violations)

    @staticmethod
    def _authorization_request_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        violations = list(ResolutionStateMachine._simulation_violations(case))
        if not case.requires_authorization:
            violations.append("authorization_not_required")
        authorization = case.evidence.authorization
        if authorization is None:
            violations.append("authorization_request_missing")
        elif authorization.status not in {
            AuthorizationRequestStatus.PENDING,
            AuthorizationRequestStatus.PARTIALLY_APPROVED,
        }:
            violations.append("authorization_request_not_pending")
        violations.extend(
            ResolutionStateMachine._authorization_scope_violations(case)
        )
        return tuple(dict.fromkeys(violations))

    @staticmethod
    def _authorization_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        violations = list(ResolutionStateMachine._simulation_violations(case))
        authorization = case.evidence.authorization
        policy = case.evidence.policy_authorization
        if case.requires_authorization:
            if authorization is None:
                violations.append("authorization_evidence_missing")
            elif (
                authorization.status
                is not AuthorizationRequestStatus.APPROVED
            ):
                violations.append("authorization_not_approved")
            elif (
                authorization.approved_decision_count
                < authorization.required_approvals
            ):
                violations.append("authorization_approvals_incomplete")
            elif authorization.has_blocking_decision:
                violations.append("authorization_has_blocking_decision")
            violations.extend(
                ResolutionStateMachine._authorization_scope_violations(case)
            )
        else:
            if policy is None or policy.outcome != "allowed":
                violations.append("policy_authorization_missing")
            elif case.evidence.plan and case.evidence.simulation:
                plan = case.evidence.plan
                simulation = case.evidence.simulation
                if (
                    policy.plan_id != plan.id
                    or policy.plan_version != plan.version
                    or policy.plan_hash != plan.plan_hash
                ):
                    violations.append("policy_authorization_plan_mismatch")
                if (
                    policy.simulation_id != simulation.id
                    or policy.simulation_hash != simulation.simulation_hash
                ):
                    violations.append(
                        "policy_authorization_simulation_mismatch"
                    )
        return tuple(dict.fromkeys(violations))

    @staticmethod
    def _authorization_scope_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        evidence = case.evidence
        authorization = evidence.authorization
        plan = evidence.plan
        simulation = evidence.simulation
        if authorization is None or plan is None or simulation is None:
            return ()
        violations = []
        if (
            authorization.plan_id != plan.id
            or authorization.plan_hash != plan.plan_hash
        ):
            violations.append("authorization_plan_mismatch")
        if (
            authorization.simulation_id != simulation.id
            or authorization.simulation_hash != simulation.simulation_hash
        ):
            violations.append("authorization_simulation_mismatch")
        return tuple(violations)

    @staticmethod
    def _accepted_revalidation_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        evidence = case.evidence
        violations = list(ResolutionStateMachine._authorization_violations(case))
        revalidation = evidence.revalidation
        if revalidation is None:
            violations.append("revalidation_missing")
        else:
            if evidence.plan and revalidation.plan_id != evidence.plan.id:
                violations.append("revalidation_plan_mismatch")
            if evidence.context and revalidation.current_context_id != evidence.context.id:
                violations.append("revalidation_current_context_mismatch")
            if evidence.plan and (
                revalidation.previous_context_id != evidence.plan.context_id
            ):
                violations.append("revalidation_previous_context_mismatch")
            if revalidation.status not in {
                RevalidationStatus.VALID,
                RevalidationStatus.VALID_WITH_WARNINGS,
            }:
                violations.append("revalidation_not_valid")
        return tuple(dict.fromkeys(violations))

    @staticmethod
    def _new_plan_revalidation_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        evidence = case.evidence
        revalidation = evidence.revalidation
        if revalidation is None:
            return ("revalidation_missing",)
        violations = []
        if evidence.plan and revalidation.plan_id != evidence.plan.id:
            violations.append("revalidation_plan_mismatch")
        if revalidation.status is not RevalidationStatus.REQUIRES_NEW_PLAN:
            violations.append("revalidation_does_not_require_new_plan")
        return tuple(violations)

    @staticmethod
    def _no_action_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        if case.status is ResolutionStatus.ANALYZED:
            analysis = case.evidence.analysis
            if analysis and analysis.status is AnalysisStatus.ALREADY_RESOLVED:
                return ()
            return ("analysis_does_not_support_no_action",)
        revalidation = case.evidence.revalidation
        if (
            revalidation
            and revalidation.status is RevalidationStatus.NO_LONGER_RESOLVABLE
        ):
            return ()
        return ("revalidation_does_not_support_no_action",)

    @staticmethod
    def _rejection_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        if case.status is not ResolutionStatus.PENDING_AUTHORIZATION:
            return ()
        authorization = case.evidence.authorization
        if (
            authorization
            and authorization.status is AuthorizationRequestStatus.REJECTED
        ):
            return ()
        return ("authorization_rejection_missing",)

    @staticmethod
    def _start_execution_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        violations = list(
            ResolutionStateMachine._accepted_revalidation_violations(case)
        )
        plan = case.evidence.plan
        if plan is None or plan.status is not PlanStatus.AUTHORIZED:
            violations.append("plan_not_authorized")
        if case.evidence.execution is not None:
            violations.append("execution_already_exists")
        return tuple(dict.fromkeys(violations))

    @staticmethod
    def _execution_violations(
        case: ResolutionLifecycle,
        *,
        expected_status: str,
    ) -> list[str]:
        execution = case.evidence.execution
        violations: list[str] = []
        if execution is None:
            return ["execution_missing"]
        plan = case.evidence.plan
        revalidation = case.evidence.revalidation
        if plan is None or execution.plan_id != plan.id:
            violations.append("execution_plan_mismatch")
        if revalidation is None or execution.revalidation_id != revalidation.id:
            violations.append("execution_revalidation_mismatch")
        if execution.status != expected_status:
            violations.append("execution_status_mismatch")
        if execution.total_steps <= 0:
            violations.append("execution_has_no_steps")
        return violations

    @staticmethod
    def _completed_execution_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        violations = ResolutionStateMachine._execution_violations(
            case,
            expected_status="completed",
        )
        execution = case.evidence.execution
        if execution and (
            execution.completed_steps != execution.total_steps
            or execution.failed_steps
            or execution.blocked_steps
        ):
            violations.append("execution_not_fully_completed")
        return tuple(violations)

    @staticmethod
    def _partial_execution_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        violations = ResolutionStateMachine._execution_violations(
            case,
            expected_status="partially_completed",
        )
        execution = case.evidence.execution
        if execution and (
            execution.completed_steps <= 0
            or execution.failed_steps <= 0
            or execution.blocked_steps
        ):
            violations.append("execution_not_partial")
        return tuple(violations)

    @staticmethod
    def _failed_execution_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        violations = ResolutionStateMachine._execution_violations(
            case,
            expected_status="failed",
        )
        execution = case.evidence.execution
        if execution and (
            execution.completed_steps
            or execution.failed_steps <= 0
            or execution.blocked_steps
        ):
            violations.append("execution_not_failed")
        return tuple(violations)

    @staticmethod
    def _blocked_execution_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        violations = ResolutionStateMachine._execution_violations(
            case,
            expected_status="blocked",
        )
        execution = case.evidence.execution
        if execution and execution.blocked_steps <= 0:
            violations.append("execution_not_blocked")
        return tuple(violations)

    @staticmethod
    def _start_compensation_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        compensation = case.evidence.compensation
        execution = case.evidence.execution
        violations: list[str] = []
        if execution is None:
            violations.append("execution_missing")
        if compensation is None:
            violations.append("compensation_plan_missing")
            return tuple(violations)
        if compensation.status != "prepared":
            violations.append("compensation_plan_not_prepared")
        if compensation.total_steps <= 0:
            violations.append("compensation_plan_has_no_steps")
        if (
            execution is not None
            and compensation.source_execution_id != execution.id
        ):
            violations.append("compensation_source_execution_mismatch")
        if compensation.execution_id is not None:
            violations.append("compensation_execution_already_exists")
        return tuple(violations)

    @staticmethod
    def _compensation_violations(
        case: ResolutionLifecycle,
        *,
        expected_status: str,
    ) -> list[str]:
        compensation = case.evidence.compensation
        if compensation is None:
            return ["compensation_evidence_missing"]
        violations: list[str] = []
        if compensation.execution_id is None:
            violations.append("compensation_execution_missing")
        if compensation.status != expected_status:
            violations.append("compensation_status_mismatch")
        if compensation.total_steps <= 0:
            violations.append("compensation_has_no_steps")
        return violations

    @staticmethod
    def _completed_compensation_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        violations = ResolutionStateMachine._compensation_violations(
            case,
            expected_status="compensated",
        )
        compensation = case.evidence.compensation
        if compensation and (
            compensation.compensated_steps != compensation.total_steps
            or compensation.failed_steps
            or compensation.blocked_steps
        ):
            violations.append("compensation_not_complete")
        return tuple(violations)

    @staticmethod
    def _partial_compensation_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        violations = ResolutionStateMachine._compensation_violations(
            case,
            expected_status="partially_compensated",
        )
        compensation = case.evidence.compensation
        if compensation and (
            compensation.compensated_steps <= 0
            or compensation.failed_steps <= 0
            or compensation.blocked_steps
        ):
            violations.append("compensation_not_partial")
        return tuple(violations)

    @staticmethod
    def _failed_compensation_violations(
        case: ResolutionLifecycle,
    ) -> tuple[str, ...]:
        compensation = case.evidence.compensation
        if compensation is None:
            return ("compensation_evidence_missing",)
        if compensation.status not in {"failed", "blocked"}:
            return ("compensation_status_mismatch",)
        violations = []
        if compensation.execution_id is None:
            violations.append("compensation_execution_missing")
        if compensation.status == "failed" and compensation.failed_steps <= 0:
            violations.append("compensation_has_no_failed_step")
        if (
            compensation.status == "blocked"
            and compensation.blocked_steps <= 0
        ):
            violations.append("compensation_has_no_blocked_step")
        return tuple(violations)
