from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.resolution_engine.application.action_runner import ActionRunner
from app.resolution_engine.application.execution import ResolutionExecutor
from app.resolution_engine.application.outbox import OutboxPublicationService
from app.resolution_engine.application.security import (
    OrganizationBoundaryPolicy,
    PermissionPolicy,
    ResolutionAuthorizationService,
    SecurityPolicyEvaluator,
)
from app.resolution_engine.contracts.execution import (
    ExecuteResolutionCommand,
    PublishOutboxCommand,
    execution_security_operation_payload,
    outbox_security_operation_payload,
)
from app.resolution_engine.domain.enums import (
    EntityRelationshipType,
    ExecutionStatus,
    ResolutionLockType,
    ResolutionStatus,
)
from app.resolution_engine.domain.exceptions import (
    ExecutionIdempotencyConflictError,
    ExecutionLockUnavailableError,
    ExecutionNotReadyError,
)
from app.resolution_engine.domain.execution import (
    ActionCertainty,
    DomainActionResult,
    ExecutionEngine,
    ExecutionEntityEffect,
)
from app.resolution_engine.domain.lifecycle import ResolutionStateMachine
from app.resolution_engine.domain.security import (
    ActorContext,
    ActorIdentity,
    ActorType,
    AuthenticationContext,
    PermissionGrant,
    SecurityDecisionUseMode,
    SecurityRequest,
    SecurityResource,
)
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_engine.infrastructure.execution import (
    SqlAlchemyExecutionStore,
)
from app.resolution_engine.infrastructure.execution_control import (
    SqlAlchemyExecutionControl,
)
from app.resolution_engine.infrastructure.outbox import (
    SqlAlchemyOutboxStore,
)
from app.resolution_engine.infrastructure.security import (
    SqlAlchemySecurityEvidenceStore,
    SqlAlchemySecurityResourceVerifier,
)
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionAnalysis,
    ResolutionAuditEvent,
    ResolutionAuthorizationDecision,
    ResolutionAuthorizationRequest,
    ResolutionContextSnapshot,
    ResolutionEntityReference,
    ResolutionExecution,
    ResolutionIdempotencyRecord,
    ResolutionLock,
    ResolutionOutboxEvent,
    ResolutionPlan,
    ResolutionPlanStep,
    ResolutionResult,
    ResolutionRevalidation,
    ResolutionSecurityDecision,
    ResolutionSimulation,
    ResolutionStepExecution,
    ResolutionStrategySelection,
)

NOW = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)
PLAN_HASH = "a" * 64
SIMULATION_HASH = "b" * 64
CONTEXT_HASH = "c" * 64


class AdvancingClock:
    def __init__(self, current=NOW):
        self.current = current

    def now(self):
        self.current += timedelta(seconds=1)
        return self.current


class Identifiers:
    def __init__(self):
        self.sequence = 0

    def new_id(self):
        self.sequence += 1
        return f"lock-token-{self.sequence}"


class Handler:
    operation_key = ComponentKey("example.create")

    def __init__(self, after_call=None):
        self.calls = []
        self.after_call = after_call

    def execute(self, request):
        self.calls.append(request)
        result = DomainActionResult(
            success=True,
            certainty=ActionCertainty.CONFIRMED,
            response_payload={"entity_id": "created-1"},
            entity_effects=(
                ExecutionEntityEffect(
                    relationship=EntityRelationshipType.CREATED,
                    entity_type="example",
                    entity_id="created-1",
                    module="example",
                ),
            ),
            domain_transaction_reference="example-tx-1",
        )
        if self.after_call is not None:
            self.after_call(request)
        return result


class Publisher:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.messages = []

    def publish(self, message):
        self.messages.append(message)
        if self.fail:
            raise RuntimeError("publisher unavailable")


def sqlite_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")

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
    return engine


def actor():
    return ActorContext(
        identity=ActorIdentity(
            actor_id="executor-1",
            actor_type=ActorType.HUMAN,
            principal="executor@example.test",
            organization_id="organization-1",
        ),
        authentication=AuthenticationContext(
            authenticated_at=NOW - timedelta(minutes=1),
            method="test",
            session_id="session-1",
            assurance_level="high",
            source="phase-5-test",
            correlation_id="correlation-1",
        ),
        permissions=(
            PermissionGrant(
                permission=ComponentKey("resolution.execute"),
            ),
            PermissionGrant(
                permission=ComponentKey("resolution.compensate"),
            ),
            PermissionGrant(
                permission=ComponentKey("resolution.outbox.publish"),
            ),
        ),
    )


def command(
    resolution_id,
    *,
    key="execution-request-1",
    security_decision_id=1,
):
    return ExecuteResolutionCommand(
        resolution_id=resolution_id,
        idempotency_key=key,
        security_decision_id=security_decision_id,
        actor=actor(),
        lock_owner="phase-5-test",
        lock_ttl=timedelta(minutes=5),
    )


def seed_ready_resolution(session):
    root = Resolution(
        public_id="resolution-phase-5",
        resolution_type="example.resolve",
        definition_version="1.0",
        status=ResolutionStatus.READY_FOR_EXECUTION.value,
        source="system",
        subject_type="example",
        subject_id="42",
        requested_by_actor_id="requester-1",
        organization_id="organization-1",
        correlation_id="correlation-1",
        title="Execute exact plan",
        requires_authorization=True,
        version=9,
    )
    session.add(root)
    session.flush()
    context = ResolutionContextSnapshot(
        resolution_id=root.id,
        snapshot_type="revalidation",
        sequence=1,
        context_version="1.0",
        context_hash=CONTEXT_HASH,
        schema_version="1.0",
        captured_at=NOW,
        facts={"case": 42},
    )
    session.add(context)
    session.flush()
    analysis = ResolutionAnalysis(
        resolution_id=root.id,
        context_snapshot_id=context.id,
        analysis_version=1,
        is_resolvable=True,
        status="resolvable",
        analyzed_at=NOW,
        analyzed_by="test",
        analysis_hash="d" * 64,
    )
    session.add(analysis)
    session.flush()
    strategy = ResolutionStrategySelection(
        resolution_id=root.id,
        analysis_id=analysis.id,
        strategy_key="example.strategy",
        strategy_version="1.0",
        selection_mode="automatic",
        selected_at=NOW,
    )
    session.add(strategy)
    session.flush()
    plan = ResolutionPlan(
        resolution_id=root.id,
        strategy_selection_id=strategy.id,
        context_snapshot_id=context.id,
        version=1,
        schema_version="1.0",
        status="authorized",
        summary="Create the exact entity",
        plan_hash=PLAN_HASH,
        created_by_actor_id="planner-1",
        is_active=True,
    )
    session.add(plan)
    session.flush()
    step = ResolutionPlanStep(
        plan_id=plan.id,
        step_key="create",
        sequence=1,
        operation_key="example.create",
        owner_module="example",
        description="Create one example entity",
        input_payload={"value": 42},
        step_hash="e" * 64,
    )
    session.add(step)
    simulation = ResolutionSimulation(
        resolution_id=root.id,
        plan_id=plan.id,
        context_snapshot_id=context.id,
        simulation_version=1,
        status="valid",
        is_valid=True,
        simulation_hash=SIMULATION_HASH,
        simulated_at=NOW,
        simulated_by="test",
    )
    session.add(simulation)
    session.flush()
    authorization = ResolutionAuthorizationRequest(
        resolution_id=root.id,
        plan_id=plan.id,
        simulation_id=simulation.id,
        policy_key="test.policy",
        policy_version="1.0",
        status="approved",
        requested_by_actor_id="requester-1",
        requester_actor_snapshot={},
        requested_at=NOW,
        required_approvals=1,
        authorization_scope={},
        plan_hash=PLAN_HASH,
        simulation_hash=SIMULATION_HASH,
    )
    session.add(authorization)
    session.flush()
    session.add(
        ResolutionAuthorizationDecision(
            authorization_request_id=authorization.id,
            decision="approved",
            approver_actor_id="approver-1",
            approver_actor_type="human",
            approver_function="approver",
            decided_at=NOW,
            permission_snapshot={},
            actor_snapshot={},
        )
    )
    revalidation = ResolutionRevalidation(
        resolution_id=root.id,
        plan_id=plan.id,
        previous_context_snapshot_id=context.id,
        current_context_snapshot_id=context.id,
        status="valid",
        result={},
        revalidated_at=NOW,
        revalidated_by="test",
        validator_version="1.0",
        revalidation_hash="f" * 64,
    )
    session.add(revalidation)
    session.flush()
    root.current_context_snapshot_id = context.id
    root.current_strategy_selection_id = strategy.id
    root.current_plan_id = plan.id
    authorize_execution(session, root.id, revalidation)
    session.commit()
    return root.id


def add_revalidation(session, resolution_id, *, marker, revalidated_at):
    root = session.get(Resolution, resolution_id)
    revalidation = ResolutionRevalidation(
        resolution_id=resolution_id,
        plan_id=root.current_plan_id,
        previous_context_snapshot_id=root.current_context_snapshot_id,
        current_context_snapshot_id=root.current_context_snapshot_id,
        status="valid",
        result={"marker": marker},
        revalidated_at=revalidated_at,
        revalidated_by="test",
        validator_version="1.0",
        revalidation_hash=marker * 64,
    )
    session.add(revalidation)
    session.flush()
    return revalidation.id


def authorize_execution(session, resolution_id, revalidation):
    root = session.get(Resolution, resolution_id)
    plan = session.get(ResolutionPlan, root.current_plan_id)
    request = SecurityRequest(
        actor=actor(),
        action=ComponentKey("resolution.execute"),
        resource=SecurityResource(
            resource_type="resolution_plan",
            resource_id=str(plan.id),
            organization_id=root.organization_id,
            resolution_id=root.id,
            resolution_public_id=root.public_id,
            plan_id=plan.id,
            plan_version=plan.version,
            plan_hash=plan.plan_hash,
            revalidation_id=revalidation.id,
            revalidation_hash=revalidation.revalidation_hash,
        ),
        required_permissions=(
            ComponentKey("resolution.execute"),
        ),
        use_mode=SecurityDecisionUseMode.SINGLE_OPERATION,
        operation_id="execution-request-1",
        operation_payload=execution_security_operation_payload(
            resolution_id=root.id,
            plan_id=plan.id,
            plan_version=plan.version,
            plan_hash=plan.plan_hash,
            revalidation_id=revalidation.id,
            revalidation_hash=revalidation.revalidation_hash,
            actor_id=actor().identity.actor_id,
            organization_id=actor().identity.organization_id,
        ),
        context={
            "resolution_status": (
                ResolutionStatus.READY_FOR_EXECUTION.value
            ),
        },
    )
    service = ResolutionAuthorizationService(
        evaluator=SecurityPolicyEvaluator(
            (PermissionPolicy(), OrganizationBoundaryPolicy())
        ),
        evidence_store=SqlAlchemySecurityEvidenceStore(session),
        resource_verifier=SqlAlchemySecurityResourceVerifier(session),
        clock=AdvancingClock(NOW),
    )
    decision = service.authorize(request)
    assert decision.outcome.value == "allowed"
    session.flush()
    return session.scalar(
        select(func.max(ResolutionSecurityDecision.id))
    )


def authorize_outbox(session, *, limit=100):
    request = SecurityRequest(
        actor=actor(),
        action=ComponentKey("resolution.outbox.publish"),
        resource=SecurityResource(
            resource_type="resolution_outbox",
            resource_id=actor().identity.organization_id,
            organization_id=actor().identity.organization_id,
        ),
        required_permissions=(
            ComponentKey("resolution.outbox.publish"),
        ),
        use_mode=SecurityDecisionUseMode.SINGLE_OPERATION,
        operation_id=f"outbox-batch-{limit}",
        operation_payload=outbox_security_operation_payload(
            organization_id=actor().identity.organization_id,
            limit=limit,
        ),
        context={"limit": limit},
    )
    decision = ResolutionAuthorizationService(
        evaluator=SecurityPolicyEvaluator(
            (PermissionPolicy(), OrganizationBoundaryPolicy())
        ),
        evidence_store=SqlAlchemySecurityEvidenceStore(session),
        resource_verifier=SqlAlchemySecurityResourceVerifier(session),
        clock=AdvancingClock(NOW + timedelta(hours=1)),
    ).authorize(request)
    assert decision.outcome.value == "allowed"
    session.flush()
    return session.scalar(
        select(func.max(ResolutionSecurityDecision.id))
    )


def build_executor(factory, handler, *, clock=None, store=None):
    return ResolutionExecutor(
        store=store or SqlAlchemyExecutionStore(factory),
        action_runner=ActionRunner((handler,)),
        engine=ExecutionEngine(),
        state_machine=ResolutionStateMachine(),
        clock=clock or AdvancingClock(),
        identifiers=Identifiers(),
    )


def test_sql_execution_persists_exact_evidence_and_replays_idempotently():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
    handler = Handler()
    service = build_executor(factory, handler)

    outcome = service.execute(command(resolution_id))
    replay = service.execute(command(resolution_id))

    assert outcome.execution_status is ExecutionStatus.COMPLETED
    assert replay.idempotent_replay is True
    assert replay.execution_id == outcome.execution_id
    assert len(handler.calls) == 1
    with factory() as session:
        root = session.get(Resolution, resolution_id)
        execution = session.scalar(
            select(ResolutionExecution).where(
                ResolutionExecution.resolution_id == resolution_id
            )
        )
        step = session.scalar(
            select(ResolutionStepExecution).where(
                ResolutionStepExecution.execution_id == execution.id
            )
        )
        result = session.scalar(
            select(ResolutionResult).where(
                ResolutionResult.execution_id == execution.id
            )
        )
        reference = session.scalar(
            select(ResolutionEntityReference).where(
                ResolutionEntityReference.execution_id == execution.id
            )
        )
        lock = session.scalar(
            select(ResolutionLock).where(
                ResolutionLock.resolution_id == resolution_id
            )
        )
        assert root.status == ResolutionStatus.COMPLETED.value
        assert execution.plan_id == root.current_plan_id
        assert execution.revalidation_id is not None
        assert execution.initial_context_hash == CONTEXT_HASH
        assert execution.status == ExecutionStatus.COMPLETED.value
        assert step.plan_id == execution.plan_id
        assert step.plan_step_id is not None
        assert step.status == "completed"
        assert result.result_hash == outcome.result_hash
        assert reference.entity_id == "created-1"
        assert lock.released_at is not None
        assert session.scalar(
            select(func.count(ResolutionIdempotencyRecord.id))
        ) == 2
        assert session.scalar(
            select(func.count(ResolutionAuditEvent.id))
        ) == 4
        step_events = tuple(
            session.scalars(
                select(ResolutionAuditEvent).where(
                    ResolutionAuditEvent.event_type.like(
                        "resolution.step_%"
                    )
                )
            )
        )
        assert {item.actor_id for item in step_events} == {"executor-1"}
        assert {item.source for item in step_events} == {"phase-5-test"}
        assert {
                item.execution_id
                for item in session.scalars(
                    select(ResolutionAuditEvent).where(
                        ResolutionAuditEvent.event_type.in_(
                            {
                                "resolution.lifecycle.start_execution",
                                "resolution.lifecycle.complete_execution",
                            }
                        )
                    )
                )
        } == {execution.id}
        assert session.scalar(
            select(func.count(ResolutionOutboxEvent.id))
        ) == 3


def test_execution_rejects_an_active_lock_before_invoking_actions():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
        session.add(
            ResolutionLock(
                resolution_id=resolution_id,
                lock_type=ResolutionLockType.EXECUTION.value,
                lock_key=f"resolution:{resolution_id}",
                owner="another-process",
                token="another-token",
                acquired_at=NOW,
                expires_at=NOW + timedelta(minutes=30),
                metadata_json={},
            )
        )
        session.commit()
    handler = Handler()

    with pytest.raises(ExecutionLockUnavailableError):
        build_executor(factory, handler).execute(command(resolution_id))

    assert handler.calls == []
    with factory() as session:
        assert session.get(Resolution, resolution_id).status == (
            ResolutionStatus.READY_FOR_EXECUTION.value
        )
        assert session.scalar(
            select(func.count(ResolutionExecution.id))
        ) == 0


def test_action_finishing_after_lock_ttl_is_blocked_without_reinvocation():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
    clock = AdvancingClock()
    handler = Handler(
        after_call=lambda _: setattr(
            clock,
            "current",
            clock.current + timedelta(minutes=10),
        )
    )

    outcome = build_executor(
        factory,
        handler,
        clock=clock,
    ).execute(command(resolution_id))

    assert outcome.execution_status is ExecutionStatus.BLOCKED
    assert len(handler.calls) == 1
    with factory() as session:
        step = session.scalar(select(ResolutionStepExecution))
        assert step.status == "blocked"
        assert step.error_code == "execution_lock_lost_after_action"
        assert session.get(Resolution, resolution_id).status == "blocked"
        assert session.scalar(
            select(func.count(ResolutionEntityReference.id))
        ) == 0


def test_replaced_lock_token_cannot_confirm_the_first_executor_result():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
    clock = AdvancingClock()

    def replace_lock(_):
        clock.current += timedelta(minutes=10)
        with factory() as session:
            with session.begin():
                SqlAlchemyExecutionControl.acquire_lock(
                    session,
                    resolution_id=resolution_id,
                    lock_key=f"resolution:{resolution_id}",
                    owner="replacement",
                    token="replacement-token",
                    acquired_at=clock.current,
                    expires_at=clock.current + timedelta(minutes=5),
                )

    handler = Handler(after_call=replace_lock)

    outcome = build_executor(
        factory,
        handler,
        clock=clock,
    ).execute(command(resolution_id))

    assert outcome.execution_status is ExecutionStatus.BLOCKED
    assert len(handler.calls) == 1
    with factory() as session:
        step = session.scalar(select(ResolutionStepExecution))
        active_lock = session.scalar(
            select(ResolutionLock).where(
                ResolutionLock.released_at.is_(None)
            )
        )
        assert step.status == "blocked"
        assert active_lock.token == "replacement-token"


def test_execution_idempotency_key_cannot_be_reused_for_another_request():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
    service = build_executor(factory, Handler())
    service.execute(command(resolution_id))

    with pytest.raises(ExecutionIdempotencyConflictError):
        SqlAlchemyExecutionStore(factory).find_outcome(
            idempotency_key="execution-request-1",
            request_hash="0" * 64,
        )


def test_execution_preserves_the_latest_exact_revalidation_identity():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
        latest_id = add_revalidation(
            session,
            resolution_id,
            marker="9",
            revalidated_at=NOW + timedelta(minutes=1),
        )
        latest = session.get(ResolutionRevalidation, latest_id)
        security_decision_id = authorize_execution(
            session,
            resolution_id,
            latest,
        )
        session.commit()
    store = SqlAlchemyExecutionStore(factory)

    candidate = store.load_candidate(resolution_id)
    outcome = build_executor(
        factory,
        Handler(),
        store=store,
    ).execute(
        command(
            resolution_id,
            security_decision_id=security_decision_id,
        )
    )

    assert candidate.revalidation_id == latest_id
    assert outcome.execution_status is ExecutionStatus.COMPLETED
    with factory() as session:
        execution = session.scalar(select(ResolutionExecution))
        started = session.scalar(
            select(ResolutionAuditEvent).where(
                ResolutionAuditEvent.event_type
                == "resolution.lifecycle.start_execution"
            )
        )
        assert execution.revalidation_id == latest_id
        assert (
            started.payload["metadata"]["revalidation_id"]
            == latest_id
        )


def test_changed_revalidation_rejects_prepared_execution_before_action():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        resolution_id = seed_ready_resolution(session)

    class ChangingStore(SqlAlchemyExecutionStore):
        def load_candidate(self, resolution_id):
            candidate = super().load_candidate(resolution_id)
            with factory() as session:
                add_revalidation(
                    session,
                    resolution_id,
                    marker="8",
                    revalidated_at=NOW + timedelta(minutes=2),
                )
                session.commit()
            return candidate

    handler = Handler()

    with pytest.raises(
        ExecutionNotReadyError,
        match="prepared revalidation is no longer current",
    ):
        build_executor(
            factory,
            handler,
            store=ChangingStore(factory),
        ).execute(command(resolution_id))

    assert handler.calls == []
    with factory() as session:
        assert session.get(Resolution, resolution_id).status == (
            ResolutionStatus.READY_FOR_EXECUTION.value
        )
        assert session.scalar(
            select(func.count(ResolutionExecution.id))
        ) == 0


def test_outbox_publication_is_explicit_and_does_not_retry_failures():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
    build_executor(factory, Handler()).execute(command(resolution_id))
    with factory() as session:
        security_decision_id = authorize_outbox(session)
        session.commit()
    publisher = Publisher(fail=True)
    publication = OutboxPublicationService(
        store=SqlAlchemyOutboxStore(factory),
        publisher=publisher,
        clock=AdvancingClock(NOW + timedelta(hours=1)),
    )

    publication_command = PublishOutboxCommand(
        security_decision_id=security_decision_id,
        actor=actor(),
        organization_id="organization-1",
        operation_id="outbox-batch-100",
    )
    first = publication.publish_available(publication_command)
    second = publication.publish_available(publication_command)

    assert first.failed == 3
    assert second == first
    assert len(publisher.messages) == 3
    with factory() as session:
        rows = tuple(session.scalars(select(ResolutionOutboxEvent)))
        assert {row.status for row in rows} == {"failed"}
        assert {row.attempts for row in rows} == {1}
        assert {row.last_error for row in rows} == {
            "publisher unavailable"
        }
        assert [
            row.failed_at.replace(tzinfo=timezone.utc)
            for row in rows
        ] == [
            NOW + timedelta(hours=1, seconds=offset)
            for offset in (2, 3, 4)
        ]


def test_outbox_publication_marks_each_event_published_once():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
    build_executor(factory, Handler()).execute(command(resolution_id))
    with factory() as session:
        security_decision_id = authorize_outbox(session)
        session.commit()
    publisher = Publisher()
    publication = OutboxPublicationService(
        store=SqlAlchemyOutboxStore(factory),
        publisher=publisher,
        clock=AdvancingClock(NOW + timedelta(hours=1)),
    )

    report = publication.publish_available(
        PublishOutboxCommand(
            security_decision_id=security_decision_id,
            actor=actor(),
            organization_id="organization-1",
            operation_id="outbox-batch-100",
        )
    )

    assert report.published == 3
    assert report.failed == 0
    assert len({message.event_key for message in publisher.messages}) == 3
    assert {len(message.payload_hash) for message in publisher.messages} == {64}
    with factory() as session:
        rows = tuple(session.scalars(select(ResolutionOutboxEvent)))
        assert {row.status for row in rows} == {"published"}
        assert {row.attempts for row in rows} == {1}
        assert all(row.published_at is not None for row in rows)


def test_outbox_decision_never_selects_a_second_batch_on_replay():
    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        resolution_id = seed_ready_resolution(session)
    build_executor(factory, Handler()).execute(command(resolution_id))
    with factory() as session:
        security_decision_id = authorize_outbox(session, limit=1)
        session.commit()
    publisher = Publisher()
    publication = OutboxPublicationService(
        store=SqlAlchemyOutboxStore(factory),
        publisher=publisher,
        clock=AdvancingClock(NOW + timedelta(hours=1)),
    )
    publication_command = PublishOutboxCommand(
        security_decision_id=security_decision_id,
        actor=actor(),
        organization_id="organization-1",
        operation_id="outbox-batch-1",
        limit=1,
    )

    first = publication.publish_available(publication_command)
    replay = publication.publish_available(publication_command)

    assert first == replay
    assert first.published == 1
    assert len(publisher.messages) == 1
    with factory() as session:
        remaining = tuple(
            session.scalars(
                select(ResolutionOutboxEvent).where(
                    ResolutionOutboxEvent.status == "pending"
                )
            )
        )
        assert len(remaining) == 2
        assert all(
            row.publication_operation_id is None for row in remaining
        )
