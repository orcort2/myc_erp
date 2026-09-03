"""Regresión P0: c2d4e6f8a0b1 creó created_at/updated_at de las 3 tablas
nuevas de Delivery como NOT NULL sin server_default (drift respecto a
TimestampMixin), lo que producía un 500 (NotNullViolation) en cualquier
INSERT real -- porque el ORM, al ver `server_default` declarado en el
modelo Python, confía en que la BD lo resuelve y omite la columna del
INSERT explícito. d3e4f5a6b7c8 corrige eso agregando el server_default
faltante sin tocar c2d4e6f8a0b1 ni los datos existentes.

Estos tests corren contra un esquema Postgres real, MIGRADO con Alembic de
verdad (no Base.metadata.create_all, que ya usaba el modelo correcto y por
lo tanto nunca habría reproducido este bug) para probar exactamente lo que
un despliegue real ejecuta.
"""

from __future__ import annotations

import base64
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.lab_delivery_group_receipt import LabDeliveryGroupReceipt
from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.user import Role, User


ROOT = Path(__file__).resolve().parents[2]
_TABLES = ("lab_work_order_deliveries", "lab_delivery_items", "lab_delivery_group_receipts")
_TIMESTAMP_COLUMNS = ("created_at", "updated_at")

PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
).decode()

pytestmark = pytest.mark.skipif(
    not os.getenv("LAB_POSTGRES_TEST_URL"),
    reason="requiere LAB_POSTGRES_TEST_URL para migrar un esquema Postgres real",
)


@pytest.fixture()
def migrated_schema():
    """Crea un schema Postgres aislado y le aplica TODAS las migraciones
    reales vía Alembic (no metadata.create_all) -- es la única forma de
    reproducir fielmente lo que un despliegue real ejecuta."""
    database_url = os.environ["LAB_POSTGRES_TEST_URL"]
    schema = f"lab_delivery_ts_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    previous_url = settings.database_url
    # Sin percent-encoding: ConfigParser interpola "%" (env.py fija esta URL
    # vía config.set_main_option, que pasa por configparser) y fallaría con
    # "invalid interpolation syntax" si el valor trae %3D.
    settings.database_url = f"{database_url}?options=-csearch_path={schema}"
    try:
        config = Config(str(ROOT / "backend" / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "backend" / "migrations"))
        command.upgrade(config, "head")
    finally:
        settings.database_url = previous_url

    engine = create_engine(database_url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        yield engine, schema
    finally:
        engine.dispose()
        admin_engine.dispose()
        with create_engine(database_url).begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


def test_lab_delivery_tables_have_real_server_defaults_after_migration(migrated_schema):
    """Compara el esquema REALMENTE migrado contra TimestampMixin
    (server_default=func.now(), nullable=False) -- lo que hubiera atrapado
    este drift antes de que produjera un 500 en producción."""
    engine, schema = migrated_schema
    inspector = inspect(engine)
    for table in _TABLES:
        columns = {column["name"]: column for column in inspector.get_columns(table, schema=schema)}
        for column_name in _TIMESTAMP_COLUMNS:
            column = columns[column_name]
            assert column["nullable"] is False, f"{table}.{column_name} debe seguir siendo NOT NULL"
            assert column["default"], (
                f"{table}.{column_name} no tiene server_default -- diverge de TimestampMixin"
            )


@pytest.fixture()
def migrated_lab_context(migrated_schema):
    engine, _schema = migrated_schema
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        # 9c0d1e2f3a14_add_user_roles ya siembra "Tecnico"/"Administrador"
        # como parte de la migración real -- reutilizarlos en vez de
        # insertarlos de nuevo (violaría ix_roles_name).
        technician_role = db.scalar(select(Role).where(Role.name == "Tecnico"))
        admin_role = db.scalar(select(Role).where(Role.name == "Administrador"))
        assert technician_role is not None and admin_role is not None
        users = []
        for key, role in (("tech", technician_role), ("admin", admin_role)):
            user = User(
                username=f"lab-ts-{key}-{uuid.uuid4().hex[:8]}",
                email=f"lab-ts-{key}-{uuid.uuid4().hex[:8]}@example.test",
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


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_payload(client_name: str) -> dict:
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


def _equipment_payload(index: int) -> dict:
    return {
        "instrument": f"Instrumento {index}",
        "brand": "MYC Test",
        "identification": f"ID-{index}",
        "serial_number": f"SER-{index}",
        "report_number": None,
        "is_good_condition": True,
    }


def _configure_default_services(client: TestClient, headers: dict[str, str], work_order_id: int) -> None:
    detail = client.get(f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}", headers=headers).json()
    for item in detail["equipment"]:
        if item["service_type"] is not None:
            continue
        response = client.put(
            f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}/equipment/{item['id']}/service",
            json={"service_type": "traceable", "linked_company_id": None},
            headers=headers,
        )
        assert response.status_code == 200, response.text


def _signatures_payload() -> dict:
    signed_at = datetime.now(timezone.utc).isoformat()
    return {
        "technician": {"signer_name": "Técnico LAB", "signed_at": signed_at, "version": 1, "signature_data_url": PNG_DATA_URL},
        "client": {"signer_name": "Cliente LAB", "signed_at": signed_at, "version": 1, "signature_data_url": PNG_DATA_URL},
    }


def _delivery_payload(**extra) -> dict:
    return {
        "delivery_method": "direct",
        "delivered_by_signature_data_url": PNG_DATA_URL,
        "recipient_name": "María Receptora",
        "recipient_signature_data_url": PNG_DATA_URL,
        **extra,
    }


def _completed_single(client: TestClient, token: str, name: str, *, equipment_count: int = 1) -> dict:
    headers = _auth(token)
    created = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=_create_payload(name), headers=headers
    ).json()
    for index in range(equipment_count):
        response = client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{created['id']}/equipment",
            json=_equipment_payload(index + 1),
            headers=headers,
        )
        assert response.status_code == 201, response.text
    _configure_default_services(client, headers, created["id"])
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{created['id']}/signatures",
        json=_signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    completed = client.post(f"/api/mobile/v1/technician/lab-work-orders/{created['id']}/complete", headers=headers)
    assert completed.status_code == 200, completed.text
    return completed.json()


def test_full_delivery_on_migrated_schema_never_sends_manual_timestamps(migrated_lab_context):
    """Reproduce el 500 real: POST .../delivery sobre un esquema migrado de
    verdad. Ni este test ni el request HTTP fijan created_at/updated_at en
    ningún momento -- si el server_default faltara, esto volvería a fallar
    con NotNullViolation como en producción."""
    client, factory, tokens = migrated_lab_context
    completed = _completed_single(client, tokens["tech"], "Cliente timestamps", equipment_count=1)
    endpoint = f"/api/mobile/v1/technician/lab-work-orders/{completed['id']}"

    response = client.post(f"{endpoint}/delivery", json=_delivery_payload(), headers=_auth(tokens["tech"]))
    assert response.status_code == 201, response.text
    delivery_id = response.json()["id"]

    with factory() as db:
        delivery = db.get(LabWorkOrderDelivery, delivery_id)
        assert delivery.created_at is not None
        assert delivery.updated_at is not None
        items = list(db.scalars(select(LabDeliveryItem).where(LabDeliveryItem.delivery_id == delivery_id)))
        assert items
        for item in items:
            assert item.created_at is not None
            assert item.updated_at is not None
        # Un solo equipo/una sola OT: la exhibición ya cierra el grupo, así
        # que también se congela el resumen final (LabDeliveryGroupReceipt).
        receipt = db.scalar(
            select(LabDeliveryGroupReceipt).where(
                LabDeliveryGroupReceipt.root_work_order_id == delivery.root_work_order_id
            )
        )
        assert receipt is not None
        assert receipt.created_at is not None
        assert receipt.updated_at is not None


def test_partial_delivery_on_migrated_schema_never_sends_manual_timestamps(migrated_lab_context):
    client, factory, tokens = migrated_lab_context
    tech_headers = _auth(tokens["tech"])
    admin_headers = _auth(tokens["admin"])
    completed = _completed_single(client, tokens["tech"], "Cliente parcial timestamps", equipment_count=2)
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
    approved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}/approve-partial-delivery", json={}, headers=admin_headers
    )
    assert approved.status_code == 200, approved.text
    executed = client.post(
        f"{endpoint}/delivery/partial/{ticket['id']}", json=_delivery_payload(), headers=tech_headers
    )
    assert executed.status_code == 201, executed.text
    delivery_id = executed.json()["id"]

    with factory() as db:
        delivery = db.get(LabWorkOrderDelivery, delivery_id)
        assert delivery.created_at is not None
        assert delivery.updated_at is not None
        item = db.scalar(select(LabDeliveryItem).where(LabDeliveryItem.delivery_id == delivery_id))
        assert item is not None
        assert item.created_at is not None
        assert item.updated_at is not None
