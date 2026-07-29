from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.catalog_item import CatalogItem
from app.models.certificate import Certificate
from app.models.client import Client
from app.models.equipment import Equipment
from app.models.service_order import ServiceOrder, ServiceOrderItem, ServiceWorkOrder
from app.models.user import Role, User
from app.resolution_center.definitions import build_resolution_center_registry
from app.resolution_center.schemas import (
    AuthorizationRequest,
    CreateAdministrativeResolutionRequest,
)
from app.resolution_center.worker import decode_execution_command
from app.resolution_center.workflow import ResolutionCenterWorkflowService
from app.resolution_engine.application.action_runner import ActionRunner
from app.resolution_engine.application.distribution import (
    DistributedWorker,
    ResolutionExecutionWorkHandler,
)
from app.resolution_engine.application.execution import ResolutionExecutor
from app.resolution_engine.application.orchestration import ResolutionOrchestrator
from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.contracts.distribution import WorkerRegistration
from app.resolution_engine.domain.execution import ExecutionEngine
from app.resolution_engine.domain.lifecycle import ResolutionStateMachine
from app.resolution_engine.infrastructure.distribution import (
    SqlAlchemyDistributedWorkStore,
)
from app.resolution_engine.infrastructure.execution import SqlAlchemyExecutionStore
from app.resolution_engine.infrastructure.persistence import Resolution, ResolutionWorkItem
from app.resolution_engine.infrastructure.runtime import (
    SystemClock,
    UuidIdentifierFactory,
)
from app.resolution_engine.domain.enums import AnalysisStatus, SimulationStatus
from app.resolution_integrations.additional_equipment.application import (
    ADDITIONAL_EQUIPMENT_RESOLUTION_TYPE,
)
from app.resolution_integrations.additional_equipment.domain import (
    AdditionalEquipmentFacts,
    AdditionalEquipmentResolutionRequest,
)
from app.resolution_integrations.additional_equipment.infrastructure import (
    AdditionalEquipmentComponentResolver,
    SqlAlchemyAdditionalEquipmentCommandService,
)
from app.resolution_integrations.additional_equipment.application import (
    AdditionalEquipmentResolutionIntegration,
    build_additional_equipment_resolution_definition,
)
from app.services.additional_equipment_resolutions import (
    AdditionalEquipmentProposal,
    request_additional_equipment_resolution,
)


ROOT = Path(__file__).resolve().parents[3]


class Facts:
    def __init__(self, facts: AdditionalEquipmentFacts) -> None:
        self.facts = facts

    def read(self, _request):
        return self.facts


def request(**changes) -> AdditionalEquipmentResolutionRequest:
    values = {
        "service_order_id": 41,
        "reconciliation_id": "offline-device-41-001",
        "name": "Termómetro patrón",
        "calibration_scope": "traceable",
        "catalog_item_id": 8,
        "quantity": 1,
        "serial_number": "SER-001",
        "source": "mobile_app",
        "requested_at": "2026-07-29T10:00:00-06:00",
    }
    values.update(changes)
    return AdditionalEquipmentResolutionRequest(**values)


def facts(**changes) -> AdditionalEquipmentFacts:
    values = {
        "service_order_id": 41,
        "service_order_folio": "OSMYC-26-07-0041",
        "service_order_status": "in_progress",
        "service_order_active": True,
        "technician_id": 9,
        "client_id": 3,
        "quotation_id": 5,
        "signature_status": "pending",
        "signatures_confirmed": False,
        "active_work_orders": (
            {
                "id": 2,
                "work_order_number": 101,
                "sequence": 1,
                "status": "in_progress",
                "equipment_count": 9,
                "equipment_limit": 10,
                "available_slots": 1,
            },
        ),
        "catalog_exists": True,
        "catalog_active": True,
        "catalog_name": "Calibración de termómetro",
        "scope_allowed": True,
        "service_order_item_id": 6,
        "commercial_adjustment_required": False,
        "duplicate_equipment_id": None,
        "duplicate_reconciliation": False,
        "invoice_statuses": (),
        "late_stage": False,
        "updated_at": "2026-07-29T16:00:00+00:00",
    }
    values.update(changes)
    return AdditionalEquipmentFacts(**values)


def integration(current_facts: AdditionalEquipmentFacts):
    definition = build_additional_equipment_resolution_definition()
    return AdditionalEquipmentResolutionIntegration(
        definition=definition,
        component_resolver=AdditionalEquipmentComponentResolver(
            facts=Facts(current_facts)
        ),
        action_handlers=(),
        compensation_handlers=(),
    )


def orchestrate(current_facts: AdditionalEquipmentFacts):
    installed = integration(current_facts)
    registry = ResolutionRegistry()
    installed.register(registry)
    orchestrator = ResolutionOrchestrator(
        registry=registry,
        components=installed.component_resolver,
    )
    context = orchestrator.build_context(
        resolution_type=str(ADDITIONAL_EQUIPMENT_RESOLUTION_TYPE),
        definition_version="1.0",
        request=request(),
    )
    analysis = orchestrator.analyze(
        resolution_type=str(ADDITIONAL_EQUIPMENT_RESOLUTION_TYPE),
        definition_version="1.0",
        context=context,
    )
    strategy, plan = orchestrator.build_plan(
        resolution_type=str(ADDITIONAL_EQUIPMENT_RESOLUTION_TYPE),
        definition_version="1.0",
        context=context,
        analysis=analysis,
    )
    simulation = orchestrator.simulate(
        resolution_type=str(ADDITIONAL_EQUIPMENT_RESOLUTION_TYPE),
        definition_version="1.0",
        context=context,
        plan=plan,
    )
    return orchestrator, context, analysis, strategy, plan, simulation


def test_installed_composition_publishes_both_verticals_without_domain_branches():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    factory = sessionmaker(bind=engine)
    registry = ResolutionRegistry()
    center, integrations = build_resolution_center_registry(
        factory,
        engine_registry=registry,
    )

    assert [entry.key for entry in center.list()] == [
        ("certificate.resolve_incorrect_release", "1.0"),
        ("service_order.resolve_additional_equipment", "1.0"),
    ]
    assert len(integrations) == 2
    additional = center.resolve(
        "service_order.resolve_additional_equipment",
        "1.0",
    )
    assert additional.presentation.parameter_schema["additionalProperties"] is False
    assert additional.presentation.supports_simulation is True
    assert additional.presentation.supports_compensation is True
    public_source = (
        ROOT / "backend/app/resolution_public_api/application.py"
    ).read_text()
    assert "build_installed_resolution_integrations" in public_source
    assert "build_certificate_resolution_integration" not in public_source
    frontend_source = (
        ROOT / "frontend/src/pages/ResolutionCenterPage.jsx"
    ).read_text()
    assert "service_order.resolve_additional_equipment" not in frontend_source


def test_pure_vertical_analysis_plan_simulation_authorization_and_revalidation():
    orchestrator, context, analysis, strategy, plan, simulation = orchestrate(
        facts()
    )
    requirements = orchestrator.authorization_requirements(
        resolution_type=str(ADDITIONAL_EQUIPMENT_RESOLUTION_TYPE),
        definition_version="1.0",
        context=context,
        plan=plan,
        simulation=simulation,
    )
    revalidation = orchestrator.revalidate(
        resolution_type=str(ADDITIONAL_EQUIPMENT_RESOLUTION_TYPE),
        definition_version="1.0",
        authorized_context=context,
        current_context=context,
        plan=plan,
        simulation=simulation,
    )

    assert analysis.status is AnalysisStatus.RESOLVABLE
    assert analysis.reason_codes == ("requires_authorization",)
    assert strategy.key.value == "attach_existing_work_order"
    assert plan.steps[0].operation_key == (
        "service_orders.register_additional_equipment"
    )
    assert plan.steps[0].compensation_operation_key == (
        "service_orders.compensate_additional_equipment"
    )
    assert simulation.status is SimulationStatus.VALID
    assert (
        "certificate:provisional_reference_only_until_execution"
        in simulation.impacts
    )
    assert requirements.required_permissions == (
        "service_orders.additional_equipment.authorize",
    )
    assert revalidation.is_valid


def test_analysis_outcomes_are_explicit_and_deterministic():
    cases = (
        (
            facts(
                service_order_status="missing",
                service_order_active=False,
                catalog_exists=False,
                catalog_active=False,
            ),
            AnalysisStatus.BLOCKED,
            "blocked_service_state",
        ),
        (
            facts(service_order_status="cancelled"),
            AnalysisStatus.BLOCKED,
            "blocked_service_state",
        ),
        (
            facts(service_order_status="closed"),
            AnalysisStatus.BLOCKED,
            "blocked_service_state",
        ),
        (
            facts(catalog_exists=False, catalog_active=False),
            AnalysisStatus.REQUIRES_INFORMATION,
            "missing_catalog",
        ),
        (
            facts(scope_allowed=False),
            AnalysisStatus.BLOCKED,
            "invalid_classification",
        ),
        (
            facts(duplicate_equipment_id=77),
            AnalysisStatus.ALREADY_RESOLVED,
            "duplicate_equipment",
        ),
        (
            facts(duplicate_reconciliation=True),
            AnalysisStatus.ALREADY_RESOLVED,
            "already_resolved",
        ),
    )
    for current, expected_status, reason in cases:
        _, _, analysis, _, plan, simulation = orchestrate(current)
        assert analysis.status is expected_status
        assert reason in analysis.reason_codes
        assert plan.steps == ()
        assert simulation.status is SimulationStatus.BLOCKED

    _, _, analysis, strategy, _, simulation = orchestrate(
        facts(
            signatures_confirmed=True,
            commercial_adjustment_required=True,
            invoice_statuses=("draft",),
            late_stage=True,
        )
    )
    assert {
        "requires_signature",
        "requires_commercial_adjustment",
        "requires_manual_review",
    }.issubset(analysis.reason_codes)
    assert strategy.key.value == "pending_signature"
    assert simulation.status is SimulationStatus.VALID_WITH_WARNINGS
    assert "invoice:commercial_review_required" in simulation.impacts


def test_revalidation_detects_critical_drift():
    orchestrator, context, analysis, _, plan, simulation = orchestrate(facts())
    changed_context = replace(
        context,
        facts=replace(context.facts, service_order_status="quality_review"),
    )
    result = orchestrator.revalidate(
        resolution_type=str(ADDITIONAL_EQUIPMENT_RESOLUTION_TYPE),
        definition_version="1.0",
        authorized_context=context,
        current_context=changed_context,
        plan=plan,
        simulation=simulation,
    )
    assert analysis.is_resolvable
    assert result.is_valid is False
    assert result.reason_codes == ("critical_service_order_facts_changed",)


def _factory(path: Path, *, serialized_writes: bool = False):
    engine = create_engine(
        f"sqlite+pysqlite:///{path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def configure(connection, _):
        connection.isolation_level = None
        connection.execute("PRAGMA journal_mode=WAL")

    if serialized_writes:
        @event.listens_for(engine, "begin")
        def begin_immediate(connection):
            connection.exec_driver_sql("BEGIN IMMEDIATE")

    tables = [
        table
        for name, table in Base.metadata.tables.items()
        if not name.startswith(("activity_", "notification"))
    ]
    Base.metadata.create_all(engine, tables=tables)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed(factory):
    with factory() as session, session.begin():
        client = Client(legal_name="Laboratorio de prueba")
        catalog = CatalogItem(
            item_type="service",
            service_kind="simple",
            commodity="calibration",
            category="Calibracion",
            name="Calibración de termómetro",
            origin_price=Decimal("100"),
            origin_currency="MXN",
            exchange_rate=Decimal("1"),
            margin_percent=Decimal("0"),
            final_price_mxn=Decimal("100"),
            calibration_scope="traceable",
            tax_object="iva_16",
            tax_rate=Decimal("16"),
        )
        session.add_all((client, catalog))
        session.flush()
        service_order = ServiceOrder(
            folio="OSMYC-26-07-0001",
            work_order_number=100,
            client_id=client.id,
            status="in_progress",
            signature_status="pending",
        )
        session.add(service_order)
        session.flush()
        item = ServiceOrderItem(
            service_order_id=service_order.id,
            catalog_item_id=catalog.id,
            service_name=catalog.name,
            calibration_scope="traceable",
            quantity=1,
            status="pending",
        )
        work_order = ServiceWorkOrder(
            service_order_id=service_order.id,
            work_order_number=101,
            sequence=1,
            status="in_progress",
            equipment_limit=10,
        )
        session.add_all((item, work_order))
        session.flush()
        return service_order.id, catalog.id, item.id, work_order.id


def _command_values(service_order_id, catalog_id, item_id, work_order_id):
    return {
        "resolution_id": 9001,
        "service_order_id": service_order_id,
        "reconciliation_id": "offline-stable-001",
        "request_hash": "a" * 64,
        "expected_service_order_status": "in_progress",
        "catalog_item_id": catalog_id,
        "service_order_item_id": item_id,
        "calibration_scope": "traceable",
        "name": "Termómetro adicional",
        "brand": "MYC",
        "model": "T-1",
        "serial_number": "SER-NEW-1",
        "internal_id": "INT-NEW-1",
        "range_or_capacity": "-20 a 120 °C",
        "notes": "Detectado fuera de línea",
        "preferred_work_order_id": work_order_id,
        "allow_new_work_order": True,
        "requires_signature": False,
        "requires_commercial_adjustment": False,
        "actor_id": "system:phase14",
    }


def test_execution_is_atomic_idempotent_concurrent_and_compensable(tmp_path):
    factory = _factory(
        tmp_path / "phase14.sqlite",
        serialized_writes=True,
    )
    identifiers = _seed(factory)
    commands = SqlAlchemyAdditionalEquipmentCommandService(factory)
    values = _command_values(*identifiers)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: commands.register(**values), range(2)))

    assert {item.equipment_id for item in outcomes} == {
        outcomes[0].equipment_id
    }
    assert outcomes[0].certificate_id is not None
    with factory() as session:
        equipment = list(
            session.scalars(
                select(Equipment).where(
                    Equipment.resolution_reconciliation_id
                    == "offline-stable-001"
                )
            )
        )
        assert len(equipment) == 1
        assert equipment[0].work_order_id == identifiers[3]
        certificate = session.get(Certificate, outcomes[0].certificate_id)
        assert certificate.status == "expected"

    compensated = commands.compensate(
        service_order_id=identifiers[0],
        reconciliation_id="offline-stable-001",
        actor_id="system:phase14",
    )
    assert compensated.after_snapshot["is_active"] is False
    replay = commands.compensate(
        service_order_id=identifiers[0],
        reconciliation_id="offline-stable-001",
        actor_id="system:phase14",
    )
    assert replay.after_snapshot["is_active"] is False
    with factory() as session:
        equipment = session.get(Equipment, outcomes[0].equipment_id)
        certificate = session.get(Certificate, outcomes[0].certificate_id)
        assert equipment.status == "cancelled"
        assert certificate.status == "cancelled"


def test_erp_producer_creates_an_idempotent_proposal_with_domain_permission(
    tmp_path,
):
    factory = _factory(tmp_path / "phase14-producer.sqlite")
    service_order_id, catalog_id, _, _ = _seed(factory)
    with factory() as session, session.begin():
        role = Role(name="Comercial", description="Comercial")
        user = User(
            email="commercial-phase14@example.test",
            full_name="Comercial Fase 14",
            hashed_password="unused",
        )
        user.roles.append(role)
        session.add(user)
        session.flush()
        user_id = user.id

    proposal = AdditionalEquipmentProposal(
        service_order_id=service_order_id,
        reconciliation_id="producer-001",
        catalog_item_id=catalog_id,
        name="Termómetro propuesto",
        calibration_scope="traceable",
    )
    with factory() as session:
        user = session.get(User, user_id)
        first = request_additional_equipment_resolution(
            session,
            proposal,
            user=user,
            idempotency_key="producer-key",
            session_factory=factory,
        )
        replay = request_additional_equipment_resolution(
            session,
            proposal,
            user=user,
            idempotency_key="producer-key",
            session_factory=factory,
        )

    assert first.public_id == replay.public_id
    assert first.lifecycle_status == "draft"


def test_full_vertical_finishes_in_canonical_worker_after_request_session_closes(
    tmp_path,
):
    factory = _factory(tmp_path / "phase14-e2e.sqlite")
    service_order_id, catalog_id, _, _ = _seed(factory)
    with factory() as session, session.begin():
        operator_role = Role(name="Operador", description="Operación")
        quality_role = Role(name="Calidad", description="Calidad")
        technical_role = Role(name="Tecnico", description="Técnico")
        operator = User(
            email="operator-phase14@example.test",
            full_name="Operador Fase 14",
            hashed_password="unused",
            roles=[operator_role],
        )
        quality = User(
            email="quality-phase14@example.test",
            full_name="Calidad Fase 14",
            hashed_password="unused",
            roles=[quality_role],
        )
        technical = User(
            email="technical-phase14@example.test",
            full_name="Técnico Fase 14",
            hashed_password="unused",
            roles=[technical_role],
        )
        session.add_all((operator, quality, technical))
        session.flush()
        operator_id = operator.id
        quality_id = quality.id
        technical_id = technical.id

    with factory() as session:
        operator = session.get(User, operator_id)
        quality = session.get(User, quality_id)
        technical = session.get(User, technical_id)
        workflow = ResolutionCenterWorkflowService(
            session,
            organization_id="myc",
            session_factory=factory,
        )
        created = workflow.create(
            CreateAdministrativeResolutionRequest(
                resolution_type=(
                    "service_order.resolve_additional_equipment"
                ),
                definition_version="1.0",
                subject_type="service_order",
                subject_id=str(service_order_id),
                title="Conciliar termómetro adicional",
                reason="Detectado en servicio",
                parameters={
                    "reconciliation_id": "e2e-offline-001",
                    "catalog_item_id": catalog_id,
                    "name": "Termómetro E2E",
                    "calibration_scope": "traceable",
                    "serial_number": "E2E-SERIAL-1",
                    "source": "mobile_app",
                },
            ),
            user=operator,
            idempotency_key="phase14-create",
            correlation_id="phase14-e2e",
        )
        for method in ("prepare_context", "analyze", "build_plan", "simulate"):
            getattr(workflow, method)(
                created.public_id,
                user=operator,
                correlation_id="phase14-e2e",
            )
        workflow.authorize(
            created.public_id,
            AuthorizationRequest(comment="Aprobación técnica"),
            user=quality,
            correlation_id="phase14-e2e",
        )
        workflow.execute(
            created.public_id,
            user=technical,
            idempotency_key="phase14-execute",
            correlation_id="phase14-e2e",
        )

    registry = ResolutionRegistry()
    _, installed = build_resolution_center_registry(
        factory,
        engine_registry=registry,
    )
    executor = ResolutionExecutor(
        store=SqlAlchemyExecutionStore(factory),
        action_runner=ActionRunner(
            tuple(
                handler
                for item in installed
                for handler in item.action_handlers
            )
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
            node_id="phase-14-worker",
            instance_id="phase-14-instance",
        ),
        clock=SystemClock(),
        identifiers=UuidIdentifierFactory(),
    )
    worker.start()
    outcome = worker.run_once()

    assert outcome is not None
    with factory() as session:
        root = session.scalar(
            select(Resolution).where(Resolution.public_id == created.public_id)
        )
        work = session.scalar(
            select(ResolutionWorkItem).where(
                ResolutionWorkItem.resolution_id == root.id
            )
        )
        equipment = session.scalar(
            select(Equipment).where(
                Equipment.resolution_reconciliation_id
                == "e2e-offline-001"
            )
        )
        assert root.status == "completed"
        assert work.status == "succeeded"
        assert equipment is not None
        assert equipment.resolution_id == root.id
