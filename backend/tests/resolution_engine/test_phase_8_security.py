"""Suite específica de Fase 8: seguridad integral del Motor."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.resolution_engine.application.lifecycle import (
    LifecycleActor,
    ResolutionLifecycleService,
)
from app.resolution_engine.application.security import (
    INTEGRAL_SECURITY_CONTROLS,
    OrganizationBoundaryPolicy,
    PermissionPolicy,
    SecurityPolicyEvaluator,
)
from app.resolution_engine.domain.enums import ResolutionStatus
from app.resolution_engine.domain.exceptions import (
    ExecutionNotReadyError,
    LifecycleInvariantError,
)
from app.resolution_engine.domain.lifecycle import ResolutionStateMachine
from app.resolution_engine.domain.lifecycle import LifecycleAction
from app.resolution_engine.contracts.lifecycle import (
    lifecycle_transition_operation_payload,
)
from app.resolution_engine.domain.security import (
    ActorContext,
    ActorIdentity,
    ActorType,
    AuthenticationContext,
    PermissionGrant,
    SecurityDecisionOutcome,
    SecurityDecisionUseMode,
    SecurityRequest,
    SecurityResource,
)
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionExecution,
    ResolutionSecurityDecision,
    ResolutionSecurityDecisionUse,
)
from app.resolution_engine.infrastructure.lifecycle import (
    SqlAlchemyLifecycleStore,
)
from tests.resolution_engine.test_execution_persistence import (
    Handler,
    NOW,
    actor,
    build_executor,
    command,
    seed_ready_resolution,
    sqlite_engine,
)
from tests.resolution_engine.test_lifecycle_persistence import (
    FixedClock,
    FixedIdentifiers,
    authorize as lifecycle_authorize,
    command as lifecycle_command,
    registry,
)

ROOT = Path(__file__).resolve().parents[2]


def request(
    *,
    action: str = "resolution.execute",
    permission: str = "resolution.execute",
    resource_type: str = "resolution_plan",
    context=None,
    grant_constraints=None,
    authenticated_at=NOW - timedelta(minutes=1),
):
    operation_context = (
        {"resolution_status": ResolutionStatus.READY_FOR_EXECUTION.value}
        if context is None
        else context
    )
    return SecurityRequest(
        actor=ActorContext(
            identity=ActorIdentity(
                actor_id="phase-8-actor",
                actor_type=ActorType.HUMAN,
                principal="phase8@example.test",
                organization_id="organization-1",
            ),
            authentication=AuthenticationContext(
                authenticated_at=authenticated_at,
                method="test",
                session_id="phase-8-session",
                assurance_level="high",
                source="phase-8-test",
                correlation_id="phase-8-correlation",
            ),
            permissions=(
                PermissionGrant(
                    permission=ComponentKey(permission),
                    constraints=grant_constraints or {},
                ),
            ),
        ),
        action=ComponentKey(action),
        resource=SecurityResource(
            resource_type=resource_type,
            resource_id="10",
            organization_id="organization-1",
            resolution_id=1,
            plan_id=10 if resource_type == "resolution_plan" else None,
            plan_version=1 if resource_type == "resolution_plan" else None,
            plan_hash="a" * 64 if resource_type == "resolution_plan" else None,
            revalidation_id=20
            if resource_type == "resolution_plan"
            else None,
            revalidation_hash="b" * 64
            if resource_type == "resolution_plan"
            else None,
        ),
        required_permissions=(ComponentKey(permission),),
        use_mode=SecurityDecisionUseMode.SINGLE_OPERATION,
        operation_id="phase-8-operation",
        operation_payload={"resource_id": "10"},
        context=operation_context,
    )


def evaluator():
    return SecurityPolicyEvaluator(
        (PermissionPolicy(), OrganizationBoundaryPolicy())
    )


def test_integral_catalog_covers_every_phase_1_to_7_capability_once():
    actions = tuple(str(control.action) for control in INTEGRAL_SECURITY_CONTROLS)

    assert len(actions) == len(set(actions))
    assert set(actions) == {
        "resolution.create",
        "resolution.lifecycle.transition",
        "resolution.context.build",
        "resolution.analyze",
        "resolution.strategy.select",
        "resolution.plan.build",
        "resolution.simulate",
        "resolution.plan.authorize",
        "resolution.revalidate",
        "resolution.execute",
        "resolution.compensate",
        "resolution.audit.inspect",
        "resolution.outbox.publish",
    }
    modes = {
        str(control.action): control.use_mode
        for control in INTEGRAL_SECURITY_CONTROLS
    }
    assert modes["resolution.audit.inspect"] is (
        SecurityDecisionUseMode.REUSABLE_READ
    )
    assert all(
        mode is SecurityDecisionUseMode.SINGLE_OPERATION
        for action, mode in modes.items()
        if action != "resolution.audit.inspect"
    )


@pytest.mark.parametrize(
    ("security_request", "reason"),
    (
        (
            request(action="resolution.unknown", permission="resolution.unknown"),
            "unregistered_protected_action",
        ),
        (
            request(permission="resolution.audit.inspect"),
            "required_permissions_downgrade",
        ),
        (
            request(resource_type="resolution"),
            "protected_resource_type_mismatch",
        ),
    ),
)
def test_integral_catalog_denies_unknown_downgraded_or_mistyped_requests(
    security_request,
    reason,
):
    decision = evaluator().evaluate(
        security_request,
        evaluated_at=NOW,
    )

    assert decision.outcome is SecurityDecisionOutcome.DENIED
    assert reason in decision.reason_codes
    assert len(decision.policy_results) == 1


def test_contextual_permission_cannot_be_reused_outside_its_constraints():
    constrained = request(
        context={"resolution_status": "draft"},
        grant_constraints={
            "resolution_status": ResolutionStatus.READY_FOR_EXECUTION.value,
        },
    )

    decision = evaluator().evaluate(constrained, evaluated_at=NOW)

    assert decision.outcome is SecurityDecisionOutcome.DENIED
    assert "missing_required_permissions" in decision.reason_codes


def test_baseline_policies_cannot_be_removed_by_composition():
    security_request = request()
    security_request = replace(
        security_request,
        actor=replace(security_request.actor, permissions=()),
    )

    decision = SecurityPolicyEvaluator(()).evaluate(
        security_request,
        evaluated_at=NOW,
    )

    assert decision.outcome is SecurityDecisionOutcome.DENIED
    assert "missing_required_permissions" in decision.reason_codes


def test_authentication_is_rejected_before_its_validity_window():
    decision = evaluator().evaluate(
        request(authenticated_at=NOW + timedelta(minutes=1)),
        evaluated_at=NOW,
    )

    assert decision.outcome is SecurityDecisionOutcome.DENIED
    assert "authentication_not_yet_valid" in decision.reason_codes


def test_execution_rejects_tampered_security_evidence_before_any_effect():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
        decision = session.scalar(select(ResolutionSecurityDecision))
        decision.context_snapshot = {
            **decision.context_snapshot,
            "context": {"resolution_status": "draft"},
        }
        session.commit()
    handler = Handler()

    with pytest.raises(
        ExecutionNotReadyError,
        match="exact execution authorization is invalid",
    ):
        build_executor(factory, handler).execute(command(resolution_id))

    assert handler.calls == []
    with factory() as session:
        assert session.scalar(select(ResolutionExecution)) is None


def test_idempotency_replay_does_not_disclose_another_actors_outcome():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
    handler = Handler()
    service = build_executor(factory, handler)
    service.execute(command(resolution_id))
    foreign_actor = replace(
        actor(),
        identity=replace(actor().identity, actor_id="foreign-actor"),
    )

    with pytest.raises(
        ExecutionNotReadyError,
        match="exact execution authorization is invalid",
    ):
        service.execute(
            replace(command(resolution_id), actor=foreign_actor)
        )

    assert len(handler.calls) == 1


def test_phase_8_migration_preserves_historical_rows_and_exact_links():
    source = (
        ROOT
        / "migrations"
        / "versions"
        / "e7f9a1b3c5d7_resolution_engine_phase_8_security.py"
    ).read_text()

    assert 'down_revision: str | None = "d6e8f0a2b4c5"' in source
    assert "fk_resolution_executions_security_decision" in source
    assert "fk_resolution_security_decisions_revalidation" in source
    assert "ck_resolution_security_decisions_revalidation_complete" in source
    assert 'sa.Column("security_decision_id", BIGINT_ID)' in source

    replay_source = (
        ROOT
        / "migrations"
        / "versions"
        / "f8a0b2c4d6e8_phase_8_security_decision_replay.py"
    ).read_text()
    assert 'down_revision: str | None = "fabc2cd495ef"' in replay_source
    assert "resolution_security_decision_uses" in replay_source
    assert "trg_resolution_security_decision_uses_immutable" in replay_source
    assert "publication_operation_id" in replay_source


def lifecycle_service(session):
    return ResolutionLifecycleService(
        registry=registry(),
        store=SqlAlchemyLifecycleStore(session),
        state_machine=ResolutionStateMachine(),
        clock=FixedClock(),
        identifiers=FixedIdentifiers(),
    )


def test_creation_decision_replays_only_the_same_canonical_request():
    engine = sqlite_engine()
    with Session(engine) as session:
        creation = lifecycle_command(session)
        first = lifecycle_service(session).create(creation)
        replay = lifecycle_service(session).create(creation)

        assert replay.resolution_id == first.resolution_id
        assert session.scalar(
            select(func.count(ResolutionSecurityDecisionUse.id))
        ) == 1
        assert session.scalar(
            select(func.count(Resolution.id))
        ) == 1

        with pytest.raises(
            LifecycleInvariantError,
            match="security_operation_hash_mismatch",
        ):
            lifecycle_service(session).create(
                replace(creation, subject_id="different-subject")
            )


def test_rolled_back_creation_does_not_consume_the_decision():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        creation = lifecycle_command(session)
        session.commit()

    with factory() as session:
        lifecycle_service(session).create(creation)
        session.rollback()

    with factory() as session:
        assert session.scalar(
            select(func.count(ResolutionSecurityDecisionUse.id))
        ) == 0
        created = lifecycle_service(session).create(creation)
        session.commit()
        assert created.resolution_id > 0


def test_lifecycle_decision_cannot_cross_aggregate_version():
    engine = sqlite_engine()
    with Session(engine) as session:
        creation = lifecycle_command(session)
        created = lifecycle_service(session).create(creation)
        root = session.get(Resolution, created.resolution_id)
        operation_id = "transition-version-1"
        action = LifecycleAction.CANCEL.value
        context = {
            "lifecycle_action": action,
            "expected_state": root.status,
            "expected_version": root.version,
        }
        decision_id = lifecycle_authorize(
            session,
            action="resolution.lifecycle.transition",
            resource_type="resolution",
            resource_id=str(root.id),
            resolution_id=root.id,
            context=context,
            operation_id=operation_id,
            operation_payload=lifecycle_transition_operation_payload(
                resolution_id=root.id,
                action=action,
                expected_state=root.status,
                expected_version=root.version,
                reason=None,
                metadata=None,
            ),
        )
        root.version += 1
        session.flush()

        with pytest.raises(
            LifecycleInvariantError,
            match="security_operation_hash_mismatch",
        ):
            lifecycle_service(session).transition(
                root.id,
                LifecycleAction.CANCEL,
                actor=LifecycleActor(
                    context=creation.actor,
                    security_decision_id=decision_id,
                    operation_id=operation_id,
                ),
            )


def test_concurrent_different_creations_cannot_consume_one_decision(
    tmp_path,
):
    database = tmp_path / "phase8-replay.sqlite"
    engine = create_engine(
        f"sqlite:///{database}",
        connect_args={"check_same_thread": False, "timeout": 5},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    tables = [
        table
        for name, table in Base.metadata.tables.items()
        if name == "resolutions"
        or name.startswith("resolution_")
        or name in {"users", "controlled_documents"}
    ]
    Base.metadata.create_all(engine, tables=tables)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        creation = lifecycle_command(session)
        session.commit()

    commands = (
        creation,
        replace(creation, subject_id="different-subject"),
    )

    def attempt(item):
        with factory() as session:
            try:
                result = lifecycle_service(session).create(item)
                session.commit()
                return ("created", result.resolution_id)
            except LifecycleInvariantError as exc:
                session.rollback()
                return ("denied", tuple(exc.violations))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(attempt, commands))

    assert sorted(value[0] for value in results) == [
        "created",
        "denied",
    ]
    with factory() as session:
        assert session.scalar(
            select(func.count(ResolutionSecurityDecisionUse.id))
        ) == 1


def test_critical_consumers_share_one_persisted_decision_verifier():
    infrastructure = ROOT / "app" / "resolution_engine" / "infrastructure"
    for filename in (
        "execution.py",
        "compensation.py",
        "audit.py",
        "lifecycle.py",
        "outbox.py",
    ):
        source = (infrastructure / filename).read_text()
        assert "SqlAlchemySecurityDecisionVerifier" in source
    evaluator_definitions = sum(
        path.read_text().count("class SecurityPolicyEvaluator")
        for path in (ROOT / "app" / "resolution_engine").rglob("*.py")
    )
    assert evaluator_definitions == 1
