from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.catalog_item import CatalogItem
from app.models.client import Client
from app.models.maintenance_execution import MaintenanceExecution
from app.models.quotation import Quotation, QuotationItem, QuotationItemDecision
from app.models.service_execution import ServiceStage, ServiceUnit
from app.models.user import Role, User
from app.schemas.maintenance_execution import (
    MaintenanceCapture,
    MaintenanceChangeCreate,
    MaintenanceChangeResolve,
    MaintenanceEquipmentCreate,
    MaintenanceMaterialCreate,
    MaintenanceBoardRead,
    MaintenancePauseCreate,
    MaintenancePrepare,
    MaintenanceSignature,
)
from app.schemas.service_order import ServiceOrderCreate
from app.services.maintenance_execution import (
    accept_field_visit,
    add_material,
    add_pause,
    close_execution,
    complete_technical,
    generate_report,
    maintenance_board,
    prepare_execution,
    register_arrival,
    register_field_equipment,
    request_change,
    resolve_change,
    resolve_investigation,
    resolve_pause,
    save_capture,
    sign_report,
    start_execution,
)
from app.services.quotations import _build_operational_snapshot
from app.services.service_orders import create_service_order


VALID_SIGNATURE = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@pytest.fixture()
def ctx():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    admin_role = Role(name="Administrador", description="Admin")
    tech_role = Role(name="Tecnico", description="Técnico")
    commercial_role = Role(name="Comercial", description="Comercial")
    db.add_all([admin_role, tech_role, commercial_role]); db.flush()
    admin = User(username="maint-admin", email="maint-admin@example.test", full_name="Admin Mantenimiento", hashed_password="unused", role_id=admin_role.id, roles=[admin_role])
    technician = User(username="maint-tech", email="maint-tech@example.test", full_name="Técnico Mantenimiento", hashed_password="unused", role_id=tech_role.id, roles=[tech_role])
    advisor = User(username="maint-advisor", email="maint-advisor@example.test", full_name="Asesor Mantenimiento", hashed_password="unused", role_id=commercial_role.id, roles=[commercial_role])
    client = Client(legal_name="Cliente Mantenimiento")
    db.add_all([admin, technician, advisor, client]); db.commit()
    yield db, admin, technician, advisor, client
    db.close(); engine.dispose()


def _catalog(db, *, maintenance_type="preventive", location="laboratory", name="Mantenimiento"):
    item = CatalogItem(
        item_type="service", service_kind="simple", commodity="maintenance", category="Mantenimiento",
        operational_category="maintenance", name=name, origin_price=Decimal("100"), origin_currency="MXN",
        exchange_rate=Decimal("1"), margin_percent=Decimal("0"), final_price_mxn=Decimal("100"),
        tax_object="iva_16", tax_rate=Decimal("16"), calibration_scope=maintenance_type, maintenance_type=maintenance_type,
        maintenance_location=location,
        maintenance_base_materials=[{"name": "Sello base", "quantity": 1, "unit": "pieza", "internal_unit_cost": "25"}] if maintenance_type == "corrective" else [],
    )
    db.add(item); db.flush(); return item


def _other_service(db, category):
    labels = {"repair": "Reparacion", "general_service": "Servicio general"}
    item = CatalogItem(
        item_type="service", service_kind="simple", commodity=category, category=labels[category],
        operational_category=category, name=labels[category], origin_price=Decimal("100"),
        origin_currency="MXN", exchange_rate=Decimal("1"), margin_percent=Decimal("0"),
        final_price_mxn=Decimal("100"), tax_object="iva_16", tax_rate=Decimal("16"),
    )
    db.add(item); db.flush(); return item


def _order(db, client, advisor, catalog, *, quantity=1, folio="COT-MANT-1", extra_catalog=None):
    quote = Quotation(folio=folio, client_id=client.id, advisor_id=advisor.id, status="waiting", subtotal=Decimal("100"), tax_total=Decimal("16"), total=Decimal("116"))
    catalogs = [catalog] + ([extra_catalog] if extra_catalog else [])
    quote.items = [QuotationItem(
        catalog_item_id=item.id, service_name=item.name, operational_category=item.operational_category,
        commodity=item.commodity, quantity=quantity if item is catalog else 1, unit_price=Decimal("100"),
        discount_percent=Decimal("0"), tax_rate=Decimal("16"), tax_total=Decimal("16"), total=Decimal("100"),
        operational_snapshot=_build_operational_snapshot(db, item),
    ) for item in catalogs]
    db.add(quote); db.commit()
    return create_service_order(db, ServiceOrderCreate(client_id=client.id, quotation_id=quote.id, advisor_id=advisor.id), user_id=advisor.id)


def _execution(db, order):
    return db.scalar(select(MaintenanceExecution).where(MaintenanceExecution.service_order_id == order.id).order_by(MaintenanceExecution.id))


def _capture(final_condition="operational", *, recommendations=None):
    return MaintenanceCapture(
        initial_condition="operational_with_anomalies", initial_description="Suciedad y ajuste pendiente",
        findings=[{"component": "motor", "description": "Suciedad", "severity": "medium", "classification": "maintenance", "resolution": "corrected"}],
        actions=[{"action": "cleaning", "component": "motor", "result": "corrected"}],
        final_condition=final_condition, functional_result="Prueba funcional documentada",
        technical_conclusion="Intervención concluida según alcance", recommendations=recommendations or [],
        before_photos=["maintenance/before-1.jpg"], after_photos=["maintenance/after-1.jpg"],
    )


def _start_lab(db, order, execution, advisor, technician):
    register_arrival(db, order.id, execution.id, MaintenanceEquipmentCreate(name="Bomba", brand="MYC", model="P1", serial_number="S-1"), actor=advisor)
    prepare_execution(db, order.id, execution.id, MaintenancePrepare(technician_id=technician.id), actor=advisor)
    start_execution(db, order.id, execution.id, actor=technician)


def test_preventive_laboratory_birth_freezes_snapshot_and_materializes_ot_units(ctx):
    db, _, _, advisor, client = ctx
    catalog = _catalog(db)
    order = _order(db, client, advisor, catalog, quantity=2)
    executions = list(db.scalars(select(MaintenanceExecution).where(MaintenanceExecution.service_order_id == order.id)).all())
    assert len(executions) == 2
    assert {item.maintenance_type for item in executions} == {"preventive"}
    assert {item.location_mode for item in executions} == {"laboratory"}
    assert all(item.service_unit.evolution_enabled is False for item in executions)
    assert all(item.service_unit.work_order_id for item in executions)
    catalog.maintenance_type = "corrective"; catalog.maintenance_location = "field"; db.commit()
    board = maintenance_board(db, order.id)
    MaintenanceBoardRead.model_validate(board)
    assert {item["maintenance_type"] for item in board["executions"]} == {"preventive"}
    assert {item["location_mode"] for item in board["executions"]} == {"laboratory"}


def test_corrective_catalog_base_material_is_frozen_without_exposing_cost(ctx):
    db, _, _, advisor, client = ctx
    order = _order(db, client, advisor, _catalog(db, maintenance_type="corrective"))
    execution = _execution(db, order)
    assert execution.materials[0].source == "catalog_snapshot"
    assert execution.materials[0].internal_unit_cost == Decimal("25")
    assert execution.configuration_snapshot["base_materials"][0]["name"] == "Sello base"


def test_field_has_no_arrival_and_requires_equipment_request_acceptance_and_schedule(ctx):
    db, _, technician, advisor, client = ctx
    order = _order(db, client, advisor, _catalog(db, location="field"))
    execution = _execution(db, order)
    assert execution.status == "pending_assignment"
    register_field_equipment(db, order.id, execution.id, MaintenanceEquipmentCreate(name="Báscula", serial_number="F-1"), actor=advisor)
    prepare_execution(db, order.id, execution.id, MaintenancePrepare(technician_id=technician.id, field_address={"street": "Industria 10"}), actor=advisor)
    with pytest.raises(HTTPException):
        start_execution(db, order.id, execution.id, actor=technician)
    scheduled = datetime.now(timezone.utc)
    accept_field_visit(db, order.id, execution.id, scheduled, actor=technician)
    start_execution(db, order.id, execution.id, actor=technician)
    assert _execution(db, order).status == "in_maintenance"
    assert _execution(db, order).scheduled_for.replace(tzinfo=timezone.utc) == scheduled


def test_typed_spare_part_pause_and_second_visit_are_traceable(ctx):
    db, _, technician, advisor, client = ctx

    order = _order(
        db,
        client,
        advisor,
        _catalog(db),
    )

    execution = _execution(db, order)

    _start_lab(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    board = add_pause(
        db,
        order.id,
        execution.id,
        MaintenancePauseCreate(
            pause_type="spare_part",
            reason="Esperando sello",
            responsible_user_id=advisor.id,
        ),
        actor=technician,
    )

    pause = board["executions"][0]["pauses"][0]

    assert (
        board["executions"][0]["status"]
        == "in_maintenance"
    )
    assert (
        board["executions"][0]["has_active_pause"]
        is True
    )
    assert pause.status == "active"
    assert pause.pause_type == "spare_part"

    resolve_pause(
        db,
        order.id,
        execution.id,
        pause.id,
        "Sello recibido",
        actor=technician,
    )

    board = add_pause(
        db,
        order.id,
        execution.id,
        MaintenancePauseCreate(
            pause_type="second_intervention",
            reason="Segunda visita necesaria",
            responsible_user_id=technician.id,
        ),
        actor=technician,
    )

    assert (
        board["executions"][0]["status"]
        == "in_maintenance"
    )

    assert len(
        _execution(db, order).pauses
    ) == 2


def test_preventive_corrective_requires_own_approved_commercial_link(ctx):
    db, admin, technician, advisor, client = ctx
    order = _order(db, client, advisor, _catalog(db))
    execution = _execution(db, order); _start_lab(db, order, execution, advisor, technician)
    request_change(db, order.id, execution.id, MaintenanceChangeCreate(change_type="corrective", summary="Requiere cambio de rodamiento"), actor=technician)
    change = _execution(db, order).changes[0]
    with pytest.raises(HTTPException):
        resolve_change(db, order.id, execution.id, change.id, MaintenanceChangeResolve(decision="approved", reason="Aprobado por cliente", quotation_item_id=order.items[0].quotation_item_id), actor=admin)

    quote = Quotation(folio="COT-CORR-LINK", client_id=client.id, advisor_id=advisor.id, status="approved", subtotal=Decimal("100"), tax_total=Decimal("16"), total=Decimal("116"))
    linked = QuotationItem(quotation=quote, service_name="Correctivo adicional", operational_category="maintenance", commodity="maintenance", quantity=1, unit_price=Decimal("100"), discount_percent=Decimal("0"), tax_rate=Decimal("16"), tax_total=Decimal("16"), total=Decimal("100"), source_service_order_id=order.id, source_service_unit_id=execution.service_unit_id, source_stage_id=execution.service_stage_id, technical_request_id=1)
    db.add(linked); db.flush()
    db.add(QuotationItemDecision(quotation_item_id=linked.id, decision="approved", decided_by_id=admin.id, decided_at=datetime.now(timezone.utc), source="internal", enabled_stage_categories=["maintenance"]))
    db.commit()
    resolve_change(db, order.id, execution.id, change.id, MaintenanceChangeResolve(decision="approved", reason="Cotización aprobada por cliente", quotation_item_id=linked.id), actor=admin)
    assert _execution(db, order).maintenance_type == "corrective"


def test_rejected_corrective_remains_documented_and_does_not_block_preventive_close(ctx):
    db, admin, technician, advisor, client = ctx
    order = _order(db, client, advisor, _catalog(db))
    execution = _execution(db, order); _start_lab(db, order, execution, advisor, technician)
    request_change(db, order.id, execution.id, MaintenanceChangeCreate(change_type="corrective", summary="Se recomienda refacción"), actor=technician)
    change = _execution(db, order).changes[0]
    resolve_change(db, order.id, execution.id, change.id, MaintenanceChangeResolve(decision="rejected", reason="Cliente decide no ampliar alcance"), actor=admin)
    save_capture(db, order.id, execution.id, _capture(recommendations=[{"description": "Cambiar refacción", "decision": "rejected"}]), actor=technician)
    complete_technical(db, order.id, execution.id, actor=technician)
    content, _ = generate_report(db, order.id, execution.id, actor=advisor)
    assert content.startswith(b"%PDF")
    sign_report(db, order.id, execution.id, MaintenanceSignature(signer_name="Cliente", signature_data_url=VALID_SIGNATURE, client_decision="rejected_additional_work"), actor=advisor)
    assert close_execution(db, order.id, execution.id, actor=admin)["executions"][0]["status"] == "closed"


def test_material_used_and_required_are_separate_and_report_has_no_internal_cost(ctx):
    db, _, technician, advisor, client = ctx
    order = _order(db, client, advisor, _catalog(db))
    execution = _execution(db, order); _start_lab(db, order, execution, advisor, technician)
    add_material(db, order.id, execution.id, MaintenanceMaterialCreate(material_type="used", name="Lubricante", quantity=Decimal("0.2"), unit="litro", internal_unit_cost=Decimal("80")), actor=technician)
    add_material(db, order.id, execution.id, MaintenanceMaterialCreate(material_type="required", name="Rodamiento", quantity=1, unit="pieza", internal_unit_cost=Decimal("900"), decision="pending"), actor=technician)
    save_capture(db, order.id, execution.id, _capture(), actor=technician)
    complete_technical(db, order.id, execution.id, actor=technician)
    captured = {}
    class FakeHTML:
        def __init__(self, string): captured["html"] = string
        def write_pdf(self): return b"%PDF fake"
    import app.services.maintenance_execution as service
    original = service.HTML; service.HTML = FakeHTML
    try: generate_report(db, order.id, execution.id, actor=advisor)
    finally: service.HTML = original
    assert "Lubricante" in captured["html"] and "Rodamiento" in captured["html"]
    assert "900" not in captured["html"] and "80" not in captured["html"]
    assert "maintenance/before-1.jpg" in captured["html"] and "maintenance/after-1.jpg" in captured["html"]


def test_repair_is_only_requested_and_never_executed_inside_maintenance(ctx):
    db, admin, technician, advisor, client = ctx
    order = _order(db, client, advisor, _catalog(db))
    execution = _execution(db, order); _start_lab(db, order, execution, advisor, technician)
    request_change(db, order.id, execution.id, MaintenanceChangeCreate(change_type="repair", summary="Reparación fuera de alcance"), actor=technician)
    change = _execution(db, order).changes[0]
    target = _order(db, client, advisor, _other_service(db, "repair"), folio="COT-LINK-REPAIR")
    resolve_change(db, order.id, execution.id, change.id, MaintenanceChangeResolve(decision="linked", reason="ETS separado de reparación", linked_service_order_id=target.id), actor=admin)
    assert all(stage.category != "repair" for stage in db.scalars(select(ServiceStage).where(ServiceStage.service_unit_id == execution.service_unit_id)).all())


def test_inoperable_creates_administrative_block_and_linked_investigation(ctx):
    db, admin, technician, advisor, client = ctx

    order = _order(
        db,
        client,
        advisor,
        _catalog(db),
    )

    execution = _execution(db, order)

    _start_lab(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    save_capture(
        db,
        order.id,
        execution.id,
        _capture("not_operational"),
        actor=technician,
    )

    execution = _execution(db, order)

    # El lifecycle principal no cambia.
    assert execution.status == "in_maintenance"

    # El técnico solamente declara la condición.
    assert (
        execution.investigation_status
        == "required"
    )

    # Todavía no existe una pausa administrativa:
    # el técnico no tiene autoridad para abrirla.
    assert not any(
        item.status == "active"
        and item.pause_type
        == "administrative_investigation"
        for item in execution.pauses
    )

    # La investigación requerida bloquea la
    # terminación técnica.
    with pytest.raises(HTTPException):
        complete_technical(
            db,
            order.id,
            execution.id,
            actor=technician,
        )

    request_change(
        db,
        order.id,
        execution.id,
        MaintenanceChangeCreate(
            change_type="investigation",
            summary="Diagnóstico administrativo",
        ),
        actor=technician,
    )

    change = _execution(
        db,
        order,
    ).changes[-1]

    investigation_order = _order(
        db,
        client,
        advisor,
        _other_service(
            db,
            "general_service",
        ),
        folio="COT-INVESTIGATION",
    )

    resolve_change(
        db,
        order.id,
        execution.id,
        change.id,
        MaintenanceChangeResolve(
            decision="linked",
            reason="Investigación vinculada",
            linked_service_order_id=(
                investigation_order.id
            ),
        ),
        actor=admin,
    )

    execution = _execution(db, order)

    assert (
        execution.status
        == "in_maintenance"
    )

    assert (
        execution.investigation_status
        == "open"
    )

    assert (
        execution.linked_investigation_stage_id
        is not None
    )

    # Ahora sí existe la pausa administrativa,
    # creada dentro de la resolución autorizada.
    assert any(
        item.status == "active"
        and item.pause_type
        == "administrative_investigation"
        for item in execution.pauses
    )

    resolve_investigation(
        db,
        order.id,
        execution.id,
        "Investigación concluida y documentada",
        actor=admin,
    )

    execution = _execution(db, order)

    assert (
        execution.investigation_status
        == "resolved"
    )

    assert not any(
        item.status == "active"
        and item.pause_type
        == "administrative_investigation"
        for item in execution.pauses
    )


def test_maintenance_and_calibration_coexist_as_independent_units(ctx):
    db, _, _, advisor, client = ctx
    maintenance = _catalog(db)
    calibration = CatalogItem(item_type="service", service_kind="simple", commodity="calibration", category="Calibracion", operational_category="calibration", name="Calibración", origin_price=Decimal("50"), origin_currency="MXN", exchange_rate=Decimal("1"), margin_percent=Decimal("0"), final_price_mxn=Decimal("50"), tax_object="iva_16", tax_rate=Decimal("16"), calibration_scope="traceable", service_type="traceable")
    db.add(calibration); db.flush()
    order = _order(db, client, advisor, maintenance, extra_catalog=calibration)
    execution = _execution(db, order)
    assert execution.service_unit.initial_category == "maintenance"
    assert any(item.operational_category == "calibration" for item in order.items)
    assert execution.service_unit.evolution_enabled is False


def test_technical_completion_report_signature_and_close_are_distinct(ctx):
    db, admin, technician, advisor, client = ctx
    order = _order(db, client, advisor, _catalog(db))
    execution = _execution(db, order); _start_lab(db, order, execution, advisor, technician)
    save_capture(db, order.id, execution.id, _capture(), actor=technician)
    complete_technical(db, order.id, execution.id, actor=technician)
    assert _execution(db, order).status == "technically_completed"
    with pytest.raises(HTTPException): close_execution(db, order.id, execution.id, actor=admin)
    generate_report(db, order.id, execution.id, actor=advisor)
    assert _execution(db, order).status == "pending_release"
    sign_report(db, order.id, execution.id, MaintenanceSignature(signer_name="Cliente", signature_data_url=VALID_SIGNATURE, client_decision="acknowledged"), actor=advisor)
    close_execution(db, order.id, execution.id, actor=admin)
    assert _execution(db, order).status == "closed"
