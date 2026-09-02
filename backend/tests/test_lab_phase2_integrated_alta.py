"""Fase 2 del rediseño LAB: integración operativa OT -> cliente receptor ->
equipos -> cliente documental -> servicio -> folio, como alta integrada.

Cubre exclusivamente lo que Fase 2 introduce:
- create_configured_equipment() / POST .../equipment/configured (transacción única).
- Selección de LabClient receptor con scope/estado.
- Cliente documental por equipo conectado al alta (Fase 1 ya lo preparaba).
- Guard 2G de edición insegura de servicio/folio ya reservado.
- Regresión: endpoints previos, grupos, folios, tickets, FieldSheet, SignatureSession.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.client import Client
from app.models.client_portal_membership import ClientPortalMembership
from app.models.client_portal_membership_role import ClientPortalMembershipRole
from app.models.client_portal_role import ClientPortalRole
from app.models.field_sheet import FieldSheet
from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.lab_client import LabClient
from app.models.lab_work_order import (
    LabWorkOrder,
    LabWorkOrderEquipment,
    LabWorkOrderSignatureSession,
)
from app.models.linked_company import LinkedCompany
from app.models.operational_ticket import OperationalTicket
from app.models.user import Role, User
from app.schemas.lab_client import LabClientCreate
from app.schemas.lab_work_order import LabWorkOrderCreate
from app.services.lab_clients import create_lab_client
from app.services.lab_work_orders import create_work_order
from app.services.portal.permission_service import ensure_portal_catalog


PASSWORD = "MobilePass123"


@pytest.fixture()
def phase2_context():
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
        admin_role = Role(name="Administrador", description="Administrador")
        tech_role = Role(name="Tecnico", description="Técnico")
        capture_role = Role(name="Captura", description="Captura")
        db.add_all([admin_role, tech_role, capture_role])
        db.flush()
        internal_users = {}
        for key, role in (("admin", admin_role), ("tech", tech_role), ("capture", capture_role)):
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
            internal_users[key] = user
        db.add_all(internal_users.values())
        db.commit()

        client_a = Client(legal_name="Tenant A", commercial_name="Tenant A")
        client_b = Client(legal_name="Tenant B", commercial_name="Tenant B")
        db.add_all([client_a, client_b])
        db.commit()
        ensure_portal_catalog(db)

        external_users = {}
        for key, client in (("external_a", client_a), ("external_b", client_b)):
            user = User(
                username=f"{key}@client.example.com",
                email=f"{key}@client.example.com",
                full_name=key,
                hashed_password=hash_password(PASSWORD),
                account_type="client_portal",
                status="active",
                email_verified_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.flush()
            role = db.scalar(
                select(ClientPortalRole).where(ClientPortalRole.code == "external_operator_sr")
            )
            membership = ClientPortalMembership(client_id=client.id, user_id=user.id, status="active")
            db.add(membership)
            db.flush()
            db.add(ClientPortalMembershipRole(membership_id=membership.id, role_id=role.id))
            external_users[key] = user
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
        for key, user in internal_users.items()
    }
    try:
        yield client, factory, tokens, {"client_a": client_a, "client_b": client_b}
    finally:
        app.dependency_overrides.clear()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def external_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/mobile/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_payload(client_name: str = "Cliente LAB", **extra) -> dict:
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
        **extra,
    }


def equipment_body(index: int, **extra) -> dict:
    return {
        "instrument": f"Instrumento {index}",
        "brand": "MYC Test",
        "identification": f"ID-{index}",
        "serial_number": f"SER-{index}",
        "report_number": None,
        "is_good_condition": True,
        **extra,
    }


def configured_payload(
    index: int,
    service_type: str,
    *,
    linked_company_id: int | None = None,
    certificate_client: dict | None = None,
) -> dict:
    body = {
        "equipment": equipment_body(index),
        "service": {"service_type": service_type, "linked_company_id": linked_company_id},
    }
    if certificate_client is not None:
        body["certificate_client"] = certificate_client
    return body


def _signatures_payload() -> dict:
    import base64

    png = "data:image/png;base64," + base64.b64encode(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
    ).decode()
    signed_at = datetime.now(timezone.utc).isoformat()
    return {
        "technician": {"signer_name": "Técnico", "signed_at": signed_at, "version": 1, "signature_data_url": png},
        "client": {"signer_name": "Cliente", "signed_at": signed_at, "version": 1, "signature_data_url": png},
    }


def _create_order(client, headers, **overrides) -> int:
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload(**overrides),
        headers=headers,
    )
    assert order.status_code == 201, order.text
    return order.json()["id"]


CONFIGURED_URL = "/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/configured"
CONFIGURED_EDIT_URL = (
    "/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/configured"
)


# --------------------------------------------------------------------------
# CLIENTE OT (1-5)
# --------------------------------------------------------------------------

def test_can_select_active_lab_client_for_new_work_order(phase2_context):
    """1. Puede seleccionar LabClient activo."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        lab_client = create_lab_client(
            db, LabClientCreate(company="Receptor Activo", address="Calle 1", attention="Ing. A"),
            admin, operator_client_id=None,
        )
        lab_client_id = lab_client.id
    payload = create_payload("Se reemplaza por snapshot")
    payload["lab_client_id"] = lab_client_id
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=payload, headers=headers
    )
    assert order.status_code == 201, order.text
    assert order.json()["lab_client_id"] == lab_client_id


def test_work_order_freezes_correct_client_snapshots(phase2_context):
    """2. Congela snapshots correctos (client_name/address/contact_name)."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        lab_client = create_lab_client(
            db, LabClientCreate(company="Empresa Snapshot", address="Calle Snapshot", attention="Ing. Snapshot"),
            admin, operator_client_id=None,
        )
        lab_client_id = lab_client.id
    payload = create_payload("Reemplazado")
    payload["lab_client_id"] = lab_client_id
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=payload, headers=headers
    ).json()
    assert order["client_name"] == "Empresa Snapshot"
    assert order["address"] == "Calle Snapshot"
    assert order["contact_name"] == "Ing. Snapshot"


def test_modifying_lab_client_afterward_does_not_alter_work_order(phase2_context):
    """3. Modificar LabClient después no altera OT."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        lab_client = create_lab_client(
            db, LabClientCreate(company="Original SA", address="Dir Original", attention="Ing. Original"),
            admin, operator_client_id=None,
        )
        lab_client_id = lab_client.id
    payload = create_payload("Reemplazado")
    payload["lab_client_id"] = lab_client_id
    order_id = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=payload, headers=headers
    ).json()["id"]

    with factory() as db:
        lab_client = db.get(LabClient, lab_client_id)
        lab_client.company = "RENOMBRADA"
        lab_client.address = "Dir RENOMBRADA"
        db.commit()

    refreshed = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers
    ).json()
    assert refreshed["client_name"] == "Original SA"
    assert refreshed["address"] == "Dir Original"


def test_inactive_client_cannot_be_selected_for_a_new_work_order(phase2_context):
    """4. Cliente inactivo no puede seleccionarse para una OT nueva."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        lab_client = create_lab_client(
            db, LabClientCreate(company="Inactivo SA", address="", attention=""),
            admin, operator_client_id=None,
        )
        lab_client_id = lab_client.id
        lab_client.is_active = False
        db.commit()

    payload = create_payload("Cualquiera")
    payload["lab_client_id"] = lab_client_id
    response = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=payload, headers=headers
    )
    assert response.status_code == 404, response.text


def test_external_tenant_cannot_select_another_tenants_lab_client(phase2_context):
    """5. Tenant externo no puede seleccionar cliente ajeno."""
    _client, factory, _tokens, tenants = phase2_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        foreign_client = create_lab_client(
            db, LabClientCreate(company="Cliente de Tenant A", address="", attention=""),
            admin, operator_client_id=tenants["client_a"].id,
        )
        foreign_client_id = foreign_client.id

        with pytest.raises(Exception) as excinfo:
            create_work_order(
                db,
                LabWorkOrderCreate(**create_payload("Reemplazado"), lab_client_id=foreign_client_id),
                admin,
                operator_client_id=tenants["client_b"].id,
            )
        assert getattr(excinfo.value, "status_code", None) == 404


# --------------------------------------------------------------------------
# CLIENTE DOCUMENTAL (6-13)
# --------------------------------------------------------------------------

def test_configured_equipment_default_mode_is_order(phase2_context):
    """6. Default de equipo es mode=order."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    equipment = response.json()["equipment"][-1]
    assert equipment["certificate_client_mode"] == "order"
    assert equipment["final_client_company_snapshot"] is None


def test_mode_order_resolves_the_work_order_client(phase2_context):
    """7. mode=order resuelve cliente OT."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers, client_name="Receptor Directo")
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    equipment_id = response.json()["equipment"][-1]["id"]
    with factory() as db:
        from app.services.lab_work_orders import resolve_equipment_certificate_client

        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        resolved = resolve_equipment_certificate_client(equipment, equipment.work_order)
        assert resolved["company"] == "Receptor Directo"


def test_mode_different_selects_an_authorized_lab_client(phase2_context):
    """8. different selecciona LabClient autorizado."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        final_client = create_lab_client(
            db, LabClientCreate(company="Cliente Final Autorizado", address="Calle F", attention="Ing. F"),
            admin, operator_client_id=None,
        )
        final_client_id = final_client.id
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(
            1, "accredited",
            certificate_client={
                "certificate_client_mode": "different",
                "final_lab_client_id": final_client_id,
                "final_client_company_snapshot": "Cliente Final Autorizado",
                "final_client_address_snapshot": "Calle F",
                "final_client_attention_snapshot": "Ing. F",
            },
        ),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    equipment = response.json()["equipment"][-1]
    assert equipment["certificate_client_mode"] == "different"
    assert equipment["final_lab_client_id"] == final_client_id


def test_mode_different_freezes_snapshots(phase2_context):
    """9. different congela snapshots."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(
            1, "traceable",
            certificate_client={
                "certificate_client_mode": "different",
                "final_client_company_snapshot": "Cliente B Congelado",
            },
        ),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    equipment = response.json()["equipment"][-1]
    assert equipment["final_client_company_snapshot"] == "Cliente B Congelado"


def test_modifying_lab_client_afterward_does_not_change_equipment_snapshot(phase2_context):
    """10. Modificar LabClient después no cambia equipo."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        final_client = create_lab_client(
            db, LabClientCreate(company="Antes de Renombrar", address="Calle X", attention="Ing. X"),
            admin, operator_client_id=None,
        )
        final_client_id = final_client.id
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(
            1, "accredited",
            certificate_client={
                "certificate_client_mode": "different",
                "final_lab_client_id": final_client_id,
                "final_client_company_snapshot": "Antes de Renombrar",
                "final_client_address_snapshot": "Calle X",
                "final_client_attention_snapshot": "Ing. X",
            },
        ),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    equipment_id = response.json()["equipment"][-1]["id"]

    with factory() as db:
        final_client = db.get(LabClient, final_client_id)
        final_client.company = "RENOMBRADO"
        db.commit()

    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.final_client_company_snapshot == "Antes de Renombrar"


def test_mode_different_allows_null_address(phase2_context):
    """11. different admite address null."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(
            1, "accredited",
            certificate_client={
                "certificate_client_mode": "different",
                "final_client_company_snapshot": "Sin Dirección Final",
            },
        ),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["equipment"][-1]["final_client_address_snapshot"] is None


def test_mode_different_allows_null_attention(phase2_context):
    """12. different admite attention null."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(
            1, "accredited",
            certificate_client={
                "certificate_client_mode": "different",
                "final_client_company_snapshot": "Sin Atención Final",
            },
        ),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["equipment"][-1]["final_client_attention_snapshot"] is None


def test_external_tenant_cannot_use_a_foreign_final_client(phase2_context):
    """13. Tenant externo no puede usar cliente final ajeno."""
    client, factory, tokens, tenants = phase2_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        foreign_final_client = create_lab_client(
            db, LabClientCreate(company="Final de Tenant A", address="", attention=""),
            admin, operator_client_id=tenants["client_a"].id,
        )
        foreign_final_client_id = foreign_final_client.id
        order = create_work_order(
            db, LabWorkOrderCreate(**create_payload("OT de Tenant B")), admin,
            operator_client_id=tenants["client_b"].id,
        )
        order_id = order.id

    external_b_headers = external_headers(client, "external_b@client.example.com")
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(
            1, "accredited",
            certificate_client={
                "certificate_client_mode": "different",
                "final_lab_client_id": foreign_final_client_id,
                "final_client_company_snapshot": "Final de Tenant A",
            },
        ),
        headers=external_b_headers,
    )
    assert response.status_code == 404, response.text


# --------------------------------------------------------------------------
# ENDURECIMIENTO -- autoridad backend del snapshot de cliente documental
# --------------------------------------------------------------------------

def test_manipulated_snapshot_is_ignored_and_real_lab_client_data_is_persisted(phase2_context):
    """Petición manipulada: final_lab_client_id de un LabClient REAL, pero con
    company/address/attention falsos en el payload. El backend debe ignorar
    por completo los snapshots suministrados y persistir SIEMPRE lo que dice
    el LabClient autorizado -- nunca el dato falso."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        real_client = create_lab_client(
            db, LabClientCreate(company="CLIENTE REAL", address="DIRECCION REAL", attention="PERSONA REAL"),
            admin, operator_client_id=None,
        )
        real_client_id = real_client.id
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(
            1, "accredited",
            certificate_client={
                "certificate_client_mode": "different",
                "final_lab_client_id": real_client_id,
                "final_client_company_snapshot": "CLIENTE FALSO",
                "final_client_address_snapshot": "DIRECCION FALSA",
                "final_client_attention_snapshot": "PERSONA FALSA",
            },
        ),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    equipment = response.json()["equipment"][-1]
    assert equipment["final_client_company_snapshot"] == "CLIENTE REAL"
    assert equipment["final_client_address_snapshot"] == "DIRECCION REAL"
    assert equipment["final_client_attention_snapshot"] == "PERSONA REAL"
    with factory() as db:
        persisted = db.get(LabWorkOrderEquipment, equipment["id"])
        assert persisted.final_client_company_snapshot == "CLIENTE REAL"
        assert persisted.final_client_address_snapshot == "DIRECCION REAL"
        assert persisted.final_client_attention_snapshot == "PERSONA REAL"


def test_inactive_lab_client_by_id_is_rejected_for_certificate_client(phase2_context):
    """LabClient inactive por ID -> rechazo, aunque el id sea válido y del mismo scope."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        inactive_client = create_lab_client(
            db, LabClientCreate(company="Cliente Inactivo", address="", attention=""),
            admin, operator_client_id=None,
        )
        inactive_client_id = inactive_client.id
        inactive_client.is_active = False
        db.commit()
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(
            1, "accredited",
            certificate_client={
                "certificate_client_mode": "different",
                "final_lab_client_id": inactive_client_id,
            },
        ),
        headers=headers,
    )
    assert response.status_code == 404, response.text
    with factory() as db:
        assert db.scalar(select(LabWorkOrderEquipment)) is None  # rollback completo, sin huérfano


def test_cross_tenant_lab_client_by_id_is_rejected_for_certificate_client(phase2_context):
    """LabClient de otro tenant por ID -> rechazo."""
    client, factory, tokens, tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        foreign_client = create_lab_client(
            db, LabClientCreate(company="Cliente de Otro Tenant", address="", attention=""),
            admin, operator_client_id=tenants["client_a"].id,
        )
        foreign_client_id = foreign_client.id
    order_id = _create_order(client, headers)  # OT interna, operator_client_id=None
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(
            1, "accredited",
            certificate_client={
                "certificate_client_mode": "different",
                "final_lab_client_id": foreign_client_id,
            },
        ),
        headers=headers,
    )
    assert response.status_code == 404, response.text


def test_nonexistent_lab_client_id_is_rejected_for_certificate_client(phase2_context):
    """ID inexistente -> rechazo."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(
            1, "accredited",
            certificate_client={"certificate_client_mode": "different", "final_lab_client_id": 999999},
        ),
        headers=headers,
    )
    assert response.status_code == 404, response.text


def test_mode_order_rejects_final_lab_client_id(phase2_context):
    """mode=order no acepta/procesa final_lab_client_id -- rechazado a nivel schema (422)."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json={
            "equipment": equipment_body(1),
            "certificate_client": {"certificate_client_mode": "order", "final_lab_client_id": 1},
            "service": {"service_type": "accredited", "linked_company_id": None},
        },
        headers=headers,
    )
    assert response.status_code == 422, response.text


def test_different_mode_without_final_lab_client_id_still_requires_a_snapshot_company(phase2_context):
    """Camino sin catálogo (sin final_lab_client_id): el snapshot de empresa
    sigue siendo obligatorio y es la única autoridad en ese caso puntual."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json={
            "equipment": equipment_body(1),
            "certificate_client": {"certificate_client_mode": "different"},
            "service": {"service_type": "accredited", "linked_company_id": None},
        },
        headers=headers,
    )
    assert response.status_code == 422, response.text


# --------------------------------------------------------------------------
# ALTA INTEGRADA (14-20)
# --------------------------------------------------------------------------

def test_configured_endpoint_creates_equipment_client_and_service_coherently(phase2_context):
    """14. Crea equipo + cliente documental + servicio en una operación coherente."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(
            1, "traceable",
            certificate_client={
                "certificate_client_mode": "different",
                "final_client_company_snapshot": "Cliente Coherente",
            },
        ),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    equipment = response.json()["equipment"][-1]
    assert equipment["instrument"] == "Instrumento 1"
    assert equipment["certificate_client_mode"] == "different"
    assert equipment["final_client_company_snapshot"] == "Cliente Coherente"
    assert equipment["service_type"] == "traceable"
    assert equipment["folio_status"] == "reserved"


def test_accredited_reserves_myca(phase2_context):
    """15. accredited reserva MYCA."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    month_year = date.today().strftime("%m-%y")
    assert response.json()["equipment"][-1]["certificate_folio"] == f"MYCA-{month_year}-4700"


def test_traceable_reserves_myct(phase2_context):
    """16. traceable reserva MYCT."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "traceable"),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    month_year = date.today().strftime("%m-%y")
    assert response.json()["equipment"][-1]["certificate_folio"] == f"MYCT-{month_year}-1640"


def test_linked_preserves_linked_company_snapshots(phase2_context):
    """17. linked conserva LinkedCompany snapshots."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        linked = LinkedCompany(
            name="Laboratorio Vinculado", abbreviation="LV", default_certificate_prefix="LVT",
        )
        db.add(linked)
        db.commit()
        linked_id = linked.id
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "linked", linked_company_id=linked_id),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    equipment = response.json()["equipment"][-1]
    assert equipment["linked_company_id"] == linked_id
    assert equipment["linked_company_name_snapshot"] == "Laboratorio Vinculado"
    assert equipment["linked_company_prefix_snapshot"] == "LVT"


def test_linked_does_not_create_myca_or_myct(phase2_context):
    """18. linked no crea MYCA/MYCT."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        linked = LinkedCompany(name="Vinculada Sin Folio", abbreviation="VSF", default_certificate_prefix="VSF")
        db.add(linked)
        db.commit()
        linked_id = linked.id
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "linked", linked_company_id=linked_id),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    equipment = response.json()["equipment"][-1]
    assert equipment["certificate_folio"] is None
    assert equipment["folio_status"] == "pending"
    with factory() as db:
        sequences = list(
            db.scalars(
                select(InstitutionalFolioSequence).where(
                    InstitutionalFolioSequence.document_type == "lab_certificate"
                )
            )
        )
        assert sequences == []


def test_linked_without_company_creates_one_atomic_folio_request_and_reuses_it(phase2_context):
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "linked", linked_company_id=None),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    equipment = created.json()["equipment"][-1]
    assert equipment["linked_company_id"] is None
    assert equipment["certificate_folio"] is None
    assert equipment["automatic_certificate_folio"] is None
    assert equipment["folio_status"] == "pending"
    assert equipment["folio_ticket_id"] is not None

    with factory() as db:
        tickets = list(
            db.scalars(
                select(OperationalTicket).where(
                    OperationalTicket.equipment_id == equipment["id"],
                    OperationalTicket.type == "linked_folio",
                )
            )
        )
        assert len(tickets) == 1
        ticket_id = tickets[0].id
        assert tickets[0].linked_company_id is None
        assert tickets[0].conversation_id is not None

    edited_payload = configured_payload(1, "linked", linked_company_id=None)
    edited_payload["equipment"]["brand"] = "MYC Test editado"
    edited = client.patch(
        CONFIGURED_EDIT_URL.format(order_id=order_id, equipment_id=equipment["id"]),
        json=edited_payload,
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    with factory() as db:
        assert len(
            list(
                db.scalars(
                    select(OperationalTicket).where(
                        OperationalTicket.equipment_id == equipment["id"],
                        OperationalTicket.type == "linked_folio",
                    )
                )
            )
        ) == 1
        assert db.get(LabWorkOrderEquipment, equipment["id"]).folio_ticket_id == ticket_id

    ticket_read = client.get(
        f"/api/mobile/v1/technician/tickets/{ticket_id}",
        headers=auth(tokens["admin"]),
    )
    assert ticket_read.status_code == 200, ticket_read.text
    assert {
        "equipment_position": 1,
        "equipment_instrument": "Instrumento 1",
        "equipment_brand": "MYC Test editado",
        "equipment_model": None,
        "equipment_identification": "ID-1",
        "equipment_serial_number": "SER-1",
        "equipment_service_type": "linked",
        "equipment_folio_status": "pending",
    }.items() <= ticket_read.json().items()


def test_allocation_failure_rolls_back_the_entire_operation(phase2_context):
    """19 & 20. Un fallo (folio agotado) hace rollback completo: no queda
    equipo huérfano parcialmente configurado."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        db.add(
            InstitutionalFolioSequence(
                document_type="lab_certificate", prefix="MYCA", year=0, next_value=8000,
            )
        )
        db.commit()
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    assert response.status_code == 409, response.text
    with factory() as db:
        equipment_count = db.scalar(
            select(LabWorkOrderEquipment).where(LabWorkOrderEquipment.work_order_id == order_id)
        )
        assert equipment_count is None
        work_order = db.get(LabWorkOrder, order_id)
        assert work_order.edit_version == 1  # nunca se incrementó: el add_equipment también se revirtió


# --------------------------------------------------------------------------
# TRAZABILIDAD (21-25)
# --------------------------------------------------------------------------

def test_reserved_folio_is_never_reused(phase2_context):
    """21. Folio reservado no se reutiliza."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    first = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    assert first.status_code == 201, first.text
    first_folio = first.json()["equipment"][-1]["certificate_folio"]
    second = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(2, "accredited"),
        headers=headers,
    )
    assert second.status_code == 201, second.text
    second_folio = second.json()["equipment"][-1]["certificate_folio"]
    assert first_folio != second_folio


def test_unsafe_service_change_on_reserved_folio_is_rejected(phase2_context):
    """22. Cambio inseguro de servicio se rechaza (409), sin liberar el folio."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]
    original_folio = created.json()["equipment"][-1]["certificate_folio"]

    response = client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "traceable", "linked_company_id": None},
        headers=headers,
    )
    assert response.status_code == 409, response.text
    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.certificate_folio == original_folio
        assert equipment.service_type == "accredited"


def test_reconfirming_the_same_service_on_reserved_folio_is_a_safe_noop(phase2_context):
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]
    original_folio = created.json()["equipment"][-1]["certificate_folio"]

    response = client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "accredited", "linked_company_id": None},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["equipment"][-1]["certificate_folio"] == original_folio


def test_linked_company_mutated_later_does_not_change_equipment_snapshot(phase2_context):
    """23. LinkedCompany mutable posteriormente no cambia snapshots del equipo."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        linked = LinkedCompany(name="Antes de Cambiar", abbreviation="ADC", default_certificate_prefix="ADC")
        db.add(linked)
        db.commit()
        linked_id = linked.id
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "linked", linked_company_id=linked_id),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]

    with factory() as db:
        linked = db.get(LinkedCompany, linked_id)
        linked.name = "RENOMBRADA"
        db.commit()

    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.linked_company_name_snapshot == "Antes de Cambiar"


def test_work_order_can_contain_equipment_with_different_documentary_clients(phase2_context):
    """24. OT puede contener equipos con diferentes clientes documentales."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    second = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(
            2, "traceable",
            certificate_client={
                "certificate_client_mode": "different",
                "final_client_company_snapshot": "Cliente Final Distinto",
            },
        ),
        headers=headers,
    )
    assert second.status_code == 201, second.text
    equipment = second.json()["equipment"]
    assert equipment[0]["certificate_client_mode"] == "order"
    assert equipment[1]["final_client_company_snapshot"] == "Cliente Final Distinto"


def test_group_can_contain_distinct_documentary_clients_per_equipment(phase2_context):
    """25. Grupo puede contener clientes documentales distintos por equipo
    (ejemplo SAVERGLASS: receptor único, documental distinto por equipo/OT)."""
    client, factory, tokens, _tenants = phase2_context
    admin_headers = auth(tokens["admin"])
    tech_headers = auth(tokens["tech"])
    group = client.post(
        "/api/lab-work-order-groups",
        json={**create_payload("SAVERGLASS"), "quantity": 2},
        headers=admin_headers,
    )
    assert group.status_code == 201, group.text
    members = group.json()["related_work_orders"]

    first_ot_first_equipment = client.post(
        CONFIGURED_URL.format(order_id=members[0]["id"]),
        json=configured_payload(1, "accredited"),
        headers=tech_headers,
    )
    assert first_ot_first_equipment.status_code == 201, first_ot_first_equipment.text
    first_ot_second_equipment = client.post(
        CONFIGURED_URL.format(order_id=members[0]["id"]),
        json=configured_payload(
            2, "traceable",
            certificate_client={
                "certificate_client_mode": "different",
                "final_client_company_snapshot": "CLIENTE FINAL X",
            },
        ),
        headers=tech_headers,
    )
    assert first_ot_second_equipment.status_code == 201, first_ot_second_equipment.text
    second_ot_first_equipment = client.post(
        CONFIGURED_URL.format(order_id=members[1]["id"]),
        json=configured_payload(
            1, "accredited",
            certificate_client={
                "certificate_client_mode": "different",
                "final_client_company_snapshot": "CLIENTE FINAL Y",
            },
        ),
        headers=tech_headers,
    )
    assert second_ot_first_equipment.status_code == 201, second_ot_first_equipment.text

    with factory() as db:
        modes = {
            item.id: (item.certificate_client_mode, item.final_client_company_snapshot)
            for item in db.scalars(select(LabWorkOrderEquipment))
        }
        assert ("order", None) in modes.values()
        assert ("different", "CLIENTE FINAL X") in modes.values()
        assert ("different", "CLIENTE FINAL Y") in modes.values()


# --------------------------------------------------------------------------
# PERMISOS (26-28)
# --------------------------------------------------------------------------

def test_captura_does_not_gain_new_administrative_capability(phase2_context):
    """26. Captura no obtiene capacidad administrativa nueva."""
    client, factory, tokens, _tenants = phase2_context
    order_id = _create_order(client, auth(tokens["tech"]))
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=auth(tokens["capture"]),
    )
    assert response.status_code == 403, response.text


def test_external_operator_stays_tenant_scoped(phase2_context):
    """27. Externo queda tenant-scoped: no puede configurar equipo en una OT
    ajena, aun con permisos operativos válidos."""
    client, factory, tokens, tenants = phase2_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        order = create_work_order(
            db, LabWorkOrderCreate(**create_payload("OT de Tenant A")), admin,
            operator_client_id=tenants["client_a"].id,
        )
        order_id = order.id
    external_b_headers = external_headers(client, "external_b@client.example.com")
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=external_b_headers,
    )
    assert response.status_code == 404, response.text


def test_authorized_staff_can_use_the_configured_endpoint(phase2_context):
    """28. Staff autorizado funciona."""
    client, factory, tokens, _tenants = phase2_context
    order_id = _create_order(client, auth(tokens["tech"]))
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=auth(tokens["tech"]),
    )
    assert response.status_code == 201, response.text


# --------------------------------------------------------------------------
# REGRESIÓN (29-35)
# --------------------------------------------------------------------------

def test_previous_step_by_step_endpoints_still_work(phase2_context):
    """29. Endpoints anteriores (POST equipment, PUT service) continúan
    funcionando de forma independiente tras el refactor a núcleos."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_body(1),
        headers=headers,
    )
    assert added.status_code == 201, added.text
    equipment_id = added.json()["equipment"][-1]["id"]
    serviced = client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "accredited", "linked_company_id": None},
        headers=headers,
    )
    assert serviced.status_code == 200, serviced.text


def test_group_creation_still_works(phase2_context):
    """30. Creación de grupos continúa funcionando."""
    client, factory, tokens, _tenants = phase2_context
    group = client.post(
        "/api/lab-work-order-groups",
        json={**create_payload("Grupo regresión"), "quantity": 3},
        headers=auth(tokens["admin"]),
    )
    assert group.status_code == 201, group.text
    assert len(group.json()["related_work_orders"]) == 3


def test_maximum_ten_equipment_per_work_order_still_enforced(phase2_context):
    """31. Máximo 10 equipos por OT continúa funcionando (vía alta integrada)."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    for index in range(1, 11):
        response = client.post(
            CONFIGURED_URL.format(order_id=order_id),
            json=configured_payload(index, "accredited"),
            headers=headers,
        )
        assert response.status_code == 201, response.text
    eleventh = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(11, "accredited"),
        headers=headers,
    )
    assert eleventh.status_code == 409, eleventh.text
    with factory() as db:
        count = len(
            list(
                db.scalars(
                    select(LabWorkOrderEquipment).where(
                        LabWorkOrderEquipment.work_order_id == order_id
                    )
                )
            )
        )
        assert count == 10


def test_myca_myct_authority_unchanged(phase2_context):
    """32. Folios MYCA/MYCT siguen usando la autoridad existente (mismo rango/formato)."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    response = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    month_year = date.today().strftime("%m-%y")
    assert response.json()["equipment"][-1]["certificate_folio"] == f"MYCA-{month_year}-4700"
    with factory() as db:
        sequence = db.scalar(
            select(InstitutionalFolioSequence).where(
                InstitutionalFolioSequence.document_type == "lab_certificate",
                InstitutionalFolioSequence.prefix == "MYCA",
            )
        )
        assert sequence.next_value == 4701


def test_manual_linked_folio_endpoint_does_not_duplicate_automatic_request(phase2_context):
    """33. El endpoint compatible no duplica la solicitud automática linked."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        linked = LinkedCompany(name="Vinculada Ticket", abbreviation="VT", default_certificate_prefix="VT")
        db.add(linked)
        db.commit()
        linked_id = linked.id
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "linked", linked_company_id=linked_id),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]
    ticket = client.post(
        "/api/mobile/v1/technician/tickets/folio",
        json={
            "work_order_id": order_id,
            "equipment_id": equipment_id,
            "type": "linked_folio",
            "requested_folio": None,
            "reason": "Prueba de regresión",
            "description": "Solicitar folio autorizado",
        },
        headers=headers,
    )
    assert ticket.status_code == 409, ticket.text
    with factory() as db:
        assert len(list(db.scalars(select(OperationalTicket).where(
            OperationalTicket.equipment_id == equipment_id,
            OperationalTicket.type == "linked_folio",
        )))) == 1


# --------------------------------------------------------------------------
# Cierre UX 2026-09 (items C, D, E): ciclo de vida al abandonar Vinculado,
# TODAS las entradas backend de asignacion linked crean solicitud, e
# idempotencia de ensure_linked_folio_request.
# --------------------------------------------------------------------------

SERVICE_URL = "/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service"


def test_leaving_linked_cancels_the_pending_ticket_and_new_folio_follows_current_logic(phase2_context):
    """Item C: linked -> ticket pending automatico -> editar a accredited ->
    ticket anterior cancelled -> equipo ya no lo referencia -> el nuevo folio
    MYCA sigue la logica actual (reservado normalmente)."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "linked", linked_company_id=None),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    equipment_id = created.json()["equipment"][-1]["id"]
    original_ticket_id = created.json()["equipment"][-1]["folio_ticket_id"]
    assert original_ticket_id is not None

    edited_payload = configured_payload(1, "accredited")
    edited = client.patch(
        CONFIGURED_EDIT_URL.format(order_id=order_id, equipment_id=equipment_id),
        json=edited_payload,
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    updated_equipment = edited.json()["equipment"][-1]
    assert updated_equipment["service_type"] == "accredited"
    assert updated_equipment["folio_status"] == "reserved"
    assert updated_equipment["certificate_folio"] is not None
    # El equipo ya no referencia el ticket linked_folio anterior.
    assert updated_equipment["folio_ticket_id"] is None

    with factory() as db:
        old_ticket = db.get(OperationalTicket, original_ticket_id)
        assert old_ticket.status == "cancelled"
        assert old_ticket.reviewed_at is not None
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.folio_ticket_id is None
        assert equipment.service_type == "accredited"


def test_linked_to_linked_does_not_cancel_nor_duplicate_the_ticket(phase2_context):
    """Item C (regresion inversa): linked -> linked (reconfirmando el mismo
    servicio) no cancela el ticket pending ni crea uno nuevo."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "linked", linked_company_id=None),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]
    original_ticket_id = created.json()["equipment"][-1]["folio_ticket_id"]

    edited_payload = configured_payload(1, "linked", linked_company_id=None)
    edited_payload["equipment"]["brand"] = "MYC Test (linked->linked)"
    edited = client.patch(
        CONFIGURED_EDIT_URL.format(order_id=order_id, equipment_id=equipment_id),
        json=edited_payload,
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    updated_equipment = edited.json()["equipment"][-1]
    assert updated_equipment["service_type"] == "linked"
    assert updated_equipment["folio_ticket_id"] == original_ticket_id

    with factory() as db:
        ticket = db.get(OperationalTicket, original_ticket_id)
        assert ticket.status == "pending"
        assert len(list(db.scalars(select(OperationalTicket).where(
            OperationalTicket.equipment_id == equipment_id,
            OperationalTicket.type == "linked_folio",
        )))) == 1


def test_standalone_service_endpoint_assigning_linked_also_creates_the_automatic_request(phase2_context):
    """Item D: assign_equipment_service() (el endpoint PUT .../service
    individual, fuera del alta integrada) tambien debe materializar la
    solicitud linked_folio automatica -- antes era la unica entrada que no
    lo hacia."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_body(1),
        headers=headers,
    )
    assert added.status_code == 201, added.text
    equipment_id = added.json()["equipment"][-1]["id"]
    assert added.json()["equipment"][-1]["service_type"] is None

    response = client.put(
        SERVICE_URL.format(order_id=order_id, equipment_id=equipment_id),
        json={"service_type": "linked", "linked_company_id": None},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    updated_equipment = response.json()["equipment"][-1]
    assert updated_equipment["service_type"] == "linked"
    assert updated_equipment["folio_status"] == "pending"
    assert updated_equipment["folio_ticket_id"] is not None

    with factory() as db:
        tickets = list(db.scalars(select(OperationalTicket).where(
            OperationalTicket.equipment_id == equipment_id,
            OperationalTicket.type == "linked_folio",
        )))
        assert len(tickets) == 1
        assert tickets[0].status == "pending"


def test_standalone_service_endpoint_reconfirming_linked_is_idempotent(phase2_context):
    """Item E: ensure_linked_folio_request() sigue siendo idempotente cuando
    se llama repetidamente a traves del endpoint individual -- no duplica el
    ticket, folio_ticket_id sigue apuntando al mismo, folio_status permanece
    pending."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_body(1),
        headers=headers,
    )
    equipment_id = added.json()["equipment"][-1]["id"]

    first = client.put(
        SERVICE_URL.format(order_id=order_id, equipment_id=equipment_id),
        json={"service_type": "linked", "linked_company_id": None},
        headers=headers,
    )
    assert first.status_code == 200, first.text
    first_ticket_id = first.json()["equipment"][-1]["folio_ticket_id"]

    second = client.put(
        SERVICE_URL.format(order_id=order_id, equipment_id=equipment_id),
        json={"service_type": "linked", "linked_company_id": None},
        headers=headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["equipment"][-1]["folio_ticket_id"] == first_ticket_id
    assert second.json()["equipment"][-1]["folio_status"] == "pending"

    with factory() as db:
        assert len(list(db.scalars(select(OperationalTicket).where(
            OperationalTicket.equipment_id == equipment_id,
            OperationalTicket.type == "linked_folio",
        )))) == 1


def test_field_sheet_ownership_unchanged(phase2_context):
    """34. FieldSheet ownership no cambia."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]
    # Fase 3: la captura FieldSheet sólo procede tras la recepción firmada.
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json=_signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    sheet = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert sheet.status_code == 201, sheet.text
    with factory() as db:
        field_sheet = db.get(FieldSheet, sheet.json()["id"])
        assert field_sheet.lab_equipment_id == equipment_id
        assert field_sheet.equipment_id is None


def test_signature_session_model_unchanged(phase2_context):
    """35. SignatureSession no cambia."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    import base64 as _base64

    png = "data:image/png;base64," + _base64.b64encode(
        _base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
    ).decode()
    signed_at = datetime.now(timezone.utc).isoformat()
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json={
            "technician": {"signer_name": "Técnico", "signed_at": signed_at, "version": 1, "signature_data_url": png},
            "client": {"signer_name": "Cliente", "signed_at": signed_at, "version": 1, "signature_data_url": png},
        },
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    with factory() as db:
        session = db.scalar(select(LabWorkOrderSignatureSession))
        assert session is not None
        assert {item.signature_type for item in session.signatures} == {"technician", "client"}


# --------------------------------------------------------------------------
# EDICIÓN INTEGRADA -- PATCH .../equipment/{id}/configured (una sola transacción)
# --------------------------------------------------------------------------

def test_combined_edit_persists_all_three_sections(phase2_context):
    """1 & 2. Edición combinada exitosa: datos básicos + cliente documental +
    servicio, todo en una sola llamada/transacción. Arranca en 'linked' (sin
    folio MYCA/MYCT comprometido todavía) para poder cambiar de servicio sin
    chocar con el guard de folio ya reservado -- eso se prueba aparte."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        linked = LinkedCompany(name="Vinculada Inicial", abbreviation="VI", default_certificate_prefix="VI")
        db.add(linked)
        db.commit()
        linked_id = linked.id
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "linked", linked_company_id=linked_id),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]

    response = client.patch(
        CONFIGURED_EDIT_URL.format(order_id=order_id, equipment_id=equipment_id),
        json=configured_payload(
            1, "accredited",
            certificate_client={
                "certificate_client_mode": "different",
                "final_client_company_snapshot": "Cliente Final Editado",
            },
        ),
        headers=headers,
    )
    assert response.status_code == 200, response.text
    equipment = next(item for item in response.json()["equipment"] if item["id"] == equipment_id)
    assert equipment["certificate_client_mode"] == "different"
    assert equipment["final_client_company_snapshot"] == "Cliente Final Editado"
    assert equipment["service_type"] == "accredited"
    month_year = date.today().strftime("%m-%y")
    assert equipment["certificate_folio"] == f"MYCA-{month_year}-4700"


def test_edit_fails_with_409_when_reserved_folio_would_be_destroyed(phase2_context):
    """3. Fallo del servicio por folio reservado produce 409."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]

    response = client.patch(
        CONFIGURED_EDIT_URL.format(order_id=order_id, equipment_id=equipment_id),
        json=configured_payload(
            2, "traceable",  # intenta cambiar instrumento Y servicio a la vez
            certificate_client={
                "certificate_client_mode": "different",
                "final_client_company_snapshot": "Cliente Que No Debe Persistir",
            },
        ),
        headers=headers,
    )
    assert response.status_code == 409, response.text


def test_edit_409_does_not_change_basic_data(phase2_context):
    """4. Después del 409 los datos básicos NO cambiaron."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]

    client.patch(
        CONFIGURED_EDIT_URL.format(order_id=order_id, equipment_id=equipment_id),
        json=configured_payload(2, "traceable"),
        headers=headers,
    )
    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.instrument == "Instrumento 1"  # NO "Instrumento 2"
        assert equipment.service_type == "accredited"


def test_edit_409_does_not_change_documentary_client(phase2_context):
    """5. Después del 409 el cliente documental NO cambió."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]

    client.patch(
        CONFIGURED_EDIT_URL.format(order_id=order_id, equipment_id=equipment_id),
        json=configured_payload(
            1, "traceable",
            certificate_client={
                "certificate_client_mode": "different",
                "final_client_company_snapshot": "Cliente Que No Debe Persistir",
            },
        ),
        headers=headers,
    )
    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.certificate_client_mode == "order"
        assert equipment.final_client_company_snapshot is None


def test_edit_409_does_not_partially_bump_edit_version(phase2_context):
    """6. edit_version no queda incrementado parcialmente tras el 409."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]
    with factory() as db:
        edit_version_before = db.get(LabWorkOrder, order_id).edit_version

    client.patch(
        CONFIGURED_EDIT_URL.format(order_id=order_id, equipment_id=equipment_id),
        json=configured_payload(2, "traceable"),
        headers=headers,
    )
    with factory() as db:
        assert db.get(LabWorkOrder, order_id).edit_version == edit_version_before


def test_edit_cross_tenant_final_client_rolls_back_completely(phase2_context):
    """7. Cross-tenant provoca rollback completo."""
    client, factory, tokens, tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        foreign_client = create_lab_client(
            db, LabClientCreate(company="Cliente de Otro Tenant", address="", attention=""),
            admin, operator_client_id=tenants["client_a"].id,
        )
        foreign_client_id = foreign_client.id
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]

    response = client.patch(
        CONFIGURED_EDIT_URL.format(order_id=order_id, equipment_id=equipment_id),
        json=configured_payload(
            2, "traceable",
            certificate_client={"certificate_client_mode": "different", "final_lab_client_id": foreign_client_id},
        ),
        headers=headers,
    )
    assert response.status_code == 404, response.text
    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.instrument == "Instrumento 1"
        assert equipment.certificate_client_mode == "order"
        assert equipment.service_type == "accredited"


def test_edit_inactive_lab_client_rolls_back_completely(phase2_context):
    """8. LabClient inactive provoca rollback completo."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        inactive_client = create_lab_client(
            db, LabClientCreate(company="Cliente Inactivo Edit", address="", attention=""),
            admin, operator_client_id=None,
        )
        inactive_client_id = inactive_client.id
        inactive_client.is_active = False
        db.commit()
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "accredited"),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]

    response = client.patch(
        CONFIGURED_EDIT_URL.format(order_id=order_id, equipment_id=equipment_id),
        json=configured_payload(
            2, "traceable",
            certificate_client={"certificate_client_mode": "different", "final_lab_client_id": inactive_client_id},
        ),
        headers=headers,
    )
    assert response.status_code == 404, response.text
    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.instrument == "Instrumento 1"
        assert equipment.certificate_client_mode == "order"


def test_edit_invalid_linked_company_rolls_back_completely(phase2_context):
    """9. LinkedCompany inválida provoca rollback completo. Arranca en
    'linked' con una empresa válida (sin folio MYCA/MYCT comprometido) para
    aislar específicamente el rechazo por LinkedCompany inexistente, sin
    mezclarlo con el guard de folio ya reservado."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    with factory() as db:
        linked = LinkedCompany(name="Vinculada Valida", abbreviation="VV", default_certificate_prefix="VV")
        db.add(linked)
        db.commit()
        linked_id = linked.id
    order_id = _create_order(client, headers)
    created = client.post(
        CONFIGURED_URL.format(order_id=order_id),
        json=configured_payload(1, "linked", linked_company_id=linked_id),
        headers=headers,
    )
    equipment_id = created.json()["equipment"][-1]["id"]

    response = client.patch(
        CONFIGURED_EDIT_URL.format(order_id=order_id, equipment_id=equipment_id),
        json=configured_payload(2, "linked", linked_company_id=999999),
        headers=headers,
    )
    assert response.status_code == 404, response.text
    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.instrument == "Instrumento 1"
        assert equipment.linked_company_id == linked_id


def test_legacy_equipment_endpoints_still_work_after_configured_edit_added(phase2_context):
    """10. Endpoints legacy (PATCH equipo, PATCH certificate-client, PUT
    service) continúan funcionando de forma independiente."""
    client, factory, tokens, _tenants = phase2_context
    headers = auth(tokens["tech"])
    order_id = _create_order(client, headers)
    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_body(1),
        headers=headers,
    )
    assert added.status_code == 201, added.text
    equipment_id = added.json()["equipment"][-1]["id"]

    patched = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}",
        json={**equipment_body(1, instrument="Instrumento Legacy"), "expected_edit_version": added.json()["edit_version"]},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text

    certificate_client_patched = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/certificate-client",
        json={"certificate_client_mode": "order"},
        headers=headers,
    )
    assert certificate_client_patched.status_code == 200, certificate_client_patched.text

    serviced = client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "accredited", "linked_company_id": None},
        headers=headers,
    )
    assert serviced.status_code == 200, serviced.text
