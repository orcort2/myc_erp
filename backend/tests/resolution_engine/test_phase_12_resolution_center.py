from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base
from app.models.user import Role, User
from app.resolution_center.query import (
    ResolutionCenterCursorError,
    ResolutionCenterNotFoundError,
    ResolutionOperationsQueryService,
)
from app.resolution_center.schemas import (
    AuthorizationRequest,
    CreateAdministrativeResolutionRequest,
)
from app.resolution_center.workflow import (
    ResolutionCenterWorkflowError,
    ResolutionCenterWorkflowService,
)
from app.resolution_center.worker import decode_execution_command
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionWorkItem,
)
from app.resolution_integrations.certificates.application import (
    build_certificate_resolution_definition,
)
from app.resolution_integrations.certificates.domain import CertificateFacts
from app.resolution_integrations.certificates.infrastructure import (
    CertificateComponentResolver,
)


ROOT = Path(__file__).resolve().parents[3]
MIGRATION = (
    ROOT
    / "backend/migrations/versions"
    / "d2f4a6b8c0e3_phase_12_plan_lifecycle_guard.py"
)


class Facts:
    def __init__(self):
        self.status = "released_to_client"
        self.client_visible = True

    def read(self, certificate_id):
        return CertificateFacts(
            certificate_id=certificate_id,
            folio=f"CERT-{certificate_id}",
            status=self.status,
            client_visible=self.client_visible,
            authenticated_document_present=True,
            released_on="2026-07-20",
            released_to_client_at="2026-07-20T12:00:00+00:00",
            released_to_client_by_id=9,
            is_active=True,
            updated_at="2026-07-28T12:00:00+00:00",
        )


def integration(facts=None):
    facts = facts or Facts()
    return SimpleNamespace(
        definition=build_certificate_resolution_definition(),
        component_resolver=CertificateComponentResolver(facts=facts),
        action_handlers=(),
        compensation_handlers=(),
        register=lambda registry: registry.register(
            build_certificate_resolution_definition()
        ),
    )


@pytest.fixture
def center():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    tables = [
        table
        for name, table in Base.metadata.tables.items()
        if name.startswith("resolution_")
        or name in {"resolutions", "users", "roles", "user_roles"}
    ]
    Base.metadata.create_all(engine, tables=tables)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session, session.begin():
        role = Role(name="Administrador", description="Admin")
        user = User(
            email="admin@example.test",
            full_name="Administradora",
            hashed_password="unused",
        )
        user.roles.append(role)
        session.add(user)
    with factory() as session:
        user = session.scalar(select(User))
        yield session, factory, user


def payload():
    return CreateAdministrativeResolutionRequest(
        resolution_type="certificate.resolve_incorrect_release",
        definition_version="1.0",
        subject_type="certificate",
        subject_id="41",
        title="Retirar certificado incorrecto",
        reason="Liberación administrativa incorrecta",
        parameters={"reason": "Liberación administrativa incorrecta"},
    )


def service(session, factory):
    return ResolutionCenterWorkflowService(
        session,
        organization_id="myc",
        session_factory=factory,
        integration=integration(),
    )


def test_guided_flow_reaches_durable_queue_without_http_session(center):
    session, factory, user = center
    workflow = service(session, factory)

    created = workflow.create(
        payload(),
        user=user,
        idempotency_key="create-41",
        correlation_id="correlation-41",
    )
    public_id = created.public_id
    assert workflow.prepare_context(
        public_id, user=user, correlation_id="correlation-41"
    ).lifecycle_status == "context_ready"
    assert workflow.analyze(
        public_id, user=user, correlation_id="correlation-41"
    ).lifecycle_status == "analyzed"
    assert workflow.build_plan(
        public_id, user=user, correlation_id="correlation-41"
    ).lifecycle_status == "plan_ready"
    assert workflow.simulate(
        public_id, user=user, correlation_id="correlation-41"
    ).lifecycle_status == "simulated"
    assert session.scalar(select(ResolutionWorkItem)) is None
    assert workflow.authorize(
        public_id,
        AuthorizationRequest(comment="Aprobada"),
        user=user,
        correlation_id="correlation-41",
    ).lifecycle_status == "ready_for_execution"
    accepted = workflow.execute(
        public_id,
        user=user,
        idempotency_key="execute-41",
        correlation_id="correlation-41",
    )

    assert accepted.message == "Resolución aceptada para ejecución"
    assert accepted.distributed_status == "queued"
    session.expire_all()
    root = session.scalar(
        select(Resolution).where(Resolution.public_id == public_id)
    )
    work = session.scalar(
        select(ResolutionWorkItem).where(
            ResolutionWorkItem.resolution_id == root.id
        )
    )
    assert root.status == "ready_for_execution"
    assert work.payload["actor"]["identity"]["actor_id"] == f"user:{user.id}"
    assert "lease_token" not in work.payload
    detail = ResolutionOperationsQueryService(session).get(
        public_id,
        organization_id="myc",
        actor_id=f"user:{user.id}",
        can_read_all=True,
        include_technical=True,
        include_audit=True,
    )
    assert detail.evidence["revalidations"][0]["outcome"] == "valid"
    assert detail.evidence["context_snapshots"][-1]["context_hash"]


def test_idempotency_and_query_redaction(center):
    session, factory, user = center
    workflow = service(session, factory)
    first = workflow.create(
        payload(),
        user=user,
        idempotency_key="same",
        correlation_id="correlation",
    )
    replay = workflow.create(
        payload(),
        user=user,
        idempotency_key="same",
        correlation_id="correlation",
    )
    assert replay.public_id == first.public_id
    workflow.prepare_context(
        first.public_id,
        user=user,
        correlation_id="correlation",
    )

    query = ResolutionOperationsQueryService(session)
    collection = query.list(
        organization_id="myc",
        actor_id=f"user:{user.id}",
        can_read_all=True,
        search=first.public_id,
        limit=20,
    )
    detail = query.get(
        first.public_id,
        organization_id="myc",
        actor_id=f"user:{user.id}",
        can_read_all=True,
        include_technical=False,
        include_audit=True,
    )

    assert len(collection.items) == 1
    assert detail.summary.public_id == first.public_id
    assert detail.evidence["security_decisions"]
    assert all(
        "evidence_hash" not in decision
        for decision in detail.evidence["security_decisions"]
    )
    assert query.list(
        organization_id="myc",
        actor_id=f"user:{user.id}",
        can_read_all=True,
        requester="Administra",
    ).items


def test_creation_rejects_parameters_outside_versioned_contract(center):
    session, factory, user = center
    invalid = payload().model_copy(
        update={"parameters": {"reason": "válido", "command": "arbitrario"}}
    )
    with pytest.raises(
        ResolutionCenterWorkflowError,
        match="parámetros no declarados",
    ):
        service(session, factory).create(
            invalid,
            user=user,
            idempotency_key="invalid-contract",
            correlation_id="invalid-contract",
        )
    assert session.scalar(select(Resolution)) is None


def test_cursor_is_bound_to_actor_filters_and_page_size(center):
    session, factory, user = center
    workflow = service(session, factory)
    for suffix in ("a", "b"):
        data = payload().model_copy(
            update={
                "subject_id": "41" if suffix == "a" else "42",
                "title": f"Resolución {suffix}",
            }
        )
        workflow.create(
            data,
            user=user,
            idempotency_key=suffix,
            correlation_id=f"correlation-{suffix}",
        )
    query = ResolutionOperationsQueryService(session)
    first = query.list(
        organization_id="myc",
        actor_id=f"user:{user.id}",
        can_read_all=True,
        limit=1,
    )
    assert first.next_cursor
    with pytest.raises(ResolutionCenterCursorError):
        query.list(
            organization_id="myc",
            actor_id="user:999",
            can_read_all=True,
            cursor=first.next_cursor,
            limit=1,
        )


def test_worker_command_reconstructs_canonical_actor(center):
    session, factory, user = center
    workflow = service(session, factory)
    created = workflow.create(
        payload(),
        user=user,
        idempotency_key="worker",
        correlation_id="correlation-worker",
    )
    workflow.prepare_context(
        created.public_id, user=user, correlation_id="correlation-worker"
    )
    workflow.analyze(
        created.public_id, user=user, correlation_id="correlation-worker"
    )
    workflow.build_plan(
        created.public_id, user=user, correlation_id="correlation-worker"
    )
    workflow.simulate(
        created.public_id, user=user, correlation_id="correlation-worker"
    )
    workflow.authorize(
        created.public_id,
        AuthorizationRequest(),
        user=user,
        correlation_id="correlation-worker",
    )
    workflow.execute(
        created.public_id,
        user=user,
        idempotency_key="execute-worker",
        correlation_id="correlation-worker",
    )
    work = session.scalar(select(ResolutionWorkItem))
    command = decode_execution_command(work.payload)

    assert command.resolution_id == work.resolution_id
    assert command.actor.identity.actor_id == f"user:{user.id}"
    assert command.actor.authentication.expires_at is None
    assert str(command.actor.permissions[-1].permission).startswith("resolution.")


def test_query_isolates_organization_and_non_privileged_actor(center):
    session, factory, user = center
    workflow = service(session, factory)
    created = workflow.create(
        payload(),
        user=user,
        idempotency_key="isolation",
        correlation_id="correlation-isolation",
    )
    query = ResolutionOperationsQueryService(session)

    assert not query.list(
        organization_id="other",
        actor_id=f"user:{user.id}",
        can_read_all=True,
    ).items
    assert not query.list(
        organization_id="myc",
        actor_id="user:999",
        can_read_all=False,
    ).items
    with pytest.raises(ResolutionCenterNotFoundError):
        query.get(
            created.public_id,
            organization_id="myc",
            actor_id="user:999",
            can_read_all=False,
            include_technical=False,
        )


def test_execute_is_single_durable_dispatch_across_replays(center):
    session, factory, user = center
    workflow = service(session, factory)
    created = workflow.create(
        payload(),
        user=user,
        idempotency_key="single-dispatch",
        correlation_id="correlation-single",
    )
    for method in ("prepare_context", "analyze", "build_plan", "simulate"):
        getattr(workflow, method)(
            created.public_id,
            user=user,
            correlation_id="correlation-single",
        )
    workflow.authorize(
        created.public_id,
        AuthorizationRequest(),
        user=user,
        correlation_id="correlation-single",
    )

    first = workflow.execute(
        created.public_id,
        user=user,
        idempotency_key="first",
        correlation_id="correlation-single",
    )
    replay = workflow.execute(
        created.public_id,
        user=user,
        idempotency_key="second",
        correlation_id="correlation-reconnected",
    )

    assert replay.work_key == first.work_key
    assert replay.distributed_status == "queued"
    assert len(tuple(session.scalars(select(ResolutionWorkItem)))) == 1


def test_stages_use_snapshot_and_revalidation_drift_is_persisted(center):
    session, factory, user = center
    facts = Facts()
    workflow = ResolutionCenterWorkflowService(
        session,
        organization_id="myc",
        session_factory=factory,
        integration=integration(facts),
    )
    created = workflow.create(
        payload(),
        user=user,
        idempotency_key="drift",
        correlation_id="correlation-drift",
    )
    workflow.prepare_context(
        created.public_id,
        user=user,
        correlation_id="correlation-drift",
    )
    facts.status = "draft"
    facts.client_visible = False
    assert workflow.analyze(
        created.public_id,
        user=user,
        correlation_id="correlation-drift",
    ).lifecycle_status == "analyzed"
    workflow.build_plan(
        created.public_id,
        user=user,
        correlation_id="correlation-drift",
    )
    workflow.simulate(
        created.public_id,
        user=user,
        correlation_id="correlation-drift",
    )

    with pytest.raises(
        ResolutionCenterWorkflowError,
        match="requiere un plan nuevo",
    ):
        workflow.authorize(
            created.public_id,
            AuthorizationRequest(),
            user=user,
            correlation_id="correlation-drift",
        )

    root = session.scalar(
        select(Resolution).where(
            Resolution.public_id == created.public_id
        )
    )
    assert root.status == "plan_ready"
    detail = ResolutionOperationsQueryService(session).get(
        created.public_id,
        organization_id="myc",
        actor_id=f"user:{user.id}",
        can_read_all=True,
        include_technical=False,
        include_audit=True,
    )
    assert detail.evidence["revalidations"][-1]["outcome"] in {
        "requires_new_plan",
        "no_longer_resolvable",
    }
    assert detail.capabilities == ()


def test_phase_12_router_has_no_engine_infrastructure_imports():
    router = (
        ROOT / "backend/app/routers/resolution_center.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(router)
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(
        module.startswith("app.resolution_engine.infrastructure")
        for module in imported
    )
    assert "session.add(" not in router
    assert "session.execute(" not in router
    for permission in (
        "resolution_center.read",
        "resolution_center.create",
        "resolution_center.prepare",
        "resolution_center.analyze",
        "resolution_center.plan",
        "resolution_center.simulate",
        "resolution_center.authorize",
        "resolution_center.execute",
    ):
        assert permission in router


def test_phase_12_migration_preserves_plan_content_and_is_reversible():
    source = MIGRATION.read_text(encoding="utf-8")
    namespace = {}
    exec(compile(source, str(MIGRATION), "exec"), namespace)

    assert namespace["down_revision"] == "c1e3f5a7b9d2"
    assert "plan identity and content are immutable" in source
    assert "CREATE OR REPLACE FUNCTION resolution_engine_guard_plan_update" in source
    assert source.count("CREATE OR REPLACE FUNCTION") == 2


def test_frontend_uses_internal_api_and_not_engine_internals():
    page = (
        ROOT / "frontend/src/pages/ResolutionCenterPage.jsx"
    ).read_text(encoding="utf-8")
    api = (ROOT / "frontend/src/services/api.js").read_text(encoding="utf-8")

    assert "/resolution-center/v1/" in api
    assert "resolution_engine" not in page
    assert "localStorage" not in page
    assert "document.visibilityState" in page
