from dataclasses import replace
from datetime import datetime, timezone

import pytest

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
from app.resolution_engine.domain.lifecycle import (
    AnalysisEvidence,
    AuthorizationEvidence,
    ContextEvidence,
    LifecycleAction,
    LifecycleEvidence,
    PlanEvidence,
    PolicyAuthorizationEvidence,
    ResolutionLifecycle,
    ResolutionStateMachine,
    RevalidationEvidence,
    SimulationEvidence,
    StrategyEvidence,
)

NOW = datetime(2026, 7, 27, 12, tzinfo=timezone.utc)
HASH_A = "a" * 64
HASH_B = "b" * 64


def evidence(
    *,
    authorization_status=AuthorizationRequestStatus.PENDING,
    revalidation_status=RevalidationStatus.VALID,
) -> LifecycleEvidence:
    return LifecycleEvidence(
        context=ContextEvidence(id=10, context_hash="c" * 64),
        analysis=AnalysisEvidence(
            id=20,
            context_id=10,
            status=AnalysisStatus.RESOLVABLE,
        ),
        strategy=StrategyEvidence(id=30, analysis_id=20, is_active=True),
        plan=PlanEvidence(
            id=40,
            version=3,
            plan_hash=HASH_A,
            context_id=10,
            strategy_id=30,
            status=PlanStatus.READY,
            is_active=True,
        ),
        simulation=SimulationEvidence(
            id=50,
            simulation_hash=HASH_B,
            plan_id=40,
            context_id=10,
            status=SimulationStatus.VALID,
        ),
        authorization=AuthorizationEvidence(
            request_id=60,
            plan_id=40,
            plan_hash=HASH_A,
            simulation_id=50,
            simulation_hash=HASH_B,
            status=authorization_status,
            required_approvals=1,
            approved_decision_count=(
                1
                if authorization_status is AuthorizationRequestStatus.APPROVED
                else 0
            ),
            has_blocking_decision=False,
            expires_at=None,
        ),
        revalidation=RevalidationEvidence(
            id=70,
            plan_id=40,
            previous_context_id=10,
            current_context_id=10,
            status=revalidation_status,
        ),
    )


def case(
    status: ResolutionStatus,
    *,
    current_evidence: LifecycleEvidence | None = None,
    requires_authorization: bool = True,
    version: int = 1,
) -> ResolutionLifecycle:
    return ResolutionLifecycle(
        resolution_id=1,
        public_id="resolution-1",
        resolution_type="example.resolve",
        definition_version="1.0",
        status=status,
        version=version,
        requires_authorization=requires_authorization,
        evidence=current_evidence or evidence(),
    )


def transition(
    machine: ResolutionStateMachine,
    current: ResolutionLifecycle,
    action: LifecycleAction,
):
    result = machine.transition(
        current,
        action,
        occurred_at=NOW,
        actor_id="actor-1",
        actor_type="human",
    )
    return replace(
        current,
        status=result.new_state,
        version=result.new_version,
    ), result


def test_main_lifecycle_reaches_ready_for_execution_deterministically():
    machine = ResolutionStateMachine()
    current = case(ResolutionStatus.DRAFT)
    steps = [
        (LifecycleAction.RECORD_CONTEXT, ResolutionStatus.CONTEXT_READY),
        (LifecycleAction.RECORD_ANALYSIS, ResolutionStatus.ANALYZED),
        (LifecycleAction.RECORD_PLAN, ResolutionStatus.PLAN_READY),
        (LifecycleAction.RECORD_SIMULATION, ResolutionStatus.SIMULATED),
        (
            LifecycleAction.REQUEST_AUTHORIZATION,
            ResolutionStatus.PENDING_AUTHORIZATION,
        ),
    ]
    for action, expected in steps:
        current, result = transition(machine, current, action)
        assert current.status is expected
        assert result.event.previous_state is result.previous_state
        assert len(result.event.payload_hash) == 64

    current = replace(
        current,
        evidence=evidence(
            authorization_status=AuthorizationRequestStatus.APPROVED
        ),
    )
    for action, expected in [
        (LifecycleAction.CONFIRM_AUTHORIZATION, ResolutionStatus.AUTHORIZED),
        (LifecycleAction.BEGIN_REVALIDATION, ResolutionStatus.REVALIDATING),
        (
            LifecycleAction.ACCEPT_REVALIDATION,
            ResolutionStatus.READY_FOR_EXECUTION,
        ),
    ]:
        current, _ = transition(machine, current, action)
        assert current.status is expected

    assert current.version == 9


def test_policy_authorization_can_replace_human_request_when_not_required():
    base = evidence()
    policy = PolicyAuthorizationEvidence(
        decision_id=80,
        plan_id=40,
        plan_version=3,
        plan_hash=HASH_A,
        simulation_id=50,
        simulation_hash=HASH_B,
        outcome="allowed",
    )
    current = case(
        ResolutionStatus.SIMULATED,
        current_evidence=replace(
            base,
            authorization=None,
            policy_authorization=policy,
        ),
        requires_authorization=False,
    )

    next_case, _ = transition(
        ResolutionStateMachine(),
        current,
        LifecycleAction.CONFIRM_AUTHORIZATION,
    )

    assert next_case.status is ResolutionStatus.AUTHORIZED


@pytest.mark.parametrize(
    ("mutation", "action", "violation"),
    [
        (
            lambda value: replace(
                value,
                simulation=replace(
                    value.simulation,
                    plan_id=999,
                ),
            ),
            LifecycleAction.REQUEST_AUTHORIZATION,
            "simulation_plan_mismatch",
        ),
        (
            lambda value: replace(
                value,
                authorization=replace(
                    value.authorization,
                    plan_hash="x" * 64,
                    status=AuthorizationRequestStatus.APPROVED,
                ),
            ),
            LifecycleAction.CONFIRM_AUTHORIZATION,
            "authorization_plan_mismatch",
        ),
        (
            lambda value: replace(
                value,
                revalidation=replace(
                    value.revalidation,
                    current_context_id=999,
                ),
                authorization=replace(
                    value.authorization,
                    status=AuthorizationRequestStatus.APPROVED,
                ),
            ),
            LifecycleAction.ACCEPT_REVALIDATION,
            "revalidation_current_context_mismatch",
        ),
    ],
)
def test_exact_evidence_invariants_reject_mismatches(
    mutation,
    action,
    violation,
):
    state = {
        LifecycleAction.REQUEST_AUTHORIZATION: ResolutionStatus.SIMULATED,
        LifecycleAction.CONFIRM_AUTHORIZATION:
            ResolutionStatus.PENDING_AUTHORIZATION,
        LifecycleAction.ACCEPT_REVALIDATION: ResolutionStatus.REVALIDATING,
    }[action]
    with pytest.raises(LifecycleInvariantError) as caught:
        transition(
            ResolutionStateMachine(),
            case(state, current_evidence=mutation(evidence())),
            action,
        )

    assert violation in caught.value.violations


@pytest.mark.parametrize(
    ("authorization_change", "violation"),
    [
        (
            {"required_approvals": 2, "approved_decision_count": 1},
            "authorization_approvals_incomplete",
        ),
        (
            {"has_blocking_decision": True},
            "authorization_has_blocking_decision",
        ),
        (
            {"expires_at": NOW},
            "authorization_expired",
        ),
    ],
)
def test_authorization_requires_current_append_only_decision_evidence(
    authorization_change,
    violation,
):
    current_evidence = evidence(
        authorization_status=AuthorizationRequestStatus.APPROVED
    )
    current_evidence = replace(
        current_evidence,
        authorization=replace(
            current_evidence.authorization,
            **authorization_change,
        ),
    )

    with pytest.raises(LifecycleInvariantError) as caught:
        transition(
            ResolutionStateMachine(),
            case(
                ResolutionStatus.PENDING_AUTHORIZATION,
                current_evidence=current_evidence,
            ),
            LifecycleAction.CONFIRM_AUTHORIZATION,
        )

    assert violation in caught.value.violations


@pytest.mark.parametrize(
    "terminal",
    [
        ResolutionStatus.CANCELLED,
        ResolutionStatus.REJECTED,
        ResolutionStatus.SUPERSEDED,
        ResolutionStatus.NO_ACTION_REQUIRED,
        ResolutionStatus.COMPLETED,
    ],
)
def test_terminal_states_have_no_outgoing_phase_4_transitions(terminal):
    with pytest.raises(InvalidLifecycleTransitionError):
        transition(
            ResolutionStateMachine(),
            case(terminal),
            LifecycleAction.RECORD_CONTEXT,
        )


def test_execution_requires_an_authorized_plan():
    with pytest.raises(LifecycleInvariantError) as caught:
        transition(
            ResolutionStateMachine(),
            case(ResolutionStatus.READY_FOR_EXECUTION),
            LifecycleAction.START_EXECUTION,
        )

    assert "plan_not_authorized" in caught.value.violations


def test_governance_transitions_require_a_reason():
    with pytest.raises(LifecycleInvariantError) as caught:
        transition(
            ResolutionStateMachine(),
            case(ResolutionStatus.ANALYZED),
            LifecycleAction.REJECT,
        )

    assert "reason_required" in caught.value.violations


@pytest.mark.parametrize(
    ("state", "action", "target", "metadata"),
    [
        (
            ResolutionStatus.CONTEXT_READY,
            LifecycleAction.BLOCK,
            ResolutionStatus.BLOCKED,
            {},
        ),
        (
            ResolutionStatus.ANALYZED,
            LifecycleAction.REJECT,
            ResolutionStatus.REJECTED,
            {},
        ),
        (
            ResolutionStatus.AUTHORIZED,
            LifecycleAction.CANCEL,
            ResolutionStatus.CANCELLED,
            {},
        ),
        (
            ResolutionStatus.READY_FOR_EXECUTION,
            LifecycleAction.SUPERSEDE,
            ResolutionStatus.SUPERSEDED,
            {"superseded_by_resolution_id": 2},
        ),
    ],
)
def test_governance_transitions_are_explicit(
    state,
    action,
    target,
    metadata,
):
    result = ResolutionStateMachine().transition(
        case(state),
        action,
        occurred_at=NOW,
        actor_id="actor-1",
        actor_type="human",
        reason="explicit reason",
        metadata=metadata,
    )

    assert result.new_state is target


def test_pending_authorization_rejection_requires_persisted_rejection():
    current_evidence = evidence(
        authorization_status=AuthorizationRequestStatus.REJECTED
    )

    result = ResolutionStateMachine().transition(
        case(
            ResolutionStatus.PENDING_AUTHORIZATION,
            current_evidence=current_evidence,
        ),
        LifecycleAction.REJECT,
        occurred_at=NOW,
        actor_id="actor-1",
        actor_type="human",
        reason="authorization rejected",
    )

    assert result.new_state is ResolutionStatus.REJECTED


def test_revalidation_can_require_a_new_plan():
    current = case(
        ResolutionStatus.REVALIDATING,
        current_evidence=evidence(
            authorization_status=AuthorizationRequestStatus.APPROVED,
            revalidation_status=RevalidationStatus.REQUIRES_NEW_PLAN,
        ),
    )

    next_case, _ = transition(
        ResolutionStateMachine(),
        current,
        LifecycleAction.REQUIRE_NEW_PLAN,
    )

    assert next_case.status is ResolutionStatus.PLAN_READY


def test_no_action_requires_specific_persisted_analysis_evidence():
    current_evidence = replace(
        evidence(),
        analysis=replace(
            evidence().analysis,
            status=AnalysisStatus.ALREADY_RESOLVED,
        ),
    )

    next_case, _ = transition(
        ResolutionStateMachine(),
        case(
            ResolutionStatus.ANALYZED,
            current_evidence=current_evidence,
        ),
        LifecycleAction.MARK_NO_ACTION,
    )

    assert next_case.status is ResolutionStatus.NO_ACTION_REQUIRED


def test_every_undeclared_state_action_pair_is_rejected():
    valid_pairs = set()
    machine = ResolutionStateMachine()
    for state in ResolutionStatus:
        for action in LifecycleAction:
            current = case(state)
            if action is LifecycleAction.MARK_NO_ACTION:
                current = replace(
                    current,
                    evidence=replace(
                        current.evidence,
                        analysis=replace(
                            current.evidence.analysis,
                            status=AnalysisStatus.ALREADY_RESOLVED,
                        ),
                        revalidation=replace(
                            current.evidence.revalidation,
                            status=RevalidationStatus.NO_LONGER_RESOLVABLE,
                        ),
                    ),
                )
            try:
                machine.transition(
                    current,
                    action,
                    occurred_at=NOW,
                    actor_id="actor-1",
                    actor_type="human",
                    reason="reason",
                    metadata={"superseded_by_resolution_id": 2},
                )
            except LifecycleInvariantError:
                valid_pairs.add((state, action))
            except InvalidLifecycleTransitionError:
                continue
            else:
                valid_pairs.add((state, action))

    expected = {
        (ResolutionStatus.DRAFT, LifecycleAction.RECORD_CONTEXT),
        (ResolutionStatus.CONTEXT_READY, LifecycleAction.RECORD_ANALYSIS),
        (ResolutionStatus.ANALYZED, LifecycleAction.RECORD_PLAN),
        (ResolutionStatus.ANALYZED, LifecycleAction.MARK_NO_ACTION),
        (ResolutionStatus.PLAN_READY, LifecycleAction.RECORD_SIMULATION),
        (
            ResolutionStatus.SIMULATED,
            LifecycleAction.REQUEST_AUTHORIZATION,
        ),
        (
            ResolutionStatus.SIMULATED,
            LifecycleAction.CONFIRM_AUTHORIZATION,
        ),
        (
            ResolutionStatus.PENDING_AUTHORIZATION,
            LifecycleAction.CONFIRM_AUTHORIZATION,
        ),
        (
            ResolutionStatus.AUTHORIZED,
            LifecycleAction.BEGIN_REVALIDATION,
        ),
        (
            ResolutionStatus.REVALIDATING,
            LifecycleAction.ACCEPT_REVALIDATION,
        ),
        (
            ResolutionStatus.REVALIDATING,
            LifecycleAction.REQUIRE_NEW_PLAN,
        ),
        (
            ResolutionStatus.REVALIDATING,
            LifecycleAction.MARK_NO_ACTION,
        ),
        (
            ResolutionStatus.READY_FOR_EXECUTION,
            LifecycleAction.START_EXECUTION,
        ),
        (
            ResolutionStatus.EXECUTING,
            LifecycleAction.COMPLETE_EXECUTION,
        ),
        (
            ResolutionStatus.EXECUTING,
            LifecycleAction.COMPLETE_PARTIAL_EXECUTION,
        ),
        (
            ResolutionStatus.EXECUTING,
            LifecycleAction.FAIL_EXECUTION,
        ),
        (
            ResolutionStatus.EXECUTING,
            LifecycleAction.BLOCK_EXECUTION,
        ),
        (
            ResolutionStatus.COMPLETED,
            LifecycleAction.START_COMPENSATION,
        ),
        (
            ResolutionStatus.PARTIALLY_COMPLETED,
            LifecycleAction.START_COMPENSATION,
        ),
        (
            ResolutionStatus.FAILED,
            LifecycleAction.START_COMPENSATION,
        ),
        (
            ResolutionStatus.COMPENSATING,
            LifecycleAction.COMPLETE_COMPENSATION,
        ),
        (
            ResolutionStatus.COMPENSATING,
            LifecycleAction.COMPLETE_PARTIAL_COMPENSATION,
        ),
        (
            ResolutionStatus.COMPENSATING,
            LifecycleAction.FAIL_COMPENSATION,
        ),
    }
    expected.update(
        (state, LifecycleAction.CANCEL)
        for state in {
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
    expected.update(
        (state, LifecycleAction.BLOCK)
        for state in {
            ResolutionStatus.CONTEXT_READY,
            ResolutionStatus.ANALYZED,
            ResolutionStatus.PLAN_READY,
            ResolutionStatus.SIMULATED,
            ResolutionStatus.PENDING_AUTHORIZATION,
            ResolutionStatus.AUTHORIZED,
            ResolutionStatus.REVALIDATING,
        }
    )
    expected.update(
        (state, LifecycleAction.REJECT)
        for state in {
            ResolutionStatus.ANALYZED,
            ResolutionStatus.SIMULATED,
            ResolutionStatus.PENDING_AUTHORIZATION,
        }
    )
    expected.update(
        (state, LifecycleAction.SUPERSEDE)
        for state in {
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

    assert valid_pairs == expected
