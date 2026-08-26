from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.client import Client
from app.models.quotation import Quotation
from app.models.service_order import ServiceOrder, ServiceWorkOrder
from app.models.user import Role, User
from app.resolution_center.definitions import build_resolution_center_registry
from app.resolution_center.schemas import AuthorizationRequest, CreateAdministrativeResolutionRequest
from app.resolution_center.worker import decode_execution_command
from app.resolution_center.workflow import ResolutionCenterWorkflowService
from app.resolution_engine.application.action_runner import ActionRunner
from app.resolution_engine.application.distribution import DistributedWorker, ResolutionExecutionWorkHandler
from app.resolution_engine.application.execution import ResolutionExecutor
from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.contracts.distribution import WorkerRegistration
from app.resolution_engine.domain.execution import ExecutionEngine
from app.resolution_engine.domain.lifecycle import ResolutionStateMachine
from app.resolution_engine.infrastructure.distribution import SqlAlchemyDistributedWorkStore
from app.resolution_engine.infrastructure.execution import SqlAlchemyExecutionStore
from app.resolution_engine.infrastructure.persistence import Resolution, ResolutionWorkItem
from app.resolution_engine.infrastructure.runtime import SystemClock, UuidIdentifierFactory
from app.resolution_integrations.service_order_administration.domain import ServiceOrderAdministrationRequest
from app.resolution_integrations.service_order_administration.infrastructure import SqlAlchemyAdministrationFactsReader
from app.schemas.service_order import ServiceOrderCreate
from app.services.service_order_administration import execute_service_order_administration
from app.services.service_orders import create_service_order
from fastapi import HTTPException
import pytest


def _factory(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed(factory, *, with_order=True):
    with factory() as session, session.begin():
        actor = User(username="admin-tools", email="admin-tools@example.test", full_name="Admin Tools", hashed_password="unused")
        client = Client(legal_name="Cliente herramientas")
        session.add_all((actor, client))
        session.flush()
        quotation = Quotation(folio="COT-ADMIN-001", client_id=client.id, advisor_id=actor.id, status="accepted")
        session.add(quotation)
        session.flush()
        order = None
        if with_order:
            order = ServiceOrder(folio="OSMYC-26-08-7001", work_order_number=7001, client_id=client.id, quotation_id=quotation.id, advisor_id=actor.id, status="scheduled")
            session.add(order)
            session.flush()
            session.add(ServiceWorkOrder(service_order_id=order.id, work_order_number=7002, sequence=1, status="pending", equipment_limit=10))
            session.flush()
        return actor.id, client.id, quotation.id, order.id if order else None


def _execute(session, *, operation, subject_id, order, actor_id, resolution_id):
    return execute_service_order_administration(
        session,
        operation=operation,
        subject_id=subject_id,
        reason="Corrección institucional comprobada",
        expected_service_order_id=order.id if order else None,
        expected_active_sibling_id=None,
        expected_updated_at=order.updated_at.isoformat() if order and order.updated_at else None,
        resolution_id=resolution_id,
        request_hash=str(resolution_id) * 32,
        actor_id=actor_id,
    )


def test_installed_definitions_expose_explicit_administrative_family(tmp_path):
    factory = _factory(tmp_path / "definitions.sqlite")
    registry, _ = build_resolution_center_registry(factory, engine_registry=ResolutionRegistry())
    tools = [entry for entry in registry.list() if entry.presentation.family == "administrative_tools"]
    assert {str(entry.definition.resolution_type) for entry in tools} == {
        "service_order.restore_soft_deleted",
        "service_order.rebuild_from_accepted_quotation",
        "service_order.void_preserving_history",
    }
    assert {entry.presentation.risk_level for entry in tools} == {"high", "critical"}


def test_void_and_restore_preserve_same_ets_and_work_order_status(tmp_path):
    factory = _factory(tmp_path / "restore.sqlite")
    actor_id, _, _, order_id = _seed(factory)
    with factory() as session, session.begin():
        order = session.get(ServiceOrder, order_id)
        voided = _execute(session, operation="void", subject_id=order.id, order=order, actor_id=actor_id, resolution_id=101)
        assert voided.service_order_id == order_id
        assert order.is_active is False
        assert order.work_orders[0].status == "pending"
    with factory() as session, session.begin():
        order = session.get(ServiceOrder, order_id)
        restored = _execute(session, operation="restore", subject_id=order.id, order=order, actor_id=actor_id, resolution_id=102)
        assert restored.service_order_id == order_id
        assert order.is_active is True
        assert order.work_orders[0].status == "pending"


def test_ordinary_creation_refuses_to_replace_inactive_ets(tmp_path):
    factory = _factory(tmp_path / "guard.sqlite")
    actor_id, client_id, quotation_id, order_id = _seed(factory)
    with factory() as session, session.begin():
        order = session.get(ServiceOrder, order_id)
        _execute(session, operation="void", subject_id=order.id, order=order, actor_id=actor_id, resolution_id=201)
    with factory() as session:
        with pytest.raises(HTTPException) as raised:
            create_service_order(session, ServiceOrderCreate(client_id=client_id, quotation_id=quotation_id), user_id=actor_id)
        assert raised.value.detail["code"] == "inactive_service_order_requires_resolution"


def test_rebuild_is_idempotent_and_only_allowed_when_no_order_exists(tmp_path):
    factory = _factory(tmp_path / "rebuild.sqlite")
    actor_id, _, quotation_id, _ = _seed(factory, with_order=False)
    with factory() as session, session.begin():
        first = _execute(session, operation="rebuild", subject_id=quotation_id, order=None, actor_id=actor_id, resolution_id=301)
        second = _execute(session, operation="rebuild", subject_id=quotation_id, order=None, actor_id=actor_id, resolution_id=301)
        assert first.created is True
        assert second.created is False
        assert first.service_order_id == second.service_order_id
        assert len(tuple(session.scalars(select(ServiceOrder).where(ServiceOrder.quotation_id == quotation_id)))) == 1


def test_precheck_blocks_rebuild_when_inactive_ets_should_be_restored(tmp_path):
    factory = _factory(tmp_path / "precheck.sqlite")
    actor_id, _, quotation_id, order_id = _seed(factory)
    with factory() as session, session.begin():
        order = session.get(ServiceOrder, order_id)
        _execute(session, operation="void", subject_id=order.id, order=order, actor_id=actor_id, resolution_id=401)
    facts = SqlAlchemyAdministrationFactsReader(factory).read(
        ServiceOrderAdministrationRequest("rebuild", quotation_id, "Reconstrucción solicitada")
    )
    assert facts.allowed is False
    assert "inactive_service_order_requires_restore" in facts.blockers


def test_void_runs_end_to_end_through_canonical_worker(tmp_path):
    factory = _factory(tmp_path / "worker.sqlite")
    _, _, _, order_id = _seed(factory)
    with factory() as session, session.begin():
        operator_role = Role(name="Operador")
        quality_role = Role(name="Calidad")
        operator = User(email="phase15-operator@example.test", full_name="Operador", hashed_password="unused", roles=[operator_role])
        quality = User(email="phase15-quality@example.test", full_name="Calidad", hashed_password="unused", roles=[quality_role])
        session.add_all((operator, quality))
        session.flush()
        operator_id, quality_id = operator.id, quality.id

    with factory() as session:
        workflow = ResolutionCenterWorkflowService(session, organization_id="myc", session_factory=factory)
        created = workflow.create(
            CreateAdministrativeResolutionRequest(
                resolution_type="service_order.void_preserving_history",
                definition_version="1.0",
                subject_type="service_order",
                subject_id=str(order_id),
                title="Baja administrativa controlada",
                reason="ETS creado por error comprobado",
                parameters={"reason": "ETS creado por error comprobado"},
            ),
            user=session.get(User, operator_id),
            idempotency_key="phase15-create",
            correlation_id="phase15-e2e",
        )
        for method in ("prepare_context", "analyze", "build_plan", "simulate"):
            getattr(workflow, method)(created.public_id, user=session.get(User, operator_id), correlation_id="phase15-e2e")
        workflow.authorize(created.public_id, AuthorizationRequest(comment="Autorización de Calidad"), user=session.get(User, quality_id), correlation_id="phase15-e2e")
        workflow.execute(created.public_id, user=session.get(User, operator_id), idempotency_key="phase15-execute", correlation_id="phase15-e2e")

    registry = ResolutionRegistry()
    _, installed = build_resolution_center_registry(factory, engine_registry=registry)
    executor = ResolutionExecutor(
        store=SqlAlchemyExecutionStore(factory),
        action_runner=ActionRunner(tuple(handler for item in installed for handler in item.action_handlers)),
        engine=ExecutionEngine(), state_machine=ResolutionStateMachine(),
        clock=SystemClock(), identifiers=UuidIdentifierFactory(),
    )
    worker = DistributedWorker(
        store=SqlAlchemyDistributedWorkStore(factory),
        handlers=(ResolutionExecutionWorkHandler(executor=executor, command_decoder=decode_execution_command),),
        registration=WorkerRegistration(node_id="phase15-worker", instance_id="phase15-instance"),
        clock=SystemClock(), identifiers=UuidIdentifierFactory(),
    )
    worker.start()
    assert worker.run_once() is not None
    with factory() as session:
        order = session.get(ServiceOrder, order_id)
        root = session.scalar(select(Resolution).where(Resolution.public_id == created.public_id))
        work = session.scalar(select(ResolutionWorkItem).where(ResolutionWorkItem.resolution_id == root.id))
        assert root.status == "completed", (work.status, work.last_error_code, work.last_error_message, work.result_payload)
        assert work.status == "succeeded"
        assert order.is_active is False
        assert order.work_orders[0].status == "pending"
