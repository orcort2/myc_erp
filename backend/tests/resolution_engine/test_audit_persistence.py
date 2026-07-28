from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Event

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.db import Base
from app.resolution_engine.application.audit import AuditQueryService
from app.resolution_engine.application.security import (
    OrganizationBoundaryPolicy,
    PermissionPolicy,
    ResolutionAuthorizationService,
    SecurityPolicyEvaluator,
)
from app.resolution_engine.application.lifecycle import (
    LifecycleActor,
    ResolutionLifecycleService,
)
from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.contracts.lifecycle import (
    CreateResolutionCommand,
    ResolutionProblemInput,
    lifecycle_transition_operation_payload,
)
from app.resolution_engine.contracts.audit import (
    AuditQuery,
    audit_security_operation_payload,
)
from app.resolution_engine.domain.definitions import (
    ComponentReference,
    ResolutionDefinition,
)
from app.resolution_engine.domain.enums import (
    ComponentKind,
    ContextSnapshotType,
    ResolutionSource,
)
from app.resolution_engine.domain.audit import EvidenceIntegrity
from app.resolution_engine.domain.exceptions import AuditAccessDeniedError
from app.resolution_engine.domain.lifecycle import (
    LifecycleAction,
    ResolutionStateMachine,
)
from app.resolution_engine.domain.security import (
    ActorContext,
    ActorIdentity,
    ActorType,
    AuthenticationContext,
    PermissionGrant,
    SecurityDecision,
    SecurityDecisionOutcome,
    SecurityDecisionUseMode,
    SecurityRequest,
    SecurityResource,
)
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
    ResolutionType,
)
from app.resolution_engine.infrastructure.audit import (
    SqlAlchemyAuditAccessVerifier,
    SqlAlchemyAuditRecordStore,
)
from app.resolution_engine.infrastructure.lifecycle import (
    SqlAlchemyLifecycleStore,
)
from app.resolution_engine.infrastructure.security import (
    SqlAlchemySecurityEvidenceStore,
    SqlAlchemySecurityResourceVerifier,
)
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionAuditEvent,
    ResolutionContextSnapshot,
    ResolutionSecurityDecision,
    ResolutionSecurityDecisionUse,
)

NOW = datetime(2026, 7, 27, 18, tzinfo=timezone.utc)


class FixedClock:
    def now(self):
        return NOW


class FixedIdentifiers:
    def new_id(self):
        return "resolution-audit-1"


class ContextComponent:
    component_key = ComponentKey("audit.context")
    component_version = DefinitionVersion("1.0")


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


def concurrent_sqlite_engine(tmp_path):
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'audit-snapshot.db'}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL")

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
            actor_id="auditor-1",
            actor_type=ActorType.HUMAN,
            principal="auditor@example.test",
            organization_id="organization-1",
        ),
        authentication=AuthenticationContext(
            authenticated_at=NOW - timedelta(minutes=1),
            method="test",
            session_id="session-audit",
            assurance_level="high",
            source="test",
            correlation_id="correlation-audit",
        ),
        permissions=(
            PermissionGrant(
                permission=ComponentKey("resolution.create"),
            ),
            PermissionGrant(
                permission=ComponentKey(
                    "resolution.lifecycle.transition"
                ),
            ),
            PermissionGrant(
                permission=ComponentKey("resolution.audit.inspect"),
            ),
        ),
    )


def registry():
    value = ResolutionRegistry()
    value.register(
        ResolutionDefinition(
            resolution_type=ResolutionType("audit.resolve"),
            version=DefinitionVersion("1.0"),
            components={
                ComponentKind.CONTEXT_PROVIDER: ComponentReference(
                    kind=ComponentKind.CONTEXT_PROVIDER,
                    key=ContextComponent.component_key,
                    version=ContextComponent.component_version,
                    implementation=ContextComponent,
                )
            },
        )
    )
    return value


def lifecycle_service(session):
    return ResolutionLifecycleService(
        registry=registry(),
        store=SqlAlchemyLifecycleStore(session),
        state_machine=ResolutionStateMachine(),
        clock=FixedClock(),
        identifiers=FixedIdentifiers(),
    )


def create_resolution(session):
    service = lifecycle_service(session)
    base = CreateResolutionCommand(
        resolution_type="audit.resolve",
        source=ResolutionSource.SYSTEM,
        subject_type="example",
        subject_id="42",
        title="Auditable",
        actor=actor(),
        security_decision_id=1,
        request_key="create-audit-resolution",
        problem=ResolutionProblemInput(
            problem_code="audit.problem",
            summary="Evidence required",
            detected_by="test",
            detected_at=NOW,
        ),
    )
    definition = registry().resolve("audit.resolve", None)
    security_decision_id = authorize_action(
        session,
        action="resolution.create",
        resource_type="resolution_definition",
        resource_id="audit.resolve@1.0",
        context={"source": ResolutionSource.SYSTEM.value},
        operation_id=base.request_key,
        operation_payload=base.security_operation_payload(definition),
    )
    created = service.create(
        replace(
            base,
            security_decision_id=security_decision_id,
        )
    )
    session.commit()
    return created.resolution_id


def create_auditable_resolution(session):
    resolution_id = create_resolution(session)
    service = lifecycle_service(session)
    context = ResolutionContextSnapshot(
        resolution_id=resolution_id,
        snapshot_type=ContextSnapshotType.INITIAL.value,
        sequence=1,
        context_version="1.0",
        context_hash="c" * 64,
        schema_version="1.0",
        captured_at=NOW,
        captured_by_actor_id="auditor-1",
        facts={"case": 42},
    )
    session.add(context)
    session.flush()
    root = session.get(Resolution, resolution_id)
    root.current_context_snapshot_id = context.id
    session.flush()
    service.transition(
        resolution_id,
        LifecycleAction.RECORD_CONTEXT,
        actor=LifecycleActor(
            context=actor(),
            security_decision_id=authorize_action(
                session,
                action="resolution.lifecycle.transition",
                resource_type="resolution",
                resource_id=str(resolution_id),
                resolution_id=resolution_id,
                context={
                    "lifecycle_action": (
                        LifecycleAction.RECORD_CONTEXT.value
                    ),
                    "expected_state": root.status,
                    "expected_version": root.version,
                },
                operation_id="audit-record-context",
                operation_payload=lifecycle_transition_operation_payload(
                    resolution_id=resolution_id,
                    action=LifecycleAction.RECORD_CONTEXT.value,
                    expected_state=root.status,
                    expected_version=root.version,
                    reason=None,
                    metadata=None,
                ),
            ),
            operation_id="audit-record-context",
        ),
    )
    session.commit()
    return resolution_id


def authorize_action(
    session,
    *,
    action,
    resource_type,
    resource_id,
    context,
    resolution_id=None,
    operation_id,
    operation_payload,
    use_mode=SecurityDecisionUseMode.SINGLE_OPERATION,
):
    request = SecurityRequest(
        actor=actor(),
        action=ComponentKey(action),
        resource=SecurityResource(
            resource_type=resource_type,
            resource_id=resource_id,
            organization_id="organization-1",
            resolution_id=resolution_id,
        ),
        required_permissions=(ComponentKey(action),),
        use_mode=use_mode,
        operation_id=operation_id,
        operation_payload=operation_payload,
        context=context,
    )
    decision = ResolutionAuthorizationService(
        evaluator=SecurityPolicyEvaluator(
            (PermissionPolicy(), OrganizationBoundaryPolicy())
        ),
        evidence_store=SqlAlchemySecurityEvidenceStore(session),
        resource_verifier=SqlAlchemySecurityResourceVerifier(session),
        clock=FixedClock(),
    ).authorize(request)
    assert decision.outcome is SecurityDecisionOutcome.ALLOWED
    session.flush()
    return session.scalar(
        select(ResolutionSecurityDecision.id)
        .where(
            ResolutionSecurityDecision.action == action,
            ResolutionSecurityDecision.resource_id == resource_id,
        )
        .order_by(ResolutionSecurityDecision.id.desc())
    )


def authorize_audit_query(session, resolution_id):
    audit_context = {"purpose": "phase-7-test"}
    operation_id = f"audit-query:{resolution_id}:phase-7"
    request = SecurityRequest(
        actor=actor(),
        action=ComponentKey("resolution.audit.inspect"),
        resource=SecurityResource(
            resource_type="resolution",
            resource_id=str(resolution_id),
            organization_id="organization-1",
            resolution_id=resolution_id,
        ),
        required_permissions=(
            ComponentKey("resolution.audit.inspect"),
        ),
        use_mode=SecurityDecisionUseMode.REUSABLE_READ,
        operation_id=operation_id,
        operation_payload=audit_security_operation_payload(
            resolution_id=resolution_id,
            context=audit_context,
        ),
        occurred_functions={"requester": ("auditor-1",)},
        context=audit_context,
    )
    decision = ResolutionAuthorizationService(
        evaluator=SecurityPolicyEvaluator(
            (PermissionPolicy(), OrganizationBoundaryPolicy())
        ),
        evidence_store=SqlAlchemySecurityEvidenceStore(session),
        resource_verifier=SqlAlchemySecurityResourceVerifier(session),
        clock=FixedClock(),
    ).authorize(request)
    assert decision.outcome is SecurityDecisionOutcome.ALLOWED
    session.flush()
    persisted = session.scalar(
        select(ResolutionSecurityDecision)
        .where(
            ResolutionSecurityDecision.resolution_id == resolution_id,
            ResolutionSecurityDecision.action
            == "resolution.audit.inspect",
        )
        .order_by(ResolutionSecurityDecision.id.desc())
    )
    return (
        AuditQuery(
            resolution_id=resolution_id,
            security_decision_id=persisted.id,
            actor=actor(),
            requested_at=NOW,
            operation_id=operation_id,
            context=audit_context,
        ),
        persisted,
    )


def test_sql_audit_reconstructs_and_verifies_persisted_history():
    engine = sqlite_engine()
    with Session(engine) as session:
        resolution_id = create_auditable_resolution(session)
        query, _ = authorize_audit_query(session, resolution_id)
        session.commit()
        service = AuditQueryService(
            store=SqlAlchemyAuditRecordStore(session),
            access_verifier=SqlAlchemyAuditAccessVerifier(session),
        )

        first = service.inspect(query)
        second = service.inspect(query)

        assert first.is_valid
        assert first.record_hash == second.record_hash
        assert [entry.kind for entry in first.timeline].count(
            "audit_event"
        ) == 2
        assert {node.kind for node in first.nodes}.issuperset(
            {"resolution", "problem", "context_snapshot", "audit_event"}
        )
        assert len(service.evidence(
            query,
            kinds=("audit_event",),
        )) == 2
        assert session.scalar(
            select(func.count(ResolutionSecurityDecisionUse.id))
        ) == 2
        with pytest.raises(AuditAccessDeniedError):
            service.inspect(
                replace(query, operation_id="another-audit-scope")
            )


def test_sql_audit_uses_one_snapshot_during_concurrent_transition(tmp_path):
    engine = concurrent_sqlite_engine(tmp_path)
    with Session(engine) as session:
        resolution_id = create_resolution(session)
        query, _ = authorize_audit_query(session, resolution_id)
        session.commit()
        prior = AuditQueryService(
            store=SqlAlchemyAuditRecordStore(session),
            access_verifier=SqlAlchemyAuditAccessVerifier(session),
        ).inspect(query)

    root_loaded = Event()
    writer_committed = Event()

    def pause_snapshot_after_root(
        _connection,
        _cursor,
        statement,
        _parameters,
        context,
        _executemany,
    ):
        if (
            context.execution_options.get("resolution_audit_snapshot")
            and "from resolutions" in statement.lower()
            and not root_loaded.is_set()
        ):
            root_loaded.set()
            assert writer_committed.wait(timeout=5)

    event.listen(engine, "after_cursor_execute", pause_snapshot_after_root)

    def reconstruct():
        with Session(engine) as session:
            return AuditQueryService(
                store=SqlAlchemyAuditRecordStore(session),
                access_verifier=SqlAlchemyAuditAccessVerifier(session),
            ).inspect(query)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(reconstruct)
            assert root_loaded.wait(timeout=5)
            with Session(engine) as writer:
                context = ResolutionContextSnapshot(
                    resolution_id=resolution_id,
                    snapshot_type=ContextSnapshotType.INITIAL.value,
                    sequence=1,
                    context_version="1.0",
                    context_hash="d" * 64,
                    schema_version="1.0",
                    captured_at=NOW,
                    captured_by_actor_id="auditor-1",
                    facts={"concurrent": True},
                )
                writer.add(context)
                writer.flush()
                root = writer.get(Resolution, resolution_id)
                root.current_context_snapshot_id = context.id
                writer.flush()
                lifecycle_service(writer).transition(
                    resolution_id,
                    LifecycleAction.RECORD_CONTEXT,
                    actor=LifecycleActor(
                        context=actor(),
                        security_decision_id=authorize_action(
                            writer,
                            action=(
                                "resolution.lifecycle.transition"
                            ),
                            resource_type="resolution",
                            resource_id=str(resolution_id),
                            resolution_id=resolution_id,
                            context={
                                "lifecycle_action": (
                                    LifecycleAction.RECORD_CONTEXT.value
                                ),
                                "expected_state": root.status,
                                "expected_version": root.version,
                            },
                            operation_id="concurrent-record-context",
                            operation_payload=(
                                lifecycle_transition_operation_payload(
                                    resolution_id=resolution_id,
                                    action=(
                                        LifecycleAction
                                        .RECORD_CONTEXT.value
                                    ),
                                    expected_state=root.status,
                                    expected_version=root.version,
                                    reason=None,
                                    metadata=None,
                                )
                            ),
                        ),
                        operation_id="concurrent-record-context",
                    ),
                )
                writer.commit()
            writer_committed.set()
            concurrent = future.result(timeout=5)
    finally:
        writer_committed.set()
        event.remove(
            engine,
            "after_cursor_execute",
            pause_snapshot_after_root,
        )

    with Session(engine) as session:
        posterior = AuditQueryService(
            store=SqlAlchemyAuditRecordStore(session),
            access_verifier=SqlAlchemyAuditAccessVerifier(session),
        ).inspect(query)

    assert concurrent.is_valid
    assert concurrent.status == "draft"
    assert concurrent.version == 1
    assert concurrent.record_hash == prior.record_hash
    assert concurrent.issues == prior.issues == ()
    assert concurrent.verifications == prior.verifications
    assert concurrent.timeline == prior.timeline
    assert {
        node.kind for node in concurrent.nodes
    }.isdisjoint({"context_snapshot"})
    assert posterior.is_valid
    assert posterior.status == "context_ready"
    assert posterior.version == 2
    assert posterior.record_hash != prior.record_hash
    assert "context_snapshot" in {node.kind for node in posterior.nodes}
    assert [entry.kind for entry in posterior.timeline].count(
        "audit_event"
    ) == 2


def test_sql_audit_detects_tampered_persisted_payload():
    engine = sqlite_engine()
    with Session(engine) as session:
        resolution_id = create_auditable_resolution(session)
        query, _ = authorize_audit_query(session, resolution_id)
        event_row = session.scalar(
            select(ResolutionAuditEvent)
            .where(ResolutionAuditEvent.resolution_id == resolution_id)
            .order_by(ResolutionAuditEvent.sequence)
        )
        event_row.payload = {"tampered": True}
        session.commit()

        report = AuditQueryService(
            store=SqlAlchemyAuditRecordStore(session),
            access_verifier=SqlAlchemyAuditAccessVerifier(session),
        ).inspect(query)

        assert not report.is_valid
        assert "evidence_hash_mismatch" in {
            issue.code for issue in report.issues
        }


def test_new_security_evidence_is_exactly_reproducible_by_audit():
    engine = sqlite_engine()
    with Session(engine) as session:
        resolution_id = create_auditable_resolution(session)
        query, persisted = authorize_audit_query(session, resolution_id)
        session.commit()

        report = AuditQueryService(
            store=SqlAlchemyAuditRecordStore(session),
            access_verifier=SqlAlchemyAuditAccessVerifier(session),
        ).inspect(query)
        verification = next(
            item
            for item in report.verifications
            if item.node_key == f"security_decision:{persisted.id}"
        )

        assert report.is_valid
        assert verification.integrity.value == "verified"
        assert verification.calculated_hash == persisted.evidence_hash


def test_sql_audit_access_is_bound_to_exact_actor_and_correlation():
    engine = sqlite_engine()
    with Session(engine) as session:
        resolution_id = create_auditable_resolution(session)
        query, _ = authorize_audit_query(session, resolution_id)
        session.commit()
        verifier = SqlAlchemyAuditAccessVerifier(session)

        assert verifier.verify(query) == ()
        assert set(verifier.verify(
            replace(
                query,
                actor=replace(
                    query.actor,
                    identity=replace(
                        query.actor.identity,
                        actor_id="another-actor",
                    ),
                ),
            )
        )) == {
            "security_actor_mismatch",
            "security_actor_snapshot_mismatch",
        }
        assert set(verifier.verify(
            replace(
                query,
                actor=replace(
                    query.actor,
                    authentication=replace(
                        query.actor.authentication,
                        correlation_id="another-correlation",
                    ),
                ),
            )
        )) == {
            "security_correlation_mismatch",
            "security_authentication_snapshot_mismatch",
        }
        assert verifier.verify(
            replace(query, security_decision_id=999999)
        ) == ("security_decision_missing",)


def test_completed_compensation_is_reconstructed_without_side_effects():
    from sqlalchemy.orm import sessionmaker

    from app.resolution_engine.contracts.compensation import (
        ExecuteCompensationCommand,
    )
    from tests.resolution_engine.test_compensation_persistence import (
        CompensationHandler,
        actor as compensation_actor,
        build_services,
        prepare_command,
        seed_completed_compensable_execution,
    )

    engine = sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    resolution_id, execution_id, decision_id = (
        seed_completed_compensable_execution(factory)
    )
    planner, executor = build_services(factory, CompensationHandler())
    plan = planner.prepare(
        prepare_command(resolution_id, execution_id, decision_id)
    )
    executor.execute(
        ExecuteCompensationCommand(
            compensation_plan_id=plan.id,
            idempotency_key="audit-compensation",
            actor=compensation_actor(),
            lock_owner="phase-7-audit",
        )
    )

    with factory() as session:
        query, _ = authorize_audit_query(session, resolution_id)
        session.commit()
        report = AuditQueryService(
            store=SqlAlchemyAuditRecordStore(session),
            access_verifier=SqlAlchemyAuditAccessVerifier(session),
        ).inspect(query)

        assert not report.is_valid
        assert "lifecycle_audit_prefix_unavailable" in {
            issue.code for issue in report.issues
        }
        kinds = {node.kind for node in report.nodes}
        assert {
            "execution",
            "step_execution",
            "result",
            "compensation_plan",
            "compensation_plan_step",
            "compensation_execution",
            "compensation_step_execution",
            "outbox_event",
        }.issubset(kinds)
        verification_by_key = {
            item.node_key: item.integrity
            for item in report.verifications
        }
        verified_kinds = {
            node.kind
            for node in report.nodes
            if verification_by_key[node.key]
            is EvidenceIntegrity.VERIFIED
        }
        assert {
            "audit_event",
            "outbox_event",
            "security_decision",
            "compensation_plan",
            "compensation_plan_step",
        }.issubset(verified_kinds)
