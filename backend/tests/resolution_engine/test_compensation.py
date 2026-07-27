from dataclasses import replace

import pytest

from app.resolution_engine.domain.compensation import (
    CompensableAction,
    ConfirmedEffect,
    CompensationEngine,
    CompensationSource,
)
from app.resolution_engine.domain.enums import (
    CompensationStatus,
    CompensationStrategy,
    ResolutionStatus,
)
from app.resolution_engine.domain.exceptions import (
    CompensationDependencyClosureError,
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


def dependency_chain_source(
    *,
    active_keys=("A", "B", "C"),
):
    definitions = (
        (1, 11, "A", 1, ()),
        (2, 12, "B", 2, (1,)),
        (3, 13, "C", 3, (2,)),
    )
    active = {
        step_key
        for step_key in active_keys
    }
    actions = tuple(
        CompensableAction(
            plan_step_id=plan_step_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
            original_sequence=sequence,
            operation_key=f"example.do_{step_key.lower()}",
            compensation_operation_key=(
                f"example.undo_{step_key.lower()}"
            ),
            owner_module="example",
            compensation_payload={"step": step_key},
            dependency_step_ids=dependencies,
        )
        for (
            plan_step_id,
            step_execution_id,
            step_key,
            sequence,
            dependencies,
        ) in definitions
        if step_key in active
    )
    effects = tuple(
        ConfirmedEffect(
            plan_step_id=plan_step_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
            original_sequence=sequence,
            dependency_step_ids=dependencies,
        )
        for (
            plan_step_id,
            step_execution_id,
            step_key,
            sequence,
            dependencies,
        ) in definitions
        if step_key in active
    )
    return CompensationSource(
        lifecycle=lifecycle(ResolutionStatus.PARTIALLY_COMPLETED),
        execution_id=80,
        actions=actions,
        completed_step_execution_ids=tuple(
            effect.step_execution_id for effect in effects
        ),
        non_compensable_step_execution_ids=(),
        confirmed_effects=effects,
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


@pytest.mark.parametrize(
    ("selection", "dependents", "paths"),
    [
        (
            (11,),
            ((12, "B"), (13, "C")),
            ((11, 12), (11, 12, 13)),
        ),
        (
            (11, 12),
            ((13, "C"),),
            ((11, 12, 13),),
        ),
    ],
)
def test_partial_selection_requires_transitive_dependency_closure(
    selection,
    dependents,
    paths,
):
    with pytest.raises(
        CompensationDependencyClosureError,
        match="Compensation dependency closure violated",
    ) as captured:
        CompensationEngine().build_plan(
            dependency_chain_source(),
            strategy=CompensationStrategy.PARTIAL,
            reason="preserve active dependents",
            selected_step_execution_ids=selection,
        )

    error = captured.value
    assert error.error_code == (
        "compensation_dependency_closure_violation"
    )
    assert error.selected_step_execution_id == 11
    assert error.selected_step_key == "A"
    assert error.active_dependents == dependents
    assert error.dependency_paths == paths


@pytest.mark.parametrize(
    ("selection", "expected_order"),
    [
        ((13,), (13,)),
        ((12, 13), (13, 12)),
        ((11, 12, 13), (13, 12, 11)),
    ],
)
def test_closed_partial_selection_is_valid_and_uses_inverse_order(
    selection,
    expected_order,
):
    plan = CompensationEngine().build_plan(
        dependency_chain_source(),
        strategy=CompensationStrategy.PARTIAL,
        reason="closed partial compensation",
        selected_step_execution_ids=selection,
    )

    assert tuple(
        step.source_step_execution_id for step in plan.steps
    ) == expected_order


def test_dependent_without_confirmed_effect_does_not_block():
    plan = CompensationEngine().build_plan(
        dependency_chain_source(active_keys=("A", "B")),
        strategy=CompensationStrategy.PARTIAL,
        reason="C produced no confirmed effect",
        selected_step_execution_ids=(12,),
    )

    assert tuple(
        step.source_step_execution_id for step in plan.steps
    ) == (12,)


def test_previously_compensated_dependent_is_not_active():
    plan = CompensationEngine().build_plan(
        dependency_chain_source(active_keys=("A",)),
        strategy=CompensationStrategy.PARTIAL,
        reason="B and C were already compensated",
        selected_step_execution_ids=(11,),
    )

    assert tuple(
        step.source_step_execution_id for step in plan.steps
    ) == (11,)


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
