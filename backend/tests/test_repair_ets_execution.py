from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.catalog_item import CatalogItem
from app.models.client import Client
from app.models.quotation import Quotation, QuotationItem
from app.models.repair_execution import RepairExecution
from app.models.user import Role, User
from app.schemas.maintenance_execution import (
    MaintenanceChangeCreate,
    MaintenanceChangeResolve,
    MaintenanceEquipmentCreate,
    MaintenancePrepare,
)
from app.schemas.repair_execution import (
    RepairAssign,
    RepairCancel,
    RepairChangeCreate,
    RepairChangeResolve,
    RepairConclude,
    RepairDiagnosis,
    RepairEquipmentCreate,
    RepairInterventionComplete,
    RepairInterventionStart,
    RepairPauseCreate,
    RepairPauseResolve,
    RepairSignature,
    RepairTestCreate,
    RepairWarrantyReopen,
)
from app.schemas.service_order import ServiceOrderCreate
from app.services.maintenance_execution import (
    prepare_execution as prepare_maintenance_execution,
    register_arrival as register_maintenance_arrival,
    request_change as request_maintenance_change,
    resolve_change as resolve_maintenance_change,
    start_execution as start_maintenance_execution,
)
from app.services.quotations import _build_operational_snapshot
from app.services.repair_execution import (
    add_intervention,
    add_pause,
    add_test,
    assign_technician,
    cancel_execution,
    close_execution,
    complete_intervention,
    complete_technical,
    conclude_evaluation,
    generate_report,
    register_arrival,
    reopen_for_warranty,
    repair_board,
    request_change,
    resolve_change,
    resolve_pause,
    sign_report,
    start_evaluation,
    save_diagnosis,
)
from app.services.service_orders import create_service_order


VALID_SIGNATURE = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
    "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@pytest.fixture()
def ctx():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    db = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )()

    admin_role = Role(
        name="Administrador",
        description="Admin",
    )

    tech_role = Role(
        name="Tecnico",
        description="Técnico",
    )

    commercial_role = Role(
        name="Comercial",
        description="Comercial",
    )

    db.add_all(
        [
            admin_role,
            tech_role,
            commercial_role,
        ]
    )

    db.flush()

    admin = User(
        username="repair-admin",
        email="repair-admin@example.test",
        full_name="Admin Reparación",
        hashed_password="unused",
        role_id=admin_role.id,
        roles=[admin_role],
    )

    technician = User(
        username="repair-tech",
        email="repair-tech@example.test",
        full_name="Técnico Reparación",
        hashed_password="unused",
        role_id=tech_role.id,
        roles=[tech_role],
    )

    advisor = User(
        username="repair-advisor",
        email="repair-advisor@example.test",
        full_name="Asesor Reparación",
        hashed_password="unused",
        role_id=commercial_role.id,
        roles=[commercial_role],
    )

    client = Client(
        legal_name="Cliente Reparación",
    )

    db.add_all(
        [
            admin,
            technician,
            advisor,
            client,
        ]
    )

    db.commit()

    yield (
        db,
        admin,
        technician,
        advisor,
        client,
    )

    db.close()
    engine.dispose()


def _auth_headers(
    user: User,
    *,
    auth_context: str = "internal",
) -> dict[str, str]:
    token = create_access_token(
        str(user.id),
        extra_claims={
            "roles": [
                role.name
                for role in user.roles
            ],
            "auth_context": auth_context,
        },
    )

    return {
        "Authorization": f"Bearer {token}",
    }


def _catalog(
    db,
    *,
    category="repair",
    name="Reparación de bomba",
):
    item = CatalogItem(
        item_type="service",
        service_kind="simple",
        commodity=category,
        category=(
            "Reparación"
            if category == "repair"
            else "Mantenimiento"
        ),
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


def _order(
    db,
    client,
    advisor,
    catalog,
    *,
    quantity=1,
    folio="COT-REP-1",
):
    quote = Quotation(
        folio=folio,
        client_id=client.id,
        advisor_id=advisor.id,
        status="waiting",
        subtotal=Decimal("100"),
        tax_total=Decimal("16"),
        total=Decimal("116"),
    )

    quote.items = [
        QuotationItem(
            catalog_item_id=catalog.id,
            service_name=catalog.name,
            operational_category=(
                catalog.operational_category
            ),
            commodity=catalog.commodity,
            quantity=quantity,
            unit_price=Decimal("100"),
            discount_percent=Decimal("0"),
            tax_rate=Decimal("16"),
            tax_total=Decimal("16"),
            total=Decimal("100"),
            operational_snapshot=(
                _build_operational_snapshot(
                    db,
                    catalog,
                )
            ),
        )
    ]

    db.add(quote)
    db.commit()

    return create_service_order(
        db,
        ServiceOrderCreate(
            client_id=client.id,
            quotation_id=quote.id,
            advisor_id=advisor.id,
        ),
        user_id=advisor.id,
    )


def _executions(
    db,
    order,
):
    return list(
        db.scalars(
            select(
                RepairExecution,
            )
            .where(
                RepairExecution.service_order_id
                == order.id
            )
            .order_by(
                RepairExecution.id,
            )
        )
    )


def _execution(
    db,
    order,
):
    return _executions(
        db,
        order,
    )[0]


def _advance_to_in_repair(
    db,
    order,
    execution,
    advisor,
    technician,
):
    register_arrival(
        db,
        order.id,
        execution.id,
        RepairEquipmentCreate(
            name="Bomba",
            brand="MYC",
            model="P1",
            serial_number="S-1",
        ),
        actor=advisor,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "pending_assignment"
    )

    assign_technician(
        db,
        order.id,
        execution.id,
        RepairAssign(
            technician_id=technician.id,
        ),
        actor=advisor,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "assigned"
    )

    start_evaluation(
        db,
        order.id,
        execution.id,
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "in_evaluation"
    )

    conclude_evaluation(
        db,
        order.id,
        execution.id,
        RepairConclude(
            conclusion="repaired",
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "in_repair"
    )

    return execution


def _advance_warranty_to_in_repair(
    db,
    order,
    execution,
    advisor,
    technician,
):
    """Igual que _advance_to_in_repair pero para trabajo de garantía: el
    equipo ya fue recibido en el ciclo original, así que se parte desde
    'pending_assignment' (reopen_for_warranty ya dejó la ejecución ahí) sin
    volver a pasar por register_arrival."""

    assign_technician(
        db,
        order.id,
        execution.id,
        RepairAssign(
            technician_id=technician.id,
        ),
        actor=advisor,
    )

    execution = _execution(db, order)
    assert execution.status == "assigned"

    start_evaluation(
        db,
        order.id,
        execution.id,
        actor=technician,
    )

    execution = _execution(db, order)
    assert execution.status == "in_evaluation"

    conclude_evaluation(
        db,
        order.id,
        execution.id,
        RepairConclude(
            conclusion="repaired",
        ),
        actor=technician,
    )

    execution = _execution(db, order)
    assert execution.status == "in_repair"

    return execution


def _advance_to_closed(
    db,
    order,
    execution,
    admin,
    technician,
    *,
    intervention_description="Reemplazo de sello",
    test_type="functional",
):
    """Completa intervención + prueba pass + technical-complete + reporte
    firmado + cierre, dejando la ejecución en status == 'closed'."""

    add_intervention(
        db,
        order.id,
        execution.id,
        RepairInterventionStart(
            description=intervention_description,
        ),
        actor=technician,
    )

    execution = _execution(db, order)

    complete_intervention(
        db,
        order.id,
        execution.id,
        execution.interventions[-1].id,
        RepairInterventionComplete(
            actions=[{"action": "replace_seal"}],
            outcome="effective",
        ),
        actor=technician,
    )

    execution = _execution(db, order)

    add_test(
        db,
        order.id,
        execution.id,
        RepairTestCreate(
            test_type=test_type,
            result="pass",
            intervention_id=execution.interventions[-1].id,
        ),
        actor=technician,
    )

    complete_technical(
        db,
        order.id,
        execution.id,
        actor=technician,
    )

    generate_report(
        db,
        order.id,
        execution.id,
        actor=admin,
    )

    sign_report(
        db,
        order.id,
        execution.id,
        RepairSignature(
            signer_name="Cliente",
            signature_data_url=VALID_SIGNATURE,
            client_decision="accepted",
        ),
        actor=admin,
    )

    close_execution(
        db,
        order.id,
        execution.id,
        actor=admin,
    )

    return _execution(db, order)


def _open_warranty_cycle(db, order, execution, admin, *, reason="Falla recurrente reportada por el cliente"):
    reopen_for_warranty(
        db,
        order.id,
        execution.id,
        RepairWarrantyReopen(reason=reason),
        actor=admin,
    )

    return _execution(db, order)


def test_structured_diagnosis_is_persisted_and_does_not_change_status(
    ctx,
):
    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(
        db,
    )

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-DIAG-STRUCT",
    )

    execution = _execution(
        db,
        order,
    )

    register_arrival(
        db,
        order.id,
        execution.id,
        RepairEquipmentCreate(
            name="Bomba",
            brand="MYC",
            model="D-1",
            serial_number="DIAG-001",
        ),
        actor=advisor,
    )

    execution = _execution(
        db,
        order,
    )

    assign_technician(
        db,
        order.id,
        execution.id,
        RepairAssign(
            technician_id=technician.id,
        ),
        actor=advisor,
    )

    execution = _execution(
        db,
        order,
    )

    start_evaluation(
        db,
        order.id,
        execution.id,
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert execution.status == "in_evaluation"

    save_diagnosis(
        db,
        order.id,
        execution.id,
        RepairDiagnosis(
            reported_issue=(
                "El equipo no enciende"
            ),
            observed_condition=(
                "No presenta alimentación "
                "en la tarjeta principal"
            ),
            findings=[
                "Fusible de entrada abierto",
                "Capacitor de fuente deteriorado",
            ],
            probable_causes=[
                "Sobretensión de alimentación",
            ],
            severity="major",
            repairability="repairable",
            diagnosis_notes=(
                "Se recomienda reemplazo "
                "y prueba funcional."
            ),
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert execution.status == "in_evaluation"

    assert execution.diagnosis_data == {
        "reported_issue":
            "El equipo no enciende",
        "observed_condition":
            (
                "No presenta alimentación "
                "en la tarjeta principal"
            ),
        "findings": [
            "Fusible de entrada abierto",
            "Capacitor de fuente deteriorado",
        ],
        "probable_causes": [
            "Sobretensión de alimentación",
        ],
        "severity": "major",
        "repairability": "repairable",
    }

    assert (
        execution.diagnosis_notes
        == (
            "Se recomienda reemplazo "
            "y prueba funcional."
        )
    )

    assert (
        execution.diagnosis_completed_at
        is not None
    )


def test_diagnosis_validation_and_editing_rules(
    ctx,
):
    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(
        db,
    )

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-DIAG-RULES",
    )

    execution = _execution(
        db,
        order,
    )

    register_arrival(
        db,
        order.id,
        execution.id,
        RepairEquipmentCreate(
            name="Bomba",
        ),
        actor=advisor,
    )

    execution = _execution(
        db,
        order,
    )

    assign_technician(
        db,
        order.id,
        execution.id,
        RepairAssign(
            technician_id=technician.id,
        ),
        actor=advisor,
    )

    execution = _execution(
        db,
        order,
    )

    start_evaluation(
        db,
        order.id,
        execution.id,
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    # Diagnóstico completamente vacío:
    # debe rechazarse por contrato.
    with pytest.raises(Exception):
        RepairDiagnosis()

    # Diagnóstico exclusivamente narrativo:
    # sigue siendo válido.
    save_diagnosis(
        db,
        order.id,
        execution.id,
        RepairDiagnosis(
            diagnosis_notes=(
                "Se detecta desgaste "
                "en el sistema mecánico."
            ),
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert execution.status == "in_evaluation"

    assert (
        execution.diagnosis_notes
        == (
            "Se detecta desgaste "
            "en el sistema mecánico."
        )
    )

    # Mientras siga en evaluación,
    # el diagnóstico puede editarse.
    save_diagnosis(
        db,
        order.id,
        execution.id,
        RepairDiagnosis(
            findings=[
                "Desgaste excesivo en rodamiento",
            ],
            severity="moderate",
            repairability=(
                "conditionally_repairable"
            ),
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.diagnosis_data[
            "severity"
        ]
        == "moderate"
    )

    assert (
        execution.diagnosis_data[
            "repairability"
        ]
        == "conditionally_repairable"
    )

    assert (
        execution.diagnosis_notes
        is None
    )

    # Concluir evaluación sigue siendo
    # independiente del diagnóstico.
    conclude_evaluation(
        db,
        order.id,
        execution.id,
        RepairConclude(
            conclusion="repaired",
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert execution.status == "in_repair"

    # Después de concluir,
    # el diagnóstico ya no puede editarse.
    with pytest.raises(
        HTTPException,
    ) as exc_info:
        save_diagnosis(
            db,
            order.id,
            execution.id,
            RepairDiagnosis(
                diagnosis_notes=(
                    "Intento posterior "
                    "a la conclusión"
                ),
            ),
            actor=technician,
        )

    assert (
        exc_info.value.status_code
        == 409
    )


def test_intervention_http_contract(
    ctx,
):
    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(
        db,
    )

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-HTTP",
    )

    execution = _execution(
        db,
        order,
    )

    execution = _advance_to_in_repair(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    def override_db():
        yield db

    app.dependency_overrides[
        get_db
    ] = override_db

    api_client = TestClient(
        app,
    )

    try:
        start_path = (
            f"/api/service-orders/"
            f"{order.id}/repair/"
            f"{execution.id}/interventions"
        )

        unauthenticated = (
            api_client.post(
                start_path,
                json={
                    "description":
                        "Intervención HTTP",
                },
            )
        )

        assert (
            unauthenticated.status_code
            == 401
        )

        started = api_client.post(
            start_path,
            json={
                "description":
                    "Intervención HTTP",
            },
            headers=_auth_headers(
                technician,
            ),
        )

        assert (
            started.status_code
            == 200
        )

        started_body = (
            started.json()
        )

        current_execution = next(
            item
            for item
            in started_body[
                "executions"
            ]
            if (
                item["id"]
                == execution.id
            )
        )

        assert (
            len(
                current_execution[
                    "interventions"
                ]
            )
            == 1
        )

        intervention = (
            current_execution[
                "interventions"
            ][0]
        )

        assert (
            intervention[
                "completed_at"
            ]
            is None
        )

        intervention_id = (
            intervention["id"]
        )

        complete_path = (
            f"/api/service-orders/"
            f"{order.id}/repair/"
            f"{execution.id}/interventions/"
            f"{intervention_id}/complete"
        )

        unauthenticated_complete = (
            api_client.post(
                complete_path,
                json={
                    "actions": [],
                    "removed_components": [],
                    "outcome": "effective",
                },
            )
        )

        assert (
            unauthenticated_complete.status_code
            == 401
        )

        completed = api_client.post(
            complete_path,
            json={
                "actions": [
                    {
                        "action":
                            "replace_component",
                    },
                ],
                "removed_components": [],
                "outcome": "effective",
            },
            headers=_auth_headers(
                technician,
            ),
        )

        assert (
            completed.status_code
            == 200
        )

        completed_body = (
            completed.json()
        )

        completed_execution = next(
            item
            for item
            in completed_body[
                "executions"
            ]
            if (
                item["id"]
                == execution.id
            )
        )

        completed_intervention = next(
            item
            for item
            in completed_execution[
                "interventions"
            ]
            if (
                item["id"]
                == intervention_id
            )
        )

        assert (
            completed_intervention[
                "completed_at"
            ]
            is not None
        )

        assert (
            completed_intervention[
                "outcome"
            ]
            == "effective"
        )

        duplicate_completion = (
            api_client.post(
                complete_path,
                json={
                    "actions": [],
                    "removed_components": [],
                    "outcome": "effective",
                },
                headers=_auth_headers(
                    technician,
                ),
            )
        )

        assert (
            duplicate_completion.status_code
            == 409
        )

    finally:
        api_client.close()

        app.dependency_overrides.pop(
            get_db,
            None,
        )


def test_quantity_materializes_n_independent_units(
    ctx,
):
    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(
        db,
    )

    order = _order(
        db,
        client,
        advisor,
        catalog,
        quantity=3,
        folio="COT-REP-N",
    )

    executions = _executions(
        db,
        order,
    )

    assert (
        len(executions)
        == 3
    )

    assert (
        len(
            {
                execution.service_unit_id
                for execution in executions
            }
        )
        == 3
    )

    assert all(
        execution.status
        == "pending_arrival"
        for execution in executions
    )

    assert all(
        execution.origin
        == "quotation"
        for execution in executions
    )


def test_direct_quotation_happy_path_to_closed(
    ctx,
):
    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(
        db,
    )

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-HAPPY",
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "pending_arrival"
    )

    execution = _advance_to_in_repair(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    add_intervention(
        db,
        order.id,
        execution.id,
        RepairInterventionStart(
            description="Reemplazo de sello",
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "in_repair"
    )

    assert (
        len(
            execution.interventions
        )
        == 1
    )

    assert (
        execution
        .interventions[0]
        .completed_at
        is None
    )

    complete_intervention(
        db,
        order.id,
        execution.id,
        execution.interventions[0].id,
        RepairInterventionComplete(
            actions=[
                {
                    "action":
                        "replace_seal",
                },
            ],
            outcome="effective",
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution
        .interventions[0]
        .completed_at
        is not None
    )

    add_test(
        db,
        order.id,
        execution.id,
        RepairTestCreate(
            test_type="functional",
            result="pass",
            intervention_id=(
                execution
                .interventions[0]
                .id
            ),
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "testing"
    )

    board = complete_technical(
        db,
        order.id,
        execution.id,
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "technically_completed"
    )

    assert (
        execution.conclusion
        == "repaired"
    )

    assert (
        board["can_close"]
        is False
    )

    closure_blockers = (
        repair_board(
            db,
            order.id,
        )[
            "closure_blockers"
        ]
    )

    assert any(
        (
            "pending_release"
            in blocker["message"]
            or "cerrar"
            in blocker["message"]
        )
        for blocker
        in closure_blockers
    )


def test_equipment_not_suitable_skips_repair_and_testing(
    ctx,
):
    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(
        db,
    )

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-NOTSUIT",
    )

    execution = _execution(
        db,
        order,
    )

    register_arrival(
        db,
        order.id,
        execution.id,
        RepairEquipmentCreate(
            name="Bomba",
        ),
        actor=advisor,
    )

    execution = _execution(
        db,
        order,
    )

    assign_technician(
        db,
        order.id,
        execution.id,
        RepairAssign(
            technician_id=technician.id,
        ),
        actor=advisor,
    )

    execution = _execution(
        db,
        order,
    )

    start_evaluation(
        db,
        order.id,
        execution.id,
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    with pytest.raises(
        Exception,
    ):
        conclude_evaluation(
            db,
            order.id,
            execution.id,
            RepairConclude(
                conclusion=(
                    "equipment_not_suitable"
                ),
            ),
            actor=technician,
        )

    conclude_evaluation(
        db,
        order.id,
        execution.id,
        RepairConclude(
            conclusion=(
                "equipment_not_suitable"
            ),
            conclusion_reason=(
                "Daño estructural "
                "irreparable"
            ),
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "equipment_not_suitable"
    )

    assert (
        execution.conclusion_reason
        == "Daño estructural irreparable"
    )

    assert (
        execution.technical_completed_at
        is not None
    )

    assert (
        len(
            execution.interventions
        )
        == 0
    )

    assert (
        len(
            execution.tests
        )
        == 0
    )


def test_multiple_interventions_and_failed_test_cycles_back(
    ctx,
):
    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(
        db,
    )

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-CYCLE",
    )

    execution = _execution(
        db,
        order,
    )

    execution = _advance_to_in_repair(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    add_intervention(
        db,
        order.id,
        execution.id,
        RepairInterventionStart(
            description="Intervención 1",
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    first_intervention_id = (
        execution
        .interventions[0]
        .id
    )

    complete_intervention(
        db,
        order.id,
        execution.id,
        first_intervention_id,
        RepairInterventionComplete(
            outcome="ineffective",
        ),
        actor=technician,
    )

    add_test(
        db,
        order.id,
        execution.id,
        RepairTestCreate(
            test_type="functional",
            result="fail",
            intervention_id=(
                first_intervention_id
            ),
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "in_repair"
    )

    assert (
        len(
            execution.tests
        )
        == 1
    )

    add_intervention(
        db,
        order.id,
        execution.id,
        RepairInterventionStart(
            description="Intervención 2",
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    second_intervention_id = (
        execution
        .interventions[1]
        .id
    )

    complete_intervention(
        db,
        order.id,
        execution.id,
        second_intervention_id,
        RepairInterventionComplete(
            outcome="effective",
        ),
        actor=technician,
    )

    add_test(
        db,
        order.id,
        execution.id,
        RepairTestCreate(
            test_type="functional",
            result="pass",
            intervention_id=(
                second_intervention_id
            ),
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "testing"
    )

    assert (
        len(
            execution.interventions
        )
        == 2
    )

    assert (
        len(
            execution.tests
        )
        == 2
    )

    assert [
        intervention.sequence
        for intervention
        in execution.interventions
    ] == [
        1,
        2,
    ]


def test_removed_component_disposition_defaults_and_validates(
    ctx,
):
    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(
        db,
    )

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-COMPONENT",
    )

    execution = _execution(
        db,
        order,
    )

    execution = _advance_to_in_repair(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    add_intervention(
        db,
        order.id,
        execution.id,
        RepairInterventionStart(
            description=(
                "Retiro de tarjeta dañada"
            ),
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    complete_intervention(
        db,
        order.id,
        execution.id,
        execution.interventions[0].id,
        RepairInterventionComplete(
            removed_components=[
                {
                    "name":
                        "Tarjeta control",
                },
            ],
            outcome="effective",
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution
        .interventions[0]
        .removed_components[0]
        ["disposition"]
        == "return_to_client"
    )

    with pytest.raises(
        Exception,
    ):
        RepairInterventionComplete(
            removed_components=[
                {
                    "name":
                        "Fusible",
                    "disposition":
                        "invalid",
                },
            ],
            outcome="partial",
        )


def test_pause_types_are_parallel_and_reject_active_duplicates(
    ctx,
):
    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(
        db,
    )

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-PAUSE",
    )

    execution = _execution(
        db,
        order,
    )

    execution = _advance_to_in_repair(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    status_before = execution.status

    # ---------------------------------------------------------
    # Warehouse es un bloqueante paralelo.
    # No modifica el lifecycle principal.
    # ---------------------------------------------------------

    add_pause(
        db,
        order.id,
        execution.id,
        RepairPauseCreate(
            pause_type="warehouse",
            reason=(
                "Pendiente de surtido "
                "interno de almacén"
            ),
            responsible_user_id=technician.id,
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert execution.status == status_before

    assert len(execution.pauses) == 1

    warehouse_pause = execution.pauses[0]

    assert warehouse_pause.pause_type == "warehouse"
    assert warehouse_pause.status == "active"

    # ---------------------------------------------------------
    # No debe permitirse duplicar el mismo bloqueante activo.
    # ---------------------------------------------------------

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        add_pause(
            db,
            order.id,
            execution.id,
            RepairPauseCreate(
                pause_type="warehouse",
                reason=(
                    "Segundo bloqueo "
                    "de almacén"
                ),
                responsible_user_id=technician.id,
            ),
            actor=technician,
        )

    assert exc_info.value.status_code == 409

    # ---------------------------------------------------------
    # Un bloqueante diferente sí puede coexistir.
    # ---------------------------------------------------------

    add_pause(
        db,
        order.id,
        execution.id,
        RepairPauseCreate(
            pause_type="authorization",
            reason=(
                "Pendiente de autorización "
                "adicional"
            ),
            responsible_user_id=technician.id,
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert execution.status == status_before

    active_types = {
        pause.pause_type
        for pause in execution.pauses
        if pause.status == "active"
    }

    assert active_types == {
        "warehouse",
        "authorization",
    }

    # ---------------------------------------------------------
    # Resolver warehouse tampoco modifica el lifecycle.
    # ---------------------------------------------------------

    warehouse_pause = next(
        pause
        for pause in execution.pauses
        if pause.pause_type == "warehouse"
    )

    resolve_pause(
        db,
        order.id,
        execution.id,
        warehouse_pause.id,
        RepairPauseResolve(
            resolution=(
                "Material entregado "
                "por almacén"
            ),
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert execution.status == status_before

    warehouse_pause = next(
        pause
        for pause in execution.pauses
        if (
            pause.id
            == warehouse_pause.id
        )
    )

    assert warehouse_pause.status == "resolved"
    assert warehouse_pause.resolved_at is not None

    # Authorization continúa activa.
    assert any(
        pause.pause_type == "authorization"
        and pause.status == "active"
        for pause in execution.pauses
    )

    # ---------------------------------------------------------
    # Una vez resuelta, warehouse puede volver a abrirse.
    # ---------------------------------------------------------

    add_pause(
        db,
        order.id,
        execution.id,
        RepairPauseCreate(
            pause_type="warehouse",
            reason=(
                "Nuevo requerimiento "
                "de almacén"
            ),
            responsible_user_id=technician.id,
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    assert execution.status == status_before

    warehouse_pauses = [
        pause
        for pause in execution.pauses
        if pause.pause_type == "warehouse"
    ]

    assert len(warehouse_pauses) == 2

    assert sum(
        pause.status == "active"
        for pause in warehouse_pauses
    ) == 1

    assert sum(
        pause.status == "resolved"
        for pause in warehouse_pauses
    ) == 1


def test_blockers_prevent_premature_closure(
    ctx,
):
    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(
        db,
    )

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-BLOCK",
    )

    execution = _execution(
        db,
        order,
    )

    board = repair_board(
        db,
        order.id,
    )

    assert (
        board["can_close"]
        is False
    )

    assert any(
        blocker["field"]
        == "status"
        for blocker
        in board[
            "closure_blockers"
        ]
    )


def test_cancel_before_first_intervention(
    ctx,
):
    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(
        db,
    )

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-CANCEL-EARLY",
    )

    execution = _execution(
        db,
        order,
    )

    cancel_execution(
        db,
        order.id,
        execution.id,
        RepairCancel(
            reason=(
                "Cliente desistió "
                "antes de iniciar"
            ),
        ),
        actor=advisor,
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "cancelled"
    )

    assert (
        execution.cancelled_after_intervention
        is False
    )


def test_cancel_after_first_intervention(
    ctx,
):
    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(
        db,
    )

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-CANCEL-LATE",
    )

    execution = _execution(
        db,
        order,
    )

    execution = _advance_to_in_repair(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    add_intervention(
        db,
        order.id,
        execution.id,
        RepairInterventionStart(
            description="Intervención 1",
        ),
        actor=technician,
    )

    execution = _execution(
        db,
        order,
    )

    with pytest.raises(
        HTTPException,
    ) as exc_info:
        cancel_execution(
            db,
            order.id,
            execution.id,
            RepairCancel(
                reason=(
                    "Cliente desistió "
                    "tras intervención"
                ),
            ),
            actor=advisor,
        )

    assert (
        exc_info.value.status_code
        == 409
    )

    execution = _execution(
        db,
        order,
    )

    assert (
        execution.status
        == "in_repair"
    )

    assert (
        execution.cancelled_after_intervention
        is False
    )

    assert (
        len(
            execution.interventions
        )
        == 1
    )


def test_maintenance_linked_repair_origin_and_investigation_regression(
    ctx,
):
    """Confirma la trazabilidad Mantenimiento -> Reparación.

    La necesidad de Reparación debe originarse desde un Mantenimiento
    realmente iniciado y por el técnico asignado. El asesor/administrador
    interviene después en la resolución comercial, no como autor del
    hallazgo técnico.
    """

    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

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

    maintenance_execution = (
        db.scalar(
            select(
                MaintenanceExecution,
            ).where(
                MaintenanceExecution
                .service_order_id
                == maintenance_order.id
            )
        )
    )

    assert (
        maintenance_execution
        is not None
    )

    prepare_maintenance_execution(
        db,
        maintenance_order.id,
        maintenance_execution.id,
        MaintenancePrepare(
            technician_id=(
                technician.id
            ),
            location_mode="laboratory",
        ),
        actor=advisor,
    )

    maintenance_execution = (
        db.scalar(
            select(
                MaintenanceExecution,
            ).where(
                MaintenanceExecution.id
                == maintenance_execution.id
            )
        )
    )

    assert (
        maintenance_execution
        .location_mode
        == "laboratory"
    )

    assert (
        maintenance_execution
        .status
        == "pending_arrival"
    )

    register_maintenance_arrival(
        db,
        maintenance_order.id,
        maintenance_execution.id,
        MaintenanceEquipmentCreate(
            name=(
                "Equipo origen "
                "de reparación"
            ),
            brand="MYC",
            model="REP-TEST",
            serial_number=(
                "REP-MANT-001"
            ),
        ),
        actor=advisor,
    )

    maintenance_execution = (
        db.scalar(
            select(
                MaintenanceExecution,
            ).where(
                MaintenanceExecution.id
                == maintenance_execution.id
            )
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

    maintenance_execution = (
        db.scalar(
            select(
                MaintenanceExecution,
            ).where(
                MaintenanceExecution.id
                == maintenance_execution.id
            )
        )
    )

    assert (
        maintenance_execution.status
        == "in_maintenance"
    )

    request_maintenance_change(
        db,
        maintenance_order.id,
        maintenance_execution.id,
        MaintenanceChangeCreate(
            change_type="repair",
            summary=(
                "Requiere "
                "reparación mayor"
            ),
        ),
        actor=technician,
    )

    from app.models.maintenance_execution import (
        MaintenanceChangeRequest,
    )

    maintenance_change = (
        db.scalar(
            select(
                MaintenanceChangeRequest,
            )
            .where(
                MaintenanceChangeRequest
                .maintenance_execution_id
                == maintenance_execution.id,
                MaintenanceChangeRequest
                .change_type
                == "repair",
                MaintenanceChangeRequest
                .status
                == "requested",
            )
            .order_by(
                MaintenanceChangeRequest
                .id
                .desc()
            )
        )
    )

    assert (
        maintenance_change
        is not None
    )

    change_id = (
        maintenance_change.id
    )

    resolve_maintenance_change(
        db,
        maintenance_order.id,
        maintenance_execution.id,
        change_id,
        MaintenanceChangeResolve(
            decision="linked",
            reason=(
                "Vinculado a ETS de "
                "reparación existente"
            ),
            linked_service_order_id=(
                repair_order.id
            ),
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

# ---------------------------------------------------------------------------
# GARANTÍA VERSIONADA (RepairWarrantyCycle)
# ---------------------------------------------------------------------------


def test_warranty_cycle_full_lifecycle_preserves_history(
    ctx,
):
    """Ciclo original -> WarrantyCycle #1 -> WarrantyCycle #2, sin destruir
    ni reinterpretar retroactivamente ningún cierre anterior.

    Cubre A, B, C, D, E, F, G y H del contrato funcional.
    """

    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(db)

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-WARRANTY-1",
    )

    execution = _execution(db, order)

    execution = _advance_to_in_repair(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    # --- A: la reparación original cierra normalmente ---------------------
    execution = _advance_to_closed(
        db,
        order,
        execution,
        admin,
        technician,
        intervention_description="Reemplazo de sello original",
        test_type="functional-original",
    )

    assert execution.status == "closed"
    assert execution.conclusion == "repaired"
    assert execution.original_closed_at is not None
    assert execution.original_conclusion == "repaired"
    assert execution.original_technical_completed_at is not None
    assert execution.warranty_reopened_count == 0
    assert execution.warranty_cycles == []

    original_closed_at = execution.original_closed_at
    original_conclusion = execution.original_conclusion
    original_technical_completed_at = execution.original_technical_completed_at
    vigente_closed_at_before_warranty = execution.closed_at
    original_intervention_id = execution.interventions[0].id

    assert execution.interventions[0].warranty_cycle_id is None
    assert execution.tests[0].warranty_cycle_id is None

    # --- B: primera garantía crea WarrantyCycle #1 sin destruir historia --
    execution = _open_warranty_cycle(
        db,
        order,
        execution,
        admin,
        reason="El equipo volvió a fallar dentro del periodo de garantía",
    )

    assert execution.status == "pending_assignment"
    assert execution.warranty_reopened_count == 1
    assert len(execution.warranty_cycles) == 1

    cycle_1 = execution.warranty_cycles[0]
    assert cycle_1.sequence == 1
    assert cycle_1.status == "open"
    assert cycle_1.opened_by_id == admin.id
    assert cycle_1.opened_at is not None
    assert cycle_1.closed_at is None

    # El cierre histórico original NUNCA se sobrescribe.
    assert execution.original_closed_at == original_closed_at
    assert execution.original_conclusion == original_conclusion
    assert execution.original_technical_completed_at == original_technical_completed_at

    # Y el cierre/conclusión "vigentes" tampoco se destruyen al reabrir:
    # siguen reflejando el último estado conocido hasta que el nuevo ciclo
    # los actualice mediante el lifecycle normal.
    assert execution.closed_at == vigente_closed_at_before_warranty
    assert execution.conclusion == "repaired"

    # --- C/D: intervención y prueba durante la garantía se asocian a #1 ---
    execution = _advance_warranty_to_in_repair(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    add_intervention(
        db,
        order.id,
        execution.id,
        RepairInterventionStart(
            description="Segunda intervención por garantía",
        ),
        actor=technician,
    )

    execution = _execution(db, order)
    warranty_intervention = execution.interventions[-1]

    assert warranty_intervention.warranty_cycle_id == cycle_1.id

    complete_intervention(
        db,
        order.id,
        execution.id,
        warranty_intervention.id,
        RepairInterventionComplete(
            actions=[{"action": "replace_seal_again"}],
            outcome="effective",
        ),
        actor=technician,
    )

    execution = _execution(db, order)

    add_test(
        db,
        order.id,
        execution.id,
        RepairTestCreate(
            test_type="functional-warranty-1",
            result="pass",
            intervention_id=warranty_intervention.id,
        ),
        actor=technician,
    )

    execution = _execution(db, order)
    warranty_test = execution.tests[-1]

    assert warranty_test.warranty_cycle_id == cycle_1.id

    # El trabajo del ciclo original permanece identificable (H, parcial).
    assert execution.interventions[0].id == original_intervention_id
    assert execution.interventions[0].warranty_cycle_id is None

    # --- E: cerrar WarrantyCycle #1 conserva su propio historial ----------
    complete_technical(
        db,
        order.id,
        execution.id,
        actor=technician,
    )

    generate_report(
        db,
        order.id,
        execution.id,
        actor=admin,
    )

    sign_report(
        db,
        order.id,
        execution.id,
        RepairSignature(
            signer_name="Cliente",
            signature_data_url=VALID_SIGNATURE,
            client_decision="accepted",
        ),
        actor=admin,
    )

    close_execution(
        db,
        order.id,
        execution.id,
        actor=admin,
    )

    execution = _execution(db, order)
    cycle_1 = execution.warranty_cycles[0]

    assert execution.status == "closed"
    assert cycle_1.status == "closed"
    assert cycle_1.resolution == "repaired"
    assert cycle_1.closed_by_id == admin.id
    assert cycle_1.closed_at is not None
    assert cycle_1.closed_at == execution.closed_at

    # El cierre histórico original sigue intacto tras cerrar la garantía.
    assert execution.original_closed_at == original_closed_at
    assert execution.original_conclusion == original_conclusion
    assert execution.original_technical_completed_at == original_technical_completed_at

    cycle_1_snapshot = {
        "sequence": cycle_1.sequence,
        "status": cycle_1.status,
        "resolution": cycle_1.resolution,
        "reason": cycle_1.reason,
        "opened_at": cycle_1.opened_at,
        "closed_at": cycle_1.closed_at,
    }

    # --- F: puede abrirse WarrantyCycle #2 ---------------------------------
    execution = _open_warranty_cycle(
        db,
        order,
        execution,
        admin,
        reason="Segunda falla, dentro de una nueva ventana de garantía",
    )

    assert execution.warranty_reopened_count == 2
    assert len(execution.warranty_cycles) == 2

    cycle_2 = next(
        cycle for cycle in execution.warranty_cycles if cycle.sequence == 2
    )
    assert cycle_2.status == "open"
    assert cycle_2.closed_at is None

    # --- G: WarrantyCycle #1 permanece intacto tras crear #2 --------------
    cycle_1_after = next(
        cycle for cycle in execution.warranty_cycles if cycle.sequence == 1
    )

    assert {
        "sequence": cycle_1_after.sequence,
        "status": cycle_1_after.status,
        "resolution": cycle_1_after.resolution,
        "reason": cycle_1_after.reason,
        "opened_at": cycle_1_after.opened_at,
        "closed_at": cycle_1_after.closed_at,
    } == cycle_1_snapshot

    # El trabajo técnico del ciclo #1 tampoco migra hacia el ciclo #2.
    assert warranty_intervention.warranty_cycle_id == cycle_1.id
    assert warranty_test.warranty_cycle_id == cycle_1.id

    # --- H: el ciclo original permanece identificable ----------------------
    assert execution.original_closed_at == original_closed_at
    assert execution.original_conclusion == original_conclusion
    assert execution.original_technical_completed_at == original_technical_completed_at
    assert execution.interventions[0].warranty_cycle_id is None


def test_cannot_open_second_warranty_cycle_while_one_is_active(
    ctx,
):
    """I: no pueden existir dos WarrantyCycle activos simultáneamente.

    El propio lifecycle lo impide estructuralmente: mientras un ciclo de
    garantía está 'open', la ejecución ya no está en status == 'closed'
    (solo close_execution() vuelve a dejarla cerrada, y eso cierra el ciclo
    activo como efecto colateral), así que reopen_for_warranty() no puede
    volver a dispararse hasta que el ciclo vigente se cierre.
    """

    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(db)

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-WARRANTY-2",
    )

    execution = _execution(db, order)

    execution = _advance_to_in_repair(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    execution = _advance_to_closed(
        db,
        order,
        execution,
        admin,
        technician,
    )

    execution = _open_warranty_cycle(
        db,
        order,
        execution,
        admin,
    )

    assert execution.status == "pending_assignment"
    assert len(execution.warranty_cycles) == 1

    with pytest.raises(HTTPException) as exc_info:
        reopen_for_warranty(
            db,
            order.id,
            execution.id,
            RepairWarrantyReopen(
                reason="Segundo intento de reapertura simultánea",
            ),
            actor=admin,
        )

    assert exc_info.value.status_code == 409

    execution = _execution(db, order)
    assert len(execution.warranty_cycles) == 1


def test_warranty_reopen_requires_closed_execution(
    ctx,
):
    """J: no puede abrirse garantía sobre una ejecución que no satisfaga
    las precondiciones (no está cerrada)."""

    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(db)

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-WARRANTY-3",
    )

    execution = _execution(db, order)

    assert execution.status == "pending_arrival"

    with pytest.raises(HTTPException) as exc_info:
        reopen_for_warranty(
            db,
            order.id,
            execution.id,
            RepairWarrantyReopen(
                reason="Garantía sobre una ejecución nunca cerrada",
            ),
            actor=admin,
        )

    assert exc_info.value.status_code == 409

    execution = _execution(db, order)
    assert execution.warranty_cycles == []
    assert execution.warranty_reopened_count == 0

    # Tampoco puede reabrirse a mitad del ciclo original (in_repair).
    execution = _advance_to_in_repair(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    with pytest.raises(HTTPException) as exc_info:
        reopen_for_warranty(
            db,
            order.id,
            execution.id,
            RepairWarrantyReopen(
                reason="Garantía a mitad de la reparación original",
            ),
            actor=admin,
        )

    assert exc_info.value.status_code == 409


def test_client_cannot_assign_arbitrary_warranty_cycle_id(
    ctx,
):
    """K: el backend determina siempre el ciclo activo; un cliente HTTP no
    puede asociar trabajo técnico nuevo a un ciclo histórico arbitrario.

    Los schemas de entrada (RepairInterventionStart, RepairTestCreate,
    RepairPauseCreate, RepairChangeCreate) no exponen warranty_cycle_id, así
    que ni siquiera intentar inyectarlo como kwarg puede alcanzar al modelo.
    """

    for schema in (
        RepairInterventionStart,
        RepairTestCreate,
        RepairPauseCreate,
        RepairChangeCreate,
    ):
        assert "warranty_cycle_id" not in schema.model_fields

    (
        db,
        admin,
        technician,
        advisor,
        client,
    ) = ctx

    catalog = _catalog(db)

    order = _order(
        db,
        client,
        advisor,
        catalog,
        folio="COT-REP-WARRANTY-4",
    )

    execution = _execution(db, order)

    execution = _advance_to_in_repair(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    execution = _advance_to_closed(
        db,
        order,
        execution,
        admin,
        technician,
    )

    execution = _open_warranty_cycle(
        db,
        order,
        execution,
        admin,
    )

    cycle_1_id = execution.warranty_cycles[0].id

    execution = _advance_warranty_to_in_repair(
        db,
        order,
        execution,
        advisor,
        technician,
    )

    # Un payload validado (p. ej. reconstruido a partir de JSON externo con
    # una clave extra "warranty_cycle_id") simplemente ignora ese campo:
    # pydantic descarta claves no declaradas en el schema.
    tampered = RepairInterventionStart.model_validate(
        {
            "description": "Intento de intervención con cycle inyectado",
            "warranty_cycle_id": cycle_1_id + 999,
        }
    )

    assert not hasattr(tampered, "warranty_cycle_id")

    add_intervention(
        db,
        order.id,
        execution.id,
        tampered,
        actor=technician,
    )

    execution = _execution(db, order)

    assert execution.interventions[-1].warranty_cycle_id == cycle_1_id
