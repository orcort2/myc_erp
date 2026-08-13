from __future__ import annotations

import base64
import io
import json
import zipfile
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.lab_work_order import LabWorkOrder
from app.models.user import Role, User


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
    for work_order_id in (root["id"], extra["id"]):
        pdf = client.get(
            f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}/pdf",
            headers=headers,
        )
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")


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
