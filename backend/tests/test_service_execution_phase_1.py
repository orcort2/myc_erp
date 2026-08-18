from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base
from app.core.db import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.activity import ActivityMessage
from app.models.catalog_item import CatalogItem
from app.models.client import Client
from app.models.quotation import Quotation, QuotationItem, QuotationItemDecision
from app.models.service_execution import ServiceStage, ServiceTask, TechnicalServiceRequest
from app.models.service_order import ServiceOrder, ServiceOrderItem, ServiceWorkOrder
from app.models.user import Role, User
from app.schemas.activity import ActivityMessageCreate
from app.schemas.service_execution import (
    QuotationItemDecisionCreate,
    ServiceStageCreate,
    ServiceStageUpdate,
    ServiceUnitBatchCreate,
    ServiceUnitCreate,
    TechnicalServiceRequestCreate,
)
from app.services.activity import create_message, get_activity
from app.services.service_execution import (
    add_service_stage,
    create_service_units,
    create_technical_request,
    decide_quotation_item,
    execution_board,
    update_service_stage,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()


@pytest.fixture()
def context(db: Session):
    admin_role = Role(name="Administrador", description="Administrador")
    technical_role = Role(name="Tecnico", description="Técnico")
    commercial_role = Role(name="Comercial", description="Comercial")
    client_role = Role(name="Cliente", description="Cliente")
    db.add_all([admin_role, technical_role, commercial_role, client_role])
    db.flush()
    admin = User(
        username="ets-admin", email="ets-admin@example.test", full_name="Admin ETS",
        hashed_password="unused", role_id=admin_role.id, roles=[admin_role],
    )
    technician = User(
        username="ets-tech", email="ets-tech@example.test", full_name="Técnico ETS",
        hashed_password="unused", role_id=technical_role.id, roles=[technical_role],
    )
    advisor = User(
        username="ets-advisor", email="ets-advisor@example.test", full_name="Asesor ETS",
        hashed_password="unused", role_id=commercial_role.id, roles=[commercial_role],
    )
    outsider = User(
        username="ets-outsider", email="ets-outsider@example.test", full_name="Sin autoridad ETS",
        hashed_password="unused", role_id=client_role.id, roles=[client_role],
    )
    client = Client(legal_name="Cliente ETS evolucionado")
    db.add_all([admin, technician, advisor, outsider, client])
    db.flush()
    general = CatalogItem(
        item_type="service", service_kind="simple", commodity="general_service",
        category="Servicio General", internal_key="SG-001", name="Servicio General",
        origin_price=Decimal("0"), origin_currency="MXN", exchange_rate=Decimal("1"),
        margin_percent=Decimal("0"), final_price_mxn=Decimal("0"),
        tax_object="iva_16", tax_rate=Decimal("16"),
    )
    db.add(general)
    db.flush()
    ets = ServiceOrder(
        folio="OSMYC-26-08-8100", work_order_number=8100, client_id=client.id,
        status="in_progress", requires_payment=True,
    )
    db.add(ets)
    db.flush()
    work_order = ServiceWorkOrder(
        service_order_id=ets.id, work_order_number=8100, sequence=1,
        status="pending", equipment_limit=10,
    )
    item = ServiceOrderItem(
        service_order_id=ets.id, catalog_item_id=general.id,
        service_name="Servicio General", quantity=3, status="pending",
    )
    db.add_all([work_order, item])
    db.commit()
    return {
        "admin": admin, "technician": technician, "advisor": advisor,
        "client": client, "outsider": outsider, "ets": ets, "work_order": work_order,
    }


def _auth_headers(user: User, *, auth_context: str = "internal") -> dict[str, str]:
    token = create_access_token(
        str(user.id), extra_claims={"roles": [role.name for role in user.roles], "auth_context": auth_context}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def api_client(db: Session):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    yield client
    client.close()
    app.dependency_overrides.pop(get_db, None)


def _three_units(db: Session, context):
    return create_service_units(
        db,
        context["ets"].id,
        ServiceUnitBatchCreate(
            units=[
                ServiceUnitCreate(
                    work_order_id=context["work_order"].id,
                    name=f"Equipo {letter}", brand=brand, model=None,
                    serial_number=serial,
                    identification_notes="Modelo no disponible físicamente",
                    initial_stages=[ServiceStageCreate(category="diagnosis")],
                )
                for letter, brand, serial in (
                    ("A", "Marca A", "SER-A"),
                    ("B", "Marca B", "SER-B"),
                    ("C", None, None),
                )
            ]
        ),
        user_id=context["technician"].id,
    )


def _derived_item(db: Session, context, unit, request, *, folio: str, name: str):
    quotation = Quotation(
        folio=folio, client_id=context["client"].id,
        advisor_id=context["advisor"].id, status="waiting",
        subtotal=Decimal("100"), tax_total=Decimal("16"), total=Decimal("116"),
    )
    db.add(quotation)
    db.flush()
    item = QuotationItem(
        quotation_id=quotation.id, service_name=name, quantity=1,
        unit_price=Decimal("100"), discount_percent=Decimal("0"),
        tax_rate=Decimal("16"), tax_total=Decimal("16"), total=Decimal("100"),
        source_service_order_id=context["ets"].id,
        source_service_unit_id=unit.id,
        source_stage_id=request.source_stage_id,
        technical_request_id=request.id,
        equipment_snapshot={
            "brand": unit.brand, "model": unit.model, "serial_number": unit.serial_number,
        },
    )
    db.add(item)
    db.commit()
    return quotation, item


def test_scenarios_b_c_d_g_h_multiple_evolved_traceability(db: Session, context):
    units = _three_units(db, context)

    assert len(units) == 3
    assert {unit.serial_number for unit in units} == {"SER-A", "SER-B", None}
    assert all(unit.work_order_id == context["work_order"].id for unit in units)
    assert all([stage.category for stage in unit.stages] == ["diagnosis"] for unit in units)
    assert units[2].identification_status == "partial"

    requested = (("repair",), ("calibration",), ("repair", "calibration"))
    created_stage_ids = []
    for index, (unit, categories) in enumerate(zip(units, requested), start=1):
        source_stage = unit.stages[0]
        request = create_technical_request(
            db,
            source_stage.id,
            TechnicalServiceRequestCreate(
                summary=f"Cotizar {' y '.join(categories)}",
                requested_categories=list(categories),
            ),
            user_id=context["technician"].id,
        )
        quotation, item = _derived_item(
            db, context, unit, request, folio=f"MYC-08-26-81{index:02d}", name=" + ".join(categories)
        )
        decision, stage_ids = decide_quotation_item(
            db,
            quotation.id,
            item.id,
            QuotationItemDecisionCreate(
                decision="approved", enabled_stage_categories=list(categories)
            ),
            user_id=context["advisor"].id,
        )
        assert decision.decision == "approved"
        created_stage_ids.extend(stage_ids)

    board = execution_board(db, context["ets"].id)
    assert board["categories"] == ["calibration", "diagnosis", "repair"]
    routes = [[stage.category for stage in unit.stages] for unit in board["units"]]
    assert routes == [
        ["diagnosis", "repair"],
        ["diagnosis", "calibration"],
        ["diagnosis", "repair", "calibration"],
    ]
    assert all(unit.work_order_id == context["work_order"].id for unit in board["units"])
    assert len(created_stage_ids) == 4

    stage_c = board["units"][2].stages[0]
    message = create_message(
        db,
        "service_stage",
        stage_c.id,
        ActivityMessageCreate(
            body="@asesor #tarea Preparar cotización derivada",
            mentioned_user_ids=[context["advisor"].id],
        ),
        context["technician"],
    )
    task = db.scalar(select(ServiceTask).where(ServiceTask.source_message_id == message.id))
    assert task.service_order_id == context["ets"].id
    assert task.service_unit_id == board["units"][2].id
    assert task.service_stage_id == stage_c.id
    assert [assignment.user_id for assignment in task.assignees] == [context["advisor"].id]
    assert get_activity(db, "service_stage", stage_c.id, context["technician"])["entity"]["entity_id"] == stage_c.id

    last_stage = db.get(ServiceStage, created_stage_ids[-1])
    decision = db.get(QuotationItemDecision, last_stage.commercial_decision_id)
    commercial_item = db.get(QuotationItem, decision.quotation_item_id)
    technical_request = db.get(TechnicalServiceRequest, commercial_item.technical_request_id)
    assert technical_request.source_stage_id == last_stage.source_stage_id
    assert commercial_item.source_service_unit_id == last_stage.service_unit_id


def test_scenarios_e_f_partial_rejection_and_execution_gate(db: Session, context):
    unit = _three_units(db, context)[0]
    diagnosis = unit.stages[0]
    request = create_technical_request(
        db,
        diagnosis.id,
        TechnicalServiceRequestCreate(
            summary="Reparación y calibración", requested_categories=["repair", "calibration"]
        ),
        user_id=context["technician"].id,
    )
    repair_quote, repair_item = _derived_item(
        db, context, unit, request, folio="MYC-08-26-8201", name="Reparación"
    )
    calibration_quote, calibration_item = _derived_item(
        db, context, unit, request, folio="MYC-08-26-8202", name="Calibración"
    )
    _, repair_stage_ids = decide_quotation_item(
        db,
        repair_quote.id,
        repair_item.id,
        QuotationItemDecisionCreate(decision="approved", enabled_stage_categories=["repair"]),
        user_id=context["advisor"].id,
    )
    assert db.get(TechnicalServiceRequest, request.id).status == "partially_approved"
    _, calibration_stage_ids = decide_quotation_item(
        db,
        calibration_quote.id,
        calibration_item.id,
        QuotationItemDecisionCreate(decision="rejected", comment="Cliente no autoriza"),
        user_id=context["advisor"].id,
    )
    assert len(repair_stage_ids) == 1
    assert calibration_stage_ids == []
    assert db.get(TechnicalServiceRequest, request.id).status == "partially_approved"
    assert db.get(ServiceStage, repair_stage_ids[0]).category == "repair"
    running = update_service_stage(
        db,
        repair_stage_ids[0],
        ServiceStageUpdate(status="in_progress"),
        user_id=context["technician"].id,
    )
    completed = update_service_stage(
        db,
        running.id,
        ServiceStageUpdate(status="completed", result={"outcome": "repaired"}),
        user_id=context["technician"].id,
    )
    assert completed.completed_at is not None
    assert completed.result == {"outcome": "repaired"}
    assert db.scalar(select(ServiceStage).where(
        ServiceStage.service_unit_id == unit.id,
        ServiceStage.category == "calibration",
    )) is None

    paused = add_service_stage(
        db,
        unit.id,
        ServiceStageCreate(
            category="maintenance", origin="technical_request",
            source_stage_id=diagnosis.id, status="pending_approval",
        ),
        user_id=context["technician"].id,
    )
    assert paused.status == "pending_approval"
    with pytest.raises(HTTPException) as blocked:
        add_service_stage(
            db,
            unit.id,
            ServiceStageCreate(
                category="maintenance", origin="technical_request",
                source_stage_id=diagnosis.id, status="in_progress",
            ),
            user_id=context["technician"].id,
        )
    assert blocked.value.status_code == 409


def test_scenario_a_legacy_calibration_contract_remains_registered():
    assert "registered" in __import__("app.services.equipment", fromlist=["ALLOWED_TRANSITIONS"]).ALLOWED_TRANSITIONS
    assert "calibration" in {item for item in __import__(
        "app.models.service_execution", fromlist=["SERVICE_STAGE_CATEGORIES"]
    ).SERVICE_STAGE_CATEGORIES}


def test_initial_multiple_quote_decisions_can_seed_authorized_unit_stages(db: Session, context):
    quotation = Quotation(
        folio="MYC-08-26-8301", client_id=context["client"].id,
        advisor_id=context["advisor"].id, status="waiting",
        subtotal=Decimal("200"), tax_total=Decimal("32"), total=Decimal("232"),
    )
    db.add(quotation)
    db.flush()
    items = []
    for category in ("maintenance", "calibration"):
        item = QuotationItem(
            quotation_id=quotation.id, service_name=category,
            operational_category=category, quantity=1,
            unit_price=Decimal("100"), discount_percent=Decimal("0"),
            tax_rate=Decimal("16"), tax_total=Decimal("16"), total=Decimal("100"),
        )
        db.add(item)
        db.flush()
        decide_quotation_item(
            db,
            quotation.id,
            item.id,
            QuotationItemDecisionCreate(
                decision="approved", enabled_stage_categories=[category]
            ),
            user_id=context["advisor"].id,
        )
        items.append(item)

    # Este ETS no es Servicio General: representa el nacimiento múltiple desde
    # categorías ya aprobadas, sin convertir una etapa en otra.
    general_item = db.scalar(select(ServiceOrderItem).where(
        ServiceOrderItem.service_order_id == context["ets"].id
    ))
    general_item.service_name = "Servicio múltiple aprobado"
    general_item.catalog_item_id = None
    db.commit()
    units = create_service_units(
        db,
        context["ets"].id,
        ServiceUnitBatchCreate(units=[
            ServiceUnitCreate(
                work_order_id=context["work_order"].id,
                name="Equipo múltiple",
                initial_stages=[
                    ServiceStageCreate(
                        category="maintenance", status="authorized",
                        quotation_item_id=items[0].id,
                    ),
                    ServiceStageCreate(
                        category="calibration", status="authorized",
                        quotation_item_id=items[1].id,
                    ),
                ],
            )
        ]),
        user_id=context["technician"].id,
    )
    assert [stage.category for stage in units[0].stages] == ["maintenance", "calibration"]
    assert all(stage.commercial_decision_id is not None for stage in units[0].stages)


def test_execution_board_requires_authentication_and_read_permission(
    api_client: TestClient, context
):
    path = f"/api/service-orders/{context['ets'].id}/execution-board"
    assert api_client.get(path).status_code == 401
    assert api_client.get(path, headers=_auth_headers(context["outsider"])).status_code == 403
    allowed = api_client.get(path, headers=_auth_headers(context["advisor"]))
    assert allowed.status_code == 200
    assert allowed.json()["service_order_id"] == context["ets"].id


def test_item_decision_derives_internal_actor_and_rejects_unauthorized_contexts(
    db: Session, api_client: TestClient, context
):
    quotation = Quotation(
        folio="MYC-08-26-8401", client_id=context["client"].id,
        advisor_id=context["advisor"].id, status="waiting",
        subtotal=Decimal("100"), tax_total=Decimal("16"), total=Decimal("116"),
    )
    db.add(quotation)
    db.flush()
    item = QuotationItem(
        quotation_id=quotation.id, service_name="Reparación",
        operational_category="repair", quantity=1,
        unit_price=Decimal("100"), discount_percent=Decimal("0"),
        tax_rate=Decimal("16"), tax_total=Decimal("16"), total=Decimal("100"),
    )
    db.add(item)
    db.commit()
    path = f"/api/quotations/{quotation.id}/items/{item.id}/decision"
    payload = {"decision": "approved", "enabled_stage_categories": ["repair"]}

    assert api_client.post(path, json=payload).status_code == 401
    assert api_client.post(
        path, json=payload, headers=_auth_headers(context["technician"])
    ).status_code == 403
    assert api_client.post(
        path,
        json=payload,
        headers=_auth_headers(context["outsider"], auth_context="portal"),
    ).status_code == 401
    spoofed = api_client.post(
        path,
        json={**payload, "source": "client_portal"},
        headers=_auth_headers(context["advisor"]),
    )
    assert spoofed.status_code == 422

    allowed = api_client.post(
        path, json=payload, headers=_auth_headers(context["advisor"])
    )
    assert allowed.status_code == 201
    assert allowed.json()["source"] == "internal"
    assert allowed.json()["decided_by_id"] == context["advisor"].id


def test_mixed_service_order_scopes_evolution_to_general_service_unit(db: Session, context):
    general_item = db.scalar(select(ServiceOrderItem).where(
        ServiceOrderItem.service_order_id == context["ets"].id
    ))
    calibration_catalog = CatalogItem(
        item_type="service", service_kind="simple", commodity="calibration",
        category="Calibracion", internal_key="CAL-8401", name="Calibración",
        origin_price=Decimal("0"), origin_currency="MXN", exchange_rate=Decimal("1"),
        margin_percent=Decimal("0"), final_price_mxn=Decimal("0"),
        tax_object="iva_16", tax_rate=Decimal("16"),
    )
    maintenance_catalog = CatalogItem(
        item_type="service", service_kind="simple", commodity="maintenance",
        category="Mantenimiento", internal_key="MAN-8401", name="Mantenimiento",
        origin_price=Decimal("0"), origin_currency="MXN", exchange_rate=Decimal("1"),
        margin_percent=Decimal("0"), final_price_mxn=Decimal("0"),
        tax_object="iva_16", tax_rate=Decimal("16"),
    )
    db.add_all([calibration_catalog, maintenance_catalog])
    db.flush()
    calibration_item = ServiceOrderItem(
        service_order_id=context["ets"].id, catalog_item_id=calibration_catalog.id,
        service_name="Calibración", quantity=1, status="pending",
    )
    maintenance_item = ServiceOrderItem(
        service_order_id=context["ets"].id, catalog_item_id=maintenance_catalog.id,
        service_name="Mantenimiento", quantity=1, status="pending",
    )
    db.add_all([calibration_item, maintenance_item])
    db.commit()

    units = create_service_units(
        db, context["ets"].id,
        ServiceUnitBatchCreate(units=[
            ServiceUnitCreate(
                work_order_id=context["work_order"].id,
                origin_service_order_item_id=general_item.id,
                name="Equipo A",
                initial_stages=[ServiceStageCreate(category="diagnosis")],
            ),
            ServiceUnitCreate(
                work_order_id=context["work_order"].id,
                origin_service_order_item_id=calibration_item.id,
                name="Equipo B",
                initial_stages=[ServiceStageCreate(category="calibration")],
            ),
            ServiceUnitCreate(
                work_order_id=context["work_order"].id,
                origin_service_order_item_id=maintenance_item.id,
                name="Equipo C",
                initial_stages=[ServiceStageCreate(category="maintenance")],
            ),
        ]),
        user_id=context["technician"].id,
    )
    assert [(unit.initial_category, unit.evolution_enabled) for unit in units] == [
        ("general_service", True), ("calibration", False), ("maintenance", False)
    ]
    create_technical_request(
        db, units[0].stages[0].id,
        TechnicalServiceRequestCreate(summary="Requiere reparación", requested_categories=["repair"]),
        user_id=context["technician"].id,
    )
    for unit in units[1:]:
        with pytest.raises(HTTPException) as blocked:
            create_technical_request(
                db, unit.stages[0].id,
                TechnicalServiceRequestCreate(summary="Evolución indebida", requested_categories=["repair"]),
                user_id=context["technician"].id,
            )
        assert blocked.value.status_code == 409


def test_technical_request_preserves_stage_lifecycle_and_later_stage_can_evolve(db: Session, context):
    unit = _three_units(db, context)[0]
    diagnosis = update_service_stage(
        db, unit.stages[0].id, ServiceStageUpdate(status="in_progress"),
        user_id=context["technician"].id,
    )
    request = create_technical_request(
        db, diagnosis.id,
        TechnicalServiceRequestCreate(summary="Cotizar reparación", requested_categories=["repair"]),
        user_id=context["technician"].id,
    )
    assert db.get(ServiceStage, diagnosis.id).status == "in_progress"
    quotation, item = _derived_item(
        db, context, unit, request, folio="MYC-08-26-8501", name="Reparación"
    )
    _, stage_ids = decide_quotation_item(
        db, quotation.id, item.id,
        QuotationItemDecisionCreate(decision="approved", enabled_stage_categories=["repair"]),
        user_id=context["advisor"].id,
    )
    repair = update_service_stage(
        db, stage_ids[0], ServiceStageUpdate(status="in_progress"),
        user_id=context["technician"].id,
    )
    later = create_technical_request(
        db, repair.id,
        TechnicalServiceRequestCreate(summary="Hallazgo posterior", requested_categories=["calibration"]),
        user_id=context["technician"].id,
    )
    assert later.source_stage_id == repair.id
    assert db.get(ServiceStage, repair.id).status == "in_progress"
    completed = update_service_stage(
        db, repair.id, ServiceStageUpdate(status="completed"),
        user_id=context["technician"].id,
    )
    with pytest.raises(HTTPException) as blocked:
        update_service_stage(
            db, completed.id, ServiceStageUpdate(status="in_progress"),
            user_id=context["technician"].id,
        )
    assert blocked.value.status_code == 409


def test_approved_categories_must_match_request_and_quotation_item(db: Session, context):
    unit = _three_units(db, context)[0]
    request = create_technical_request(
        db, unit.stages[0].id,
        TechnicalServiceRequestCreate(summary="Solicita reparación", requested_categories=["repair"]),
        user_id=context["technician"].id,
    )
    quotation, item = _derived_item(
        db, context, unit, request, folio="MYC-08-26-8601", name="Mantenimiento"
    )
    item.operational_category = "maintenance"
    db.commit()
    with pytest.raises(HTTPException) as mismatched_item:
        decide_quotation_item(
            db, quotation.id, item.id,
            QuotationItemDecisionCreate(decision="approved", enabled_stage_categories=["repair"]),
            user_id=context["advisor"].id,
        )
    assert mismatched_item.value.status_code == 422
    item.service_name = "Reparación"
    item.operational_category = "repair"
    db.commit()
    with pytest.raises(HTTPException) as unrequested:
        decide_quotation_item(
            db, quotation.id, item.id,
            QuotationItemDecisionCreate(decision="approved", enabled_stage_categories=["maintenance"]),
            user_id=context["advisor"].id,
        )
    assert unrequested.value.status_code == 422


def test_database_constraint_prevents_two_initial_item_decisions(db: Session, context):
    quotation = Quotation(
        folio="MYC-08-26-8701", client_id=context["client"].id,
        advisor_id=context["advisor"].id, status="waiting",
        subtotal=Decimal("100"), tax_total=Decimal("16"), total=Decimal("116"),
    )
    db.add(quotation)
    db.flush()
    item = QuotationItem(
        quotation_id=quotation.id, service_name="Calibración", quantity=1,
        unit_price=Decimal("100"), discount_percent=Decimal("0"),
        tax_rate=Decimal("16"), tax_total=Decimal("16"), total=Decimal("100"),
    )
    db.add(item)
    db.flush()
    first = QuotationItemDecision(
        quotation_item_id=item.id, decision="approved", decided_by_id=context["advisor"].id,
        decided_at=quotation.created_at, source="internal", enabled_stage_categories=["calibration"],
    )
    db.add(first)
    db.flush()
    db.add(QuotationItemDecision(
        quotation_item_id=item.id, decision="rejected", decided_by_id=context["advisor"].id,
        decided_at=quotation.created_at, source="internal", enabled_stage_categories=[],
    ))
    with pytest.raises(IntegrityError):
        db.flush()
