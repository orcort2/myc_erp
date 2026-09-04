from __future__ import annotations

import base64
import io
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.lab_delivery_group_receipt import LabDeliveryGroupReceipt
from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_work_order import LabWorkOrder
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.operational_ticket import OperationalTicket
from app.models.user import Role, User


PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
).decode()
INVALID_SIGNATURE_URL = "data:image/png;base64,bm90LXBuZw=="


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
        technician_role = Role(name="Tecnico", description="Técnico")
        admin_role = Role(name="Administrador", description="Administrador")
        db.add_all([technician_role, admin_role])
        db.flush()
        users = []
        for key, role in (("tech", technician_role), ("admin", admin_role)):
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
        for key, user in zip(("tech", "admin"), users, strict=True)
    }
    try:
        yield client, factory, tokens
    finally:
        app.dependency_overrides.clear()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_payload(client_name: str = "Cliente Entrega") -> dict:
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
        "is_good_condition": True,
        **extra,
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


def signatures_payload() -> dict:
    signed_at = datetime.now(timezone.utc).isoformat()
    return {
        "technician": {"signer_name": "Técnico LAB", "signed_at": signed_at, "version": 1, "signature_data_url": PNG_DATA_URL},
        "client": {"signer_name": "Cliente LAB", "signed_at": signed_at, "version": 1, "signature_data_url": PNG_DATA_URL},
    }


def delivery_payload(**extra) -> dict:
    return {
        "delivery_method": "direct",
        "delivered_by_signature_data_url": PNG_DATA_URL,
        "recipient_name": "María Receptora",
        "recipient_signature_data_url": PNG_DATA_URL,
        **extra,
    }


def _completed_single(client: TestClient, token: str, name: str, *, equipment_count: int = 1) -> dict:
    """Grupo de UNA sola OT (root_work_order_id apunta a sí misma), técnicamente cerrada."""
    headers = auth(token)
    created = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=create_payload(name), headers=headers
    ).json()
    for index in range(equipment_count):
        response = client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{created['id']}/equipment",
            json=equipment_payload(index + 1),
            headers=headers,
        )
        assert response.status_code == 201, response.text
    configure_default_services(client, headers, created["id"])
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{created['id']}/signatures",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{created['id']}/complete", headers=headers
    )
    assert completed.status_code == 200, completed.text
    return completed.json()


def _completed_group(client: TestClient, token: str, name: str, *, member_count: int = 2) -> list[dict]:
    """Grupo de VARIAS OT (root_work_order_id compartido), todas cerradas."""
    headers = auth(token)
    group = client.post(
        "/api/mobile/v1/technician/lab-work-orders/groups",
        json={**create_payload(name), "quantity": member_count},
        headers=headers,
    )
    assert group.status_code == 201, group.text
    root_id = group.json()["id"]
    for member in group.json()["related_work_orders"]:
        response = client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{member['id']}/equipment",
            json=equipment_payload(member["sequence_number"]),
            headers=headers,
        )
        assert response.status_code == 201, response.text
        configure_default_services(client, headers, member["id"])
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{root_id}/signatures",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{root_id}/complete", headers=headers
    )
    assert completed.status_code == 200, completed.text
    members = [
        client.get(f"/api/mobile/v1/technician/lab-work-orders/{item['id']}", headers=headers).json()
        for item in completed.json()["related_work_orders"]
    ]
    return members


def _delivery_status(client, token, work_order_id) -> dict:
    return client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}/delivery", headers=auth(token)
    ).json()


# ---------------------------------------------------------------------------
# NORMAL
# ---------------------------------------------------------------------------


def test_normal_delivery_single_ot_delivers_all_equipment(lab_context):
    client, factory, tokens = lab_context
    completed = _completed_single(client, tokens["tech"], "Cliente normal", equipment_count=2)
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"

    status_before = _delivery_status(client, tokens["tech"], completed["id"])
    assert status_before["total_equipment"] == 2
    assert len(status_before["pending_equipment"]) == 2
    assert status_before["group_complete"] is False

    response = client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=auth(tokens["tech"]))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["delivery_type"] == "full"
    assert body["exhibition_number"] == 1
    assert len(body["items"]) == 2
    assert body["voucher_available"] is True

    status_after = _delivery_status(client, tokens["tech"], completed["id"])
    assert status_after["group_complete"] is True
    assert status_after["pending_equipment"] == []
    assert status_after["final_receipt_available"] is True

    with factory() as db:
        assert db.get(LabWorkOrder, completed["id"]).departure_date is not None


def test_normal_delivery_multi_ot_group_includes_all_pending_across_members(lab_context):
    client, factory, tokens = lab_context
    members = _completed_group(client, tokens["tech"], "Cliente multi OT", member_count=3)
    root_id = members[0]["root_work_order_id"]
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{root_id}"

    status_before = _delivery_status(client, tokens["tech"], root_id)
    assert status_before["total_equipment"] == 3
    assert {item["work_order_id"] for item in status_before["pending_equipment"]} == {m["id"] for m in members}

    response = client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=auth(tokens["tech"]))
    assert response.status_code == 201, response.text
    assert len(response.json()["items"]) == 3
    assert {item["work_order_id"] for item in response.json()["items"]} == {m["id"] for m in members}

    with factory() as db:
        for member in members:
            assert db.get(LabWorkOrder, member["id"]).departure_date is not None


def test_delivery_requires_delivered_by_and_recipient_signatures(lab_context):
    client, _factory, tokens = lab_context
    completed = _completed_single(client, tokens["tech"], "Cliente firma")
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"
    headers = auth(tokens["tech"])

    bad_delivered_by = client.post(
        f"{endpoint}/delivery",
        json=delivery_payload(delivered_by_signature_data_url=INVALID_SIGNATURE_URL),
        headers=headers,
    )
    assert bad_delivered_by.status_code == 422

    bad_recipient = client.post(
        f"{endpoint}/delivery",
        json=delivery_payload(recipient_signature_data_url=INVALID_SIGNATURE_URL),
        headers=headers,
    )
    assert bad_recipient.status_code == 422


def test_delivery_blocked_while_group_not_fully_closed(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    open_order = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=create_payload("Todavía abierta"), headers=headers
    ).json()
    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{open_order['id']}/delivery",
        json=delivery_payload(),
        headers=headers,
    )
    assert response.status_code == 409


def test_delivery_voucher_pdf_is_scoped_to_its_own_exhibition(lab_context):
    client, _factory, tokens = lab_context
    completed = _completed_single(client, tokens["tech"], "Cliente voucher")
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"
    headers = auth(tokens["tech"])
    delivered = client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=headers)
    delivery_id = delivered.json()["id"]
    voucher = client.get(f"{endpoint}/delivery/{delivery_id}/pdf", headers=headers)
    assert voucher.status_code == 200 and voucher.content.startswith(b"%PDF")
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(voucher.content)).pages)
    assert "ACUSE DE ENTREGA DE EQUIPOS" in text
    assert "Exhibición 1" in text
    assert "María Receptora" in text
    assert "Cliente voucher" in text


def test_ot_departure_date_only_set_when_its_own_last_pending_equipment_delivered(lab_context):
    """Sección 15/8: cada OT proyecta su departure_date independientemente --
    entregar los equipos de UNA OT del grupo no debe fijar departure_date de
    otra OT del mismo grupo que todavía tenga equipos pendientes."""
    client, factory, tokens = lab_context
    admin_headers = auth(tokens["admin"])
    tech_headers = auth(tokens["tech"])
    members = _completed_group(client, tokens["tech"], "Cliente parcial por OT", member_count=2)
    root_id = members[0]["root_work_order_id"]
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{root_id}"
    only_first_ot_equipment = [item["id"] for item in members[0]["equipment"]]

    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={
            "work_order_id": root_id,
            "requested_equipment_ids": only_first_ot_equipment,
            "reason": "Cliente recoge un solo equipo",
            "description": "Entrega parcial de prueba",
        },
        headers=tech_headers,
    )
    assert ticket.status_code == 201, ticket.text
    ticket_id = ticket.json()["id"]
    approved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket_id}/approve-partial-delivery", json={}, headers=admin_headers
    )
    assert approved.status_code == 200, approved.text

    executed = client.post(
        f"{endpoint}/delivery/partial/{ticket_id}", json=delivery_payload(), headers=tech_headers
    )
    assert executed.status_code == 201, executed.text
    assert executed.json()["delivery_type"] == "partial"

    with factory() as db:
        assert db.get(LabWorkOrder, members[0]["id"]).departure_date is not None
        assert db.get(LabWorkOrder, members[1]["id"]).departure_date is None

    status_mid = _delivery_status(client, tokens["tech"], root_id)
    assert status_mid["group_complete"] is False
    assert len(status_mid["pending_equipment"]) == 1

    complete_rest = client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=tech_headers)
    assert complete_rest.status_code == 201, complete_rest.text
    assert complete_rest.json()["exhibition_number"] == 2
    assert complete_rest.json()["delivery_type"] == "full"

    with factory() as db:
        assert db.get(LabWorkOrder, members[1]["id"]).departure_date is not None

    status_final = _delivery_status(client, tokens["tech"], root_id)
    assert status_final["group_complete"] is True
    assert status_final["final_receipt_available"] is True


# ---------------------------------------------------------------------------
# PARCIAL
# ---------------------------------------------------------------------------


def test_partial_delivery_requires_approved_ticket(lab_context):
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    completed = _completed_single(client, tokens["tech"], "Cliente sin aprobar", equipment_count=2)
    equipment_ids = [item["id"] for item in completed["equipment"]]
    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={
            "work_order_id": completed["id"],
            "requested_equipment_ids": equipment_ids[:1],
            "reason": "Motivo",
            "description": "Descripción",
        },
        headers=tech_headers,
    )
    assert ticket.status_code == 201, ticket.text
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"
    blocked = client.post(
        f"{endpoint}/delivery/partial/{ticket.json()['id']}", json=delivery_payload(), headers=tech_headers
    )
    assert blocked.status_code == 409


def test_partial_delivery_ticket_rejects_equipment_outside_group(lab_context):
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    completed_a = _completed_single(client, tokens["tech"], "Grupo A")
    completed_b = _completed_single(client, tokens["tech"], "Grupo B")
    foreign_equipment_id = completed_b["equipment"][0]["id"]
    response = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={
            "work_order_id": completed_a["id"],
            "requested_equipment_ids": [foreign_equipment_id],
            "reason": "Motivo",
            "description": "Descripción",
        },
        headers=tech_headers,
    )
    assert response.status_code == 422


def test_partial_delivery_approval_does_not_create_delivery_and_ticket_not_reusable(lab_context):
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente aprobación", equipment_count=2)
    equipment_ids = [item["id"] for item in completed["equipment"]]
    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={
            "work_order_id": completed["id"],
            "requested_equipment_ids": equipment_ids[:1],
            "reason": "Motivo",
            "description": "Descripción",
        },
        headers=tech_headers,
    ).json()

    approved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}/approve-partial-delivery",
        json={"comment": "Autorizado"},
        headers=admin_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    with factory() as db:
        assert db.scalar(select(LabWorkOrderDelivery.id)) is None

    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"
    executed = client.post(
        f"{endpoint}/delivery/partial/{ticket['id']}", json=delivery_payload(), headers=tech_headers
    )
    assert executed.status_code == 201, executed.text
    assert [item["equipment_id"] for item in executed.json()["items"]] == [equipment_ids[0]]

    with factory() as db:
        resolved_ticket = db.get(OperationalTicket, ticket["id"])
        assert resolved_ticket.status == "resolved"

    reused = client.post(
        f"{endpoint}/delivery/partial/{ticket['id']}", json=delivery_payload(), headers=tech_headers
    )
    assert reused.status_code == 409


def test_partial_delivery_execution_exhibition_increments_and_pending_updates(lab_context):
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente exhibiciones", equipment_count=3)
    equipment_ids = [item["id"] for item in completed["equipment"]]
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"

    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={
            "work_order_id": completed["id"],
            "requested_equipment_ids": equipment_ids[:2],
            "reason": "Motivo",
            "description": "Descripción",
        },
        headers=tech_headers,
    ).json()
    client.post(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}/approve-partial-delivery", json={}, headers=admin_headers
    )
    first = client.post(
        f"{endpoint}/delivery/partial/{ticket['id']}", json=delivery_payload(), headers=tech_headers
    )
    assert first.json()["exhibition_number"] == 1

    status_mid = _delivery_status(client, tokens["tech"], completed["id"])
    assert len(status_mid["pending_equipment"]) == 1
    assert status_mid["pending_equipment"][0]["equipment_id"] == equipment_ids[2]

    # Sección 18: se puede pedir OTRA parcial mientras haya pendientes.
    second_ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={
            "work_order_id": completed["id"],
            "requested_equipment_ids": equipment_ids[2:],
            "reason": "Motivo 2",
            "description": "Descripción 2",
        },
        headers=tech_headers,
    )
    assert second_ticket.status_code == 201, second_ticket.text


def test_completar_entrega_delivers_remaining_pending_as_full(lab_context):
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente completar", equipment_count=2)
    equipment_ids = [item["id"] for item in completed["equipment"]]
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"

    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={
            "work_order_id": completed["id"],
            "requested_equipment_ids": equipment_ids[:1],
            "reason": "Motivo",
            "description": "Descripción",
        },
        headers=tech_headers,
    ).json()
    client.post(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}/approve-partial-delivery", json={}, headers=admin_headers
    )
    client.post(f"{endpoint}/delivery/partial/{ticket['id']}", json=delivery_payload(), headers=tech_headers)

    complete_rest = client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=tech_headers)
    assert complete_rest.status_code == 201, complete_rest.text
    assert complete_rest.json()["delivery_type"] == "full"
    assert [item["equipment_id"] for item in complete_rest.json()["items"]] == [equipment_ids[1]]

    status = _delivery_status(client, tokens["tech"], completed["id"])
    assert status["group_complete"] is True


# ---------------------------------------------------------------------------
# FINAL / MISMO CONTACTO
# ---------------------------------------------------------------------------


def test_final_receipt_generated_when_remaining_zero_with_correct_exhibition_count(lab_context):
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente resumen final", equipment_count=2)
    equipment_ids = [item["id"] for item in completed["equipment"]]
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"

    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={
            "work_order_id": completed["id"],
            "requested_equipment_ids": equipment_ids[:1],
            "reason": "Motivo",
            "description": "Descripción",
        },
        headers=tech_headers,
    ).json()
    client.post(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}/approve-partial-delivery", json={}, headers=admin_headers
    )
    first = client.post(
        f"{endpoint}/delivery/partial/{ticket['id']}",
        json=delivery_payload(recipient_name="Juan Pérez"),
        headers=tech_headers,
    )
    assert first.json()["delivery_type"] == "partial"
    second = client.post(
        f"{endpoint}/delivery", json=delivery_payload(recipient_name="Juan Pérez"), headers=tech_headers
    )
    assert second.status_code == 201

    status = _delivery_status(client, tokens["tech"], completed["id"])
    assert status["final_receipt_available"] is True
    assert status["final_receipt_version"] == 1

    receipt_pdf = client.get(f"{endpoint}/delivery/final-receipt/pdf", headers=tech_headers)
    assert receipt_pdf.status_code == 200 and receipt_pdf.content.startswith(b"%PDF")
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(receipt_pdf.content)).pages)
    assert "RESUMEN FINAL DE ENTREGA" in text
    assert "entregados en 2 exhibiciones" in text
    assert "Juan Pérez" in text
    assert "Mismo contacto" in text

    with factory() as db:
        assert db.scalar(select(LabDeliveryGroupReceipt.exhibitions_count)) == 2


def test_final_receipt_shows_real_name_when_recipient_differs(lab_context):
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente distinto receptor", equipment_count=2)
    equipment_ids = [item["id"] for item in completed["equipment"]]
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"

    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={
            "work_order_id": completed["id"],
            "requested_equipment_ids": equipment_ids[:1],
            "reason": "Motivo",
            "description": "Descripción",
        },
        headers=tech_headers,
    ).json()
    client.post(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}/approve-partial-delivery", json={}, headers=admin_headers
    )
    client.post(
        f"{endpoint}/delivery/partial/{ticket['id']}",
        json=delivery_payload(recipient_name="Ana López"),
        headers=tech_headers,
    )
    client.post(
        f"{endpoint}/delivery", json=delivery_payload(recipient_name="Beto Ramírez"), headers=tech_headers
    )
    receipt_pdf = client.get(f"{endpoint}/delivery/final-receipt/pdf", headers=tech_headers)
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(receipt_pdf.content)).pages)
    assert "Ana López" in text
    assert "Beto Ramírez" in text
    assert "Mismo contacto" not in text


def test_voided_exhibitions_do_not_count_toward_final_receipt_n(lab_context):
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente void y final", equipment_count=2)
    equipment_ids = [item["id"] for item in completed["equipment"]]
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"

    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={
            "work_order_id": completed["id"],
            "requested_equipment_ids": equipment_ids[:1],
            "reason": "Motivo",
            "description": "Descripción",
        },
        headers=tech_headers,
    ).json()
    client.post(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}/approve-partial-delivery", json={}, headers=admin_headers
    )
    first = client.post(
        f"{endpoint}/delivery/partial/{ticket['id']}", json=delivery_payload(), headers=tech_headers
    ).json()
    client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=tech_headers)

    voided = client.post(
        f"{endpoint}/delivery/{first['id']}/void", json={"reason": "Error de captura"}, headers=admin_headers
    )
    assert voided.status_code == 200

    status = _delivery_status(client, tokens["tech"], completed["id"])
    assert status["group_complete"] is False
    assert status["final_receipt_available"] is False


# ---------------------------------------------------------------------------
# VOID
# ---------------------------------------------------------------------------


def test_void_returns_items_to_pending_and_recalculates_departure_date(lab_context):
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente void", equipment_count=1)
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"

    delivered = client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=tech_headers)
    delivery_id = delivered.json()["id"]
    with factory() as db:
        assert db.get(LabWorkOrder, completed["id"]).departure_date is not None

    voided = client.post(
        f"{endpoint}/delivery/{delivery_id}/void", json={"reason": "Acuse capturado por error"}, headers=admin_headers
    )
    assert voided.status_code == 200
    assert voided.json()["status"] == "voided"

    with factory() as db:
        assert db.get(LabWorkOrder, completed["id"]).departure_date is None

    status = _delivery_status(client, tokens["tech"], completed["id"])
    assert len(status["pending_equipment"]) == 1
    assert status["group_complete"] is False


def test_void_allows_new_delivery_and_preserves_historical_voucher(lab_context):
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente reemplazo", equipment_count=1)
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"

    delivered = client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=tech_headers)
    delivery_id = delivered.json()["id"]
    client.post(f"{endpoint}/delivery/{delivery_id}/void", json={"reason": "Error"}, headers=admin_headers)

    replacement = client.post(
        f"{endpoint}/delivery", json=delivery_payload(recipient_name="Nuevo receptor"), headers=tech_headers
    )
    assert replacement.status_code == 201, replacement.text
    assert replacement.json()["exhibition_number"] == 2

    old_voucher = client.get(f"{endpoint}/delivery/{delivery_id}/pdf", headers=tech_headers)
    assert old_voucher.status_code == 200 and old_voucher.content.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# GUARDS: reopen / cancel
# ---------------------------------------------------------------------------


def test_delivered_equipment_blocks_reopen_and_cancel(lab_context):
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente guard", equipment_count=1)
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"
    client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=tech_headers)

    reopen = client.post(
        f"{endpoint}/reopen",
        json={"requested_signature_policy": "preserve", "reason": "Corregir"},
        headers=admin_headers,
    )
    assert reopen.status_code == 409

    cancel = client.post(f"{endpoint}/cancel", json={"reason": "Cancelar"}, headers=admin_headers)
    assert cancel.status_code == 409


def test_delivered_equipment_blocks_delete(lab_context):
    """CASO A -- AJUSTE anulación administrativa de entrega: delete_work_order
    gana el mismo guard explícito que cancel_work_order ya tenía. Sólo una
    entrega VIGENTE (completed) bloquea la eliminación, antes de cualquier
    mutación; nada se borra."""
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente guard delete", equipment_count=1)
    work_order_id = completed["id"]
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}"
    delivery = client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=tech_headers)
    assert delivery.status_code == 201, delivery.text

    delete_while_delivered = client.delete(endpoint, headers=admin_headers)
    assert delete_while_delivered.status_code == 409
    assert "entrega física de equipos" in delete_while_delivered.json()["detail"]

    with factory() as db:
        assert db.get(LabWorkOrder, work_order_id) is not None


def test_voided_delivery_of_a_single_ot_no_longer_blocks_delete_and_preserves_the_full_history(lab_context):
    """CASO B + CASO F -- una vez anulada, Delivery deja de bloquear DELETE.
    La OT y su equipo desaparecen; el delivery sigue voided con voucher/hash/
    firmas intactos; el LabDeliveryItem sobrevive con live refs en NULL pero
    *_snapshot intacto; el receipt final (el grupo quedó completo con esta
    única entrega) también sobrevive con root NULL. Cancelar después de void
    sigue funcionando igual que antes (guard sin cambios)."""
    from app.models.lab_work_order import LabWorkOrderEquipment

    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente void delete", equipment_count=1)
    work_order_id = completed["id"]
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}"

    delivery = client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=tech_headers)
    assert delivery.status_code == 201, delivery.text
    delivery_id = delivery.json()["id"]
    item = delivery.json()["items"][0]
    item_id, equipment_id = item["id"], item["equipment_id"]

    with factory() as db:
        before = db.get(LabWorkOrderDelivery, delivery_id)
        voucher_before, voucher_hash_before = before.voucher_pdf, before.voucher_pdf_sha256
        assert voucher_before, "fixture debe generar un voucher real antes de anular"
        receipt_before = db.scalar(select(LabDeliveryGroupReceipt))
        assert receipt_before is not None, "una sola OT con toda su entrega completa el grupo -- debe existir receipt"
        receipt_id, receipt_pdf_before = receipt_before.id, receipt_before.pdf

    void_response = client.post(
        f"{endpoint}/delivery/{delivery_id}/void",
        json={"reason": "Corrección administrativa"},
        headers=admin_headers,
    )
    assert void_response.status_code == 200, void_response.text

    delete_after_void = client.delete(endpoint, headers=admin_headers)
    assert delete_after_void.status_code == 204, delete_after_void.text

    with factory() as db:
        assert db.get(LabWorkOrder, work_order_id) is None
        assert db.get(LabWorkOrderEquipment, equipment_id) is None

        reloaded_delivery = db.get(LabWorkOrderDelivery, delivery_id)
        assert reloaded_delivery is not None, "el historial de entrega nunca debe borrarse"
        assert reloaded_delivery.status == "voided"
        assert reloaded_delivery.voucher_pdf == voucher_before
        assert reloaded_delivery.voucher_pdf_sha256 == voucher_hash_before
        assert reloaded_delivery.delivered_by_signature_data_url
        assert reloaded_delivery.recipient_signature_data_url
        assert reloaded_delivery.root_work_order_id is None
        assert reloaded_delivery.root_work_order_id_snapshot == work_order_id
        assert reloaded_delivery.root_work_order_folio_snapshot == completed["folio"]

        reloaded_item = db.get(LabDeliveryItem, item_id)
        assert reloaded_item is not None, "LabDeliveryItem nunca se borra"
        assert reloaded_item.work_order_id is None
        assert reloaded_item.equipment_id is None
        assert reloaded_item.work_order_id_snapshot == work_order_id
        assert reloaded_item.work_order_folio_snapshot == completed["folio"]
        assert reloaded_item.equipment_id_snapshot == equipment_id
        assert reloaded_item.instrument_snapshot

        reloaded_receipt = db.get(LabDeliveryGroupReceipt, receipt_id)
        assert reloaded_receipt is not None, "el receipt final nunca se borra"
        assert reloaded_receipt.pdf == receipt_pdf_before
        assert reloaded_receipt.root_work_order_id is None
        assert reloaded_receipt.root_work_order_id_snapshot == work_order_id


def test_deleting_the_root_of_a_multi_ot_group_after_void_reassigns_history_to_the_survivor(lab_context):
    """CASO C + CASO G -- al eliminar la raíz de un grupo con sobreviviente,
    delivery.root_work_order_id y receipt.root_work_order_id se reasignan al
    sobreviviente (igual que tickets/sesiones); los snapshots de raíz siguen
    apuntando a la OT ORIGINAL. Los items de la OT eliminada quedan con live
    refs NULL (snapshot intacto); los de la hermana viva conservan sus refs.
    get_lab_delivery_group_status vía la hermana no debe reventar con
    AttributeError y debe mostrar el folio histórico desde el snapshot."""
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    members = _completed_group(client, tokens["tech"], "Cliente grupo caso C", member_count=2)
    root_id = members[0]["root_work_order_id"]
    root_folio = next(m["folio"] for m in members if m["id"] == root_id)
    survivor_id = next(m["id"] for m in members if m["id"] != root_id)
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{root_id}"

    delivery = client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=tech_headers)
    assert delivery.status_code == 201, delivery.text
    delivery_id = delivery.json()["id"]
    root_item = next(i for i in delivery.json()["items"] if i["work_order_id"] == root_id)
    survivor_item = next(i for i in delivery.json()["items"] if i["work_order_id"] == survivor_id)

    void_response = client.post(
        f"{endpoint}/delivery/{delivery_id}/void",
        json={"reason": "Corrección administrativa"},
        headers=admin_headers,
    )
    assert void_response.status_code == 200, void_response.text

    delete_root = client.delete(endpoint, headers=admin_headers)
    assert delete_root.status_code == 204, delete_root.text

    with factory() as db:
        assert db.get(LabWorkOrder, root_id) is None
        assert db.get(LabWorkOrder, survivor_id) is not None

        reloaded_delivery = db.get(LabWorkOrderDelivery, delivery_id)
        assert reloaded_delivery.root_work_order_id == survivor_id
        assert reloaded_delivery.root_work_order_id_snapshot == root_id
        assert reloaded_delivery.root_work_order_folio_snapshot == root_folio

        reloaded_root_item = db.get(LabDeliveryItem, root_item["id"])
        assert reloaded_root_item.work_order_id is None
        assert reloaded_root_item.work_order_id_snapshot == root_id
        assert reloaded_root_item.work_order_folio_snapshot == root_folio

        reloaded_survivor_item = db.get(LabDeliveryItem, survivor_item["id"])
        assert reloaded_survivor_item.work_order_id == survivor_id

    status_via_survivor = _delivery_status(client, tokens["tech"], survivor_id)
    assert status_via_survivor["root_work_order_id"] == survivor_id
    reloaded = next(e for e in status_via_survivor["exhibitions"] if e["id"] == delivery_id)
    reloaded_root_item_read = next(i for i in reloaded["items"] if i["work_order_folio"] == root_folio)
    assert reloaded_root_item_read["work_order_id"] is None


def test_deleting_a_non_root_sibling_of_a_shared_exhibition_only_nulls_its_own_items(lab_context):
    """CASO D -- eliminar una OT hermana NO raíz de una exhibición compartida
    conserva la exhibición completa, el root sigue vivo y sin cambios; sólo
    los items que pertenecían a la OT eliminada quedan con live refs NULL,
    los de la OT que sigue viva conservan referencia intacta."""
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    members = _completed_group(client, tokens["tech"], "Cliente grupo caso D", member_count=2)
    root_id = members[0]["root_work_order_id"]
    sibling_id = next(m["id"] for m in members if m["id"] != root_id)
    sibling_folio = next(m["folio"] for m in members if m["id"] == sibling_id)
    endpoint_root = f"/api/mobile/v1/technician/lab-work-orders/{root_id}"

    delivery = client.post(f"{endpoint_root}/delivery", json=delivery_payload(), headers=tech_headers)
    assert delivery.status_code == 201, delivery.text
    delivery_id = delivery.json()["id"]
    sibling_item = next(i for i in delivery.json()["items"] if i["work_order_id"] == sibling_id)
    root_item = next(i for i in delivery.json()["items"] if i["work_order_id"] == root_id)

    void_response = client.post(
        f"{endpoint_root}/delivery/{delivery_id}/void",
        json={"reason": "Corrección administrativa"},
        headers=admin_headers,
    )
    assert void_response.status_code == 200, void_response.text

    delete_sibling = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{sibling_id}", headers=admin_headers
    )
    assert delete_sibling.status_code == 204, delete_sibling.text

    with factory() as db:
        assert db.get(LabWorkOrder, root_id) is not None
        assert db.get(LabWorkOrder, sibling_id) is None

        reloaded_delivery = db.get(LabWorkOrderDelivery, delivery_id)
        assert reloaded_delivery.root_work_order_id == root_id, "el root no cambia -- sigue vivo"

        reloaded_sibling_item = db.get(LabDeliveryItem, sibling_item["id"])
        assert reloaded_sibling_item.work_order_id is None
        assert reloaded_sibling_item.work_order_id_snapshot == sibling_id
        assert reloaded_sibling_item.work_order_folio_snapshot == sibling_folio

        reloaded_root_item = db.get(LabDeliveryItem, root_item["id"])
        assert reloaded_root_item.work_order_id == root_id


def test_historical_field_sheet_still_blocks_delete_even_with_a_voided_delivery(lab_context):
    """CASO E -- Delivery anulado deja de bloquear, pero el guard de
    FieldSheets protegidas (preexistente, ajeno a este ajuste) sigue vigente
    e independiente."""
    from app.models.field_sheet import FieldSheet
    from app.models.lab_work_order import LabWorkOrderEquipment

    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente caso E", equipment_count=1)
    work_order_id = completed["id"]
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}"

    delivery = client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=tech_headers)
    assert delivery.status_code == 201, delivery.text
    delivery_id = delivery.json()["id"]

    void_response = client.post(
        f"{endpoint}/delivery/{delivery_id}/void",
        json={"reason": "Corrección administrativa"},
        headers=admin_headers,
    )
    assert void_response.status_code == 200, void_response.text

    with factory() as db:
        work_order = db.get(LabWorkOrder, work_order_id)
        equipment = db.scalars(
            select(LabWorkOrderEquipment).where(LabWorkOrderEquipment.work_order_id == work_order.id)
        ).first()
        db.add(FieldSheet(
            lab_equipment_id=equipment.id,
            template_key="general",
            status="completed",
            is_current=True,
            final_pdf_path="storage/fixture.pdf",
            final_pdf_sha256="0" * 64,
        ))
        db.commit()

    delete_with_field_sheet = client.delete(endpoint, headers=admin_headers)
    assert delete_with_field_sheet.status_code == 409
    assert "hoja de campo" in delete_with_field_sheet.json()["detail"]

    with factory() as db:
        assert db.get(LabWorkOrder, work_order_id) is not None


# ---------------------------------------------------------------------------
# LEGACY
# ---------------------------------------------------------------------------


def test_legacy_departure_date_without_delivery_is_not_read_as_digital_delivery(lab_context):
    client, factory, tokens = lab_context
    completed = _completed_single(client, tokens["tech"], "Cliente legacy", equipment_count=1)
    with factory() as db:
        work_order = db.get(LabWorkOrder, completed["id"])
        work_order.departure_date = date(2020, 1, 1)
        db.commit()

    status = _delivery_status(client, tokens["tech"], completed["id"])
    assert status["group_complete"] is False
    assert len(status["pending_equipment"]) == 1
    assert status["exhibitions"] == []


# ---------------------------------------------------------------------------
# ATOMICIDAD
# ---------------------------------------------------------------------------


def test_delivery_pdf_render_failure_rolls_back_the_whole_event(lab_context, monkeypatch):
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    completed = _completed_single(client, tokens["tech"], "Cliente rollback", equipment_count=1)
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"

    def fail_pdf(*_args, **_kwargs):
        raise RuntimeError("renderer failure")

    monkeypatch.setattr("app.services.lab_work_order_deliveries.generate_lab_delivery_receipt", fail_pdf)
    with pytest.raises(RuntimeError, match="renderer failure"):
        client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=tech_headers)

    with factory() as db:
        assert db.scalar(select(LabWorkOrderDelivery.id)) is None
        assert db.scalar(select(LabDeliveryItem.id)) is None
        assert db.get(LabWorkOrder, completed["id"]).departure_date is None


def test_delivery_audit_log_failure_rolls_back_items_and_departure_date(lab_context, monkeypatch):
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    completed = _completed_single(client, tokens["tech"], "Cliente rollback items", equipment_count=1)
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit failure")

    monkeypatch.setattr("app.services.lab_work_order_deliveries.write_audit_log", fail_audit)
    with pytest.raises(RuntimeError, match="audit failure"):
        client.post(f"{endpoint}/delivery", json=delivery_payload(), headers=tech_headers)

    with factory() as db:
        assert db.scalar(select(LabWorkOrderDelivery.id)) is None
        assert db.scalar(select(LabDeliveryItem.id)) is None
        assert db.get(LabWorkOrder, completed["id"]).departure_date is None


# ---------------------------------------------------------------------------
# ACCESO: entrega/void/entrega-parcial reservadas a personal MYC interno
# ---------------------------------------------------------------------------


def test_delivery_endpoints_are_gated_to_internal_actors():
    """Los actores externos (portal cliente) no pueden ver ni registrar
    Delivery (sección 1). El contrato mobile deriva actor_type de la sesión
    autenticada (ver app/core/mobile/security.py); las mutaciones de entrega
    verifican explícitamente que sea 'internal' además del permiso, igual
    que ya hacían /cancel y /reopen para esta misma OT."""
    source = Path("app/routers/lab_work_orders.py").read_text()
    for anchor in ("def post_lab_delivery(", "def post_lab_partial_delivery(", "def post_void_lab_delivery("):
        start = source.index(anchor)
        block = source[start:start + 700]
        assert 'context.actor_type != "internal"' in block, anchor
    ticket_source = Path("app/routers/operational_tickets.py").read_text()
    start = ticket_source.index("def create_partial_delivery_request(")
    assert 'context.actor_type != "internal"' in ticket_source[start:start + 700]
