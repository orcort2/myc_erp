from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.resolution_engine.application.action_runner import ActionRunner
from app.resolution_engine.application.execution import ResolutionExecutor
from app.resolution_engine.contracts.execution import (
    ExecuteResolutionCommand,
    StartExecutionResult,
    StepStartResult,
)
from app.resolution_engine.domain.enums import (
    AnalysisStatus,
    AuthorizationRequestStatus,
    EntityRelationshipType,
    ExecutionStatus,
    PlanStatus,
    ResolutionResult,
    ResolutionStatus,
    RevalidationStatus,
    SimulationStatus,
)
from app.resolution_engine.domain.exceptions import (
    DuplicateActionHandlerError,
    InvalidExecutionPlanError,
    LifecycleInvariantError,
)
from app.resolution_engine.domain.execution import (
    ActionCertainty,
    DomainActionResult,
    ExecutionCandidate,
    ExecutionEngine,
    ExecutionEntityEffect,
    ExecutionOutcome,
    ExecutionPlanStep,
    ExecutionReservation,
)
from app.resolution_engine.domain.lifecycle import (
    AnalysisEvidence,
    AuthorizationEvidence,
    ContextEvidence,
    ExecutionEvidence,
    LifecycleEvidence,
    PlanEvidence,
    ResolutionLifecycle,
    ResolutionStateMachine,
    RevalidationEvidence,
    SimulationEvidence,
    StrategyEvidence,
)
from app.resolution_engine.domain.security import (
    ActorContext,
    ActorIdentity,
    ActorType,
    AuthenticationContext,
)
from app.resolution_engine.domain.value_objects import ComponentKey

NOW = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)
PLAN_HASH = "a" * 64
SIMULATION_HASH = "b" * 64


class Clock:
    def __init__(self):
        self.current = NOW

    def now(self):
        self.current += timedelta(seconds=1)
        return self.current


class Identifiers:
    def __init__(self):
        self.value = 0

    def new_id(self):
        self.value += 1
        return f"token-{self.value}"


def actor():
    return ActorContext(
        identity=ActorIdentity(
            actor_id="actor-1",
            actor_type=ActorType.HUMAN,
            principal="actor@example.test",
            organization_id="organization-1",
        ),
        authentication=AuthenticationContext(
            authenticated_at=NOW - timedelta(minutes=1),
            method="test",
            session_id="session-1",
            assurance_level="high",
            source="test",
            correlation_id="correlation-1",
        ),
    )


def lifecycle(status=ResolutionStatus.READY_FOR_EXECUTION):
    return ResolutionLifecycle(
        resolution_id=1,
        public_id="resolution-1",
        resolution_type="example.resolve",
        definition_version="1.0",
        status=status,
        version=9,
        requires_authorization=True,
        evidence=LifecycleEvidence(
            context=ContextEvidence(id=10, context_hash="c" * 64),
            analysis=AnalysisEvidence(
                id=20,
                context_id=10,
                status=AnalysisStatus.RESOLVABLE,
            ),
            strategy=StrategyEvidence(
                id=30,
                analysis_id=20,
                is_active=True,
            ),
            plan=PlanEvidence(
                id=40,
                version=1,
                plan_hash=PLAN_HASH,
                context_id=10,
                strategy_id=30,
                status=PlanStatus.AUTHORIZED,
                is_active=True,
            ),
            simulation=SimulationEvidence(
                id=50,
                simulation_hash=SIMULATION_HASH,
                plan_id=40,
                context_id=10,
                status=SimulationStatus.VALID,
            ),
            authorization=AuthorizationEvidence(
                request_id=60,
                plan_id=40,
                plan_hash=PLAN_HASH,
                simulation_id=50,
                simulation_hash=SIMULATION_HASH,
                status=AuthorizationRequestStatus.APPROVED,
                required_approvals=1,
                approved_decision_count=1,
                has_blocking_decision=False,
                expires_at=None,
            ),
            revalidation=RevalidationEvidence(
                id=70,
                plan_id=40,
                previous_context_id=10,
                current_context_id=10,
                status=RevalidationStatus.VALID,
            ),
        ),
    )


def steps():
    return (
        ExecutionPlanStep(
            id=101,
            step_key="first",
            sequence=1,
            operation_key="example.first",
            owner_module="example",
            input_payload={"value": 1},
        ),
        ExecutionPlanStep(
            id=102,
            step_key="second",
            sequence=2,
            operation_key="example.second",
            owner_module="example",
            input_payload={"value": 2},
            dependency_ids=(101,),
        ),
    )


def candidate():
    return ExecutionCandidate(
        lifecycle=lifecycle(),
        plan_id=40,
        plan_version=1,
        plan_hash=PLAN_HASH,
        revalidation_id=70,
        initial_context_hash="c" * 64,
        steps=steps(),
    )


class Handler:
    def __init__(self, key, result):
        self.operation_key = ComponentKey(key)
        self.result = result
        self.calls = []

    def execute(self, request):
        self.calls.append(request)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeStore:
    def __init__(self, current_candidate, previous=None):
        self.candidate = current_candidate
        self.previous = previous
        self.results = {}
        self.started = False
        self.renewed = 0
        self.finished = None

    def load_candidate(self, resolution_id):
        assert resolution_id == self.candidate.lifecycle.resolution_id
        return self.candidate

    def find_outcome(self, **values):
        return self.previous

    def start(self, **values):
        if self.previous is not None:
            return StartExecutionResult(previous_outcome=self.previous)
        self.started = True
        executing = replace(
            self.candidate.lifecycle,
            status=ResolutionStatus.EXECUTING,
            version=self.candidate.lifecycle.version + 1,
            evidence=replace(
                self.candidate.lifecycle.evidence,
                execution=ExecutionEvidence(
                    id=80,
                    plan_id=40,
                    revalidation_id=70,
                    status="running",
                    total_steps=2,
                    completed_steps=0,
                    failed_steps=0,
                    blocked_steps=0,
                ),
            ),
        )
        return StartExecutionResult(
            reservation=ExecutionReservation(
                execution_id=80,
                resolution_id=1,
                plan_id=40,
                plan_version=1,
                plan_hash=PLAN_HASH,
                revalidation_id=70,
                execution_key=values["execution_key"],
                lock_token=values["lock_token"],
                actor_id="actor-1",
                actor_type="human",
                actor_source="test",
                correlation_id="correlation-1",
                lifecycle=executing,
                steps=values["steps"],
                step_execution_ids={101: 201, 102: 202},
            )
        )

    def renew_lock(self, reservation, **values):
        self.renewed += 1

    def start_step(self, reservation, step, **values):
        return StepStartResult(
            step_execution_id=reservation.step_execution_ids[step.id]
        )

    def record_step_result(
        self,
        reservation,
        step,
        result,
        **values,
    ):
        self.results[step.id] = result

    def finish(
        self,
        reservation,
        summary,
        transition,
        **values,
    ):
        self.finished = (summary, transition)
        return values["outcome"]


def executor(store, handlers):
    return ResolutionExecutor(
        store=store,
        action_runner=ActionRunner(tuple(handlers)),
        engine=ExecutionEngine(),
        state_machine=ResolutionStateMachine(),
        clock=Clock(),
        identifiers=Identifiers(),
    )


def command():
    return ExecuteResolutionCommand(
        resolution_id=1,
        idempotency_key="request-1",
        actor=actor(),
        lock_owner="test",
    )


def success_result(entity_id):
    return DomainActionResult(
        success=True,
        certainty=ActionCertainty.CONFIRMED,
        response_payload={"entity_id": entity_id},
        entity_effects=(
            ExecutionEntityEffect(
                relationship=EntityRelationshipType.CREATED,
                entity_type="example",
                entity_id=entity_id,
                module="example",
            ),
        ),
    )


def test_execution_engine_orders_dependencies_and_rejects_forward_edges():
    engine = ExecutionEngine()
    value = candidate()

    assert [item.step_key for item in engine.ordered_steps(value)] == [
        "first",
        "second",
    ]

    invalid = replace(
        value,
        steps=(
            replace(value.steps[0], dependency_ids=(102,)),
            value.steps[1],
        ),
    )
    with pytest.raises(InvalidExecutionPlanError):
        engine.ordered_steps(invalid)


@pytest.mark.parametrize(
    ("results", "execution_status", "resolution_result"),
    [
        (
            {
                101: success_result("1"),
                102: success_result("2"),
            },
            ExecutionStatus.COMPLETED,
            ResolutionResult.SUCCESS,
        ),
        (
            {
                101: success_result("1"),
                102: DomainActionResult(
                    success=False,
                    certainty=ActionCertainty.CONFIRMED,
                    error_code="rejected",
                ),
            },
            ExecutionStatus.PARTIALLY_COMPLETED,
            ResolutionResult.PARTIAL_SUCCESS,
        ),
        (
            {
                101: DomainActionResult(
                    success=False,
                    certainty=ActionCertainty.CONFIRMED,
                    error_code="rejected",
                )
            },
            ExecutionStatus.FAILED,
            ResolutionResult.FAILED,
        ),
        (
            {
                101: DomainActionResult(
                    success=False,
                    certainty=ActionCertainty.UNCERTAIN,
                    error_code="uncertain",
                )
            },
            ExecutionStatus.BLOCKED,
            None,
        ),
    ],
)
def test_execution_engine_consolidates_results(
    results,
    execution_status,
    resolution_result,
):
    summary = ExecutionEngine().summarize(
        steps=steps(),
        results=results,
    )

    assert summary.execution_status is execution_status
    assert summary.resolution_result is resolution_result


def test_executor_runs_each_action_once_and_completes():
    first = Handler("example.first", success_result("1"))
    second = Handler("example.second", success_result("2"))
    store = FakeStore(candidate())

    outcome = executor(store, (first, second)).execute(command())

    assert outcome.execution_status is ExecutionStatus.COMPLETED
    assert outcome.resolution_status == ResolutionStatus.COMPLETED.value
    assert len(first.calls) == len(second.calls) == 1
    assert first.calls[0].idempotency_key != second.calls[0].idempotency_key
    assert store.renewed == 2
    assert store.finished[0].completed_steps == 2


def test_confirmed_failure_stops_remaining_actions_and_is_not_retried():
    first = Handler(
        "example.first",
        DomainActionResult(
            success=False,
            certainty=ActionCertainty.CONFIRMED,
            error_code="domain_rejected",
        ),
    )
    second = Handler("example.second", success_result("2"))
    store = FakeStore(candidate())

    outcome = executor(store, (first, second)).execute(command())

    assert outcome.execution_status is ExecutionStatus.FAILED
    assert len(first.calls) == 1
    assert second.calls == []
    assert store.finished[0].failed_steps == 1


def test_uncertain_handler_response_blocks_without_retry():
    first = Handler("example.first", RuntimeError("connection lost"))
    second = Handler("example.second", success_result("2"))
    store = FakeStore(candidate())

    outcome = executor(store, (first, second)).execute(command())

    assert outcome.execution_status is ExecutionStatus.BLOCKED
    assert outcome.resolution_status == ResolutionStatus.BLOCKED.value
    assert len(first.calls) == 1
    assert second.calls == []


def test_execution_level_idempotency_returns_previous_outcome():
    previous = ExecutionOutcome(
        execution_id=80,
        resolution_id=1,
        execution_status=ExecutionStatus.COMPLETED,
        resolution_status=ResolutionStatus.COMPLETED.value,
        idempotency_key="request-1",
        idempotent_replay=True,
        completed_steps=2,
        failed_steps=0,
        blocked_steps=0,
        total_steps=2,
        result_hash="d" * 64,
    )
    handler = Handler("example.first", success_result("1"))
    store = FakeStore(
        replace(
            candidate(),
            lifecycle=lifecycle(ResolutionStatus.COMPLETED),
        ),
        previous=previous,
    )

    outcome = executor(store, (handler,)).execute(command())

    assert outcome is previous
    assert handler.calls == []


def test_executor_rejects_a_plan_without_authorization_before_actions():
    value = candidate()
    unauthorized = replace(
        value,
        lifecycle=replace(
            value.lifecycle,
            evidence=replace(
                value.lifecycle.evidence,
                plan=replace(
                    value.lifecycle.evidence.plan,
                    status=PlanStatus.READY,
                ),
            ),
        ),
    )
    handler = Handler("example.first", success_result("1"))

    with pytest.raises(
        LifecycleInvariantError,
        match="plan_not_authorized",
    ):
        executor(FakeStore(unauthorized), (handler,)).execute(command())

    assert handler.calls == []


def test_action_runner_rejects_duplicate_handlers():
    with pytest.raises(DuplicateActionHandlerError):
        ActionRunner(
            (
                Handler("example.first", success_result("1")),
                Handler("example.first", success_result("2")),
            )
        )
