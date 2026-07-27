from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.resolution_engine.application.compensation import (
    CompensationExecutor,
    CompensationPlanner,
)
from app.resolution_engine.application.compensation_runner import (
    CompensationRunner,
)
from app.resolution_engine.contracts.compensation import (
    ExecuteCompensationCommand,
    PrepareCompensationCommand,
)
from app.resolution_engine.domain.compensation import CompensationEngine
from app.resolution_engine.domain.enums import (
    CompensationStatus,
    CompensationStrategy,
    ResolutionStatus,
)
from app.resolution_engine.domain.exceptions import (
    CompensationNotAllowedError,
    InvalidCompensationPlanError,
)
from app.resolution_engine.domain.execution import (
    ActionCertainty,
    DomainActionResult,
)
from app.resolution_engine.domain.lifecycle import ResolutionStateMachine
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_engine.infrastructure.compensation import (
    SqlAlchemyCompensationStore,
)
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionAuditEvent,
    ResolutionCompensationExecution,
    ResolutionCompensationPlan,
    ResolutionCompensationStepExecution,
    ResolutionExecution,
    ResolutionOutboxEvent,
    ResolutionPlan,
    ResolutionPlanStep,
    ResolutionPlanStepDependency,
    ResolutionSecurityDecision,
    ResolutionStepExecution,
)
from app.resolution_engine.infrastructure.repositories import (
    ResolutionRepository,
)
from tests.resolution_engine.test_execution_persistence import (
    AdvancingClock,
    Handler as ExecutionHandler,
    NOW,
    actor,
    build_executor,
    command,
    seed_ready_resolution,
    sqlite_engine,
)


class CompensationHandler:
    operation_key = ComponentKey("example.cancel")

    def __init__(self, *, fail_uncertain=False, after_call=None):
        self.calls = []
        self.fail_uncertain = fail_uncertain
        self.after_call = after_call

    def execute(self, request):
        self.calls.append(request)
        if self.fail_uncertain:
            raise RuntimeError("connection lost")
        if self.after_call is not None:
            self.after_call(request)
        return DomainActionResult(
            success=True,
            certainty=ActionCertainty.CONFIRMED,
            response_payload={"cancelled": "created-1"},
            domain_transaction_reference="cancel-tx-1",
        )


class CompensationIdentifiers:
    def new_id(self):
        return "compensation-lock-token"


def seed_completed_compensable_execution(factory):
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
        step = session.scalar(select(ResolutionPlanStep))
        step.is_compensable = True
        step.compensation_operation_key = "example.cancel"
        step.compensation_payload = {"entity_id": "created-1"}
        session.commit()
    build_executor(factory, ExecutionHandler()).execute(
        command(resolution_id)
    )
    with factory() as session:
        execution = session.scalar(select(ResolutionExecution))
        decision = ResolutionSecurityDecision(
            resolution_id=resolution_id,
            actor_id=actor().identity.actor_id,
            actor_type=actor().identity.actor_type.value,
            organization_id=actor().identity.organization_id,
            action="resolution.compensate",
            resource_type="resolution_execution",
            resource_id=str(execution.id),
            outcome="allowed",
            policy_results=[],
            required_permissions=["resolution.compensate"],
            reason_codes=["allowed_for_test"],
            actor_snapshot=actor().identity.snapshot(),
            authentication_snapshot=actor().authentication.snapshot(),
            context_snapshot={},
            evaluated_at=NOW,
            correlation_id=actor().authentication.correlation_id,
            evidence_hash="9" * 64,
        )
        session.add(decision)
        session.commit()
        return resolution_id, execution.id, decision.id


def seed_completed_dependency_chain(factory):
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
        plan = session.scalar(select(ResolutionPlan))
        step_a = session.scalar(select(ResolutionPlanStep))
        step_a.step_key = "A"
        step_a.description = "Create A"
        step_a.is_compensable = True
        step_a.compensation_operation_key = "example.cancel"
        step_a.compensation_payload = {"step": "A"}
        step_b = ResolutionPlanStep(
            plan_id=plan.id,
            step_key="B",
            sequence=2,
            operation_key="example.create",
            owner_module="example",
            description="Use A to create B",
            input_payload={"step": "B"},
            is_compensable=True,
            compensation_operation_key="example.cancel",
            compensation_payload={"step": "B"},
            step_hash="b" * 64,
        )
        step_c = ResolutionPlanStep(
            plan_id=plan.id,
            step_key="C",
            sequence=3,
            operation_key="example.create",
            owner_module="example",
            description="Use B to create C",
            input_payload={"step": "C"},
            is_compensable=True,
            compensation_operation_key="example.cancel",
            compensation_payload={"step": "C"},
            step_hash="c" * 64,
        )
        session.add_all((step_b, step_c))
        session.flush()
        session.add_all(
            (
                ResolutionPlanStepDependency(
                    plan_id=plan.id,
                    step_id=step_b.id,
                    depends_on_step_id=step_a.id,
                ),
                ResolutionPlanStepDependency(
                    plan_id=plan.id,
                    step_id=step_c.id,
                    depends_on_step_id=step_b.id,
                ),
            )
        )
        session.commit()
    build_executor(factory, ExecutionHandler()).execute(
        command(resolution_id)
    )
    with factory() as session:
        execution = session.scalar(select(ResolutionExecution))
        step_execution_ids = {
            step_key: step_execution_id
            for step_key, step_execution_id in session.execute(
                select(
                    ResolutionPlanStep.step_key,
                    ResolutionStepExecution.id,
                ).join(
                    ResolutionStepExecution,
                    ResolutionStepExecution.plan_step_id
                    == ResolutionPlanStep.id,
                )
            )
        }
        decision = ResolutionSecurityDecision(
            resolution_id=resolution_id,
            actor_id=actor().identity.actor_id,
            actor_type=actor().identity.actor_type.value,
            organization_id=actor().identity.organization_id,
            action="resolution.compensate",
            resource_type="resolution_execution",
            resource_id=str(execution.id),
            outcome="allowed",
            policy_results=[],
            required_permissions=["resolution.compensate"],
            reason_codes=["allowed_for_dependency_test"],
            actor_snapshot=actor().identity.snapshot(),
            authentication_snapshot=actor().authentication.snapshot(),
            context_snapshot={},
            evaluated_at=NOW,
            correlation_id=actor().authentication.correlation_id,
            evidence_hash="8" * 64,
        )
        session.add(decision)
        session.commit()
        return (
            resolution_id,
            execution.id,
            decision.id,
            step_execution_ids,
        )


def prepare_command(resolution_id, execution_id, decision_id, *, key="plan-1"):
    return PrepareCompensationCommand(
        resolution_id=resolution_id,
        source_execution_id=execution_id,
        strategy=CompensationStrategy.TOTAL,
        reason="restore institutional consistency",
        security_decision_id=decision_id,
        idempotency_key=key,
        actor=actor(),
    )


def prepare_partial_command(
    resolution_id,
    execution_id,
    decision_id,
    selected_ids,
    *,
    key,
):
    return PrepareCompensationCommand(
        resolution_id=resolution_id,
        source_execution_id=execution_id,
        strategy=CompensationStrategy.PARTIAL,
        reason="dependency-closed partial compensation",
        security_decision_id=decision_id,
        idempotency_key=key,
        actor=actor(),
        selected_step_execution_ids=tuple(selected_ids),
    )


def build_services(factory, handler, *, clock=None):
    store = SqlAlchemyCompensationStore(factory)
    clock = clock or AdvancingClock(NOW + timedelta(hours=2))
    engine = CompensationEngine()
    return (
        CompensationPlanner(
            store=store,
            engine=engine,
            clock=clock,
        ),
        CompensationExecutor(
            store=store,
            runner=CompensationRunner((handler,)),
            engine=engine,
            state_machine=ResolutionStateMachine(),
            clock=clock,
            identifiers=CompensationIdentifiers(),
        ),
    )


def test_compensation_persists_exact_evidence_and_replays_once():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    resolution_id, execution_id, decision_id = (
        seed_completed_compensable_execution(factory)
    )
    handler = CompensationHandler()
    planner, executor = build_services(factory, handler)

    plan = planner.prepare(
        prepare_command(resolution_id, execution_id, decision_id)
    )
    outcome = executor.execute(
        ExecuteCompensationCommand(
            compensation_plan_id=plan.id,
            idempotency_key="compensation-1",
            actor=actor(),
            lock_owner="phase-6-test",
        )
    )
    replay = executor.execute(
        ExecuteCompensationCommand(
            compensation_plan_id=plan.id,
            idempotency_key="compensation-1",
            actor=actor(),
            lock_owner="phase-6-test",
        )
    )

    assert outcome.status is CompensationStatus.COMPENSATED
    assert replay.idempotent_replay is True
    assert len(handler.calls) == 1
    with factory() as session:
        root = session.get(Resolution, resolution_id)
        original = session.get(ResolutionExecution, execution_id)
        compensation = session.scalar(
            select(ResolutionCompensationExecution)
        )
        step = session.scalar(
            select(ResolutionCompensationStepExecution)
        )
        record = ResolutionRepository(session).load_record(resolution_id)
        assert root.status == ResolutionStatus.COMPENSATED.value
        assert original.status == "completed"
        assert compensation.status == "compensated"
        assert step.status == "compensated"
        assert step.domain_transaction_reference == "cancel-tx-1"
        assert len(record.compensation_plans) == 1
        assert len(record.compensation_step_executions) == 1
        compensation_audits = session.scalar(
            select(func.count(ResolutionAuditEvent.id)).where(
                ResolutionAuditEvent.event_type.in_(
                    (
                        "resolution.compensation_plan_prepared",
                        "resolution.compensation_step_started",
                        "resolution.compensation_step_completed",
                        "resolution.lifecycle.start_compensation",
                        "resolution.lifecycle.complete_compensation",
                    )
                )
            )
        )
        assert compensation_audits == 5
        assert session.scalar(
            select(func.count(ResolutionOutboxEvent.id)).where(
                ResolutionOutboxEvent.event_type
                == "resolution.compensation_completed"
            )
        ) == 1


def test_uncertain_compensation_blocks_without_second_invocation():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    resolution_id, execution_id, decision_id = (
        seed_completed_compensable_execution(factory)
    )
    handler = CompensationHandler(fail_uncertain=True)
    planner, executor = build_services(factory, handler)
    plan = planner.prepare(
        prepare_command(resolution_id, execution_id, decision_id)
    )

    outcome = executor.execute(
        ExecuteCompensationCommand(
            compensation_plan_id=plan.id,
            idempotency_key="compensation-uncertain",
            actor=actor(),
            lock_owner="phase-6-test",
        )
    )

    assert outcome.status is CompensationStatus.BLOCKED
    assert len(handler.calls) == 1
    with factory() as session:
        assert session.get(Resolution, resolution_id).status == (
            ResolutionStatus.COMPENSATION_FAILED.value
        )
        step = session.scalar(
            select(ResolutionCompensationStepExecution)
        )
        assert step.status == "blocked"
        assert step.error_code == "compensation_result_uncertain"


def test_compensation_rejects_denied_or_foreign_security_evidence():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    resolution_id, execution_id, decision_id = (
        seed_completed_compensable_execution(factory)
    )
    with factory() as session:
        session.get(ResolutionSecurityDecision, decision_id).outcome = (
            "denied"
        )
        session.commit()
    planner, _ = build_services(factory, CompensationHandler())

    with pytest.raises(
        CompensationNotAllowedError,
        match="authorization",
    ):
        planner.prepare(
            prepare_command(resolution_id, execution_id, decision_id)
        )
    with factory() as session:
        assert session.scalar(
            select(func.count(ResolutionCompensationPlan.id))
        ) == 0


def test_plan_replay_revalidates_security_before_returning_evidence():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    resolution_id, execution_id, decision_id = (
        seed_completed_compensable_execution(factory)
    )
    planner, _ = build_services(factory, CompensationHandler())
    command = prepare_command(
        resolution_id,
        execution_id,
        decision_id,
    )
    planner.prepare(command)
    with factory() as session:
        session.get(ResolutionSecurityDecision, decision_id).outcome = (
            "denied"
        )
        session.commit()

    with pytest.raises(
        CompensationNotAllowedError,
        match="authorization",
    ):
        planner.prepare(command)


def test_compensation_execution_rejects_an_actor_other_than_authorized():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    resolution_id, execution_id, decision_id = (
        seed_completed_compensable_execution(factory)
    )
    planner, executor = build_services(factory, CompensationHandler())
    plan = planner.prepare(
        prepare_command(resolution_id, execution_id, decision_id)
    )
    authorized = actor()
    other_actor = replace(
        authorized,
        identity=replace(
            authorized.identity,
            actor_id="executor-2",
            principal="another-executor@example.test",
        ),
    )

    with pytest.raises(
        CompensationNotAllowedError,
        match="actor is not authorized",
    ):
        executor.execute(
            ExecuteCompensationCommand(
                compensation_plan_id=plan.id,
                idempotency_key="unauthorized-execution",
                actor=other_actor,
                lock_owner="phase-6-test",
            )
        )

    with factory() as session:
        assert session.get(Resolution, resolution_id).status == (
            ResolutionStatus.COMPLETED.value
        )
        assert session.scalar(
            select(func.count(ResolutionCompensationExecution.id))
        ) == 0


def test_expired_lock_after_compensation_handler_blocks_without_retry():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    resolution_id, execution_id, decision_id = (
        seed_completed_compensable_execution(factory)
    )
    clock = AdvancingClock(NOW + timedelta(hours=2))
    handler = CompensationHandler(
        after_call=lambda _: setattr(
            clock,
            "current",
            clock.current + timedelta(minutes=10),
        )
    )
    planner, executor = build_services(
        factory,
        handler,
        clock=clock,
    )
    plan = planner.prepare(
        prepare_command(resolution_id, execution_id, decision_id)
    )

    outcome = executor.execute(
        ExecuteCompensationCommand(
            compensation_plan_id=plan.id,
            idempotency_key="compensation-expired-lock",
            actor=actor(),
            lock_owner="phase-6-test",
        )
    )

    assert outcome.status is CompensationStatus.BLOCKED
    assert len(handler.calls) == 1
    with factory() as session:
        step = session.scalar(
            select(ResolutionCompensationStepExecution)
        )
        assert step.status == "blocked"
        assert step.error_code == "compensation_lock_lost_after_action"


def test_same_confirmed_step_cannot_be_planned_for_compensation_twice():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    resolution_id, execution_id, decision_id = (
        seed_completed_compensable_execution(factory)
    )
    planner, _ = build_services(factory, CompensationHandler())
    planner.prepare(
        prepare_command(
            resolution_id,
            execution_id,
            decision_id,
            key="first-plan",
        )
    )

    with pytest.raises(
        CompensationNotAllowedError,
        match="conflicts",
    ):
        planner.prepare(
            prepare_command(
                resolution_id,
                execution_id,
                decision_id,
                key="second-plan",
            )
        )


def test_point_of_no_return_prevents_ordinary_compensation():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    resolution_id, execution_id, decision_id = (
        seed_completed_compensable_execution(factory)
    )
    with factory() as session:
        session.scalar(select(ResolutionPlanStep)).point_of_no_return = True
        session.commit()
    planner, _ = build_services(factory, CompensationHandler())

    with pytest.raises(
        InvalidCompensationPlanError,
        match="unavailable",
    ):
        planner.prepare(
            prepare_command(
                resolution_id,
                execution_id,
                decision_id,
            )
        )


@pytest.mark.parametrize(
    "selected_keys",
    [
        ("A",),
        ("A", "B"),
    ],
)
def test_open_partial_dependency_selection_is_not_persisted(
    selected_keys,
):
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    (
        resolution_id,
        execution_id,
        decision_id,
        step_ids,
    ) = seed_completed_dependency_chain(factory)
    planner, _ = build_services(factory, CompensationHandler())

    with pytest.raises(
        InvalidCompensationPlanError,
        match="dependency closure violated",
    ):
        planner.prepare(
            prepare_partial_command(
                resolution_id,
                execution_id,
                decision_id,
                (step_ids[key] for key in selected_keys),
                key=f"invalid-{'-'.join(selected_keys)}",
            )
        )

    with factory() as session:
        assert session.scalar(
            select(func.count(ResolutionCompensationPlan.id))
        ) == 0


@pytest.mark.parametrize(
    ("selected_keys", "expected_order"),
    [
        (("C",), ("C",)),
        (("B", "C"), ("C", "B")),
        (("A", "B", "C"), ("C", "B", "A")),
    ],
)
def test_persisted_partial_selection_is_closed_and_reversed(
    selected_keys,
    expected_order,
):
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    (
        resolution_id,
        execution_id,
        decision_id,
        step_ids,
    ) = seed_completed_dependency_chain(factory)
    planner, _ = build_services(factory, CompensationHandler())

    plan = planner.prepare(
        prepare_partial_command(
            resolution_id,
            execution_id,
            decision_id,
            (step_ids[key] for key in selected_keys),
            key=f"valid-{'-'.join(selected_keys)}",
        )
    )

    assert tuple(step.source_step_key for step in plan.steps) == (
        expected_order
    )


def test_unconfirmed_dependent_does_not_block_persisted_plan():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    (
        resolution_id,
        execution_id,
        decision_id,
        step_ids,
    ) = seed_completed_dependency_chain(factory)
    with factory() as session:
        step_c = session.get(
            ResolutionStepExecution,
            step_ids["C"],
        )
        step_c.status = "failed"
        session.commit()
    planner, _ = build_services(factory, CompensationHandler())

    plan = planner.prepare(
        prepare_partial_command(
            resolution_id,
            execution_id,
            decision_id,
            (step_ids["B"],),
            key="unconfirmed-C",
        )
    )

    assert tuple(step.source_step_key for step in plan.steps) == ("B",)


def test_previously_compensated_dependent_does_not_block_new_plan():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    (
        resolution_id,
        execution_id,
        decision_id,
        step_ids,
    ) = seed_completed_dependency_chain(factory)
    handler = CompensationHandler()
    planner, executor = build_services(factory, handler)
    plan_c = planner.prepare(
        prepare_partial_command(
            resolution_id,
            execution_id,
            decision_id,
            (step_ids["C"],),
            key="prior-C-plan",
        )
    )
    executor.execute(
        ExecuteCompensationCommand(
            compensation_plan_id=plan_c.id,
            idempotency_key="prior-C-execution",
            actor=actor(),
            lock_owner="phase-6-dependency-test",
        )
    )
    with factory() as session:
        root = session.get(Resolution, resolution_id)
        root.status = ResolutionStatus.COMPLETED.value
        session.commit()

    plan_b = planner.prepare(
        prepare_partial_command(
            resolution_id,
            execution_id,
            decision_id,
            (step_ids["B"],),
            key="after-C-plan",
        )
    )

    assert tuple(step.source_step_key for step in plan_b.steps) == ("B",)


def test_valid_partial_plan_replay_remains_idempotent():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    (
        resolution_id,
        execution_id,
        decision_id,
        step_ids,
    ) = seed_completed_dependency_chain(factory)
    planner, _ = build_services(factory, CompensationHandler())
    command = prepare_partial_command(
        resolution_id,
        execution_id,
        decision_id,
        (step_ids["C"],),
        key="valid-C-replay",
    )

    first = planner.prepare(command)
    replay = planner.prepare(command)

    assert replay.id == first.id
    assert replay.plan_hash == first.plan_hash
    with factory() as session:
        assert session.scalar(
            select(func.count(ResolutionCompensationPlan.id))
        ) == 1
