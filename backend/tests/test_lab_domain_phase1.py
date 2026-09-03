"""Fase 1 del rediseño LAB: modelo de dominio, migración, invariantes.

Cubre exclusivamente lo que Fase 1 introduce:
- LabClient: dirección/atención opcionales, desactivación lógica.
- LabWorkOrderEquipment: cliente documental por equipo (order/different).
- OperationalTicket: nuevo tipo field_sheet_template_request.
- LabWorkOrder: estados preparatorios (backward-compatible).
- Regresión: ownership FieldSheet, folios, SignatureSession sin cambios.
"""

from __future__ import annotations

import io
from datetime import date

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.client import Client
from app.models.field_sheet import FieldSheet
from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.lab_client import LabClient
from app.models.notification import Notification
from app.models.lab_work_order import (
    LabWorkOrder,
    LabWorkOrderEquipment,
    LabWorkOrderSignatureSession,
)
from app.models.operational_ticket import OperationalTicket
from app.models.user import Role, User
from app.schemas.lab_work_order import LabEquipmentCertificateClientWrite
from app.services.lab_clients import (
    activate_lab_client,
    count_inactive_lab_clients,
    create_lab_client,
    deactivate_lab_client,
    list_lab_clients,
    normalize_lab_client_identity,
    update_lab_client,
)
from app.schemas.lab_client import LabClientCreate, LabClientUpdate
from app.services.lab_work_orders import (
    resolve_equipment_certificate_client,
    set_equipment_certificate_client,
)
from app.services.operational_tickets import create_field_sheet_template_request_ticket, reject_ticket
from app.schemas.operational_ticket import TicketReject
from app.schemas.operational_ticket import FieldSheetTemplateRequestCreate


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
        admin_role = Role(name="Administrador", description="Administrador")
        tech_role = Role(name="Tecnico", description="Técnico")
        db.add_all([admin_role, tech_role])
        db.flush()
        users = []
        for key, role in (("admin", admin_role), ("tech", tech_role)):
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
        for key, user in zip(("admin", "tech"), users, strict=True)
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
        "is_good_condition": True,
        **extra,
    }


def _signatures_payload() -> dict:
    import base64
    from datetime import datetime, timezone

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


def _setup_order_with_equipment(client, headers, *, count: int = 1) -> tuple[int, list[int]]:
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=create_payload(), headers=headers
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    equipment_ids = []
    for index in range(1, count + 1):
        added = client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
            json=equipment_payload(index),
            headers=headers,
        )
        assert added.status_code == 201, added.text
        equipment_ids.append(added.json()["equipment"][-1]["id"])
    return order_id, equipment_ids


# --------------------------------------------------------------------------
# Grupo A -- LabClient (1-12)
# --------------------------------------------------------------------------

def test_lab_client_accepts_empty_address(lab_context):
    """1. Empresa con address vacío es aceptada."""
    _client, factory, _tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        created = create_lab_client(
            db,
            LabClientCreate(company="Sin Dirección SA", address="", attention="Ing. X"),
            admin,
            operator_client_id=None,
        )
        assert created.address == ""


def test_lab_client_accepts_empty_attention(lab_context):
    """2. Empresa con attention vacío/null es aceptada."""
    _client, factory, _tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        created = create_lab_client(
            db,
            LabClientCreate(company="Sin Contacto SA", address="Calle 1", attention=""),
            admin,
            operator_client_id=None,
        )
        assert created.attention == ""


def test_lab_client_still_requires_company(lab_context):
    """3. Empresa sigue siendo obligatoria."""
    with pytest.raises(Exception):
        LabClientCreate(company="", address="Calle 1", attention="")


def test_normalization_of_null_and_blank_is_deterministic(lab_context):
    """4. Normalización de null/blank es determinista."""
    assert normalize_lab_client_identity("") == ""
    assert normalize_lab_client_identity("   ") == ""
    assert normalize_lab_client_identity("") == normalize_lab_client_identity("   ")
    assert normalize_lab_client_identity("Á B  c") == normalize_lab_client_identity("a b c")


def test_reimport_does_not_duplicate_normalized_identity(lab_context):
    """5. Reimportación no duplica identidad normalizada."""
    client, factory, tokens = lab_context
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["CLIENTE", "CONTACTO", "DIRECCIÓN"])
    sheet.append(["Repetido SA", "", ""])
    content = io.BytesIO()
    workbook.save(content)
    for _ in range(2):
        content.seek(0)
        response = client.post(
            "/api/mobile/v1/technician/lab-clients/import",
            files={
                "upload": (
                    "clientes.xlsx",
                    content.getvalue(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            headers=auth(tokens["admin"]),
        )
        assert response.status_code == 200, response.text
    with factory() as db:
        count = db.scalar(
            select(LabClient).where(LabClient.normalized_company == "repetido sa")
        )
        assert count is not None
        all_matches = list(
            db.scalars(select(LabClient).where(LabClient.normalized_company == "repetido sa"))
        )
        assert len(all_matches) == 1


def test_same_company_different_attention_is_distinct(lab_context):
    """6. Misma empresa + diferente atención sigue siendo distinta."""
    _client, factory, _tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        first = create_lab_client(
            db, LabClientCreate(company="Empresa X", address="Calle 1", attention="Ing. A"),
            admin, operator_client_id=None,
        )
        second = create_lab_client(
            db, LabClientCreate(company="Empresa X", address="Calle 1", attention="Ing. B"),
            admin, operator_client_id=None,
        )
        assert first.id != second.id


def test_same_company_different_address_is_distinct(lab_context):
    """7. Misma empresa + diferente dirección sigue siendo distinta."""
    _client, factory, _tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        first = create_lab_client(
            db, LabClientCreate(company="Empresa Y", address="Calle 1", attention="Ing. A"),
            admin, operator_client_id=None,
        )
        second = create_lab_client(
            db, LabClientCreate(company="Empresa Y", address="Calle 2", attention="Ing. A"),
            admin, operator_client_id=None,
        )
        assert first.id != second.id


def test_external_tenant_a_does_not_collide_with_tenant_b(lab_context):
    """8. Tenant externo A no colisiona con tenant B (misma identidad normalizada)."""
    _client, factory, _tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        tenant_a = Client(legal_name="Tenant A", commercial_name="Tenant A")
        tenant_b = Client(legal_name="Tenant B", commercial_name="Tenant B")
        db.add_all([tenant_a, tenant_b])
        db.flush()
        first = create_lab_client(
            db, LabClientCreate(company="Cliente Compartido", address="Calle 1", attention="Ing. A"),
            admin, operator_client_id=tenant_a.id,
        )
        second = create_lab_client(
            db, LabClientCreate(company="Cliente Compartido", address="Calle 1", attention="Ing. A"),
            admin, operator_client_id=tenant_b.id,
        )
        assert first.id != second.id
        assert first.operator_client_id == tenant_a.id
        assert second.operator_client_id == tenant_b.id


def test_internal_catalog_keeps_its_own_deduplication(lab_context):
    """9. Catálogo interno (operator_client_id NULL) conserva deduplicación propia."""
    _client, factory, _tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        first = create_lab_client(
            db, LabClientCreate(company="Interno SA", address="Calle 1", attention="Ing. A"),
            admin, operator_client_id=None,
        )
        second = create_lab_client(
            db, LabClientCreate(company="Interno SA", address="Calle 1", attention="Ing. A"),
            admin, operator_client_id=None,
        )
        assert first.id == second.id  # dedupe -> misma identidad, no duplicado

        # A nivel BD (no sólo del helper de conveniencia) dos filas NULL con la
        # misma identidad normalizada deben seguir siendo rechazadas.
        duplicate = LabClient(
            company="Interno SA",
            address="Calle 1",
            attention="Ing. A",
            normalized_company="interno sa",
            normalized_address="calle 1",
            normalized_attention="ing a",
            operator_client_id=None,
            created_by_user_id=admin.id,
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.commit()


def test_lab_client_can_be_deactivated_without_deletion(lab_context):
    """10. LabClient puede desactivarse sin borrarse."""
    _client, factory, _tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        created = create_lab_client(
            db, LabClientCreate(company="Desactivable SA", address="", attention=""),
            admin, operator_client_id=None,
        )
        client_id = created.id
        deactivated = deactivate_lab_client(db, client_id, operator_client_id=None, user=admin)
        assert deactivated.is_active is False
        assert deactivated.deleted_at is not None
        assert deactivated.deleted_by == admin.id
        # sigue existiendo (no DELETE físico)
        still_there = db.get(LabClient, client_id)
        assert still_there is not None

        reactivated = activate_lab_client(db, client_id, operator_client_id=None, user=admin)
        assert reactivated.is_active is True
        assert reactivated.deleted_at is None


def test_lab_client_structured_address_propagates_to_new_work_order(lab_context):
    """Cierre UX 2026-09: LabClient con postal_code/city/state estructurados
    (no participan del índice normalizado -- sólo company/address/attention
    lo hacen) permite propagarlos a los campos ya existentes de LabWorkOrder
    (postal_code/city/state_name) al seleccionarlo, sin inventar calle/
    número/colonia que el dominio actual no modela."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        created = create_lab_client(
            db,
            LabClientCreate(
                company="Cliente Estructurado SA",
                address="Av. X 123",
                attention="Ing. X",
                postal_code="45601",
                city="Tlaquepaque",
                state="Jalisco",
            ),
            admin,
            operator_client_id=None,
        )
        client_id = created.id
    listed = client.get("/api/mobile/v1/technician/lab-clients?search=Estructurado", headers=headers)
    assert listed.status_code == 200, listed.text
    match = next(item for item in listed.json() if item["id"] == client_id)
    assert match["postal_code"] == "45601"
    assert match["city"] == "Tlaquepaque"
    assert match["state"] == "Jalisco"


def test_lab_client_can_be_edited_via_patch(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        created = create_lab_client(
            db,
            LabClientCreate(company="Editable SA", address="Calle Vieja", attention="Ing. Y"),
            admin,
            operator_client_id=None,
        )
        client_id = created.id
    edited = client.patch(
        f"/api/mobile/v1/technician/lab-clients/{client_id}",
        json={
            "company": "Editable SA",
            "address": "Calle Nueva 45",
            "attention": "Ing. Z",
            "postal_code": "44100",
            "city": "Guadalajara",
            "state": "Jalisco",
        },
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["address"] == "Calle Nueva 45"
    assert body["postal_code"] == "44100"
    assert body["city"] == "Guadalajara"
    assert body["state"] == "Jalisco"
    with factory() as db:
        persisted = db.get(LabClient, client_id)
        assert persisted.address == "Calle Nueva 45"
        assert persisted.postal_code == "44100"


def test_lab_client_patch_rejects_duplicate_identity(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        first = create_lab_client(
            db, LabClientCreate(company="Primero SA", address="Calle 1", attention="Ing. A"),
            admin, operator_client_id=None,
        )
        second = create_lab_client(
            db, LabClientCreate(company="Segundo SA", address="Calle 2", attention="Ing. B"),
            admin, operator_client_id=None,
        )
        second_id = second.id
        first_company, first_address, first_attention = first.company, first.address, first.attention
    collide = client.patch(
        f"/api/mobile/v1/technician/lab-clients/{second_id}",
        json={"company": first_company, "address": first_address, "attention": first_attention},
        headers=headers,
    )
    assert collide.status_code == 409, collide.text


def test_lab_client_patch_denied_without_permission(lab_context):
    """Sin lab_clients.update explícito ni lab_work_orders.use, PATCH se
    rechaza -- backend sigue siendo la autoridad, no sólo la UI."""
    client, factory, _tokens = lab_context
    with factory() as db:
        no_access_role = Role(name="Sin acceso", description="Sin permisos")
        db.add(no_access_role)
        db.flush()
        blocked_user = User(
            username="lab-blocked",
            email="lab-blocked@example.test",
            full_name="LAB Blocked",
            hashed_password="unused",
            account_type="internal",
            status="active",
            is_active=True,
            role_id=no_access_role.id,
            roles=[no_access_role],
        )
        db.add(blocked_user)
        db.commit()
        blocked_token = create_access_token(
            str(blocked_user.id),
            extra_claims={"roles": [no_access_role.name], "auth_context": "internal"},
        )
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        created = create_lab_client(
            db, LabClientCreate(company="Bloqueado SA", address="", attention=""),
            admin, operator_client_id=None,
        )
        client_id = created.id
    denied = client.patch(
        f"/api/mobile/v1/technician/lab-clients/{client_id}",
        json={"company": "Bloqueado SA"},
        headers=auth(blocked_token),
    )
    assert denied.status_code == 403
    denied_listing = client.get(
        "/api/mobile/v1/technician/lab-clients?limit=5",
        headers=auth(blocked_token),
    )
    assert denied_listing.status_code == 403


def test_lab_client_listing_applies_server_search_limit_offset_and_inactive_filter(lab_context):
    client, factory, tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        created = [
            create_lab_client(
                db,
                LabClientCreate(
                    company=f"Cliente Paginado {index:02d}",
                    address=f"Calle {index}",
                    attention="Compras",
                ),
                admin,
                operator_client_id=None,
            )
            for index in range(31)
        ]
        inactive_id = created[0].id
        deactivate_lab_client(
            db,
            inactive_id,
            operator_client_id=None,
            user=admin,
        )

    headers = auth(tokens["tech"])
    first = client.get(
        "/api/mobile/v1/technician/lab-clients?search=Paginado&limit=5&offset=0",
        headers=headers,
    )
    second = client.get(
        "/api/mobile/v1/technician/lab-clients?search=Paginado&limit=5&offset=5",
        headers=headers,
    )
    assert first.status_code == second.status_code == 200
    assert len(first.json()) == len(second.json()) == 5
    assert {item["id"] for item in first.json()}.isdisjoint(
        {item["id"] for item in second.json()}
    )
    assert all("Paginado" in item["company"] for item in first.json() + second.json())
    assert inactive_id not in {item["id"] for item in first.json() + second.json()}

    default_page = client.get(
        "/api/mobile/v1/technician/lab-clients?search=Paginado",
        headers=headers,
    )
    assert default_page.status_code == 200
    assert len(default_page.json()) == 25
    assert client.get(
        "/api/mobile/v1/technician/lab-clients?limit=0",
        headers=headers,
    ).status_code == 422
    assert client.get(
        "/api/mobile/v1/technician/lab-clients?limit=101",
        headers=headers,
    ).status_code == 422

    hidden = client.get(
        "/api/mobile/v1/technician/lab-clients?search=Cliente%20Paginado%2000&limit=25",
        headers=headers,
    )
    included = client.get(
        "/api/mobile/v1/technician/lab-clients?search=Cliente%20Paginado%2000&limit=25&include_inactive=true",
        headers=headers,
    )
    assert hidden.status_code == included.status_code == 200
    assert hidden.json() == []
    assert [item["id"] for item in included.json()] == [inactive_id]


def test_inactive_clients_are_excluded_from_default_listing(lab_context):
    """11. Clientes inactivos no aparecen en el listado por default."""
    _client, factory, _tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        created = create_lab_client(
            db, LabClientCreate(company="Oculto SA", address="", attention=""),
            admin, operator_client_id=None,
        )
        deactivate_lab_client(db, created.id, operator_client_id=None, user=admin)

        default_listing = list_lab_clients(db, operator_client_id=None)
        assert created.id not in {item.id for item in default_listing}

        full_listing = list_lab_clients(db, operator_client_id=None, include_inactive=True)
        assert created.id in {item.id for item in full_listing}


def test_inactive_count_is_admin_only_and_respects_operator_scope(lab_context):
    client, factory, tokens = lab_context
    endpoint = "/api/mobile/v1/technician/lab-clients/inactive-count"
    assert client.get(endpoint, headers=auth(tokens["tech"])).status_code == 403
    assert client.get(endpoint, headers=auth(tokens["admin"])).json() == {"count": 0}

    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        tenant_a = Client(legal_name="Scope A", commercial_name="Scope A")
        tenant_b = Client(legal_name="Scope B", commercial_name="Scope B")
        db.add_all([tenant_a, tenant_b])
        db.flush()
        global_client = create_lab_client(
            db, LabClientCreate(company="Global inactivo", address="", attention=""),
            admin, operator_client_id=None,
        )
        scoped_a = create_lab_client(
            db, LabClientCreate(company="Scope A inactivo", address="", attention=""),
            admin, operator_client_id=tenant_a.id,
        )
        scoped_b = create_lab_client(
            db, LabClientCreate(company="Scope B inactivo", address="", attention=""),
            admin, operator_client_id=tenant_b.id,
        )
        deactivate_lab_client(db, global_client.id, operator_client_id=None, user=admin)
        deactivate_lab_client(db, scoped_a.id, operator_client_id=tenant_a.id, user=admin)
        deactivate_lab_client(db, scoped_b.id, operator_client_id=tenant_b.id, user=admin)
        assert count_inactive_lab_clients(db, operator_client_id=None) == 1
        assert count_inactive_lab_clients(db, operator_client_id=tenant_a.id) == 1
        assert count_inactive_lab_clients(db, operator_client_id=tenant_b.id) == 1

    assert client.get(endpoint, headers=auth(tokens["admin"])).json() == {"count": 1}


def test_deactivated_client_historical_references_remain_valid(lab_context):
    """12. Referencias históricas (OT ya creada con ese cliente) continúan válidas."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    created_client = client.post(
        "/api/mobile/v1/technician/lab-clients",
        json={"company": "Historico SA", "address": "Calle 1", "attention": "Ing. A"},
        headers=headers,
    )
    assert created_client.status_code == 201, created_client.text
    client_id = created_client.json()["id"]

    payload = create_payload("Se reemplaza por snapshot")
    payload["lab_client_id"] = client_id
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=payload, headers=headers
    )
    assert order.status_code == 201, order.text

    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        deactivate_lab_client(db, client_id, operator_client_id=None, user=admin)

    refreshed = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order.json()['id']}", headers=headers
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["client_name"] == "Historico SA"


# --------------------------------------------------------------------------
# Grupo B -- Cliente documental por equipo (13-18)
# --------------------------------------------------------------------------

def test_certificate_client_mode_order_is_valid_without_final_client(lab_context):
    """13. mode=order es válido sin cliente final."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_ids[0])
        assert equipment.certificate_client_mode == "order"
        assert equipment.final_lab_client_id is None
        assert equipment.final_client_company_snapshot is None


def test_certificate_client_mode_different_requires_company_snapshot(lab_context):
    """14. mode=different exige company snapshot (a nivel schema y a nivel BD)."""
    with pytest.raises(Exception):
        LabEquipmentCertificateClientWrite(certificate_client_mode="different")

    _client, factory, _tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        work_order = LabWorkOrder(
            folio=6400, sequence_number=1, created_by_user_id=admin.id,
            reception_date=date(2026, 8, 13), departure_date=date(2026, 8, 15),
            client_name="OT Cliente", address="Dir OT",
        )
        db.add(work_order)
        db.flush()
        work_order.root_work_order_id = work_order.id
        equipment = LabWorkOrderEquipment(
            work_order_id=work_order.id, position=1, instrument="I", brand="B",
            identification="ID", serial_number="S", is_good_condition=True,
            certificate_client_mode="different",
        )
        db.add(equipment)
        with pytest.raises(IntegrityError):
            db.commit()


def test_certificate_client_mode_different_allows_empty_address_and_attention(lab_context):
    """15. mode=different puede tener address/attention vacíos."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        payload = LabEquipmentCertificateClientWrite(
            certificate_client_mode="different",
            final_client_company_snapshot="Cliente Final B",
            final_client_address_snapshot=None,
            final_client_attention_snapshot=None,
        )
        set_equipment_certificate_client(
            db, order_id, equipment_ids[0], payload, admin, operator_client_id=None
        )
    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_ids[0])
        assert equipment.certificate_client_mode == "different"
        assert equipment.final_client_company_snapshot == "Cliente Final B"
        assert equipment.final_client_address_snapshot is None
        assert equipment.final_client_attention_snapshot is None
        resolved = resolve_equipment_certificate_client(equipment, equipment.work_order)
        assert resolved == {"company": "Cliente Final B", "address": None, "attention": None}


def test_modifying_lab_client_later_does_not_alter_equipment_snapshot(lab_context):
    """16. Modificar posteriormente LabClient NO altera snapshots ya congelados."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        origin = create_lab_client(
            db, LabClientCreate(company="Cliente Final Original", address="Calle A", attention="Ing. A"),
            admin, operator_client_id=None,
        )
        origin_id = origin.id
        payload = LabEquipmentCertificateClientWrite(
            certificate_client_mode="different",
            final_lab_client_id=origin_id,
            final_client_company_snapshot=origin.company,
            final_client_address_snapshot=origin.address,
            final_client_attention_snapshot=origin.attention,
        )
        set_equipment_certificate_client(
            db, order_id, equipment_ids[0], payload, admin, operator_client_id=None
        )

    with factory() as db:
        # El catálogo cambia después...
        origin = db.get(LabClient, origin_id)
        origin.company = "Cliente Final RENOMBRADO"
        origin.address = "Calle RENOMBRADA"
        db.commit()

    with factory() as db:
        # ...pero el snapshot congelado en el equipo no se mueve.
        equipment = db.get(LabWorkOrderEquipment, equipment_ids[0])
        assert equipment.final_client_company_snapshot == "Cliente Final Original"
        assert equipment.final_client_address_snapshot == "Calle A"
        assert equipment.final_lab_client_id == origin_id  # la FK sí sigue apuntando (procedencia)


def test_a_work_order_can_have_equipment_with_different_documentary_clients(lab_context):
    """17. Un grupo/OT puede tener equipos con diferentes clientes documentales."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=3)
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        # equipo 1: order (default, sin tocar)
        # equipo 2: different, cliente B
        set_equipment_certificate_client(
            db, order_id, equipment_ids[1],
            LabEquipmentCertificateClientWrite(
                certificate_client_mode="different", final_client_company_snapshot="Cliente B",
            ),
            admin, operator_client_id=None,
        )
        # equipo 3: different, cliente C
        set_equipment_certificate_client(
            db, order_id, equipment_ids[2],
            LabEquipmentCertificateClientWrite(
                certificate_client_mode="different", final_client_company_snapshot="Cliente C",
            ),
            admin, operator_client_id=None,
        )
    with factory() as db:
        eq1 = db.get(LabWorkOrderEquipment, equipment_ids[0])
        eq2 = db.get(LabWorkOrderEquipment, equipment_ids[1])
        eq3 = db.get(LabWorkOrderEquipment, equipment_ids[2])
        assert eq1.certificate_client_mode == "order"
        assert eq2.final_client_company_snapshot == "Cliente B"
        assert eq3.final_client_company_snapshot == "Cliente C"
        assert resolve_equipment_certificate_client(eq1, eq1.work_order)["company"] == eq1.work_order.client_name


def test_documentary_client_never_creates_a_productive_client(lab_context):
    """18. No se crea ningún Client productivo como efecto secundario."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    with factory() as db:
        before = db.scalar(select(Client.id).limit(1))
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        set_equipment_certificate_client(
            db, order_id, equipment_ids[0],
            LabEquipmentCertificateClientWrite(
                certificate_client_mode="different", final_client_company_snapshot="Cliente Final",
            ),
            admin, operator_client_id=None,
        )
    with factory() as db:
        after_count = len(list(db.scalars(select(Client))))
        assert after_count == 0
        assert before is None


# --------------------------------------------------------------------------
# Grupo C -- Tickets (19-21)
# --------------------------------------------------------------------------

def test_field_sheet_template_request_is_a_valid_ticket_type(lab_context):
    """19. field_sheet_template_request es tipo válido a nivel BD."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    with factory() as db:
        tech = db.scalar(select(User).where(User.username == "lab-tech"))
        ticket = create_field_sheet_template_request_ticket(
            db,
            FieldSheetTemplateRequestCreate(
                work_order_id=order_id,
                equipment_id=equipment_ids[0],
                reason="Falta plantilla",
                description="No encuentro la hoja de campo necesaria",
            ),
            tech,
            operator_client_id=None,
        )
        assert ticket.type == "field_sheet_template_request"
        assert ticket.status == "pending"


def test_field_sheet_template_request_links_to_work_order_and_equipment(lab_context):
    """20. Puede ligarse a OT/equipo LAB (y a conversación vía infraestructura existente)."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    response = client.post(
        "/api/mobile/v1/technician/tickets/field-sheet-template",
        json={
            "work_order_id": order_id,
            "equipment_id": equipment_ids[0],
            "reason": "Falta plantilla",
            "description": "No encuentro la hoja de campo necesaria",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["work_order_id"] == order_id
    assert body["equipment_id"] == equipment_ids[0]
    assert body["conversation_id"] is not None
    with factory() as db:
        ticket = db.get(OperationalTicket, body["id"])
        assert ticket.type == "field_sheet_template_request"


def test_previous_ticket_types_still_function(lab_context):
    """21. Tipos anteriores (folio, partial_close, etc.) siguen funcionando."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/service",
        json={"service_type": "accredited", "linked_company_id": None},
        headers=headers,
    )
    ticket = client.post(
        "/api/mobile/v1/technician/tickets/folio",
        json={
            "work_order_id": order_id,
            "equipment_id": equipment_ids[0],
            "type": "manual_myc_folio",
            "requested_folio": "MYCA-99",
            "reason": "Prueba",
            "description": "Prueba de regresión",
        },
        headers=headers,
    )
    assert ticket.status_code == 201, ticket.text
    assert ticket.json()["type"] == "manual_myc_folio"


def _sign_and_complete_field_sheet(client, headers, order_id, equipment_id) -> int:
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json=_signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    sheet_json = created.json()
    rows = [
        {
            "id": row["id"],
            "section_key": row["section_key"],
            "row_number": row["row_number"],
            "row_data": {"result": "1.00"} if index == 0 else row["row_data"],
        }
        for index, row in enumerate(sheet_json["results_rows"])
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
    return completed.json()["id"]


def test_field_sheet_reopen_is_a_valid_ticket_type(lab_context):
    """Cierre UX 2026-09: field_sheet_reopen es tipo válido a nivel BD --
    desbloqueo de UNA hoja/equipo, distinto de reopen_work_order (que reabre
    la OT completa y sólo aplica cuando ya está cerrada)."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    service = client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/service",
        json={"service_type": "accredited", "linked_company_id": None},
        headers=headers,
    )
    assert service.status_code == 200, service.text
    sheet_id = _sign_and_complete_field_sheet(client, headers, order_id, equipment_ids[0])
    with factory() as db:
        from app.schemas.operational_ticket import FieldSheetReopenTicketCreate
        from app.services.operational_tickets import create_field_sheet_reopen_ticket
        tech = db.scalar(select(User).where(User.username == "lab-tech"))
        ticket = create_field_sheet_reopen_ticket(
            db,
            FieldSheetReopenTicketCreate(
                work_order_id=order_id,
                equipment_id=equipment_ids[0],
                reason="Error de captura",
                description="El resultado de la fila 2 está mal transcrito",
            ),
            tech,
            operator_client_id=None,
        )
        assert ticket.type == "field_sheet_reopen"
        assert ticket.status == "pending"
        assert ticket.resolution_snapshot["field_sheet_id"] == sheet_id


def test_field_sheet_reopen_requires_a_completed_sheet(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    denied = client.post(
        "/api/mobile/v1/technician/tickets/field-sheet-reopen",
        json={
            "work_order_id": order_id,
            "equipment_id": equipment_ids[0],
            "reason": "Prueba",
            "description": "El equipo todavía no tiene hoja completed",
        },
        headers=headers,
    )
    assert denied.status_code == 409


def test_field_sheet_reopen_ticket_notifies_reviewer_on_create_and_requester_on_resolve(lab_context):
    """Cierre UX 2026-09: crear y resolver un ticket field_sheet_reopen deja
    Notification para el destinatario correcto en cada paso -- antes
    create_field_sheet_reopen_ticket y resolve_operational_ticket sólo
    hacían db.commit() plano, sin dispatch, y algunos tipos ni siquiera
    llamaban a notify_ticket_created."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    service = client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/service",
        json={"service_type": "accredited", "linked_company_id": None},
        headers=headers,
    )
    assert service.status_code == 200, service.text

    _sign_and_complete_field_sheet(client, headers, order_id, equipment_ids[0])

    created = client.post(
        "/api/mobile/v1/technician/tickets/field-sheet-reopen",
        json={
            "work_order_id": order_id,
            "equipment_id": equipment_ids[0],
            "reason": "Error de captura",
            "description": "Hay que recapturar un valor",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]

    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        created_notification = db.scalar(
            select(Notification).where(
                Notification.recipient_user_id == admin.id,
                Notification.notification_type == "ticket.created",
                Notification.entity_id == ticket_id,
            )
        )
        assert created_notification is not None
        assert created_notification.title == "Nueva solicitud de desbloqueo de hoja"

    resolved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket_id}/resolve",
        json={"comment": "Procede"},
        headers=admin_headers,
    )
    assert resolved.status_code == 200, resolved.text

    with factory() as db:
        tech = db.scalar(select(User).where(User.username == "lab-tech"))
        resolved_notification = db.scalar(
            select(Notification).where(
                Notification.recipient_user_id == tech.id,
                Notification.notification_type == "ticket.resolved",
                Notification.entity_id == ticket_id,
            )
        )
        assert resolved_notification is not None
        assert "OT" in resolved_notification.body


def test_reject_ticket_never_crashes_for_a_ticket_type_without_a_work_order(lab_context):
    """certificate_folio_block no lleva work_order_id (es una reserva a
    nivel cliente externo, ver create_certificate_block_ticket). reject_ticket
    es genérico -- cualquier tipo, cualquier revisor con tickets.review --
    y notify_ticket_rejected antes accedía a ticket.work_order.folio sin
    guardar, lo que lanzaba AttributeError en cuanto alguien rechazara un
    ticket de este tipo. Se prueba a nivel servicio porque crear este tipo
    de ticket por API está reservado a actores externos (client_id
    presente); el bug que se corrige está en reject/notify, no en la
    creación."""
    _client, factory, tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        tech = db.scalar(select(User).where(User.username == "lab-tech"))
        ticket = OperationalTicket(
            type="certificate_folio_block",
            status="pending",
            work_order_id=None,
            operator_client_id=None,
            requested_by_user_id=tech.id,
            reason="Prueba",
            description="Reserva de folios de prueba",
            accredited_quantity=1,
            traceable_quantity=0,
        )
        db.add(ticket)
        db.commit()
        ticket_id = ticket.id

        result = reject_ticket(db, ticket_id, TicketReject(comment="No procede"), admin)
        assert result.status == "rejected"

        notification = db.scalar(
            select(Notification).where(
                Notification.recipient_user_id == tech.id,
                Notification.notification_type == "ticket.rejected",
                Notification.entity_id == ticket_id,
            )
        )
        assert notification is not None
        assert notification.title == "Solicitud de folios certificados rechazada"
        assert notification.body == notification.title  # sin OT que citar


# --------------------------------------------------------------------------
# Grupo D -- Estados LabWorkOrder (22-24)
# --------------------------------------------------------------------------

def test_new_prepared_states_are_accepted_by_the_constraint(lab_context):
    """22. El constraint/modelo acepta los nuevos estados preparados (aún no
    producidos por ningún servicio, pero representables)."""
    _client, factory, _tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        for index, status in enumerate(("received_signed", "in_progress", "ready_to_close"), start=1):
            work_order = LabWorkOrder(
                folio=6500 + index, sequence_number=1, created_by_user_id=admin.id,
                reception_date=date(2026, 8, 13), departure_date=date(2026, 8, 15),
                client_name=f"Cliente {status}", address="Dir", status=status,
            )
            db.add(work_order)
            db.flush()
            work_order.root_work_order_id = work_order.id
        db.commit()


def test_existing_historical_states_remain_valid(lab_context):
    """23. Estados históricos existentes (draft, ready_for_signatures, completed,
    partially_closed, cancelled) siguen siendo válidos."""
    _client, factory, _tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        for index, status in enumerate(
            ("draft", "ready_for_signatures", "completed", "partially_closed", "cancelled"), start=1
        ):
            work_order = LabWorkOrder(
                folio=6600 + index, sequence_number=1, created_by_user_id=admin.id,
                reception_date=date(2026, 8, 13), departure_date=date(2026, 8, 15),
                client_name=f"Cliente {status}", address="Dir", status=status,
            )
            db.add(work_order)
            db.flush()
            work_order.root_work_order_id = work_order.id
        db.commit()


def test_existing_partial_close_and_cancellation_flows_still_work(lab_context):
    """24. Cierre parcial/cancelación existentes no se rompen."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, _equipment_ids = _setup_order_with_equipment(client, headers)
    cancelled = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/cancel",
        json={"reason": "Prueba de regresión de cancelación"},
        headers=auth(tokens["admin"]),
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"


# --------------------------------------------------------------------------
# Grupo E -- Regresión (25-27)
# --------------------------------------------------------------------------

def test_field_sheet_ownership_regression_productive_and_lab_intact(lab_context):
    """25. Ownership FieldSheet productivo/LAB (equipment_id XOR lab_equipment_id)
    continúa intacto."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/service",
        json={"service_type": "accredited", "linked_company_id": None},
        headers=headers,
    )
    # Fase 3: la captura FieldSheet sólo procede tras la recepción firmada.
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json=_signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    with factory() as db:
        sheet = db.get(FieldSheet, created.json()["id"])
        assert sheet.lab_equipment_id == equipment_ids[0]
        assert sheet.equipment_id is None
        # el constraint XOR sigue vivo: violar la mutua exclusividad debe fallar.
        sheet.equipment_id = 999999
        with pytest.raises(IntegrityError):
            db.commit()


def test_folio_generation_and_reservation_unchanged(lab_context):
    """26. Generación/reserva de folios existente no cambia."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    service = client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/service",
        json={"service_type": "accredited", "linked_company_id": None},
        headers=headers,
    )
    assert service.status_code == 200, service.text
    from datetime import date
    month_year = date.today().strftime("%m-%y")
    assert service.json()["equipment"][0]["certificate_folio"] == f"MYCA-{month_year}-4700"
    with factory() as db:
        sequence = db.scalar(
            select(InstitutionalFolioSequence).where(
                InstitutionalFolioSequence.document_type == "lab_certificate",
                InstitutionalFolioSequence.prefix == "MYCA",
            )
        )
        assert sequence.next_value == 4701


def test_signature_session_model_unchanged(lab_context):
    """27. SignatureSession existente (modelo/servicio) no cambia."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers)
    client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/service",
        json={"service_type": "traceable", "linked_company_id": None},
        headers=headers,
    )
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json=_signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    with factory() as db:
        session = db.scalar(select(LabWorkOrderSignatureSession))
        assert session is not None
        assert {item.signature_type for item in session.signatures} == {"technician", "client"}
