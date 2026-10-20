"""SG-3: Servicio General en MYC Mobile -- alta/edición de equipo sin
configuración metrológica y creación de TechnicalReport (Installation).

Cubre el contrato por categoría de `equipment/configured` y que calibración
conserva exactamente su comportamiento anterior.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.field_sheet import FieldSheet
from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.user import Role, User

BASE = "/api/mobile/v1/technician/lab-work-orders"

PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
).decode()


def signatures_payload() -> dict:
    signed_at = datetime.now(timezone.utc).isoformat()
    return {
        party: {
            "signer_name": name,
            "signed_at": signed_at,
            "version": 1,
            "signature_data_url": PNG_DATA_URL,
        }
        for party, name in (("technician", "Técnico LAB"), ("client", "Cliente LAB"))
    }


def sign_reception(client, headers, order_id: int):
    return client.post(
        f"{BASE}/{order_id}/signatures", json=signatures_payload(), headers=headers
    )


def prevalidate(client, headers, order_id: int) -> list[dict]:
    response = client.get(f"{BASE}/{order_id}/signature-group/prevalidate", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["blockers"]


@pytest.fixture()
def sg3():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        role = Role(name="Tecnico", description="Técnico")
        db.add(role)
        db.flush()
        user = User(
            username="lab-tech",
            email="lab-tech@example.test",
            full_name="LAB tech",
            hashed_password="unused",
            account_type="internal",
            status="active",
            is_active=True,
            role_id=role.id,
            roles=[role],
        )
        db.add(user)
        db.commit()
        token = create_access_token(
            str(user.id),
            extra_claims={"roles": [role.name], "auth_context": "internal"},
        )

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        yield client, factory, {"Authorization": f"Bearer {token}"}
    finally:
        app.dependency_overrides.clear()


def order_payload(**extra) -> dict:
    return {
        "reception_date": "2026-10-07",
        "client_name": "Cliente SG",
        "address": "Av. Prueba 123",
        "contact_name": "Persona Cliente",
        "contact_phone": "3312345678",
        "contact_email": "cliente@example.com",
        "postal_code": "45601",
        "city": "Tlaquepaque",
        "state_name": "Jalisco",
        "purchase_order": "OC-1",
        "notes": "Recepción",
        **extra,
    }


def equipment_body(index: int = 1, **extra) -> dict:
    return {
        "instrument": f"Equipo {index}",
        "brand": "MYC Test",
        "identification": f"ID-{index}",
        "serial_number": f"SER-{index}",
        "report_number": None,
        "is_good_condition": True,
        **extra,
    }


def create_order(client, headers, **extra) -> dict:
    response = client.post(BASE, json=order_payload(**extra), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def general_equipment(client, headers, order_id: int, index: int = 1) -> dict:
    response = client.post(
        f"{BASE}/{order_id}/equipment/configured",
        json={"equipment": equipment_body(index)},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["equipment"][-1]


def test_default_category_is_calibration(sg3):
    client, _factory, headers = sg3
    assert create_order(client, headers)["operational_category"] == "calibration"


def test_mobile_creates_general_service_order(sg3):
    client, _factory, headers = sg3
    order = create_order(client, headers, operational_category="general_service")
    assert order["operational_category"] == "general_service"


def test_general_service_with_erp_bridge_is_rejected(sg3):
    client, _factory, headers = sg3
    response = client.post(
        BASE,
        json=order_payload(operational_category="general_service", service_order_id=1),
        headers=headers,
    )
    assert response.status_code == 409, response.text


def test_general_service_equipment_has_no_metrological_configuration(sg3):
    client, factory, headers = sg3
    order = create_order(client, headers, operational_category="general_service")
    equipment = general_equipment(client, headers, order["id"])
    assert equipment["service_type"] is None
    assert equipment["linked_company_id"] is None
    assert equipment["certificate_folio"] is None
    assert equipment["folio_status"] == "unassigned"
    assert equipment["certificate_client_mode"] == "order"
    with factory() as db:
        # Nada de MYCA/MYCT ni FieldSheet.
        assert db.scalar(select(FieldSheet.id)) is None
        prefixes = {row.prefix for row in db.scalars(select(InstitutionalFolioSequence))}
        assert not prefixes & {"MYCA", "MYCT"}


@pytest.mark.parametrize(
    "extra",
    [
        {"service": {"service_type": "accredited", "linked_company_id": None}},
        {"certificate_client": {"certificate_client_mode": "order"}},
    ],
)
def test_general_service_rejects_metrological_payload(sg3, extra):
    client, _factory, headers = sg3
    order = create_order(client, headers, operational_category="general_service")
    response = client.post(
        f"{BASE}/{order['id']}/equipment/configured",
        json={"equipment": equipment_body(), **extra},
        headers=headers,
    )
    assert response.status_code == 422, response.text
    detail = client.get(f"{BASE}/{order['id']}", headers=headers).json()
    assert detail["equipment"] == []


def test_calibration_still_requires_service(sg3):
    client, _factory, headers = sg3
    order = create_order(client, headers)
    missing = client.post(
        f"{BASE}/{order['id']}/equipment/configured",
        json={"equipment": equipment_body()},
        headers=headers,
    )
    assert missing.status_code == 422, missing.text
    ok = client.post(
        f"{BASE}/{order['id']}/equipment/configured",
        json={
            "equipment": equipment_body(),
            "service": {"service_type": "traceable", "linked_company_id": None},
        },
        headers=headers,
    )
    assert ok.status_code == 201, ok.text
    equipment = ok.json()["equipment"][-1]
    assert equipment["service_type"] == "traceable"
    assert equipment["folio_status"] == "reserved"


def test_general_service_edit_keeps_service_type_null(sg3):
    client, _factory, headers = sg3
    order = create_order(client, headers, operational_category="general_service")
    equipment = general_equipment(client, headers, order["id"])
    response = client.patch(
        f"{BASE}/{order['id']}/equipment/{equipment['id']}/configured",
        json={"equipment": equipment_body(1, brand="Otra marca", model="M-1", observations="Obs")},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    updated = response.json()["equipment"][-1]
    assert updated["brand"] == "Otra marca"
    assert updated["model"] == "M-1"
    assert updated["service_type"] is None
    assert updated["folio_status"] == "unassigned"


def test_direct_metrological_endpoints_reject_general_service(sg3):
    client, _factory, headers = sg3
    order = create_order(client, headers, operational_category="general_service")
    equipment = general_equipment(client, headers, order["id"])
    service = client.put(
        f"{BASE}/{order['id']}/equipment/{equipment['id']}/service",
        json={"service_type": "accredited", "linked_company_id": None},
        headers=headers,
    )
    assert service.status_code == 409, service.text
    certificate_client = client.patch(
        f"{BASE}/{order['id']}/equipment/{equipment['id']}/certificate-client",
        json={
            "certificate_client_mode": "different",
            "final_client_company_snapshot": "Otro",
        },
        headers=headers,
    )
    assert certificate_client.status_code == 409, certificate_client.text
    sheet = client.post(
        f"{BASE}/{order['id']}/equipment/{equipment['id']}/field-sheet",
        json={"template_key": "lab_externo"},
        headers=headers,
    )
    assert sheet.status_code == 409, sheet.text


def test_general_service_follows_the_normal_lifecycle_up_to_the_installation_report(sg3):
    """OT -> equipo sin metrología -> prevalidación sin blockers -> recepción
    firmada -> captura técnica -> Installation (MYC-IN...)."""
    client, _factory, headers = sg3
    order = create_order(client, headers, operational_category="general_service")
    assert order["operational_category"] == "general_service"
    equipment = general_equipment(client, headers, order["id"])
    assert equipment["service_type"] is None
    assert equipment["folio_status"] == "unassigned"

    assert prevalidate(client, headers, order["id"]) == []

    # El reporte NO es un bypass de la recepción: en draft se rechaza.
    early = client.post(
        f"{BASE}/{order['id']}/equipment/{equipment['id']}/technical-report",
        json={"report_type": "installation"},
        headers=headers,
    )
    assert early.status_code == 409, early.text

    signed = sign_reception(client, headers, order["id"])
    assert signed.status_code == 200, signed.text
    assert signed.json()["status"] == "received_signed"
    assert signed.json()["signature_required"] is False

    created = client.post(
        f"{BASE}/{order['id']}/equipment/{equipment['id']}/technical-report",
        json={"report_type": "installation"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    report = created.json()
    assert report["folio"].startswith("MYC-IN")
    assert report["status"] == "draft"
    assert report["revision_number"] == 1

    refreshed = client.get(f"{BASE}/{order['id']}", headers=headers).json()
    assert refreshed["status"] == "in_progress"  # primera mutación técnica real
    projected = refreshed["equipment"][-1]
    assert projected["technical_report_id"] == report["id"]
    assert projected["technical_report_type"] == "installation"
    assert projected["technical_report_folio"] == report["folio"]
    assert projected["technical_report_status"] == "draft"
    assert projected["technical_report_revision_count"] == 1
    assert projected["service_type"] is None
    assert projected["folio_status"] == "unassigned"


def test_calibration_reception_keeps_requiring_service_type(sg3):
    """Calibración conserva EXACTAMENTE sus blockers: un equipo sin modalidad
    bloquea prevalidación y firma; Servicio General no produce ninguno."""
    client, _factory, headers = sg3
    calibration = create_order(client, headers)
    legacy_add = client.post(
        f"{BASE}/{calibration['id']}/equipment", json=equipment_body(1), headers=headers
    )
    assert legacy_add.status_code == 201, legacy_add.text
    blockers = prevalidate(client, headers, calibration["id"])
    assert [item["reason"] for item in blockers] == ["Selecciona el tipo de servicio"]
    blocked = sign_reception(client, headers, calibration["id"])
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["code"] == "LAB_RECEPTION_INCOMPLETE"

    general = create_order(client, headers, operational_category="general_service")
    legacy_general = client.post(
        f"{BASE}/{general['id']}/equipment", json=equipment_body(1), headers=headers
    )
    assert legacy_general.status_code == 201, legacy_general.text
    assert prevalidate(client, headers, general["id"]) == []


def test_calibration_with_service_signs_and_still_uses_field_sheets(sg3):
    client, factory, headers = sg3
    order = create_order(client, headers)
    equipment = client.post(
        f"{BASE}/{order['id']}/equipment/configured",
        json={
            "equipment": equipment_body(),
            "service": {"service_type": "traceable", "linked_company_id": None},
        },
        headers=headers,
    ).json()["equipment"][-1]
    assert prevalidate(client, headers, order["id"]) == []
    signed = sign_reception(client, headers, order["id"])
    assert signed.status_code == 200, signed.text
    assert signed.json()["status"] == "received_signed"

    # Calibración jamás crea reportes técnicos: su documento es la FieldSheet.
    rejected = client.post(
        f"{BASE}/{order['id']}/equipment/{equipment['id']}/technical-report",
        json={"report_type": "installation"},
        headers=headers,
    )
    assert rejected.status_code == 409, rejected.text
    with factory() as db:
        assert db.scalar(select(FieldSheet.id)) is None


def test_general_service_only_supports_the_group_workflow(sg3):
    client, factory, headers = sg3
    rejected = client.post(
        BASE,
        json=order_payload(operational_category="general_service", workflow_mode="equipment_by_equipment"),
        headers=headers,
    )
    assert rejected.status_code == 422, rejected.text
    group = client.post(
        f"{BASE}/groups",
        json=order_payload(operational_category="general_service", workflow_mode="equipment_by_equipment", quantity=2),
        headers=headers,
    )
    assert group.status_code == 422, group.text
    order = create_order(client, headers, operational_category="general_service")
    # La acción administrativa (permiso de cancelación) tampoco puede habilitarla.
    from fastapi import HTTPException

    from app.schemas.lab_work_order import LabWorkOrderWorkflowModeChange
    from app.services.lab_work_orders import change_lab_work_order_workflow_mode

    with factory() as db:
        admin = db.scalar(select(User))
        with pytest.raises(HTTPException) as error:
            change_lab_work_order_workflow_mode(
                db,
                order["id"],
                LabWorkOrderWorkflowModeChange(new_workflow_mode="equipment_by_equipment", reason="prueba de categoría"),
                admin,
            )
    assert error.value.status_code == 422


def test_other_report_types_and_calibration_orders_do_not_create_reports(sg3):
    client, _factory, headers = sg3
    general = create_order(client, headers, operational_category="general_service")
    equipment = general_equipment(client, headers, general["id"])
    assert sign_reception(client, headers, general["id"]).status_code == 200
    for report_type in ("verification", "repair", "maintenance", "sale"):
        response = client.post(
            f"{BASE}/{general['id']}/equipment/{equipment['id']}/technical-report",
            json={"report_type": report_type},
            headers=headers,
        )
        assert response.status_code == 409, (report_type, response.text)


# ---------------------------------------------------------------- auditoría final

REPORT_URL = "{base}/{order_id}/equipment/{equipment_id}/technical-report"


def _general_equipment_signed(client, headers):
    order = create_order(client, headers, operational_category="general_service")
    equipment = general_equipment(client, headers, order["id"])
    assert sign_reception(client, headers, order["id"]).status_code == 200
    return order, equipment


@pytest.mark.parametrize("blocked_status", ["draft", "ready_to_close", "completed", "partially_closed", "cancelled"])
def test_technical_report_is_only_created_in_received_signed_or_in_progress(sg3, blocked_status):
    from app.models.lab_work_order import LabWorkOrder

    client, factory, headers = sg3
    order, equipment = _general_equipment_signed(client, headers)
    with factory() as db:
        db.get(LabWorkOrder, order["id"]).status = blocked_status
        db.commit()
    response = client.post(
        REPORT_URL.format(base=BASE, order_id=order["id"], equipment_id=equipment["id"]),
        json={"report_type": "installation"},
        headers=headers,
    )
    assert response.status_code == 409, (blocked_status, response.text)
    with factory() as db:
        assert db.get(LabWorkOrder, order["id"]).status == blocked_status


def test_first_report_promotes_received_signed_to_in_progress_exactly_once(sg3):
    from app.models.lab_work_order import LabWorkOrder

    client, factory, headers = sg3
    order, equipment = _general_equipment_signed(client, headers)
    with factory() as db:
        assert db.get(LabWorkOrder, order["id"]).status == "received_signed"
    url = REPORT_URL.format(base=BASE, order_id=order["id"], equipment_id=equipment["id"])
    assert client.post(url, json={"report_type": "installation"}, headers=headers).status_code == 201
    with factory() as db:
        assert db.get(LabWorkOrder, order["id"]).status == "in_progress"
    # Un segundo reporte vigente se rechaza y el estado no cambia.
    assert client.post(url, json={"report_type": "installation"}, headers=headers).status_code == 409


def _with_context(factory, permissions: set[str], actor_type: str = "internal"):
    from app.core.mobile.security import MobileSecurityContext, get_mobile_context
    from app.models.user import User

    with factory() as db:
        user = db.scalar(select(User))
    app.dependency_overrides[get_mobile_context] = lambda: MobileSecurityContext(
        user=user, actor_type=actor_type, permissions=frozenset(permissions), client_id=None
    )


def test_technical_report_permissions_capture_creates_read_only_reads(sg3):
    client, factory, headers = sg3
    order, equipment = _general_equipment_signed(client, headers)
    url = REPORT_URL.format(base=BASE, order_id=order["id"], equipment_id=equipment["id"])

    _with_context(factory, {"mobile.access", "technical_reports.read"})
    assert client.post(url, json={"report_type": "installation"}, headers=headers).status_code == 403
    assert client.get(url, headers=headers).status_code == 404  # lectura permitida; aún no hay reporte

    _with_context(factory, {"mobile.access"})
    assert client.post(url, json={"report_type": "installation"}, headers=headers).status_code == 403
    assert client.get(url, headers=headers).status_code == 403

    _with_context(factory, {"mobile.access", "technical_reports.capture"})
    created = client.post(url, json={"report_type": "installation"}, headers=headers)
    assert created.status_code == 201, created.text

    _with_context(factory, {"mobile.access", "technical_reports.read"})
    read = client.get(url, headers=headers)
    assert read.status_code == 200
    assert read.json()["folio"].startswith("MYC-IN")


def test_technical_report_capture_is_internal_staff_only(sg3):
    client, factory, headers = sg3
    order, equipment = _general_equipment_signed(client, headers)
    url = REPORT_URL.format(base=BASE, order_id=order["id"], equipment_id=equipment["id"])
    _with_context(factory, {"mobile.access", "technical_reports.capture", "lab_work_orders.use"}, actor_type="client")
    assert client.post(url, json={"report_type": "installation"}, headers=headers).status_code == 403
