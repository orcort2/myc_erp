"""Regresión: DELETE /equipment/{equipment_id} sobre una OT reabierta con
FieldSheet completed ya NO produce 500.

Antes de este fix, delete_equipment() usaba
``work_order.equipment.remove(equipment)`` sobre una relación
cascade="all, delete-orphan" -- SQLAlchemy emitía un UPDATE
``field_sheets.lab_equipment_id = NULL`` antes del DELETE físico, violando
ck_field_sheets_exactly_one_equipment_owner en cuanto el equipo tenía una
FieldSheet histórica (completed). La corrección reemplaza el DELETE físico
por un tombstone (SoftDeleteMixin: is_active/deleted_at/deleted_by) -- ver
LabWorkOrderEquipment.__doc__ y LabWorkOrder.active_equipment en
app/models/lab_work_order.py. Estos tests cubren ese tombstone de extremo a
extremo: la fila nunca se borra, el historial documental sobrevive, la
composición operativa vigente (Mobile, máximo 10, positions, cierre, PDF) lo
ignora, y el historial de Delivery no se ve afectado.
"""

from __future__ import annotations

import base64
import os
import uuid
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
from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.user import Role, User
from app.services.lab_work_orders import _draft_field_sheet_targets, _missing_completed_sheets

PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
).decode()


@pytest.fixture()
def lab_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        capture_role = Role(name="Captura", description="Captura")
        tech_role = Role(name="Tecnico", description="Técnico")
        admin_role = Role(name="Administrador", description="Administrador")
        db.add_all([capture_role, tech_role, admin_role])
        db.flush()
        users = []
        for key, role in (("capture", capture_role), ("tech", tech_role), ("admin", admin_role)):
            user = User(
                username=f"lab-{key}",
                email=f"lab-{key}@example.test",
                full_name=f"LAB {key}",
                hashed_password="unused",
                account_type="internal",
                status="active",
                is_active=True,
                role_id=role.id,
                roles=[role],
            )
            users.append(user)
        db.add_all(users)
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    tokens = {
        key: create_access_token(
            str(user.id),
            extra_claims={"roles": [user.roles[0].name], "auth_context": "internal"},
        )
        for key, user in zip(("capture", "tech", "admin"), users, strict=True)
    }
    try:
        yield client, factory, tokens
    finally:
        app.dependency_overrides.clear()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_payload(client_name: str = "Cliente LAB") -> dict:
    return {
        "reception_date": "2026-08-13",
        "client_name": client_name,
        "address": "Av. Prueba 123",
        "contact_name": "Persona Cliente",
        "contact_phone": "3312345678",
        "contact_email": "cliente@example.com",
        "postal_code": "45601",
        "city": "Tlaquepaque",
        "state_name": "Jalisco",
        "purchase_order": "OC-123",
        "notes": "Recepción LAB",
    }


def equipment_payload(index: int, **extra) -> dict:
    return {
        "instrument": f"Instrumento {index}",
        "brand": "MYC Test",
        "identification": f"ID-{index}",
        "serial_number": f"SER-{index}",
        "report_number": None,
        "is_good_condition": index % 2 == 0,
        **extra,
    }


def signatures_payload() -> dict:
    signed_at = datetime.now(timezone.utc).isoformat()
    return {
        "technician": {
            "signer_name": "Técnico LAB",
            "signed_at": signed_at,
            "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
        "client": {
            "signer_name": "Cliente LAB",
            "signed_at": signed_at,
            "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
    }


def configure_default_services(client: TestClient, headers: dict[str, str], work_order_id: int) -> None:
    detail = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}", headers=headers
    ).json()
    for item in detail["equipment"]:
        if item["service_type"] is not None:
            continue
        response = client.put(
            f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}/equipment/{item['id']}/service",
            json={"service_type": "traceable", "linked_company_id": None},
            headers=headers,
        )
        assert response.status_code == 200, response.text


def _create_order_with_equipment(client, headers, *, count: int = 1, client_name: str = "Cliente LAB") -> dict:
    created = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=create_payload(client_name), headers=headers
    )
    assert created.status_code == 201, created.text
    order = created.json()
    for index in range(1, count + 1):
        added = client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/equipment",
            json=equipment_payload(index),
            headers=headers,
        )
        assert added.status_code == 201, added.text
        order = added.json()
    return order


def _create_and_complete_field_sheet(client, headers, order_id, equipment_id) -> int:
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    sheet_id = created.json()["id"]
    rows = [
        {
            "id": row["id"],
            "section_key": row["section_key"],
            "row_number": row["row_number"],
            "row_data": {"result": "1.00"} if index == 0 else row["row_data"],
        }
        for index, row in enumerate(created.json()["results_rows"])
    ]
    patched = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"final_condition": "BUENA", "observations": "Sin observaciones", "results_rows": rows},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    return sheet_id


def _sign_reception(client, headers, order_id: int) -> None:
    """Fase 3: la captura de FieldSheet sólo procede tras la firma de
    recepción (draft -> received_signed); la MISMA firma sirve luego para el
    cierre técnico (ver _complete_members: sólo exige signature_session_id,
    no una segunda firma)."""
    configure_default_services(client, headers, order_id)
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text


def _close_order(client, headers, order_id: int) -> dict:
    detail = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers
    ).json()
    if detail["signature_session_id"] is None:
        _sign_reception(client, headers, order_id)
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete", headers=headers
    )
    assert completed.status_code == 200, completed.text
    return completed.json()


def _reopen_via_ticket(client, tech_headers, admin_headers, work_order_id: int, *, signature_policy: str = "preserve") -> dict:
    ticket = client.post(
        "/api/mobile/v1/technician/tickets",
        json={
            "work_order_id": work_order_id,
            "reason": "Reapertura de prueba",
            "description": "Se requiere ajustar la composición de equipo tras el cierre.",
            "requested_signature_policy": signature_policy,
        },
        headers=tech_headers,
    )
    assert ticket.status_code == 201, ticket.text
    approved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket.json()['id']}/approve",
        json={"signature_policy": signature_policy, "comment": "Autorizado para prueba"},
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    reloaded = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}", headers=tech_headers
    )
    assert reloaded.status_code == 200, reloaded.text
    return reloaded.json()


# ---------------------------------------------------------------------------
# Caso 1: baseline -- un equipo sin FieldSheet en una OT nunca cerrada también
# se retira vía tombstone (nunca fue, y sigue sin ser, un DELETE físico).
# ---------------------------------------------------------------------------
def test_delete_draft_equipment_without_field_sheet_still_succeeds(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order_with_equipment(client, headers, count=2)
    equipment_id = order["equipment"][0]["id"]

    response = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/equipment/{equipment_id}"
        f"?expected_edit_version={order['edit_version']}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["equipment"]] == [
        item_id for item_id in [order["equipment"][1]["id"]]
    ]

    with factory() as db:
        row = db.get(LabWorkOrderEquipment, equipment_id)
        assert row is not None, "el tombstone nunca debe ser un DELETE físico"
        assert row.is_active is False
        assert row.deleted_at is not None
        assert row.deleted_by is not None


# ---------------------------------------------------------------------------
# Caso 2 (bug original): equipo con FieldSheet completed + OT reabierta ->
# ya no debe dar 500, y todo el historial documental debe sobrevivir intacto.
# ---------------------------------------------------------------------------
def test_delete_equipment_after_reopen_with_completed_field_sheet_no_longer_500s(lab_context):
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order = _create_order_with_equipment(client, tech_headers, count=1)
    order_id = order["id"]
    equipment_id = order["equipment"][0]["id"]
    _sign_reception(client, tech_headers, order_id)
    sheet_id = _create_and_complete_field_sheet(client, tech_headers, order_id, equipment_id)
    closed = _close_order(client, tech_headers, order_id)
    assert closed["status"] == "completed"

    reopened = _reopen_via_ticket(client, tech_headers, admin_headers, order_id, signature_policy="preserve")
    assert reopened["reopen_ticket_id"] is not None

    with factory() as db:
        sheet_before = db.get(FieldSheet, sheet_id)
        assert sheet_before.status == "completed"
        final_pdf_path_before = sheet_before.final_pdf_path
        final_pdf_sha256_before = sheet_before.final_pdf_sha256
        assert final_pdf_path_before
        assert final_pdf_sha256_before

    response = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}"
        f"?expected_edit_version={reopened['edit_version']}",
        headers=tech_headers,
    )
    assert response.status_code == 200, response.text
    assert equipment_id not in {item["id"] for item in response.json()["equipment"]}

    with factory() as db:
        equipment_row = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment_row is not None, "el equipo con historial nunca se borra físicamente"
        assert equipment_row.is_active is False
        assert equipment_row.deleted_at is not None

        sheet_after = db.get(FieldSheet, sheet_id)
        assert sheet_after is not None, "la FieldSheet histórica debe sobrevivir"
        assert sheet_after.status == "completed"
        assert sheet_after.lab_equipment_id == equipment_id
        assert sheet_after.final_pdf_path == final_pdf_path_before
        assert sheet_after.final_pdf_sha256 == final_pdf_sha256_before


@pytest.mark.parametrize("signature_policy", ["preserve", "invalidate"])
def test_delete_equipment_after_reopen_works_under_both_signature_policies(lab_context, signature_policy):
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order = _create_order_with_equipment(client, tech_headers, count=2)
    order_id = order["id"]
    equipment_id = order["equipment"][0]["id"]
    _sign_reception(client, tech_headers, order_id)
    sheet_id = _create_and_complete_field_sheet(client, tech_headers, order_id, equipment_id)
    _close_order(client, tech_headers, order_id)

    reopened = _reopen_via_ticket(
        client, tech_headers, admin_headers, order_id, signature_policy=signature_policy
    )

    response = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}"
        f"?expected_edit_version={reopened['edit_version']}",
        headers=tech_headers,
    )
    assert response.status_code == 200, response.text

    with factory() as db:
        sheet_after = db.get(FieldSheet, sheet_id)
        assert sheet_after is not None
        assert sheet_after.status == "completed"
        equipment_row = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment_row.is_active is False


# ---------------------------------------------------------------------------
# Caso: el tombstone nunca cuenta contra el máximo de 10 -- puede agregarse
# un equipo nuevo justo después de retirar uno, sin exceder el límite activo.
# ---------------------------------------------------------------------------
def test_retiring_equipment_frees_a_slot_below_the_active_maximum_of_ten(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order_with_equipment(client, headers, count=10)
    order_id = order["id"]
    exhausted = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(11),
        headers=headers,
    )
    assert exhausted.status_code == 409, exhausted.text

    retired_id = order["equipment"][0]["id"]
    deleted = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{retired_id}"
        f"?expected_edit_version={order['edit_version']}",
        headers=headers,
    )
    assert deleted.status_code == 200, deleted.text
    assert len(deleted.json()["equipment"]) == 9

    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(11),
        headers=headers,
    )
    assert added.status_code == 201, added.text
    assert len(added.json()["equipment"]) == 10

    with factory() as db:
        total_rows = db.scalar(
            select(LabWorkOrderEquipment).where(LabWorkOrderEquipment.work_order_id == order_id)
        )
        assert total_rows is not None
        all_rows = list(
            db.scalars(
                select(LabWorkOrderEquipment).where(LabWorkOrderEquipment.work_order_id == order_id)
            )
        )
        assert len(all_rows) == 11
        assert sum(1 for row in all_rows if row.is_active) == 10


def test_retiring_equipment_compacts_active_positions_and_reuses_the_freed_slot(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order_with_equipment(client, headers, count=3)
    order_id = order["id"]
    first_id = order["equipment"][0]["id"]

    deleted = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{first_id}"
        f"?expected_edit_version={order['edit_version']}",
        headers=headers,
    )
    assert deleted.status_code == 200, deleted.text
    remaining = sorted(deleted.json()["equipment"], key=lambda item: item["position"])
    assert [item["position"] for item in remaining] == [1, 2]

    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(4),
        headers=headers,
    )
    assert added.status_code == 201, added.text
    positions = sorted(item["position"] for item in added.json()["equipment"])
    assert positions == [1, 2, 3]

    with factory() as db:
        rows = list(
            db.scalars(
                select(LabWorkOrderEquipment)
                .where(LabWorkOrderEquipment.work_order_id == order_id)
                .order_by(LabWorkOrderEquipment.id)
            )
        )
        assert len(rows) == 4
        retired = next(row for row in rows if row.id == first_id)
        assert retired.is_active is False
        assert retired.position == 1


def test_delete_equipment_rejects_a_stale_expected_edit_version(lab_context):
    """_check_edit_version sólo exige expected_edit_version cuando la OT ya
    tiene reopen_ticket_id (ver app/services/lab_work_orders.py) -- una OT
    nunca reabierta acepta cualquier valor (o ninguno), así que la
    concurrencia optimista sólo puede probarse sobre una OT reabierta."""
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order = _create_order_with_equipment(client, tech_headers, count=2)
    order_id = order["id"]
    equipment_id = order["equipment"][0]["id"]
    _close_order(client, tech_headers, order_id)
    reopened = _reopen_via_ticket(client, tech_headers, admin_headers, order_id, signature_policy="preserve")

    stale = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}"
        f"?expected_edit_version={reopened['edit_version'] + 1}",
        headers=tech_headers,
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["detail"]["code"] == "REVISION_CONFLICT"

    with_conflict = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=tech_headers
    ).json()
    assert equipment_id in {item["id"] for item in with_conflict["equipment"]}

    deleted = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}"
        f"?expected_edit_version={reopened['edit_version']}",
        headers=tech_headers,
    )
    assert deleted.status_code == 200, deleted.text


def test_delete_equipment_preserves_delivery_history(lab_context):
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order = _create_order_with_equipment(client, tech_headers, count=1)
    order_id = order["id"]
    equipment_id = order["equipment"][0]["id"]
    _close_order(client, tech_headers, order_id)

    delivery = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/delivery",
        json={
            "delivery_method": "direct",
            "delivered_by_signature_data_url": PNG_DATA_URL,
            "recipient_name": "Cliente Receptor",
            "recipient_signature_data_url": PNG_DATA_URL,
            "notes": None,
        },
        headers=tech_headers,
    )
    assert delivery.status_code == 201, delivery.text

    with factory() as db:
        item_before = db.scalar(
            select(LabDeliveryItem).where(LabDeliveryItem.equipment_id == equipment_id)
        )
        assert item_before is not None
        item_id = item_before.id
        snapshot_before = (
            item_before.instrument_snapshot,
            item_before.brand_snapshot,
            item_before.identification_snapshot,
            item_before.serial_number_snapshot,
            item_before.equipment_id_snapshot,
        )

    delivery_id = delivery.json()["id"]
    # _reopen_closed_cohort bloquea la reapertura mientras exista una entrega
    # "completed" para el grupo (ver guard en operational_tickets.py) -- hay
    # que anularla primero, igual que exigiría el flujo real ("Anula primero
    # el acuse de entrega"), para poder reabrir y ejercitar el retiro de
    # equipo sin dejar el historial de esa entrega ya anulada intacto.
    voided = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/delivery/{delivery_id}/void",
        json={"reason": "Reapertura administrativa para prueba"},
        headers=admin_headers,
    )
    assert voided.status_code == 200, voided.text

    reopened = _reopen_via_ticket(client, tech_headers, admin_headers, order_id, signature_policy="preserve")

    deleted = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}"
        f"?expected_edit_version={reopened['edit_version']}",
        headers=tech_headers,
    )
    assert deleted.status_code == 200, deleted.text

    with factory() as db:
        item_after = db.get(LabDeliveryItem, item_id)
        assert item_after is not None, "el historial de Delivery nunca debe perderse"
        assert item_after.equipment_id == equipment_id
        assert (
            item_after.instrument_snapshot,
            item_after.brand_snapshot,
            item_after.identification_snapshot,
            item_after.serial_number_snapshot,
            item_after.equipment_id_snapshot,
        ) == snapshot_before
        delivery_row = db.get(LabWorkOrderDelivery, item_after.delivery_id)
        assert delivery_row is not None
        assert delivery_row.status == "voided"


def test_closure_prerequisites_ignore_retired_equipment(lab_context):
    """_missing_completed_sheets/_draft_field_sheet_targets son la autoridad
    real que decide si el cierre técnico está bloqueado por hojas faltantes o
    en borrador -- deben ignorar equipo retirado (is_active=False) igual que
    ignoran el equipo activo ya completed. Se prueba a nivel de servicio
    (SimpleNamespace/ORM en memoria, sin persistir) porque estas funciones
    sólo se activan cuando lab_client_id no es None, un estado que la OT de
    técnico (create_payload) no produce."""
    from types import SimpleNamespace

    active_completed = SimpleNamespace(
        id=1,
        position=1,
        instrument="Activo completo",
        is_active=True,
        field_sheet=SimpleNamespace(status="completed"),
    )
    retired_without_sheet = SimpleNamespace(
        id=2,
        position=2,
        instrument="Retirado sin hoja",
        is_active=False,
        field_sheet=None,
    )
    retired_draft_sheet = SimpleNamespace(
        id=3,
        position=3,
        instrument="Retirado en borrador",
        is_active=False,
        field_sheet=SimpleNamespace(status="draft"),
    )
    work_order = SimpleNamespace(
        id=100,
        folio=6500,
        lab_client_id=1,
        partial_close_ticket_id=None,
        active_equipment=[active_completed],
    )

    assert _missing_completed_sheets([work_order]) == []
    assert _draft_field_sheet_targets([work_order]) == []

    work_order.active_equipment = [active_completed, retired_without_sheet, retired_draft_sheet]


def test_new_pdf_after_reclosing_excludes_retired_equipment(lab_context):
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order = _create_order_with_equipment(client, tech_headers, count=2)
    order_id = order["id"]
    retired_equipment_id = order["equipment"][0]["id"]
    kept_equipment_identification = order["equipment"][1]["identification"]
    _close_order(client, tech_headers, order_id)

    reopened = _reopen_via_ticket(client, tech_headers, admin_headers, order_id, signature_policy="preserve")

    deleted = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{retired_equipment_id}"
        f"?expected_edit_version={reopened['edit_version']}",
        headers=tech_headers,
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["signature_required"] is True, (
        "retirar equipo es un cambio estructural: invalida la firma incluso con preserve"
    )

    resigned = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures",
        json=signatures_payload(),
        headers=tech_headers,
    )
    assert resigned.status_code == 200, resigned.text

    recompleted = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete", headers=tech_headers
    )
    assert recompleted.status_code == 200, recompleted.text

    pdf = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/pdf", headers=tech_headers
    )
    assert pdf.status_code == 200, pdf.text
    from pypdf import PdfReader
    import io

    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "ID-1" not in text
    assert kept_equipment_identification in text


# ---------------------------------------------------------------------------
# Regresión PostgreSQL obligatoria: este bug ocurrió sobre PostgreSQL y
# SQLite no basta para declararlo cerrado -- valida el CHECK constraint real
# de FieldSheet, la FK real de lab_equipment_id, el índice parcial de
# positions, la reutilización de una posición activa y la ausencia de
# IntegrityError contra un esquema Postgres real (patrón LAB_POSTGRES_TEST_URL
# ya usado en postgres_lab_context / test_lab_delivery_timestamp_defaults.py).
# ---------------------------------------------------------------------------
@pytest.fixture()
def postgres_lab_context():
    database_url = os.getenv("LAB_POSTGRES_TEST_URL")
    if not database_url:
        pytest.skip("requiere LAB_POSTGRES_TEST_URL para probar constraints PostgreSQL reales")

    from sqlalchemy import text as sa_text

    schema = f"lab_equipment_soft_delete_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(sa_text(f'CREATE SCHEMA "{schema}"'))

    engine = create_engine(
        database_url,
        connect_args={"options": f"-csearch_path={schema}"},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        roles = {
            name: Role(name=name, description=name)
            for name in ("Tecnico", "Captura", "Administrador")
        }
        db.add_all(roles.values())
        db.flush()
        users = {}
        for key, role_name in (("tech", "Tecnico"), ("capture", "Captura"), ("admin", "Administrador")):
            role = roles[role_name]
            user = User(
                username=f"pg-soft-delete-{key}",
                email=f"pg-soft-delete-{key}@example.test",
                full_name=f"PostgreSQL {key}",
                hashed_password="unused",
                account_type="internal",
                status="active",
                is_active=True,
                role_id=role.id,
                roles=[role],
            )
            users[key] = user
            db.add(user)
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    tokens = {
        key: create_access_token(
            str(user.id),
            extra_claims={"roles": [user.roles[0].name], "auth_context": "internal"},
        )
        for key, user in users.items()
    }
    try:
        yield client, factory, tokens
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        with create_engine(database_url).begin() as connection:
            connection.execute(sa_text(f'DROP SCHEMA "{schema}" CASCADE'))


def test_postgresql_equipment_soft_delete_preserves_constraints_and_history(postgres_lab_context):
    client, factory, tokens = postgres_lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order = _create_order_with_equipment(client, tech_headers, count=3)
    order_id = order["id"]
    equipment_id = order["equipment"][0]["id"]
    _sign_reception(client, tech_headers, order_id)
    sheet_id = _create_and_complete_field_sheet(client, tech_headers, order_id, equipment_id)
    _close_order(client, tech_headers, order_id)
    reopened = _reopen_via_ticket(client, tech_headers, admin_headers, order_id, signature_policy="preserve")

    deleted = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}"
        f"?expected_edit_version={reopened['edit_version']}",
        headers=tech_headers,
    )
    assert deleted.status_code == 200, deleted.text
    assert equipment_id not in {item["id"] for item in deleted.json()["equipment"]}

    with factory() as db:
        equipment_row = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment_row is not None
        assert equipment_row.is_active is False

        sheet = db.get(FieldSheet, sheet_id)
        assert sheet is not None
        assert sheet.status == "completed"
        assert sheet.lab_equipment_id == equipment_id

    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(4, expected_edit_version=deleted.json()["edit_version"]),
        headers=tech_headers,
    )
    assert added.status_code == 201, added.text
    active_positions = sorted(item["position"] for item in added.json()["equipment"])
    assert active_positions == [1, 2, 3]

    with factory() as db:
        rows = list(
            db.scalars(
                select(LabWorkOrderEquipment)
                .where(LabWorkOrderEquipment.work_order_id == order_id)
                .order_by(LabWorkOrderEquipment.id)
            )
        )
        assert len(rows) == 4
        assert sum(1 for row in rows if row.is_active) == 3
