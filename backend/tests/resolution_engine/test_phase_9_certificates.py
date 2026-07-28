from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base
from app.models.audit_log import AuditLog
from app.models.certificate import Certificate
from app.models.certificate_resolution_operation import (
    CertificateResolutionOperation,
)
from app.resolution_engine.application.action_runner import ActionRunner
from app.resolution_engine.application.compensation_runner import (
    CompensationRunner,
)
from app.resolution_engine.application.execution import ResolutionExecutor
from app.resolution_engine.application.orchestration import (
    ResolutionOrchestrator,
)
from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.application.security import (
    IntegralSecurityControlPolicy,
    OrganizationBoundaryPolicy,
    PermissionPolicy,
    ResolutionAuthorizationService,
    SecurityPolicyEvaluator,
)
from app.resolution_engine.contracts.execution import (
    ExecuteResolutionCommand,
    execution_security_operation_payload,
)
from app.resolution_engine.domain.compensation import (
    CompensationActionRequest,
    CompensationPlanStep,
)
from app.resolution_engine.domain.enums import (
    AnalysisStatus,
    ExecutionStatus,
    ResolutionStatus,
    SimulationStatus,
)
from app.resolution_engine.domain.execution import ExecutionEngine
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
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionAnalysis,
    ResolutionAuditEvent,
    ResolutionAuthorizationDecision,
    ResolutionAuthorizationRequest,
    ResolutionContextSnapshot,
    ResolutionEntityReference,
    ResolutionExecution,
    ResolutionPlan,
    ResolutionPlanStep,
    ResolutionRevalidation,
    ResolutionSecurityDecision,
    ResolutionSimulation,
    ResolutionStepExecution,
    ResolutionStrategySelection,
)
from app.resolution_engine.infrastructure.security import (
    SqlAlchemySecurityEvidenceStore,
    SqlAlchemySecurityResourceVerifier,
)
from app.resolution_integrations.certificates.application import (
    CERTIFICATE_RESOLUTION_TYPE,
)
from app.resolution_integrations.certificates.domain import (
    CertificateResolutionRequest,
)
from app.resolution_integrations.certificates.infrastructure import (
    SqlAlchemyCertificateCommandService,
    build_certificate_resolution_integration,
)
from app.services.certificate_resolution_operations import (
    CertificateResolutionOperationError,
)


NOW = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)
PLAN_HASH = "a" * 64
SIMULATION_HASH = "b" * 64
CONTEXT_HASH = "c" * 64
REVALIDATION_HASH = "d" * 64


class AdvancingClock:
    def __init__(self, current: datetime = NOW) -> None:
        self.current = current

    def now(self) -> datetime:
        self.current += timedelta(seconds=1)
        return self.current


class Identifiers:
    def __init__(self) -> None:
        self.sequence = 0

    def new_id(self) -> str:
        self.sequence += 1
        return f"phase-9-token-{self.sequence}"


def sqlite_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        table
        for name, table in Base.metadata.tables.items()
        if not name.startswith("activity_")
    ]
    Base.metadata.create_all(engine, tables=tables)
    return engine


def concurrent_sqlite_factory(path: Path):
    engine = create_engine(
        f"sqlite+pysqlite:///{path}",
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
        },
    )

    @event.listens_for(engine, "connect")
    def configure_connection(dbapi_connection, _record):
        dbapi_connection.isolation_level = None
        dbapi_connection.execute("PRAGMA journal_mode=WAL")

    @event.listens_for(engine, "begin")
    def begin_immediate(connection):
        connection.exec_driver_sql("BEGIN IMMEDIATE")

    tables = [
        table
        for name, table in Base.metadata.tables.items()
        if not name.startswith("activity_")
    ]
    Base.metadata.create_all(engine, tables=tables)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def factory():
    return sessionmaker(
        bind=sqlite_engine(),
        expire_on_commit=False,
    )


def actor() -> ActorContext:
    return ActorContext(
        identity=ActorIdentity(
            actor_id="7",
            actor_type=ActorType.HUMAN,
            principal="quality@example.test",
            organization_id="organization-1",
        ),
        authentication=AuthenticationContext(
            authenticated_at=NOW - timedelta(minutes=1),
            method="test",
            session_id="phase-9-session",
            assurance_level="high",
            source="phase-9-certificates",
            correlation_id="phase-9-correlation",
        ),
        permissions=(
            PermissionGrant(
                permission=ComponentKey("resolution.execute"),
            ),
            PermissionGrant(
                permission=ComponentKey("resolution.compensate"),
            ),
        ),
    )


def seed_certificate(
    session: Session,
    *,
    folio: str = "MYCA-07-2026-0901",
    visible: bool = True,
) -> Certificate:
    certificate = Certificate(
        folio=folio,
        expected_folio=folio,
        service_order_id=100,
        equipment_id=200,
        field_sheet_id=300,
        certificate_type="acreditado",
        status="released_to_client",
        issued_on=date(2026, 7, 1),
        released_on=date(2026, 7, 20),
        released_to_client_at=NOW - timedelta(days=1),
        released_to_client_by_id=7,
        authenticated_pdf_path=f"certificates/{folio}.pdf",
        client_visible=visible,
        external_source="excel",
        match_status="pending",
        is_active=True,
    )
    session.add(certificate)
    session.flush()
    return certificate


def test_vertical_definition_runs_every_pure_stage_without_effects(factory):
    with factory() as session, session.begin():
        certificate_id = seed_certificate(session).id

    integration = build_certificate_resolution_integration(factory)
    registry = ResolutionRegistry()
    integration.register(registry)
    orchestrator = ResolutionOrchestrator(
        registry=registry,
        components=integration.component_resolver,
    )
    request = CertificateResolutionRequest(
        certificate_id=certificate_id,
        reason="Liberación registrada por error operativo",
    )
    selection = orchestrator.selection(
        str(CERTIFICATE_RESOLUTION_TYPE),
        "1.0",
    )
    context = orchestrator.build_context(
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        request=request,
    )
    analysis = orchestrator.analyze(
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        context=context,
    )
    strategy, plan = orchestrator.build_plan(
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        context=context,
        analysis=analysis,
    )
    simulation = orchestrator.simulate(
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        context=context,
        plan=plan,
    )
    requirements = orchestrator.authorization_requirements(
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        context=context,
        plan=plan,
        simulation=simulation,
    )
    revalidation = orchestrator.revalidate(
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        authorized_context=context,
        current_context=context,
        plan=plan,
        simulation=simulation,
    )

    assert selection.definition_version == "1.0"
    assert len(selection.definition_fingerprint) == 64
    assert analysis.status is AnalysisStatus.RESOLVABLE
    assert strategy.key.value == "withdraw_client_access"
    assert plan.steps[0].operation_key == (
        "certificates.withdraw_incorrect_release"
    )
    assert plan.steps[0].compensation_operation_key == (
        "certificates.restore_incorrect_release_visibility"
    )
    assert simulation.status is SimulationStatus.VALID
    assert requirements.required_permissions == (
        "certificates.approve",
        "certificates.release",
    )
    assert revalidation.is_valid
    with factory() as session:
        certificate = session.get(Certificate, certificate_id)
        assert certificate.client_visible is True


def test_analysis_blocks_non_released_certificate_and_revalidation_detects_drift(
    factory,
):
    with factory() as session, session.begin():
        certificate = seed_certificate(session)
        certificate.status = "authenticated"
        certificate_id = certificate.id
    integration = build_certificate_resolution_integration(factory)
    registry = ResolutionRegistry()
    integration.register(registry)
    orchestrator = ResolutionOrchestrator(
        registry=registry,
        components=integration.component_resolver,
    )
    request = CertificateResolutionRequest(
        certificate_id=certificate_id,
        reason="Caso inválido",
    )
    context = orchestrator.build_context(
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        request=request,
    )
    analysis = orchestrator.analyze(
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        context=context,
    )
    strategy, plan = orchestrator.build_plan(
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        context=context,
        analysis=analysis,
    )
    simulation = orchestrator.simulate(
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        context=context,
        plan=plan,
    )
    assert analysis.status is AnalysisStatus.BLOCKED
    assert plan.steps == ()
    assert simulation.status is SimulationStatus.BLOCKED

    with factory() as session, session.begin():
        certificate = session.get(Certificate, certificate_id)
        certificate.status = "released_to_client"
        certificate.client_visible = True
    current = orchestrator.build_context(
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        request=request,
    )
    revalidation = orchestrator.revalidate(
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        authorized_context=context,
        current_context=current,
        plan=plan,
        simulation=simulation,
    )
    assert not revalidation.is_valid
    assert revalidation.reason_codes == ("certificate_context_changed",)


def test_domain_operation_is_atomic_idempotent_and_compensable(factory):
    with factory() as session, session.begin():
        certificate_id = seed_certificate(session).id
    commands = SqlAlchemyCertificateCommandService(factory)
    values = {
        "certificate_id": certificate_id,
        "expected_status": "released_to_client",
        "reason": "Liberación incorrecta confirmada",
        "actor_id": "7",
        "correlation_id": "phase-9-correlation",
        "idempotency_key": "certificate-withdraw-1",
        "request_hash": "a" * 64,
    }
    first = commands.withdraw_incorrect_release(**values)
    replay = commands.withdraw_incorrect_release(**values)
    assert replay.after_snapshot == first.after_snapshot

    with pytest.raises(
        CertificateResolutionOperationError,
        match="otra intención",
    ):
        commands.withdraw_incorrect_release(
            **{**values, "request_hash": "b" * 64}
        )
    with pytest.raises(
        CertificateResolutionOperationError,
        match="ya no está visible",
    ):
        commands.withdraw_incorrect_release(
            **{
                **values,
                "idempotency_key": "certificate-withdraw-2",
                "request_hash": "b" * 64,
            }
        )

    compensation_values = {
        "certificate_id": certificate_id,
        "source_operation_key": "certificate-withdraw-1",
        "actor_id": "7",
        "correlation_id": "phase-9-correlation",
        "idempotency_key": "certificate-restore-1",
        "request_hash": "c" * 64,
    }
    restored = commands.restore_incorrect_release_visibility(
        **compensation_values
    )
    restored_replay = commands.restore_incorrect_release_visibility(
        **compensation_values
    )
    assert restored_replay.after_snapshot == restored.after_snapshot

    with factory() as session:
        certificate = session.get(Certificate, certificate_id)
        operations = tuple(
            session.scalars(
                select(CertificateResolutionOperation).order_by(
                    CertificateResolutionOperation.id
                )
            )
        )
        audits = tuple(
            session.scalars(
                select(AuditLog).where(
                    AuditLog.entity == "certificates",
                    AuditLog.entity_id == certificate_id,
                )
            )
        )
        assert certificate.status == "released_to_client"
        assert certificate.released_to_client_at.replace(
            tzinfo=timezone.utc
        ) == (NOW - timedelta(days=1))
        assert certificate.client_visible is True
        assert len(operations) == 2
        assert operations[1].source_operation_id == operations[0].id
        assert len(audits) == 2


def test_exact_replay_uses_confirmed_history_after_drift_and_inactivation(
    factory,
):
    with factory() as session, session.begin():
        certificate = seed_certificate(
            session,
            folio="MYCA-07-2026-0903",
        )
        certificate_id = certificate.id
        historical_release = certificate.released_to_client_at
        historical_actor = certificate.released_to_client_by_id
    commands = SqlAlchemyCertificateCommandService(factory)
    values = {
        "certificate_id": certificate_id,
        "expected_status": "released_to_client",
        "reason": "Replay histórico estable",
        "actor_id": "7",
        "correlation_id": "phase-9-replay-history",
        "idempotency_key": "certificate-withdraw-history",
        "request_hash": "1" * 64,
    }
    confirmed = commands.withdraw_incorrect_release(**values)

    with factory() as session, session.begin():
        certificate = session.get(Certificate, certificate_id)
        operation = session.scalar(
            select(CertificateResolutionOperation).where(
                CertificateResolutionOperation.idempotency_key
                == values["idempotency_key"]
            )
        )
        assert operation is not None
        assert confirmed.after_snapshot == operation.after_snapshot
        assert (
            confirmed.after_snapshot
            == operation.result_payload["after_snapshot"]
        )
        assert confirmed.after_snapshot["updated_at"] == (
            certificate.updated_at.isoformat()
        )
        certificate.status = "cancelled"
        certificate.is_active = False

    replay = commands.withdraw_incorrect_release(**values)
    assert replay == confirmed
    with pytest.raises(
        CertificateResolutionOperationError,
        match="otra intención",
    ):
        commands.withdraw_incorrect_release(
            **{**values, "request_hash": "2" * 64}
        )
    with pytest.raises(
        CertificateResolutionOperationError,
        match="otra intención",
    ):
        commands.withdraw_incorrect_release(
            **{**values, "reason": "Payload alterado"}
        )

    with factory() as session:
        certificate = session.get(Certificate, certificate_id)
        assert certificate.status == "cancelled"
        assert certificate.is_active is False
        assert certificate.client_visible is False
        assert certificate.released_to_client_at.replace(
            tzinfo=timezone.utc
        ) == historical_release
        assert (
            certificate.released_to_client_by_id
            == historical_actor
        )
        assert (
            session.scalar(
                select(func.count(CertificateResolutionOperation.id)).where(
                    CertificateResolutionOperation.certificate_id
                    == certificate_id
                )
            )
            == 1
        )


def test_compensation_replay_uses_confirmed_snapshot_after_later_drift(
    factory,
):
    with factory() as session, session.begin():
        certificate_id = seed_certificate(
            session,
            folio="MYCA-07-2026-0904",
        ).id
    commands = SqlAlchemyCertificateCommandService(factory)
    withdrawn = commands.withdraw_incorrect_release(
        certificate_id=certificate_id,
        expected_status="released_to_client",
        reason="Preparar compensación",
        actor_id="7",
        correlation_id="phase-9-compensation-history",
        idempotency_key="certificate-withdraw-for-history",
        request_hash="3" * 64,
    )
    values = {
        "certificate_id": certificate_id,
        "source_operation_key": withdrawn.idempotency_key,
        "actor_id": "7",
        "correlation_id": "phase-9-compensation-history",
        "idempotency_key": "certificate-restore-history",
        "request_hash": "4" * 64,
    }
    restored = commands.restore_incorrect_release_visibility(**values)

    with factory() as session, session.begin():
        certificate = session.get(Certificate, certificate_id)
        operation = session.scalar(
            select(CertificateResolutionOperation).where(
                CertificateResolutionOperation.idempotency_key
                == values["idempotency_key"]
            )
        )
        assert operation is not None
        assert restored.after_snapshot == operation.after_snapshot
        assert restored.after_snapshot["updated_at"] == (
            certificate.updated_at.isoformat()
        )
        certificate.status = "cancelled"
        certificate.is_active = False

    replay = commands.restore_incorrect_release_visibility(**values)
    assert replay == restored
    with pytest.raises(
        CertificateResolutionOperationError,
        match="otra intención",
    ):
        commands.restore_incorrect_release_visibility(
            **{**values, "request_hash": "5" * 64}
        )


def test_concurrent_exact_requests_commit_one_mutation(tmp_path):
    factory = concurrent_sqlite_factory(
        tmp_path / "phase9-concurrent-exact.sqlite"
    )
    with factory() as session, session.begin():
        certificate_id = seed_certificate(
            session,
            folio="MYCA-07-2026-0905",
        ).id
    commands = SqlAlchemyCertificateCommandService(factory)
    values = {
        "certificate_id": certificate_id,
        "expected_status": "released_to_client",
        "reason": "Solicitud concurrente exacta",
        "actor_id": "7",
        "correlation_id": "phase-9-concurrent-exact",
        "idempotency_key": "certificate-concurrent-exact",
        "request_hash": "6" * 64,
    }
    barrier = Barrier(3)

    def invoke():
        barrier.wait()
        return commands.withdraw_incorrect_release(**values)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(invoke) for _ in range(2)]
        barrier.wait()
        results = [future.result(timeout=10) for future in futures]

    assert results[0] == results[1]
    with factory() as session:
        certificate = session.get(Certificate, certificate_id)
        assert certificate.client_visible is False
        assert (
            session.scalar(
                select(func.count(CertificateResolutionOperation.id)).where(
                    CertificateResolutionOperation.certificate_id
                    == certificate_id
                )
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.entity == "certificates",
                    AuditLog.entity_id == certificate_id,
                )
            )
            == 1
        )


def test_concurrent_colliding_payloads_commit_only_one_effect(tmp_path):
    factory = concurrent_sqlite_factory(
        tmp_path / "phase9-concurrent-conflict.sqlite"
    )
    with factory() as session, session.begin():
        certificate_id = seed_certificate(
            session,
            folio="MYCA-07-2026-0906",
        ).id
    commands = SqlAlchemyCertificateCommandService(factory)
    common = {
        "certificate_id": certificate_id,
        "expected_status": "released_to_client",
        "actor_id": "7",
        "correlation_id": "phase-9-concurrent-conflict",
        "idempotency_key": "certificate-concurrent-conflict",
    }
    requests = (
        {
            **common,
            "reason": "Primera intención",
            "request_hash": "7" * 64,
        },
        {
            **common,
            "reason": "Segunda intención",
            "request_hash": "8" * 64,
        },
    )
    barrier = Barrier(3)

    def invoke(values):
        barrier.wait()
        try:
            return commands.withdraw_incorrect_release(**values)
        except CertificateResolutionOperationError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(invoke, values)
            for values in requests
        ]
        barrier.wait()
        results = [future.result(timeout=10) for future in futures]

    assert sum(
        not isinstance(result, Exception) for result in results
    ) == 1
    conflict = next(
        result for result in results if isinstance(result, Exception)
    )
    assert isinstance(conflict, CertificateResolutionOperationError)
    assert conflict.code == "idempotency_conflict"
    with factory() as session:
        certificate = session.get(Certificate, certificate_id)
        assert certificate.client_visible is False
        assert session.scalar(
            select(func.count(CertificateResolutionOperation.id)).where(
                CertificateResolutionOperation.certificate_id
                == certificate_id
            )
        ) == 1
        assert session.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.entity == "certificates",
                AuditLog.entity_id == certificate_id,
            )
        ) == 1


def test_unique_race_recovers_only_the_exact_confirmed_result(factory):
    with factory() as session, session.begin():
        certificate_id = seed_certificate(
            session,
            folio="MYCA-07-2026-0907",
        ).id
    commands = SqlAlchemyCertificateCommandService(factory)
    values = {
        "certificate_id": certificate_id,
        "expected_status": "released_to_client",
        "reason": "Resultado ganador concurrente",
        "actor_id": "7",
        "correlation_id": "phase-9-unique-race",
        "idempotency_key": "certificate-unique-race",
        "request_hash": "9" * 64,
    }
    confirmed = commands.withdraw_incorrect_release(**values)
    simulated_race = IntegrityError(
        "unique idempotency race",
        {},
        RuntimeError("concurrent winner"),
    )

    with patch(
        "app.resolution_integrations.certificates.infrastructure."
        "withdraw_incorrect_release",
        side_effect=simulated_race,
    ):
        recovered = commands.withdraw_incorrect_release(**values)
        assert recovered == confirmed
        with pytest.raises(
            CertificateResolutionOperationError,
            match="otra intención",
        ):
            commands.withdraw_incorrect_release(
                **{**values, "request_hash": "0" * 64}
            )


def test_domain_operation_rolls_back_mutation_and_evidence_together(factory):
    with factory() as session, session.begin():
        certificate_id = seed_certificate(
            session,
            folio="MYCA-07-2026-0902",
        ).id
    commands = SqlAlchemyCertificateCommandService(factory)
    with patch(
        "app.services.certificate_resolution_operations.write_audit_log",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError, match="audit unavailable"):
            commands.withdraw_incorrect_release(
                certificate_id=certificate_id,
                expected_status="released_to_client",
                reason="Debe revertirse",
                actor_id="7",
                correlation_id="phase-9-rollback",
                idempotency_key="certificate-withdraw-rollback",
                request_hash="e" * 64,
            )
    with factory() as session:
        certificate = session.get(Certificate, certificate_id)
        assert certificate.client_visible is True
        assert (
            session.scalar(
                select(func.count(CertificateResolutionOperation.id)).where(
                    CertificateResolutionOperation.certificate_id
                    == certificate_id
                )
            )
            == 0
        )


def seed_ready_resolution(
    session: Session,
    *,
    certificate_id: int,
) -> tuple[int, int]:
    root = Resolution(
        public_id="resolution-certificate-incorrect-release",
        resolution_type=str(CERTIFICATE_RESOLUTION_TYPE),
        definition_version="1.0",
        status=ResolutionStatus.READY_FOR_EXECUTION.value,
        source="user",
        subject_type="certificate",
        subject_id=str(certificate_id),
        requested_by_actor_id="7",
        organization_id="organization-1",
        correlation_id="phase-9-correlation",
        title="Resolver liberación incorrecta",
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
        facts={"certificate_id": certificate_id},
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
        analyzed_by="phase-9",
        analysis_hash="e" * 64,
    )
    session.add(analysis)
    session.flush()
    strategy = ResolutionStrategySelection(
        resolution_id=root.id,
        analysis_id=analysis.id,
        strategy_key="withdraw_client_access",
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
        summary="Retirar acceso futuro sin reescribir la liberación",
        plan_hash=PLAN_HASH,
        created_by_actor_id="7",
        is_active=True,
    )
    session.add(plan)
    session.flush()
    session.add(
        ResolutionPlanStep(
            plan_id=plan.id,
            step_key="withdraw_client_access",
            sequence=1,
            operation_key="certificates.withdraw_incorrect_release",
            owner_module="certificates",
            description="Retirar visibilidad futura",
            input_payload={
                "certificate_id": certificate_id,
                "expected_status": "released_to_client",
                "reason": "Liberación incorrecta confirmada",
            },
            criticality="high",
            is_compensable=True,
            compensation_operation_key=(
                "certificates.restore_incorrect_release_visibility"
            ),
            compensation_payload={
                "certificate_id": certificate_id,
            },
            step_hash="f" * 64,
        )
    )
    simulation = ResolutionSimulation(
        resolution_id=root.id,
        plan_id=plan.id,
        context_snapshot_id=context.id,
        simulation_version=1,
        status="valid",
        is_valid=True,
        simulation_hash=SIMULATION_HASH,
        simulated_at=NOW,
        simulated_by="phase-9",
    )
    session.add(simulation)
    session.flush()
    authorization = ResolutionAuthorizationRequest(
        resolution_id=root.id,
        plan_id=plan.id,
        simulation_id=simulation.id,
        policy_key="certificates.incorrect_release.authorization",
        policy_version="1.0",
        status="approved",
        requested_by_actor_id="7",
        requester_actor_snapshot={},
        requested_at=NOW,
        required_approvals=1,
        authorization_scope={
            "permissions": [
                "certificates.approve",
                "certificates.release",
            ]
        },
        plan_hash=PLAN_HASH,
        simulation_hash=SIMULATION_HASH,
    )
    session.add(authorization)
    session.flush()
    session.add(
        ResolutionAuthorizationDecision(
            authorization_request_id=authorization.id,
            decision="approved",
            approver_actor_id="7",
            approver_actor_type="human",
            approver_function="quality",
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
        result={"certificate_context_unchanged": True},
        revalidated_at=NOW,
        revalidated_by="phase-9",
        validator_version="1.0",
        revalidation_hash=REVALIDATION_HASH,
    )
    session.add(revalidation)
    session.flush()
    root.current_context_snapshot_id = context.id
    root.current_strategy_selection_id = strategy.id
    root.current_plan_id = plan.id
    decision_id = authorize_execution(
        session,
        root=root,
        plan=plan,
        revalidation=revalidation,
    )
    session.commit()
    return root.id, decision_id


def authorize_execution(
    session: Session,
    *,
    root: Resolution,
    plan: ResolutionPlan,
    revalidation: ResolutionRevalidation,
) -> int:
    operation_id = "certificate-resolution-execution-1"
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
        required_permissions=(ComponentKey("resolution.execute"),),
        use_mode=SecurityDecisionUseMode.SINGLE_OPERATION,
        operation_id=operation_id,
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
    decision = ResolutionAuthorizationService(
        evaluator=SecurityPolicyEvaluator(
            (
                IntegralSecurityControlPolicy(),
                PermissionPolicy(),
                OrganizationBoundaryPolicy(),
            )
        ),
        evidence_store=SqlAlchemySecurityEvidenceStore(session),
        resource_verifier=SqlAlchemySecurityResourceVerifier(session),
        clock=AdvancingClock(),
    ).authorize(request)
    assert decision.outcome.value == "allowed"
    session.flush()
    return int(
        session.scalar(select(func.max(ResolutionSecurityDecision.id)))
    )


def test_real_executor_persists_motor_and_certificate_evidence_then_replays(
    factory,
):
    with factory() as session, session.begin():
        certificate_id = seed_certificate(session).id
    with factory() as session:
        resolution_id, decision_id = seed_ready_resolution(
            session,
            certificate_id=certificate_id,
        )
    integration = build_certificate_resolution_integration(factory)
    executor = ResolutionExecutor(
        store=SqlAlchemyExecutionStore(factory),
        action_runner=ActionRunner(integration.action_handlers),
        engine=ExecutionEngine(),
        state_machine=ResolutionStateMachine(),
        clock=AdvancingClock(),
        identifiers=Identifiers(),
    )
    command = ExecuteResolutionCommand(
        resolution_id=resolution_id,
        idempotency_key="certificate-resolution-execution-1",
        security_decision_id=decision_id,
        actor=actor(),
        lock_owner="phase-9-certificates",
        lock_ttl=timedelta(minutes=5),
    )
    outcome = executor.execute(command)
    replay = executor.execute(command)

    assert outcome.execution_status is ExecutionStatus.COMPLETED
    assert replay.idempotent_replay is True
    assert replay.execution_id == outcome.execution_id
    with factory() as session:
        certificate = session.get(Certificate, certificate_id)
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
        effect = session.scalar(
            select(ResolutionEntityReference).where(
                ResolutionEntityReference.execution_id == execution.id
            )
        )
        operation_count = session.scalar(
            select(func.count(CertificateResolutionOperation.id))
        )
        assert certificate.status == "released_to_client"
        assert certificate.client_visible is False
        assert root.status == ResolutionStatus.COMPLETED.value
        assert step.status == "completed"
        assert step.domain_transaction_reference.startswith(
            "certificate-operation:"
        )
        assert effect.entity_type == "certificate"
        assert effect.entity_id == str(certificate_id)
        assert operation_count == 1
        assert (
            session.scalar(
                select(func.count(ResolutionAuditEvent.id)).where(
                    ResolutionAuditEvent.resolution_id == resolution_id
                )
            )
            >= 3
        )

    compensation_step = CompensationPlanStep(
        sequence=1,
        source_plan_step_id=step.plan_step_id,
        source_step_execution_id=step.id,
        source_step_key="withdraw_client_access",
        operation_key=(
            "certificates.restore_incorrect_release_visibility"
        ),
        owner_module="certificates",
        input_payload={"certificate_id": certificate_id},
        id=1,
    )
    compensation_request = CompensationActionRequest(
        resolution_id=resolution_id,
        source_execution_id=execution.id,
        compensation_execution_id=901,
        compensation_step_execution_id=902,
        compensation_plan_id=903,
        plan_hash="9" * 64,
        step=compensation_step,
        idempotency_key="certificate-resolution-compensation-1",
        actor_id="7",
        correlation_id="phase-9-correlation",
    )
    runner = CompensationRunner(integration.compensation_handlers)
    compensated = runner.run(compensation_request)
    compensated_replay = runner.run(compensation_request)
    assert compensated.success
    assert compensated_replay.success
    with factory() as session:
        certificate = session.get(Certificate, certificate_id)
        assert certificate.status == "released_to_client"
        assert certificate.client_visible is True
        assert (
            session.scalar(
                select(func.count(CertificateResolutionOperation.id))
            )
            == 2
        )


def imported_modules(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return tuple(modules)


def test_integration_layers_and_core_dependencies_remain_separated():
    package = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "resolution_integrations"
        / "certificates"
    )
    forbidden = (
        "sqlalchemy",
        "fastapi",
        "app.models",
        "app.routers",
        "app.services",
    )
    violations = []
    for name in ("domain.py", "contracts.py", "application.py"):
        path = package / name
        for module in imported_modules(path):
            if module.startswith(forbidden):
                violations.append(f"{name} -> {module}")
    assert violations == []

    core = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "resolution_engine"
    )
    assert all(
        "app.resolution_integrations" not in path.read_text(
            encoding="utf-8"
        )
        for path in core.rglob("*.py")
    )
    infrastructure = (package / "infrastructure.py").read_text(
        encoding="utf-8"
    )
    assert "app.routers" not in infrastructure
    assert "fastapi" not in infrastructure


def test_phase_9_migration_is_linear_reversible_and_append_only():
    source = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "versions"
        / "f9c1d3e5a7b9_phase_9_certificates_integration.py"
    ).read_text(encoding="utf-8")
    assert 'down_revision: str | None = "f8a0b2c4d6e8"' in source
    assert "certificate_resolution_operations" in source
    assert "uq_certificate_resolution_operations_idempotency" in source
    assert "trg_certificate_resolution_operations_immutable" in source
    assert "DROP TRIGGER IF EXISTS" in source
