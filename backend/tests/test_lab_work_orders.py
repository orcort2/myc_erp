from __future__ import annotations

import base64
import io
import json
import os
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.user import Role, User
from app.schemas.operational_ticket import TicketReject, TicketReview
from app.services.lab_work_order_pdfs import generate_lab_work_order_pdf
from app.services.lab_work_orders import _allocate_folio, create_additional_work_order
from app.services.operational_tickets import approve_reopen_ticket, reject_ticket


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
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        technician_role = Role(name="Tecnico", description="Técnico")
        capture_role = Role(name="Captura", description="Captura")
        admin_role = Role(name="Administrador", description="Administrador")
        db.add_all([technician_role, capture_role, admin_role])
        db.flush()
        users = []
        for key, role in (
            ("tech", technician_role),
            ("capture", capture_role),
            ("admin", admin_role),
        ):
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
        for key, user in zip(("tech", "capture", "admin"), users, strict=True)
    }
    try:
        yield client, factory, tokens
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def postgres_lab_context():
    database_url = os.getenv("LAB_POSTGRES_TEST_URL")
    if not database_url:
        pytest.skip("requiere LAB_POSTGRES_TEST_URL para probar locks PostgreSQL reales")

    schema = f"ticket_lock_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

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
        for key, role_name in (
            ("tech", "Tecnico"),
            ("capture", "Captura"),
            ("admin", "Administrador"),
        ):
            role = roles[role_name]
            user = User(
                username=f"postgres-{key}",
                email=f"postgres-{key}@example.test",
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
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_payload(client_name: str = "Cliente LAB") -> dict:
    return {
        "reception_date": "2026-08-13",
        "departure_date": "2026-08-15",
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


def test_lab_security_and_initial_folio(lab_context):
    client, _factory, tokens = lab_context
    url = "/api/mobile/v1/technician/lab-work-orders"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=auth(tokens["capture"])).status_code == 403

    first = client.post(url, json=create_payload(), headers=auth(tokens["tech"]))
    second = client.post(url, json=create_payload("Otro"), headers=auth(tokens["tech"]))
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert [first.json()["folio"], second.json()["folio"]] == [6400, 6401]
    assert first.json()["root_work_order_id"] == first.json()["id"]


def test_equipment_crud_limit_and_no_model(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    created = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload(),
        headers=headers,
    ).json()
    base = f"/api/mobile/v1/technician/lab-work-orders/{created['id']}"
    invalid = client.post(
        f"{base}/equipment",
        json=equipment_payload(1, model="No permitido"),
        headers=headers,
    )
    assert invalid.status_code == 422
    for index in range(1, 11):
        response = client.post(f"{base}/equipment", json=equipment_payload(index), headers=headers)
        assert response.status_code == 201, response.text
    eleventh = client.post(f"{base}/equipment", json=equipment_payload(11), headers=headers)
    assert eleventh.status_code == 409
    detail = client.get(base, headers=headers).json()
    assert len(detail["equipment"]) == 10
    equipment_id = detail["equipment"][0]["id"]
    updated = client.patch(
        f"{base}/equipment/{equipment_id}",
        json=equipment_payload(99),
        headers=headers,
    )
    assert updated.status_code == 200
    deleted = client.delete(f"{base}/equipment/{equipment_id}", headers=headers)
    assert deleted.status_code == 200
    assert [item["position"] for item in deleted.json()["equipment"]] == list(range(1, 10))


def test_additional_work_orders_inherit_and_keep_group_chain(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    root = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload(),
        headers=headers,
    ).json()
    for index in range(1, 11):
        client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{root['id']}/equipment",
            json=equipment_payload(index),
            headers=headers,
        )
    additional = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{root['id']}/additional",
        headers=headers,
    )
    assert additional.status_code == 201, additional.text
    extra = additional.json()
    assert extra["folio"] == 6401
    assert extra["root_work_order_id"] == root["id"]
    assert extra["previous_work_order_id"] == root["id"]
    assert extra["sequence_number"] == 2
    assert extra["client_name"] == root["client_name"]
    assert extra["equipment"] == []

    for index in range(11, 21):
        client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{extra['id']}/equipment",
            json=equipment_payload(index),
            headers=headers,
        )
    third = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{extra['id']}/additional",
        headers=headers,
    ).json()
    assert (third["folio"], third["root_work_order_id"], third["previous_work_order_id"]) == (
        6402,
        root["id"],
        extra["id"],
    )
    assert [item["folio"] for item in third["related_work_orders"]] == [6400, 6401, 6402]


def test_one_signature_session_completes_and_locks_entire_group(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    mapping_payload = create_payload("CLIENTE PRUEBA")
    mapping_payload.update(
        address="Avenida Ejemplo 123",
        contact_name="Persona Prueba",
        postal_code="45601",
        city="Tlaquepaque",
        state_name="Jalisco",
        purchase_order="OC-TEST-001",
    )
    root = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=mapping_payload,
        headers=headers,
    ).json()
    for index in range(1, 11):
        client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{root['id']}/equipment",
            json=equipment_payload(index),
            headers=headers,
        )
    extra = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{root['id']}/additional",
        headers=headers,
    ).json()
    client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{extra['id']}/equipment",
        json=equipment_payload(11),
        headers=headers,
    )

    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{extra['id']}/signatures",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    signature_session_id = signed.json()["signature_session_id"]
    with factory() as db:
        group = list(db.scalars(select(LabWorkOrder).order_by(LabWorkOrder.folio)))
        assert {item.signature_session_id for item in group} == {signature_session_id}
        assert all(item.status == "ready_for_signatures" for item in group)

    assert client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{extra['id']}/equipment",
        json=equipment_payload(12),
        headers=headers,
    ).status_code == 409
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{root['id']}/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert all(item["status"] == "completed" for item in completed.json()["related_work_orders"])
    for work_order_id, expected_folio, expected_instrument in (
        (root["id"], "6400", "Instrumento 1"),
        (extra["id"], "6401", "Instrumento 11"),
    ):
        pdf = client.get(
            f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}/pdf",
            headers=headers,
        )
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")
        rendered_text = "\n".join(
            page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf.content)).pages
        )
        assert expected_folio in rendered_text
        assert expected_instrument in rendered_text
        assert "Técnico LAB" in rendered_text
        assert "Cliente LAB" in rendered_text
        assert "CLIENTE PRUEBA" in rendered_text
        assert rendered_text.count("Avenida Ejemplo 123") == 1
        assert "Persona Prueba" in rendered_text
        assert "45601" in rendered_text
        assert "Tlaquepaque" in rendered_text
        assert "Jalisco" in rendered_text
        assert "OC-TEST-001" in rendered_text
        assert "Avenida Ejemplo 123, Tlaquepaque" not in rendered_text


def test_requires_equipment_and_both_valid_signatures(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    root = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload(),
        headers=headers,
    ).json()
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{root['id']}"
    assert client.post(f"{endpoint}/signatures", json=signatures_payload(), headers=headers).status_code == 409
    client.post(f"{endpoint}/equipment", json=equipment_payload(1), headers=headers)
    invalid = signatures_payload()
    invalid["client"]["signature_data_url"] = "data:image/png;base64,bm90LXBuZw=="
    assert client.post(f"{endpoint}/signatures", json=invalid, headers=headers).status_code == 422
    assert client.post(f"{endpoint}/complete", headers=headers).status_code == 409


def test_folio_never_exceeds_6999(lab_context):
    client, factory, tokens = lab_context
    with factory() as db:
        db.add(
            InstitutionalFolioSequence(
                document_type="lab_work_order",
                prefix="LAB",
                year=0,
                next_value=6999,
            )
        )
        db.commit()
    headers = auth(tokens["tech"])
    first = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload(),
        headers=headers,
    )
    assert first.status_code == 201
    assert first.json()["folio"] == 6999
    exhausted = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload(),
        headers=headers,
    )
    assert exhausted.status_code == 409


def test_export_manifest_matches_persisted_counts(lab_context):
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    root = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload(),
        headers=tech_headers,
    ).json()
    client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{root['id']}/equipment",
        json=equipment_payload(1),
        headers=tech_headers,
    )
    assert client.get(
        "/api/mobile/v1/technician/lab-work-orders/export",
        headers=tech_headers,
    ).status_code == 403
    exported = client.get(
        "/api/mobile/v1/technician/lab-work-orders/export",
        headers=auth(tokens["admin"]),
    )
    assert exported.status_code == 200, exported.text
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        work_orders = json.loads(archive.read("work_orders.json"))
        equipment = json.loads(archive.read("equipment.json"))
    assert manifest["work_order_count"] == len(work_orders) == 1
    assert manifest["equipment_count"] == len(equipment) == 1


def test_work_order_structured_filters_are_combinable_paginated_and_protected(lab_context):
    client, _factory, tokens = lab_context
    url = "/api/mobile/v1/technician/lab-work-orders"
    headers = auth(tokens["tech"])
    for client_name in ("Susana Industrial", "SUSANA Metrología", "Cliente Distinto"):
        response = client.post(url, json=create_payload(client_name), headers=headers)
        assert response.status_code == 201

    assert client.get(url, params={"folio": "6401"}, headers=headers).json()[0]["folio"] == 6401
    assert {item["folio"] for item in client.get(url, params={"folio": "640"}, headers=headers).json()} == {
        6400, 6401, 6402
    }
    assert len(client.get(url, params={"client": "Susana Industrial"}, headers=headers).json()) == 1
    assert len(client.get(url, params={"client": "susana"}, headers=headers).json()) == 2
    combined = client.get(
        url,
        params={"folio": "6401", "client": "susana"},
        headers=headers,
    )
    assert [item["folio"] for item in combined.json()] == [6401]
    assert client.get(url, params={"client": "inexistente"}, headers=headers).json() == []
    first_page = client.get(url, params={"limit": 2, "offset": 0}, headers=headers).json()
    second_page = client.get(url, params={"limit": 2, "offset": 2}, headers=headers).json()
    assert [item["folio"] for item in first_page] == [6402, 6401]
    assert [item["folio"] for item in second_page] == [6400]
    assert client.get(url).status_code == 401
    assert client.get(url, headers=auth(tokens["capture"])).status_code == 403


def _completed_work_order(client: TestClient, token: str, name: str = "Cliente Ticket") -> dict:
    headers = auth(token)
    root = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload(name),
        headers=headers,
    ).json()
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{root['id']}"
    client.post(f"{endpoint}/equipment", json=equipment_payload(1), headers=headers)
    client.post(f"{endpoint}/signatures", json=signatures_payload(), headers=headers)
    completed = client.post(f"{endpoint}/complete", headers=headers)
    assert completed.status_code == 200, completed.text
    return completed.json()


def test_ticket_preserves_minor_change_and_versions_pdf(lab_context):
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    work_order = _completed_work_order(client, tokens["tech"])
    ticket_url = "/api/mobile/v1/technician/tickets"
    payload = {
        "work_order_id": work_order["id"],
        "reason": "Folio de certificado",
        "description": "Se recibió el folio después del cierre.",
        "requested_signature_policy": "preserve",
    }
    assert client.post(ticket_url, json=payload).status_code == 401
    assert client.post(ticket_url, json=payload, headers=auth(tokens["capture"])).status_code == 403
    created = client.post(ticket_url, json=payload, headers=tech_headers)
    assert created.status_code == 201, created.text
    ticket = created.json()
    assert ticket["status"] == "pending"
    still_closed = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}", headers=tech_headers
    ).json()
    assert still_closed["status"] == "completed"

    approved = client.post(
        f"{ticket_url}/{ticket['id']}/approve",
        json={"signature_policy": "preserve", "comment": "Cambio administrativo"},
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "in_progress"
    reopened = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}", headers=tech_headers
    ).json()
    assert reopened["revision_number"] == 2
    assert reopened["signature_preserved"] is True
    assert reopened["signature_session_id"] == work_order["signature_session_id"]

    changed = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}",
        json={"notes": "Folio de certificado CERT-2026-1", "expected_edit_version": reopened["edit_version"]},
        headers=tech_headers,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["signature_preserved"] is True
    assert client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}",
        json={"notes": "request obsoleto", "expected_edit_version": reopened["edit_version"]},
        headers=tech_headers,
    ).status_code == 409

    closed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}/complete",
        headers=tech_headers,
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["revision_number"] == 2
    assert client.get(f"{ticket_url}/{ticket['id']}", headers=tech_headers).json()["status"] == "resolved"
    history = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}/revisions",
        headers=tech_headers,
    ).json()
    assert [item["revision_number"] for item in history] == [1, 2]
    historical_pdf = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}/revisions/1/pdf",
        headers=tech_headers,
    )
    assert historical_pdf.status_code == 200
    assert historical_pdf.content.startswith(b"%PDF")


def test_structural_change_invalidates_signature_and_requires_new_signature(lab_context):
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    work_order = _completed_work_order(client, tokens["tech"], "Cliente Estructural")
    ticket = client.post(
        "/api/mobile/v1/technician/tickets",
        json={
            "work_order_id": work_order["id"],
            "reason": "Agregar equipo",
            "description": "El cliente entregó un equipo adicional.",
            "requested_signature_policy": "preserve",
        },
        headers=tech_headers,
    ).json()
    reopened = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}/approve",
        json={"signature_policy": "preserve"},
        headers=admin_headers,
    )
    assert reopened.status_code == 200
    detail = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}", headers=tech_headers
    ).json()
    changed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}/equipment",
        json={**equipment_payload(2), "expected_edit_version": detail["edit_version"]},
        headers=tech_headers,
    )
    assert changed.status_code == 201, changed.text
    assert changed.json()["signature_required"] is True
    assert changed.json()["signature_session_id"] is None
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}"
    assert client.post(f"{endpoint}/complete", headers=tech_headers).status_code == 409
    resigned = client.post(
        f"{endpoint}/signatures", json=signatures_payload(), headers=tech_headers
    )
    assert resigned.status_code == 200, resigned.text
    assert resigned.json()["signature_session_id"] != work_order["signature_session_id"]
    assert client.post(f"{endpoint}/complete", headers=tech_headers).status_code == 200


def test_ticket_rejection_and_invalid_lifecycle(lab_context):
    client, _factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    open_order = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload("Abierta"),
        headers=tech_headers,
    ).json()
    payload = {
        "work_order_id": open_order["id"],
        "reason": "No aplica",
        "description": "La orden todavía está abierta.",
        "requested_signature_policy": "invalidate",
    }
    assert client.post(
        "/api/mobile/v1/technician/tickets", json=payload, headers=tech_headers
    ).status_code == 409
    closed = _completed_work_order(client, tokens["tech"], "Para rechazo")
    payload["work_order_id"] = closed["id"]
    ticket = client.post(
        "/api/mobile/v1/technician/tickets", json=payload, headers=tech_headers
    ).json()
    rejected = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}/reject",
        json={"comment": "No se acreditó la necesidad"},
        headers=admin_headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert client.post(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}/approve",
        json={"signature_policy": "invalidate"},
        headers=admin_headers,
    ).status_code == 409


@pytest.mark.parametrize("signature_policy", ["preserve", "invalidate"])
def test_postgresql_ticket_approval_locks_only_ticket_row(
    postgres_lab_context, signature_policy
):
    client, _factory, tokens = postgres_lab_context
    work_order = _completed_work_order(
        client, tokens["tech"], f"PostgreSQL {signature_policy}"
    )
    ticket = client.post(
        "/api/mobile/v1/technician/tickets",
        json={
            "work_order_id": work_order["id"],
            "reason": "Corrección posterior al cierre",
            "description": "Validación del bloqueo de ticket en PostgreSQL.",
            "requested_signature_policy": signature_policy,
        },
        headers=auth(tokens["tech"]),
    ).json()

    approved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}/approve",
        json={"signature_policy": signature_policy},
        headers=auth(tokens["admin"]),
    )

    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "in_progress"
    reopened = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}",
        headers=auth(tokens["tech"]),
    ).json()
    assert reopened["signature_preserved"] is (signature_policy == "preserve")
    assert reopened["signature_required"] is (signature_policy == "invalidate")
    assert reopened["signature_session_id"] == (
        work_order["signature_session_id"] if signature_policy == "preserve" else None
    )


def test_postgresql_ticket_rejection_cannot_be_resolved_again(postgres_lab_context):
    client, _factory, tokens = postgres_lab_context
    work_order = _completed_work_order(client, tokens["tech"], "PostgreSQL rechazo")
    ticket = client.post(
        "/api/mobile/v1/technician/tickets",
        json={
            "work_order_id": work_order["id"],
            "reason": "Solicitud improcedente",
            "description": "Se valida el rechazo definitivo del ticket.",
            "requested_signature_policy": "invalidate",
        },
        headers=auth(tokens["tech"]),
    ).json()
    endpoint = f"/api/mobile/v1/technician/tickets/{ticket['id']}"

    rejected = client.post(
        f"{endpoint}/reject",
        json={"comment": "No procede la reapertura"},
        headers=auth(tokens["admin"]),
    )

    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert client.post(
        f"{endpoint}/reject",
        json={"comment": "Segundo rechazo"},
        headers=auth(tokens["admin"]),
    ).status_code == 409
    assert client.post(
        f"{endpoint}/approve",
        json={"signature_policy": "preserve"},
        headers=auth(tokens["admin"]),
    ).status_code == 409


def test_postgresql_concurrent_ticket_resolution_allows_one_winner(
    postgres_lab_context,
):
    client, factory, tokens = postgres_lab_context
    work_order = _completed_work_order(client, tokens["tech"], "PostgreSQL carrera")
    ticket = client.post(
        "/api/mobile/v1/technician/tickets",
        json={
            "work_order_id": work_order["id"],
            "reason": "Resolución concurrente",
            "description": "Dos revisores intentan resolver el mismo ticket.",
            "requested_signature_policy": "preserve",
        },
        headers=auth(tokens["tech"]),
    ).json()

    def resolve(action: str) -> tuple[str, int]:
        with factory() as db:
            admin = db.scalar(select(User).where(User.username == "postgres-admin"))
            assert admin is not None
            try:
                if action == "approve":
                    approve_reopen_ticket(
                        db,
                        ticket["id"],
                        TicketReview(signature_policy="preserve"),
                        admin,
                    )
                else:
                    reject_ticket(
                        db,
                        ticket["id"],
                        TicketReject(comment="Resolución concurrente rechazada"),
                        admin,
                    )
                return action, 200
            except HTTPException as exc:
                db.rollback()
                return action, exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(resolve, ("approve", "reject")))

    assert sorted(status for _action, status in outcomes) == [200, 409]
    detail = client.get(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}",
        headers=auth(tokens["admin"]),
    ).json()
    assert detail["status"] in {"in_progress", "rejected"}


def test_lab_pdf_leaves_missing_purchase_order_empty():
    payload = create_payload("CLIENTE SIN ORDEN")
    payload["purchase_order"] = None
    payload["reception_date"] = date.fromisoformat(payload["reception_date"])
    payload["departure_date"] = date.fromisoformat(payload["departure_date"])
    work_order = LabWorkOrder(
        folio=6400,
        sequence_number=1,
        created_by_user_id=1,
        status="draft",
        **payload,
    )
    work_order.equipment = [
        LabWorkOrderEquipment(position=1, **equipment_payload(1))
    ]

    pdf, _filename = generate_lab_work_order_pdf(work_order)
    rendered_text = "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages
    )

    assert "ORDEN DE COMPRA /COTIZACIÓN" in rendered_text
    assert "ORDEN DE COMPRA /COTIZACIÓN 0" not in rendered_text


@pytest.mark.skipif(
    not os.getenv("LAB_POSTGRES_TEST_URL"),
    reason="requiere PostgreSQL temporal para probar advisory/row lock real",
)
def test_postgresql_concurrent_folio_allocation_is_unique():
    engine = create_engine(os.environ["LAB_POSTGRES_TEST_URL"])
    factory = sessionmaker(bind=engine)

    def allocate() -> int:
        with factory() as db:
            with db.begin():
                value = _allocate_folio(db)
                time.sleep(0.1)
                return value

    with ThreadPoolExecutor(max_workers=2) as pool:
        values = sorted(pool.map(lambda _index: allocate(), range(2)))

    assert values == [6400, 6401]

    with factory() as db:
        role = Role(name="Tecnico LAB concurrente", description="Prueba LAB")
        user = User(
            username="lab-concurrent-tech",
            email="lab-concurrent-tech@example.test",
            full_name="Técnico LAB concurrente",
            hashed_password="unused",
            account_type="internal",
            status="active",
            is_active=True,
            role=role,
            roles=[role],
        )
        db.add(user)
        db.flush()
        root = LabWorkOrder(
            folio=6402,
            sequence_number=1,
            created_by_user_id=user.id,
            **create_payload(),
        )
        db.add(root)
        db.flush()
        root.root_work_order_id = root.id
        root.equipment = [
            LabWorkOrderEquipment(position=index, **equipment_payload(index))
            for index in range(1, 11)
        ]
        db.commit()
        root_id = root.id
        user_id = user.id

    def create_additional() -> tuple[str, int]:
        with factory() as db:
            user = db.get(User, user_id)
            assert user is not None
            try:
                result = create_additional_work_order(db, root_id, user)
                return "created", result.folio
            except HTTPException as exc:
                db.rollback()
                return "rejected", exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _index: create_additional(), range(2)))

    assert sorted(outcomes) == [("created", 6403), ("rejected", 409)]
    with factory() as db:
        folios = list(db.scalars(select(LabWorkOrder.folio).order_by(LabWorkOrder.folio)))
    assert folios == [6402, 6403]
