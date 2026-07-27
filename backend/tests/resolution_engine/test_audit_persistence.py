from dataclasses import replace
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.db import Base
from app.resolution_engine.application.audit import AuditQueryService
from app.resolution_engine.application.lifecycle import (
    LifecycleActor,
    ResolutionLifecycleService,
)
from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.contracts.lifecycle import (
    CreateResolutionCommand,
    ResolutionProblemInput,
)
from app.resolution_engine.contracts.audit import AuditQuery
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
from app.resolution_engine.domain.lifecycle import (
    LifecycleAction,
    ResolutionStateMachine,
)
from app.resolution_engine.domain.security import (
    ActorContext,
    ActorIdentity,
    ActorType,
    AuthenticationContext,
    SecurityDecision,
    SecurityDecisionOutcome,
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
)
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionAuditEvent,
    ResolutionContextSnapshot,
    ResolutionSecurityDecision,
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


def create_auditable_resolution(session):
    lifecycle_store = SqlAlchemyLifecycleStore(session)
    service = ResolutionLifecycleService(
        registry=registry(),
        store=lifecycle_store,
        state_machine=ResolutionStateMachine(),
        clock=FixedClock(),
        identifiers=FixedIdentifiers(),
    )
    created = service.create(
        CreateResolutionCommand(
            resolution_type="audit.resolve",
            source=ResolutionSource.SYSTEM,
            subject_type="example",
            subject_id="42",
            title="Auditable",
            actor=actor(),
            problem=ResolutionProblemInput(
                problem_code="audit.problem",
                summary="Evidence required",
                detected_by="test",
                detected_at=NOW,
            ),
        )
    )
    context = ResolutionContextSnapshot(
        resolution_id=created.resolution_id,
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
    session.get(Resolution, created.resolution_id).current_context_snapshot_id = (
        context.id
    )
    session.flush()
    service.transition(
        created.resolution_id,
        LifecycleAction.RECORD_CONTEXT,
        actor=LifecycleActor(
            actor_id="auditor-1",
            actor_type="human",
            correlation_id="correlation-audit",
        ),
    )
    session.commit()
    return created.resolution_id


def authorize_audit_query(session, resolution_id):
    request = SecurityRequest(
        actor=actor(),
        action=ComponentKey("resolution.audit.inspect"),
        resource=SecurityResource(
            resource_type="resolution",
            resource_id=str(resolution_id),
            organization_id="organization-1",
            resolution_id=resolution_id,
        ),
        required_permissions=(),
        occurred_functions={"requester": ("auditor-1",)},
        context={"purpose": "phase-7-test"},
    )
    decision = SecurityDecision.build(
        outcome=SecurityDecisionOutcome.ALLOWED,
        request=request,
        evaluated_at=NOW,
        policy_results=(),
        reason_codes=("audit_test_allowed",),
    )
    SqlAlchemySecurityEvidenceStore(session).append(
        decision,
        context_snapshot={
            "occurred_functions": dict(request.occurred_functions),
            "context": dict(request.context),
        },
    )
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
            actor_id="auditor-1",
            correlation_id="correlation-audit",
            security_decision_id=persisted.id,
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
        assert verifier.verify(
            replace(query, actor_id="another-actor")
        ) == ("security_actor_mismatch",)
        assert verifier.verify(
            replace(query, correlation_id="another-correlation")
        ) == ("security_correlation_mismatch",)
        assert verifier.verify(
            replace(query, security_decision_id=999999)
        ) == ("security_decision_missing_or_foreign",)


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
