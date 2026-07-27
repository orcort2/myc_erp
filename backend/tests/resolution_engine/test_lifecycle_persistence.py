from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.db import Base
from app.resolution_engine.application.lifecycle import (
    LifecycleActor,
    ResolutionLifecycleService,
)
from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.application.security import (
    OrganizationBoundaryPolicy,
    PermissionPolicy,
    ResolutionAuthorizationService,
    SecurityPolicyEvaluator,
)
from app.resolution_engine.contracts.lifecycle import (
    CreateResolutionCommand,
    ResolutionProblemInput,
)
from app.resolution_engine.domain.definitions import (
    ComponentReference,
    ResolutionDefinition,
)
from app.resolution_engine.domain.enums import (
    ComponentKind,
    ContextSnapshotType,
    ResolutionPriority,
    ResolutionSource,
    ResolutionStatus,
)
from app.resolution_engine.domain.exceptions import LifecycleConcurrencyError
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
    SecurityRequest,
    SecurityResource,
)
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
    ResolutionType,
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
)

NOW = datetime(2026, 7, 27, 12, tzinfo=timezone.utc)


class FixedClock:
    def now(self):
        return NOW


class FixedIdentifiers:
    def new_id(self):
        return "resolution-public-1"


class ContextComponent:
    component_key = ComponentKey("test.context")
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
        permissions=(
            PermissionGrant(permission=ComponentKey("resolution.create")),
            PermissionGrant(
                permission=ComponentKey(
                    "resolution.lifecycle.transition"
                )
            ),
        ),
    )


def registry():
    value = ResolutionRegistry()
    value.register(
        ResolutionDefinition(
            resolution_type=ResolutionType("example.resolve"),
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


def authorize(
    session,
    *,
    action,
    resource_type,
    resource_id,
    context,
    resolution_id=None,
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
    assert decision.outcome.value == "allowed"
    session.flush()
    return session.scalar(select(func.max(ResolutionSecurityDecision.id)))


def command(session):
    return CreateResolutionCommand(
        resolution_type="example.resolve",
        source=ResolutionSource.USER,
        subject_type="example",
        subject_id="42",
        title="Resolver caso",
        actor=actor(),
        security_decision_id=authorize(
            session,
            action="resolution.create",
            resource_type="resolution_definition",
            resource_id="example.resolve@1.0",
            context={"source": ResolutionSource.USER.value},
        ),
        priority=ResolutionPriority.HIGH,
        problem=ResolutionProblemInput(
            problem_code="example.problem",
            summary="Problema verificable",
            detected_by="test",
            detected_at=NOW,
        ),
    )


def test_creation_and_transition_are_reconstructible_and_audited():
    engine = sqlite_engine()
    with Session(engine) as session:
        store = SqlAlchemyLifecycleStore(session)
        service = ResolutionLifecycleService(
            registry=registry(),
            store=store,
            state_machine=ResolutionStateMachine(),
            clock=FixedClock(),
            identifiers=FixedIdentifiers(),
        )
        created = service.create(command(session))
        snapshot = ResolutionContextSnapshot(
            resolution_id=created.resolution_id,
            snapshot_type=ContextSnapshotType.INITIAL.value,
            sequence=1,
            context_version="1.0",
            context_hash="c" * 64,
            schema_version="1.0",
            captured_at=NOW,
            captured_by_actor_id="actor-1",
            facts={"case": 42},
        )
        session.add(snapshot)
        session.flush()
        root = session.get(Resolution, created.resolution_id)
        root.current_context_snapshot_id = snapshot.id
        session.flush()

        advanced = service.transition(
            created.resolution_id,
            LifecycleAction.RECORD_CONTEXT,
            actor=LifecycleActor(
                context=actor(),
                security_decision_id=authorize(
                    session,
                    action="resolution.lifecycle.transition",
                    resource_type="resolution",
                    resource_id=str(created.resolution_id),
                    resolution_id=created.resolution_id,
                    context={
                        "lifecycle_action": (
                            LifecycleAction.RECORD_CONTEXT.value
                        )
                    },
                ),
            ),
        )
        session.commit()

        events = tuple(
            session.scalars(
                select(ResolutionAuditEvent)
                .where(
                    ResolutionAuditEvent.resolution_id
                    == created.resolution_id
                )
                .order_by(ResolutionAuditEvent.sequence)
            )
        )
        assert created.status is ResolutionStatus.DRAFT
        assert advanced.status is ResolutionStatus.CONTEXT_READY
        assert advanced.version == 2
        assert [item.sequence for item in events] == [1, 2]
        assert events[1].previous_state == "draft"
        assert events[1].new_state == "context_ready"
        assert len(events[1].payload_hash) == 64


def test_store_rejects_a_transition_calculated_from_a_stale_version():
    engine = sqlite_engine()
    with Session(engine) as session:
        store = SqlAlchemyLifecycleStore(session)
        service = ResolutionLifecycleService(
            registry=registry(),
            store=store,
            state_machine=ResolutionStateMachine(),
            clock=FixedClock(),
            identifiers=FixedIdentifiers(),
        )
        created = service.create(command(session))
        snapshot = ResolutionContextSnapshot(
            resolution_id=created.resolution_id,
            snapshot_type=ContextSnapshotType.INITIAL.value,
            sequence=1,
            context_version="1.0",
            context_hash="c" * 64,
            schema_version="1.0",
            captured_at=NOW,
            facts={},
        )
        session.add(snapshot)
        session.flush()
        session.get(
            Resolution,
            created.resolution_id,
        ).current_context_snapshot_id = snapshot.id
        session.flush()
        lifecycle = store.load(created.resolution_id)
        machine = ResolutionStateMachine()
        first = machine.transition(
            lifecycle,
            LifecycleAction.RECORD_CONTEXT,
            occurred_at=NOW,
            actor_id="actor-1",
            actor_type="human",
        )
        stale = machine.transition(
            lifecycle,
            LifecycleAction.RECORD_CONTEXT,
            occurred_at=NOW,
            actor_id="actor-2",
            actor_type="human",
        )

        store.apply(first)
        with pytest.raises(LifecycleConcurrencyError):
            store.apply(stale)
