from dataclasses import replace

import pytest

from app.resolution_engine.domain.compensation import (
    CompensableAction,
    CompensationEngine,
    CompensationSource,
)
from app.resolution_engine.domain.enums import (
    CompensationStatus,
    CompensationStrategy,
    ResolutionStatus,
)
from app.resolution_engine.domain.exceptions import (
    InvalidCompensationPlanError,
    LifecycleInvariantError,
)
from app.resolution_engine.domain.execution import (
    ActionCertainty,
    DomainActionResult,
)
from app.resolution_engine.domain.lifecycle import (
    CompensationEvidence,
    ExecutionEvidence,
    LifecycleAction,
    ResolutionStateMachine,
)
from tests.resolution_engine.test_execution import NOW, lifecycle


def source(*, non_compensable=()):
    actions = (
        CompensableAction(
            plan_step_id=1,
            step_execution_id=11,
            step_key="create_parent",
            original_sequence=1,
            operation_key="example.create_parent",
            compensation_operation_key="example.cancel_parent",
            owner_module="example",
            compensation_payload={"id": "parent"},
        ),
        CompensableAction(
            plan_step_id=2,
            step_execution_id=12,
            step_key="create_child",
            original_sequence=2,
            operation_key="example.create_child",
            compensation_operation_key="example.cancel_child",
            owner_module="example",
            compensation_payload={"id": "child"},
            dependency_step_ids=(1,),
        ),
    )
    return CompensationSource(
        lifecycle=lifecycle(ResolutionStatus.PARTIALLY_COMPLETED),
        execution_id=80,
        actions=actions,
        completed_step_execution_ids=(11, 12) + tuple(non_compensable),
        non_compensable_step_execution_ids=tuple(non_compensable),
    )


def test_total_plan_reverses_actions_and_dependencies_deterministically():
    plan = CompensationEngine().build_plan(
        source(),
        strategy=CompensationStrategy.TOTAL,
        reason="restore consistency",
    )

    assert [step.source_step_execution_id for step in plan.steps] == [12, 11]
    assert plan.steps[1].dependency_source_step_ids == (2,)
    assert len(plan.plan_hash) == 64


def test_partial_plan_selects_only_explicit_confirmed_actions():
    plan = CompensationEngine().build_plan(
        source(non_compensable=(13,)),
        strategy=CompensationStrategy.PARTIAL,
        reason="cancel child only",
        selected_step_execution_ids=(12,),
    )

    assert len(plan.steps) == 1
    assert plan.steps[0].operation_key == "example.cancel_child"


def test_total_plan_rejects_non_compensable_completed_effects():
    with pytest.raises(
        InvalidCompensationPlanError,
        match="point of no return",
    ):
        CompensationEngine().build_plan(
            source(non_compensable=(13,)),
            strategy=CompensationStrategy.TOTAL,
            reason="invalid total",
        )


@pytest.mark.parametrize(
    ("results", "expected"),
    [
        (
            {
                11: DomainActionResult(
                    success=True,
                    certainty=ActionCertainty.CONFIRMED,
                ),
                12: DomainActionResult(
                    success=True,
                    certainty=ActionCertainty.CONFIRMED,
                ),
            },
            CompensationStatus.COMPENSATED,
        ),
        (
            {
                11: DomainActionResult(
                    success=True,
                    certainty=ActionCertainty.CONFIRMED,
                ),
                12: DomainActionResult(
                    success=False,
                    certainty=ActionCertainty.CONFIRMED,
                    error_code="rejected",
                ),
            },
            CompensationStatus.PARTIALLY_COMPENSATED,
        ),
        (
            {
                12: DomainActionResult(
                    success=False,
                    certainty=ActionCertainty.UNCERTAIN,
                    error_code="uncertain",
                ),
            },
            CompensationStatus.BLOCKED,
        ),
    ],
)
def test_summary_is_explicit(results, expected):
    plan = CompensationEngine().build_plan(
        source(),
        strategy=CompensationStrategy.TOTAL,
        reason="restore consistency",
    )

    assert CompensationEngine.summarize(plan, results).status is expected


def test_lifecycle_requires_exact_compensation_evidence():
    machine = ResolutionStateMachine()
    current = lifecycle(ResolutionStatus.COMPLETED)
    current = replace(
        current,
        evidence=replace(
            current.evidence,
            execution=ExecutionEvidence(
                id=80,
                plan_id=40,
                revalidation_id=70,
                status="completed",
                total_steps=1,
                completed_steps=1,
                failed_steps=0,
                blocked_steps=0,
            ),
            compensation=CompensationEvidence(
                plan_id=90,
                execution_id=None,
                source_execution_id=80,
                status="prepared",
                total_steps=1,
                compensated_steps=0,
                failed_steps=0,
                blocked_steps=0,
            ),
        ),
    )

    started = machine.transition(
        current,
        LifecycleAction.START_COMPENSATION,
        occurred_at=NOW,
        actor_id="actor-1",
        actor_type="human",
    )

    assert started.new_state is ResolutionStatus.COMPENSATING

    mismatch = replace(
        current,
        evidence=replace(
            current.evidence,
            compensation=replace(
                current.evidence.compensation,
                source_execution_id=999,
            ),
        ),
    )
    with pytest.raises(
        LifecycleInvariantError,
        match="compensation_source_execution_mismatch",
    ):
        machine.transition(
            mismatch,
            LifecycleAction.START_COMPENSATION,
            occurred_at=started.event.occurred_at,
            actor_id="actor-1",
            actor_type="human",
        )
