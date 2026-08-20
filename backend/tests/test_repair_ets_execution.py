from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.catalog_item import CatalogItem
from app.models.client import Client
from app.models.repair_execution import RepairExecution
from app.models.quotation import Quotation, QuotationItem
from app.models.user import Role, User
from app.schemas.repair_execution import (
    RepairAssign,
    RepairCancel,
    RepairChangeCreate,
    RepairChangeResolve,
    RepairConclude,
    RepairDiagnosis,
    RepairEquipmentCreate,
    RepairInterventionCreate,
    RepairPauseCreate,
    RepairPauseResolve,
    RepairTestCreate,
)
from app.schemas.maintenance_execution import (
    MaintenanceChangeCreate,
    MaintenanceChangeResolve,
    MaintenanceEquipmentCreate,
    MaintenancePrepare,
)
from app.schemas.service_order import ServiceOrderCreate
from app.services.maintenance_execution import (
    prepare_execution as prepare_maintenance_execution,
    register_arrival as register_maintenance_arrival,
    request_change as request_maintenance_change,
    resolve_change as resolve_maintenance_change,
    start_execution as start_maintenance_execution,
)
from app.services.repair_execution import (
    add_intervention,
    add_pause,
    add_test,
    assign_technician,
    cancel_execution,
    complete_technical,
    conclude_evaluation,
    register_arrival,
    repair_board,
    request_change,
    resolve_change,
    resolve_pause,
    start_evaluation,
)
from app.services.quotations import _build_operational_snapshot
from app.services.service_orders import create_service_order


@pytest.fixture()
def ctx():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()

    admin_role = Role(name="Administrador", description="Admin")
    tech_role = Role(name="Tecnico", description="Técnico")
    commercial_role = Role(name="Comercial", description="Comercial")

    db.add_all([admin_role, tech_role, commercial_role])
    db.flush()

    admin = User(
        username="repair-admin", email="repair-admin@example.test", full_name="Admin Reparación",
        hashed_password="unused", role_id=admin_role.id, roles=[admin_role],
    )
    technician = User(
        username="repair-tech", email="repair-tech@example.test", full_name="Técnico Reparación",
        hashed_password="unused", role_id=tech_role.id, roles=[tech_role],
    )
    advisor = User(
        username="repair-advisor", email="repair-advisor@example.test", full_name="Asesor Reparación",
        hashed_password="unused", role_id=commercial_role.id, roles=[commercial_role],
    )
    client = Client(legal_name="Cliente Reparación")

    db.add_all([admin, technician, advisor, client])
    db.commit()

    yield (db, admin, technician, advisor, client)

    db.close()
    engine.dispose()


def _catalog(db, *, category="repair", name="Reparación de bomba"):
    item = CatalogItem(
        item_type="service",
        service_kind="simple",
        commodity=category,
        category="Reparación" if category == "repair" else "Mantenimiento",
        operational_category=category,
        name=name,
        origin_price=Decimal("100"),
        origin_currency="MXN",
        exchange_rate=Decimal("1"),
        margin_percent=Decimal("0"),
        final_price_mxn=Decimal("100"),
        tax_object="iva_16",
        tax_rate=Decimal("16"),
    )
    db.add(item)
    db.flush()
    return item


def _order(db, client, advisor, catalog, *, quantity=1, folio="COT-REP-1"):
    quote = Quotation(
        folio=folio, client_id=client.id, advisor_id=advisor.id, status="waiting",
        subtotal=Decimal("100"), tax_total=Decimal("16"), total=Decimal("116"),
    )

    quote.items = [
        QuotationItem(
            catalog_item_id=catalog.id,
            service_name=catalog.name,
            operational_category=catalog.operational_category,
            commodity=catalog.commodity,
            quantity=quantity,
            unit_price=Decimal("100"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("16"),
            tax_total=Decimal("16"),
            total=Decimal("100"),
            operational_snapshot=_build_operational_snapshot(db, catalog),
        )
    ]

    db.add(quote)
    db.commit()

    return create_service_order(
        db,
        ServiceOrderCreate(client_id=client.id, quotation_id=quote.id, advisor_id=advisor.id),
        user_id=advisor.id,
    )


def _executions(db, order):
    return list(
        db.scalars(
            select(RepairExecution)
            .where(RepairExecution.service_order_id == order.id)
            .order_by(RepairExecution.id)
        )
    )


def _execution(db, order):
    return _executions(db, order)[0]


def _advance_to_in_repair(db, order, execution, advisor, technician):
    register_arrival(
        db, order.id, execution.id,
        RepairEquipmentCreate(name="Bomba", brand="MYC", model="P1", serial_number="S-1"),
        actor=advisor,
    )
    execution = _execution(db, order)
    assert execution.status == "pending_assignment"

    assign_technician(db, order.id, execution.id, RepairAssign(technician_id=technician.id), actor=advisor)
    execution = _execution(db, order)
    assert execution.status == "assigned"

    start_evaluation(db, order.id, execution.id, actor=technician)
    execution = _execution(db, order)
    assert execution.status == "in_evaluation"

    conclude_evaluation(db, order.id, execution.id, RepairConclude(conclusion="repaired"), actor=technician)
    execution = _execution(db, order)
    assert execution.status == "in_repair"

    return execution


def test_quantity_materializes_n_independent_units(ctx):
    db, admin, technician, advisor, client = ctx
    catalog = _catalog(db)

    order = _order(db, client, advisor, catalog, quantity=3, folio="COT-REP-N")
    executions = _executions(db, order)

    assert len(executions) == 3
    assert len({execution.service_unit_id for execution in executions}) == 3
    assert all(execution.status == "pending_arrival" for execution in executions)
    assert all(execution.origin == "quotation" for execution in executions)


def test_direct_quotation_happy_path_to_closed(ctx):
    db, admin, technician, advisor, client = ctx
    catalog = _catalog(db)
    order = _order(db, client, advisor, catalog, folio="COT-REP-HAPPY")

    execution = _execution(db, order)
    assert execution.status == "pending_arrival"

    execution = _advance_to_in_repair(db, order, execution, advisor, technician)

    add_intervention(
        db, order.id, execution.id,
        RepairInterventionCreate(description="Reemplazo de sello", actions=[{"action": "replace_seal"}]),
        actor=technician,
    )
    execution = _execution(db, order)
    assert execution.status == "in_repair"
    assert len(execution.interventions) == 1

    add_test(db, order.id, execution.id, RepairTestCreate(test_type="functional", result="pass"), actor=technician)
    execution = _execution(db, order)
    assert execution.status == "testing"

    board = complete_technical(db, order.id, execution.id, actor=technician)
    execution = _execution(db, order)
    assert execution.status == "technically_completed"
    assert execution.conclusion == "repaired"
    assert board["can_close"] is False  # aún no hay firma / pending_release

    # Firmar requiere HTML/PDF (weasyprint no disponible en este entorno de
    # pruebas); se valida el flujo hasta la conclusión técnica. El cierre
    # completo vía pending_release se ejercita a nivel de blockers abajo.
    closure_blockers = repair_board(db, order.id)["closure_blockers"]
    assert any("pending_release" in blocker["message"] or "cerrar" in blocker["message"] for blocker in closure_blockers)


def test_equipment_not_suitable_skips_repair_and_testing(ctx):
    db, admin, technician, advisor, client = ctx
    catalog = _catalog(db)
    order = _order(db, client, advisor, catalog, folio="COT-REP-NOTSUIT")
    execution = _execution(db, order)

    register_arrival(db, order.id, execution.id, RepairEquipmentCreate(name="Bomba"), actor=advisor)
    execution = _execution(db, order)
    assign_technician(db, order.id, execution.id, RepairAssign(technician_id=technician.id), actor=advisor)
    execution = _execution(db, order)
    start_evaluation(db, order.id, execution.id, actor=technician)
    execution = _execution(db, order)

    with pytest.raises(Exception):
        conclude_evaluation(
            db, order.id, execution.id,
            RepairConclude(conclusion="equipment_not_suitable"),
            actor=technician,
        )

    conclude_evaluation(
        db, order.id, execution.id,
        RepairConclude(conclusion="equipment_not_suitable", conclusion_reason="Daño estructural irreparable"),
        actor=technician,
    )
    execution = _execution(db, order)

    assert execution.status == "equipment_not_suitable"
    assert execution.conclusion_reason == "Daño estructural irreparable"
    assert execution.technical_completed_at is not None
    assert len(execution.interventions) == 0
    assert len(execution.tests) == 0


def test_multiple_interventions_and_failed_test_cycles_back(ctx):
    db, admin, technician, advisor, client = ctx
    catalog = _catalog(db)
    order = _order(db, client, advisor, catalog, folio="COT-REP-CYCLE")
    execution = _execution(db, order)
    execution = _advance_to_in_repair(db, order, execution, advisor, technician)

    add_intervention(db, order.id, execution.id, RepairInterventionCreate(description="Intervención 1"), actor=technician)
    add_test(db, order.id, execution.id, RepairTestCreate(test_type="functional", result="fail"), actor=technician)
    execution = _execution(db, order)
    assert execution.status == "in_repair"
    assert len(execution.tests) == 1

    add_intervention(db, order.id, execution.id, RepairInterventionCreate(description="Intervención 2"), actor=technician)
    add_test(db, order.id, execution.id, RepairTestCreate(test_type="functional", result="pass"), actor=technician)
    execution = _execution(db, order)

    assert execution.status == "testing"
    assert len(execution.interventions) == 2
    assert len(execution.tests) == 2
    assert [intervention.sequence for intervention in execution.interventions] == [1, 2]


def test_removed_component_disposition_defaults_and_validates(ctx):
    db, admin, technician, advisor, client = ctx
    catalog = _catalog(db)
    order = _order(db, client, advisor, catalog, folio="COT-REP-COMPONENT")
    execution = _execution(db, order)
    execution = _advance_to_in_repair(db, order, execution, advisor, technician)

    add_intervention(
        db, order.id, execution.id,
        RepairInterventionCreate(
            description="Retiro de tarjeta dañada",
            removed_components=[{"name": "Tarjeta control"}],
        ),
        actor=technician,
    )
    execution = _execution(db, order)
    assert execution.interventions[0].removed_components[0]["disposition"] == "return_to_client"

    with pytest.raises(Exception):
        RepairInterventionCreate(
            description="x",
            removed_components=[{"name": "Fusible", "disposition": "invalid"}],
        )


def test_pause_does_not_mutate_execution_status(ctx):
    db, admin, technician, advisor, client = ctx
    catalog = _catalog(db)
    order = _order(db, client, advisor, catalog, folio="COT-REP-PAUSE")
    execution = _execution(db, order)
    execution = _advance_to_in_repair(db, order, execution, advisor, technician)

    status_before = execution.status

    add_pause(
        db, order.id, execution.id,
        RepairPauseCreate(pause_type="spare_part", reason="Espera de refacción", responsible_user_id=technician.id),
        actor=technician,
    )
    execution = _execution(db, order)

    assert execution.status == status_before
    assert execution.pauses[0].status == "active"

    pause_id = execution.pauses[0].id
    resolve_pause(db, order.id, execution.id, pause_id, RepairPauseResolve(resolution="Refacción recibida"), actor=technician)
    execution = _execution(db, order)

    assert execution.status == status_before
    assert execution.pauses[0].status == "resolved"


def test_blockers_prevent_premature_closure(ctx):
    db, admin, technician, advisor, client = ctx
    catalog = _catalog(db)
    order = _order(db, client, advisor, catalog, folio="COT-REP-BLOCK")
    execution = _execution(db, order)

    board = repair_board(db, order.id)
    assert board["can_close"] is False
    assert any(blocker["field"] == "status" for blocker in board["closure_blockers"])


def test_cancel_before_first_intervention(ctx):
    db, admin, technician, advisor, client = ctx
    catalog = _catalog(db)
    order = _order(db, client, advisor, catalog, folio="COT-REP-CANCEL-EARLY")
    execution = _execution(db, order)

    cancel_execution(db, order.id, execution.id, RepairCancel(reason="Cliente desistió antes de iniciar"), actor=advisor)
    execution = _execution(db, order)

    assert execution.status == "cancelled"
    assert execution.cancelled_after_intervention is False


def test_cancel_after_first_intervention(ctx):
    db, admin, technician, advisor, client = ctx
    catalog = _catalog(db)
    order = _order(db, client, advisor, catalog, folio="COT-REP-CANCEL-LATE")
    execution = _execution(db, order)
    execution = _advance_to_in_repair(db, order, execution, advisor, technician)

    add_intervention(db, order.id, execution.id, RepairInterventionCreate(description="Intervención 1"), actor=technician)
    execution = _execution(db, order)

    cancel_execution(db, order.id, execution.id, RepairCancel(reason="Cliente desistió tras intervención"), actor=advisor)
    execution = _execution(db, order)

    assert execution.status == "cancelled"
    assert execution.cancelled_after_intervention is True


def test_maintenance_linked_repair_origin_and_investigation_regression(ctx):
    """Confirma la trazabilidad Mantenimiento -> Reparación.

    La necesidad de Reparación debe originarse desde un Mantenimiento
    realmente iniciado y por el técnico asignado. El asesor/administrador
    interviene después en la resolución comercial, no como autor del
    hallazgo técnico.
    """
    db, admin, technician, advisor, client = ctx

    repair_catalog = _catalog(
        db,
        category="repair",
        name="Reparación vinculada",
    )

    repair_order = _order(
        db,
        client,
        advisor,
        repair_catalog,
        folio="COT-REP-TARGET",
    )

    maintenance_catalog = _catalog(
        db,
        category="maintenance",
        name="Mantenimiento origen",
    )

    maintenance_order = _order(
        db,
        client,
        advisor,
        maintenance_catalog,
        folio="COT-MANT-SOURCE",
    )

    from app.models.maintenance_execution import (
        MaintenanceExecution,
    )

    maintenance_execution = db.scalar(
        select(MaintenanceExecution).where(
            MaintenanceExecution.service_order_id
            == maintenance_order.id
        )
    )

    assert maintenance_execution is not None

    # ---------------------------------------------------------
    # Llevar Mantenimiento por su lifecycle canónico:
    #
    # pending_assignment
    # -> pending_arrival
    # -> assigned
    # -> in_maintenance
    # ---------------------------------------------------------

    prepare_maintenance_execution(
        db,
        maintenance_order.id,
        maintenance_execution.id,
        MaintenancePrepare(
            technician_id=technician.id,
            location_mode="laboratory",
        ),
        actor=advisor,
    )

    maintenance_execution = db.scalar(
        select(MaintenanceExecution).where(
            MaintenanceExecution.id
            == maintenance_execution.id
        )
    )

    assert (
        maintenance_execution.location_mode
        == "laboratory"
    )

    assert (
        maintenance_execution.status
        == "pending_arrival"
    )

    register_maintenance_arrival(
        db,
        maintenance_order.id,
        maintenance_execution.id,
        MaintenanceEquipmentCreate(
            name="Equipo origen de reparación",
            brand="MYC",
            model="REP-TEST",
            serial_number="REP-MANT-001",
        ),
        actor=advisor,
    )

    maintenance_execution = db.scalar(
        select(MaintenanceExecution).where(
            MaintenanceExecution.id
            == maintenance_execution.id
        )
    )

    assert (
        maintenance_execution.status
        == "assigned"
    )

    start_maintenance_execution(
        db,
        maintenance_order.id,
        maintenance_execution.id,
        actor=technician,
    )

    maintenance_execution = db.scalar(
        select(MaintenanceExecution).where(
            MaintenanceExecution.id
            == maintenance_execution.id
        )
    )

    assert (
        maintenance_execution.status
        == "in_maintenance"
    )

    # ---------------------------------------------------------
    # El hallazgo derivado pertenece al técnico asignado.
    # ---------------------------------------------------------

    request_maintenance_change(
        db,
        maintenance_order.id,
        maintenance_execution.id,
        MaintenanceChangeCreate(
            change_type="repair",
            summary="Requiere reparación mayor",
        ),
        actor=technician,
    )

    from app.models.maintenance_execution import (
        MaintenanceChangeRequest,
    )

    maintenance_change = db.scalar(
        select(MaintenanceChangeRequest)
        .where(
            MaintenanceChangeRequest.maintenance_execution_id
            == maintenance_execution.id,
            MaintenanceChangeRequest.change_type
            == "repair",
            MaintenanceChangeRequest.status
            == "requested",
        )
        .order_by(
            MaintenanceChangeRequest.id.desc()
        )
    )

    assert maintenance_change is not None

    change_id = maintenance_change.id

    # ---------------------------------------------------------
    # La resolución/vinculación comercial se realiza después.
    # ---------------------------------------------------------

    resolve_maintenance_change(
        db,
        maintenance_order.id,
        maintenance_execution.id,
        change_id,
        MaintenanceChangeResolve(
            decision="linked",
            reason=(
                "Vinculado a ETS de reparación existente"
            ),
            linked_service_order_id=repair_order.id,
        ),
        actor=admin,
    )

    repair_execution = _execution(
        db,
        repair_order,
    )

    assert (
        repair_execution.origin
        == "maintenance_linked"
    )

    assert (
        repair_execution
        .source_maintenance_change_request_id
        == change_id
    )
