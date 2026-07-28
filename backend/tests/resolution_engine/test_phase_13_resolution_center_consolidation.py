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
from app.core.permissions import ROLE_PERMISSIONS
from app.models.user import Role, User
from app.resolution_center.definitions import build_resolution_center_registry
from app.resolution_center.query import ResolutionOperationsQueryService
from app.resolution_center.schemas import (
    AuthorizationRequest,
    CreateAdministrativeResolutionRequest,
)
from app.resolution_center.workflow import ResolutionCenterWorkflowService
from app.resolution_center.worker import decode_execution_command
from app.resolution_engine.application.action_runner import ActionRunner
from app.resolution_engine.application.distribution import (
    DistributedWorker,
    ResolutionExecutionWorkHandler,
)
from app.resolution_engine.application.execution import ResolutionExecutor
from app.resolution_engine.contracts.distribution import WorkerRegistration
from app.resolution_engine.domain.execution import ExecutionEngine
from app.resolution_engine.domain.lifecycle import ResolutionStateMachine
from app.resolution_engine.infrastructure.distribution import (
    SqlAlchemyDistributedWorkStore,
)
from app.resolution_engine.infrastructure.execution import (
    SqlAlchemyExecutionStore,
)
from app.resolution_engine.infrastructure.runtime import (
    SystemClock,
    UuidIdentifierFactory,
)
from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionWorkItem,
)
from app.resolution_integrations.certificates.application import (
    build_certificate_resolution_definition,
)
from app.resolution_integrations.certificates.domain import (
    CertificateFacts,
    CertificateOperationOutcome,
)
from app.resolution_integrations.certificates.infrastructure import (
    CertificateComponentResolver,
    CertificateIncorrectReleaseGateway,
)


ROOT = Path(__file__).resolve().parents[3]


class Facts:
    def read(self, certificate_id):
        return CertificateFacts(
            certificate_id=certificate_id,
            folio=f"CERT-{certificate_id}",
            status="released_to_client",
            client_visible=True,
            authenticated_document_present=True,
            released_on="2026-07-20",
            released_to_client_at="2026-07-20T12:00:00+00:00",
            released_to_client_by_id=9,
            is_active=True,
            updated_at="2026-07-28T12:00:00+00:00",
        )


def integration():
    definition = build_certificate_resolution_definition()
    return SimpleNamespace(
        definition=definition,
        component_resolver=CertificateComponentResolver(facts=Facts()),
        action_handlers=(),
        compensation_handlers=(),
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
        yield session, factory, session.scalar(select(User))


def payload(subject_id="41"):
    return CreateAdministrativeResolutionRequest(
        resolution_type="certificate.resolve_incorrect_release",
        definition_version="1.0",
        subject_type="certificate",
        subject_id=subject_id,
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


class Commands:
    def withdraw_incorrect_release(self, **values):
        return CertificateOperationOutcome(
            certificate_id=values["certificate_id"],
            folio=f"CERT-{values['certificate_id']}",
            operation_key="certificates.withdraw_incorrect_release",
            idempotency_key=values["idempotency_key"],
            before_snapshot={"client_visible": True},
            after_snapshot={"client_visible": False},
            domain_transaction_reference="certificate-operation:phase-13",
        )


def test_institutional_definition_is_complete_versioned_and_frozen(center):
    _, factory, _ = center
    engine_registry = ResolutionRegistry()
    registry, _ = build_resolution_center_registry(
        factory,
        engine_registry=engine_registry,
        certificate_integration=integration(),
    )
    entry = registry.list()[0]
    metadata = entry.presentation

    assert entry.key == ("certificate.resolve_incorrect_release", "1.0")
    assert metadata.name
    assert metadata.description
    assert metadata.domain == "certificates"
    assert metadata.object_type == "certificate"
    assert metadata.risk_level == "high"
    assert metadata.required_permissions
    assert metadata.supports_simulation is True
    assert metadata.supports_compensation is True
    assert metadata.parameter_schema["additionalProperties"] is False
    assert metadata.labels["subject"] == "Certificado"
    assert engine_registry.is_frozen is True
    with pytest.raises(RuntimeError, match="frozen"):
        registry.register(entry, engine_registry=engine_registry)


def test_backend_indicators_are_scoped_and_not_frontend_calculations(center):
    session, factory, user = center
    workflow = service(session, factory)
    workflow.create(
        payload(),
        user=user,
        idempotency_key="indicator",
        correlation_id="indicator",
    )
    query = ResolutionOperationsQueryService(session)

    indicators = query.indicators(
        organization_id="myc",
        actor_id=f"user:{user.id}",
        can_read_all=True,
    )
    hidden = query.indicators(
        organization_id="other",
        actor_id=f"user:{user.id}",
        can_read_all=True,
    )

    assert indicators.total == 1
    assert indicators.pending == 1
    assert hidden.total == 0


def test_file_exposes_parameters_analysis_attempts_and_recovery(center):
    session, factory, user = center
    workflow = service(session, factory)
    created = workflow.create(
        payload(),
        user=user,
        idempotency_key="file",
        correlation_id="file",
    )
    workflow.prepare_context(created.public_id, user=user, correlation_id="file")
    workflow.analyze(created.public_id, user=user, correlation_id="file")

    detail = ResolutionOperationsQueryService(session).get(
        created.public_id,
        organization_id="myc",
        actor_id=f"user:{user.id}",
        can_read_all=True,
        include_technical=False,
        include_audit=True,
    )

    assert detail.parameters == {
        "reason": "Liberación administrativa incorrecta"
    }
    assert detail.analysis["status"] == "resolvable"
    assert detail.analysis["findings"]
    assert detail.attempts == ()
    assert detail.recovery == ()
    assert detail.compensations == ()


def test_durable_dispatch_survives_session_and_module_abandonment(center):
    session, factory, user = center
    workflow = service(session, factory)
    created = workflow.create(
        payload(),
        user=user,
        idempotency_key="detached",
        correlation_id="detached",
    )
    for method in ("prepare_context", "analyze", "build_plan", "simulate"):
        getattr(workflow, method)(
            created.public_id,
            user=user,
            correlation_id="detached",
        )
    workflow.authorize(
        created.public_id,
        AuthorizationRequest(comment="Aprobada"),
        user=user,
        correlation_id="detached",
    )
    workflow.execute(
        created.public_id,
        user=user,
        idempotency_key="execute-detached",
        correlation_id="detached",
    )
    session.close()

    with factory() as reconnected:
        root = reconnected.scalar(
            select(Resolution).where(
                Resolution.public_id == created.public_id
            )
        )
        work = reconnected.scalar(
            select(ResolutionWorkItem).where(
                ResolutionWorkItem.resolution_id == root.id
            )
        )
        detail = ResolutionOperationsQueryService(reconnected).get(
            created.public_id,
            organization_id="myc",
            actor_id=f"user:{user.id}",
            can_read_all=True,
            include_technical=False,
            include_audit=True,
        )

    assert work.status == "queued"
    assert work.payload["actor"]["authentication"]["expires_at"] is None
    assert detail.summary.distributed_status == "queued"


def test_certificate_flow_finishes_through_canonical_worker_after_logout(center):
    session, factory, user = center
    workflow = service(session, factory)
    created = workflow.create(
        payload("73"),
        user=user,
        idempotency_key="end-to-end",
        correlation_id="end-to-end",
    )
    for method in ("prepare_context", "analyze", "build_plan", "simulate"):
        getattr(workflow, method)(
            created.public_id,
            user=user,
            correlation_id="end-to-end",
        )
    workflow.authorize(
        created.public_id,
        AuthorizationRequest(comment="Aprobada"),
        user=user,
        correlation_id="end-to-end",
    )
    workflow.execute(
        created.public_id,
        user=user,
        idempotency_key="execute-end-to-end",
        correlation_id="end-to-end",
    )
    session.close()

    executor = ResolutionExecutor(
        store=SqlAlchemyExecutionStore(factory),
        action_runner=ActionRunner(
            (CertificateIncorrectReleaseGateway(Commands()),)
        ),
        engine=ExecutionEngine(),
        state_machine=ResolutionStateMachine(),
        clock=SystemClock(),
        identifiers=UuidIdentifierFactory(),
    )
    worker = DistributedWorker(
        store=SqlAlchemyDistributedWorkStore(factory),
        handlers=(
            ResolutionExecutionWorkHandler(
                executor=executor,
                command_decoder=decode_execution_command,
            ),
        ),
        registration=WorkerRegistration(
            node_id="phase-13-worker",
            instance_id="phase-13-instance",
        ),
        clock=SystemClock(),
        identifiers=UuidIdentifierFactory(),
    )
    worker.start()
    outcome = worker.run_once()

    with factory() as reconnected:
        detail = ResolutionOperationsQueryService(reconnected).get(
            created.public_id,
            organization_id="myc",
            actor_id=f"user:{user.id}",
            can_read_all=True,
            include_technical=True,
            include_audit=True,
        )

    assert outcome is not None
    assert detail.summary.lifecycle_status == "completed"
    assert detail.summary.distributed_status == "succeeded"
    assert detail.result["status"] == "success"
    assert detail.attempts[0]["status"] == "completed"


def test_internal_api_keeps_security_and_public_api_separation():
    router_path = ROOT / "backend/app/routers/resolution_center.py"
    router = router_path.read_text(encoding="utf-8")
    tree = ast.parse(router)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert 'prefix="/resolution-center/v1"' in router
    assert '"/indicators"' in router
    assert "resolution_public_api" not in router
    assert not any(
        item.startswith("app.resolution_engine.infrastructure")
        for item in imports
    )
    for permission in (
        "resolution_center.read",
        "resolution_center.create",
        "resolution_center.authorize",
        "resolution_center.execute",
    ):
        assert permission in router


def test_administrator_auditor_operator_and_normal_user_capabilities_are_exact():
    assert ROLE_PERMISSIONS["Administrador"] == {"*"}
    assert "resolution_center.audit" in ROLE_PERMISSIONS["Auditor"]
    assert "resolution_center.authorize" not in ROLE_PERMISSIONS["Auditor"]
    assert "resolution_center.execute" in ROLE_PERMISSIONS["Operador"]
    assert "resolution_center.authorize" not in ROLE_PERMISSIONS["Operador"]
    assert ROLE_PERMISSIONS["Comercial"] & {"resolution_center.read"} == {
        "resolution_center.read"
    }
    assert "resolution_center.execute" not in ROLE_PERMISSIONS["Comercial"]


def test_frontend_is_driven_by_metadata_and_has_no_domain_form_branch():
    page = (
        ROOT / "frontend/src/pages/ResolutionCenterPage.jsx"
    ).read_text(encoding="utf-8")
    helpers = (
        ROOT / "frontend/src/utils/resolutionCenter.js"
    ).read_text(encoding="utf-8")

    assert "resolutionParameterFields(definition)" in page
    assert "buildResolutionParameters(definition" in page
    assert "getResolutionCenterIndicators" in page
    assert "module-workspace__hero clients-hero" in page
    assert "form.reason" not in page
    assert "certificate_id" not in page
    assert "additionalProperties" not in page
    assert "resolutionParameterFields" in helpers
