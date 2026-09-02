"""Fase 3 del rediseño LAB: recepción firmada + máquina de estados.

Cubre exclusivamente lo que Fase 3 introduce/cambia:
- La firma pasa a representar CONFORMIDAD DE RECEPCIÓN (antes de FieldSheets),
  no cierre técnico.
- Prerrequisitos de recepción por equipo (servicio elegido, folio
  MYCA/MYCT reservado si aplica, LinkedCompany congelada si vinculado).
- draft -> received_signed -> in_progress -> ready_to_close -> completed.
- Inmutabilidad de equipo/cliente/servicio/cliente receptor tras
  received_signed (reutiliza _ensure_members_editable, ya exigía
  status == "draft").
- Captura FieldSheet sólo después de received_signed/in_progress.
- Compatibilidad legacy de ready_for_signatures y de los endpoints Fase 2.
- Permisos: Captura puede capturar FieldSheets pero no firmar/editar
  recepción; externos no ganan facultades internas; tenant isolation intacta.

NO reconstruye nada de Fase 1/2 (LabClient, folios MYCA/MYCT, LinkedCompany,
alta/edición integrada de equipo): esas reglas están cubiertas por
test_lab_domain_phase1.py y test_lab_phase2_integrated_alta.py y no cambian
aquí, salvo en el punto exacto en que Fase 3 las reutiliza.
"""

from __future__ import annotations

import base64
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
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
from app.models.lab_work_order import (
    LabWorkOrder,
    LabWorkOrderEquipment,
    LabWorkOrderSignatureSession,
)
from app.models.linked_company import LinkedCompany
from app.models.user import Role, User
from app.services.portal.permission_service import ensure_portal_catalog


PASSWORD = "MobilePass123"

PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
).decode()


@pytest.fixture()
def phase3_context():
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


def signatures_payload(*, technician_name: str = "Técnico LAB", client_name: str = "Cliente LAB") -> dict:
    signed_at = datetime.now(timezone.utc).isoformat()
    return {
        "technician": {
            "signer_name": technician_name, "signed_at": signed_at, "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
        "client": {
            "signer_name": client_name, "signed_at": signed_at, "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
    }


def create_order(client: TestClient, headers: dict[str, str], **overrides) -> int:
    response = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=create_payload(**overrides), headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def add_equipment(client: TestClient, headers: dict[str, str], order_id: int, index: int, **extra) -> int:
    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(index, **extra),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["equipment"][-1]["id"]


def set_service(
    client: TestClient, headers: dict[str, str], order_id: int, equipment_id: int,
    service_type: str, linked_company_id: int | None = None,
) -> dict:
    response = client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": service_type, "linked_company_id": linked_company_id},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def sign(client: TestClient, headers: dict[str, str], order_id: int, *, individual: bool = True, **payload_kwargs):
    path = "signatures/individual" if individual else "signatures"
    return client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/{path}",
        json=signatures_payload(**payload_kwargs),
        headers=headers,
    )


def create_and_sign_ready_order(
    client: TestClient, headers: dict[str, str], *, service_type: str = "traceable", name: str = "Cliente LAB",
) -> tuple[int, int]:
    """A single-OT, single-equipment order already coherent and signed
    (received_signed), ready for FieldSheet capture. Shared setup for the
    many tests that only care about what happens after reception."""
    order_id = create_order(client, headers, client_name=name)
    equipment_id = add_equipment(client, headers, order_id, 1)
    set_service(client, headers, order_id, equipment_id, service_type)
    signed = sign(client, headers, order_id)
    assert signed.status_code == 200, signed.text
    assert signed.json()["status"] == "received_signed"
    return order_id, equipment_id


def create_field_sheet(client: TestClient, headers: dict[str, str], order_id: int, equipment_id: int):
    return client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )


def complete_field_sheet_fully(client: TestClient, headers: dict[str, str], order_id: int, equipment_id: int) -> int:
    created = create_field_sheet(client, headers, order_id, equipment_id)
    assert created.status_code == 201, created.text
    sheet_json = created.json()
    sheet_id = sheet_json["id"]
    rows = [
        {
            "id": row["id"],
            "section_key": row["section_key"],
            "row_number": row["row_number"],
            "row_data": {"result": "1.00"} if index == 0 else row["row_data"],
        }
        for index, row in enumerate(sheet_json["results_rows"])
    ]
    updated = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"final_condition": "BUENA", "observations": "Sin observaciones", "results_rows": rows},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    return sheet_id


# --------------------------------------------------------------------------
# Prerrequisitos de recepción (1-5)
# --------------------------------------------------------------------------

def test_signing_requires_at_least_one_equipment(phase3_context):
    """1. OT sin equipos no puede firmar recepción."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id = create_order(client, headers)
    response = sign(client, headers, order_id)
    assert response.status_code == 409
    with_group = sign(client, headers, order_id, individual=False)
    assert with_group.status_code == 409


def test_signing_blocks_incomplete_equipment_configuration(phase3_context):
    """2. Equipo incompleto (sin servicio elegido) bloquea recepción."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id = create_order(client, headers)
    add_equipment(client, headers, order_id, 1)
    response = sign(client, headers, order_id)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "LAB_RECEPTION_INCOMPLETE"
    assert response.json()["detail"]["items"][0]["reason"] == "Selecciona el tipo de servicio"


def test_signing_allows_accredited_with_reserved_folio(phase3_context):
    """3. Acreditado con MYCA válido (reservado) permite recepción."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id = create_order(client, headers)
    equipment_id = add_equipment(client, headers, order_id, 1)
    service = set_service(client, headers, order_id, equipment_id, "accredited")
    month_year = date.today().strftime("%m-%y")
    assert service["equipment"][0]["certificate_folio"] == f"MYCA-{month_year}-4700"
    response = sign(client, headers, order_id)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "received_signed"


def test_signing_allows_traceable_with_reserved_folio(phase3_context):
    """4. Trazable con MYCT válido (reservado) permite recepción."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id = create_order(client, headers)
    equipment_id = add_equipment(client, headers, order_id, 1)
    service = set_service(client, headers, order_id, equipment_id, "traceable")
    month_year = date.today().strftime("%m-%y")
    assert service["equipment"][0]["certificate_folio"] == f"MYCT-{month_year}-1640"
    response = sign(client, headers, order_id)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "received_signed"


def test_signing_allows_linked_with_pending_folio(phase3_context):
    """5. Vinculado con LinkedCompany congelada y folio PENDIENTE puede firmar
    recepción -- la autorización del folio vinculado es requisito técnico
    posterior, no de recepción."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    with factory() as db:
        linked = LinkedCompany(name="Vinculada", abbreviation="VIN", default_certificate_prefix="VIN")
        db.add(linked)
        db.commit()
        linked_id = linked.id
    order_id = create_order(client, headers)
    equipment_id = add_equipment(client, headers, order_id, 1)
    service = set_service(client, headers, order_id, equipment_id, "linked", linked_id)
    assert service["equipment"][0]["folio_status"] == "pending"
    assert service["equipment"][0]["certificate_folio"] is None
    response = sign(client, headers, order_id)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "received_signed"


def test_signing_and_field_sheet_allow_linked_without_company(phase3_context):
    """Vinculado sin empresa y con folio pendiente puede firmar y capturar."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id = create_order(client, headers)
    equipment_id = add_equipment(client, headers, order_id, 1)
    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        equipment.service_type = "linked"
        equipment.folio_status = "pending"
        db.commit()
    response = sign(client, headers, order_id)
    assert response.status_code == 200, response.text
    sheet = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert sheet.status_code == 201, sheet.text


# --------------------------------------------------------------------------
# Transición draft -> received_signed (6-7)
# --------------------------------------------------------------------------

def test_partial_signature_does_not_change_status(phase3_context):
    """6. Sólo una firma (técnico o cliente) no cambia el status -- el schema
    exige ambas en la misma llamada (no se construye un segundo sistema de
    firmas incremental); a nivel de dominio, esto se verifica confirmando que
    _create_signature_session sólo persiste AMBAS firmas atómicamente y que
    ninguna llamada parcial (payload inválido por schema) deja rastro."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id = create_order(client, headers)
    equipment_id = add_equipment(client, headers, order_id, 1)
    set_service(client, headers, order_id, equipment_id, "traceable")
    payload = signatures_payload()
    del payload["client"]
    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 422
    with factory() as db:
        work_order = db.get(LabWorkOrder, order_id)
        assert work_order.status == "draft"
        assert work_order.signature_session_id is None
        assert db.scalar(select(LabWorkOrderSignatureSession)) is None


def test_full_signature_moves_draft_to_received_signed(phase3_context):
    """7. La segunda firma (con la primera ya válida en la misma llamada)
    cambia draft -> received_signed, de forma transaccional."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, _equipment_id = create_and_sign_ready_order(client, headers)
    with factory() as db:
        work_order = db.get(LabWorkOrder, order_id)
        assert work_order.status == "received_signed"
        assert work_order.signature_session_id is not None
        session = db.get(LabWorkOrderSignatureSession, work_order.signature_session_id)
        assert {item.signature_type for item in session.signatures} == {"technician", "client"}


# --------------------------------------------------------------------------
# Inmutabilidad después de received_signed (8-13)
# --------------------------------------------------------------------------

def test_received_signed_blocks_add_equipment(phase3_context):
    """8. received_signed bloquea agregar equipo."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, _equipment_id = create_and_sign_ready_order(client, headers)
    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(2),
        headers=headers,
    )
    assert response.status_code == 409


def test_received_signed_blocks_update_equipment(phase3_context):
    """9. received_signed bloquea editar datos del equipo."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    response = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}",
        json=equipment_payload(1, serial_number="SER-1-CAMBIADO"),
        headers=headers,
    )
    assert response.status_code == 409


def test_received_signed_blocks_certificate_client_change(phase3_context):
    """10. received_signed bloquea cambiar el cliente documental."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    response = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/certificate-client",
        json={
            "certificate_client_mode": "different",
            "final_client_company_snapshot": "Cliente Final Tardío",
        },
        headers=headers,
    )
    assert response.status_code == 409


def test_received_signed_blocks_service_change(phase3_context):
    """11. received_signed bloquea cambiar el servicio."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers, service_type="traceable")
    response = client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "accredited", "linked_company_id": None},
        headers=headers,
    )
    assert response.status_code == 409


def test_received_signed_blocks_receiving_client_change(phase3_context):
    """12. received_signed bloquea cambiar el cliente receptor de la OT."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    with factory() as db:
        from app.schemas.lab_client import LabClientCreate
        from app.services.lab_clients import create_lab_client
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        lab_client = create_lab_client(
            db, LabClientCreate(company="Cliente Receptor Nuevo", address="", attention=""), admin,
            operator_client_id=None,
        )
        lab_client_id = lab_client.id
    order_id, _equipment_id = create_and_sign_ready_order(client, headers)
    response = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}",
        json={"lab_client_id": lab_client_id},
        headers=headers,
    )
    assert response.status_code == 409


def test_received_signed_preserves_folios_across_blocked_mutations(phase3_context):
    """13. received_signed preserva folios -- ninguno de los intentos
    bloqueados de 8-11 altera el folio ya reservado."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers, service_type="traceable")
    with factory() as db:
        before = db.get(LabWorkOrderEquipment, equipment_id).certificate_folio
    assert before is not None
    client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(2), headers=headers,
    )
    client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}",
        json=equipment_payload(1, serial_number="SER-1-CAMBIADO"), headers=headers,
    )
    client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "accredited", "linked_company_id": None}, headers=headers,
    )
    with factory() as db:
        after = db.get(LabWorkOrderEquipment, equipment_id).certificate_folio
    assert after == before


# --------------------------------------------------------------------------
# Captura FieldSheet gateada por recepción (14-19)
# --------------------------------------------------------------------------

def test_draft_blocks_field_sheet_creation(phase3_context):
    """14. draft no permite captura FieldSheet."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id = create_order(client, headers)
    equipment_id = add_equipment(client, headers, order_id, 1)
    set_service(client, headers, order_id, equipment_id, "traceable")
    response = create_field_sheet(client, headers, order_id, equipment_id)
    assert response.status_code == 409


def test_received_signed_allows_field_sheet_creation(phase3_context):
    """15. received_signed permite crear/iniciar FieldSheet."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    response = create_field_sheet(client, headers, order_id, equipment_id)
    assert response.status_code == 201, response.text


def test_first_field_sheet_moves_to_in_progress(phase3_context):
    """16. La primera mutación técnica real (crear la primera FieldSheet)
    cambia received_signed -> in_progress, backend-authoritative."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    with factory() as db:
        assert db.get(LabWorkOrder, order_id).status == "received_signed"
    created = create_field_sheet(client, headers, order_id, equipment_id)
    assert created.status_code == 201, created.text
    with factory() as db:
        assert db.get(LabWorkOrder, order_id).status == "in_progress"


def test_subsequent_captures_keep_in_progress(phase3_context):
    """17. Capturas posteriores mantienen in_progress (no retroceden ni
    saltan por su cuenta a ready_to_close antes de tiempo)."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id = create_order(client, headers)
    equipment_ids = [add_equipment(client, headers, order_id, index) for index in (1, 2)]
    for equipment_id in equipment_ids:
        set_service(client, headers, order_id, equipment_id, "traceable")
    signed = sign(client, headers, order_id)
    assert signed.status_code == 200, signed.text
    create_field_sheet(client, headers, order_id, equipment_ids[0])
    with factory() as db:
        assert db.get(LabWorkOrder, order_id).status == "in_progress"
    updated = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"observations": "Avance parcial"},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    with factory() as db:
        assert db.get(LabWorkOrder, order_id).status == "in_progress"


# --------------------------------------------------------------------------
# ready_to_close y cierre (18-24)
# --------------------------------------------------------------------------

def test_completing_all_sheets_moves_to_ready_to_close(phase3_context):
    """18. Completar los requisitos técnicos (todas las FieldSheet) produce
    ready_to_close."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    with factory() as db:
        assert db.get(LabWorkOrder, order_id).status == "ready_to_close"


def test_new_flow_never_produces_ready_for_signatures(phase3_context):
    """19. El nuevo flujo LAB no produce ready_for_signatures en ningún
    punto del ciclo de vida completo (draft -> ... -> completed)."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    observed = [db_status(factory, order_id)]
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    observed.append(db_status(factory, order_id))
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual", headers=headers,
    )
    assert completed.status_code == 200, completed.text
    observed.append(db_status(factory, order_id))
    assert "ready_for_signatures" not in observed
    assert observed[-1] == "completed"


def db_status(factory, order_id: int) -> str:
    with factory() as db:
        return db.get(LabWorkOrder, order_id).status


def test_ready_to_close_can_complete(phase3_context):
    """20. ready_to_close puede cerrar."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    assert db_status(factory, order_id) == "ready_to_close"
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual", headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"


def test_completion_does_not_request_a_new_reception_signature(phase3_context):
    """21. El cierre no pide ni crea una nueva firma de recepción -- ninguna
    LabWorkOrderSignatureSession adicional aparece entre ready_to_close y
    completed."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    with factory() as db:
        sessions_before = db.scalar(select(LabWorkOrderSignatureSession.id).where(
            LabWorkOrderSignatureSession.root_work_order_id == order_id
        ))
        count_before = len(list(db.scalars(select(LabWorkOrderSignatureSession))))
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual", headers=headers,
    )
    assert completed.status_code == 200, completed.text
    with factory() as db:
        count_after = len(list(db.scalars(select(LabWorkOrderSignatureSession))))
    assert count_after == count_before
    assert completed.json()["signature_session_id"] == sessions_before


def test_completed_still_has_original_signature_session(phase3_context):
    """22. completed conserva la SignatureSession original de la recepción."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    with factory() as db:
        original_session_id = db.get(LabWorkOrder, order_id).signature_session_id
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual", headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["signature_session_id"] == original_session_id


def test_field_sheet_links_to_exact_reception_signature_session(phase3_context):
    """23. La FieldSheet queda vinculada a la sesión histórica exacta de la
    recepción (no una resolución diferida ni recalculada)."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    with factory() as db:
        session_id = db.get(LabWorkOrder, order_id).signature_session_id
    created = create_field_sheet(client, headers, order_id, equipment_id)
    assert created.status_code == 201, created.text
    with factory() as db:
        sheet = db.get(FieldSheet, created.json()["id"])
        assert sheet.lab_signature_session_id == session_id


def test_field_sheet_does_not_use_latest_group_session(phase3_context):
    """24. La resolución de sesión de una FieldSheet NO usa "la última sesión
    del grupo": una OT hermana firmada DESPUÉS (creando una versión mayor
    sobre el mismo root) no debe mover la FieldSheet ya creada de la primera."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["admin"])
    tech_headers = auth(tokens["tech"])
    payload = {**create_payload("Cliente grupo histórico"), "quantity": 2}
    group = client.post("/api/lab-work-order-groups", json=payload, headers=headers)
    assert group.status_code == 201, group.text
    members = group.json()["related_work_orders"]

    first_id, second_id = (item["id"] for item in members)
    first_equipment = add_equipment(client, tech_headers, first_id, 1)
    set_service(client, tech_headers, first_id, first_equipment, "traceable")
    first_signed = sign(client, tech_headers, first_id)
    assert first_signed.status_code == 200, first_signed.text
    first_sheet_id = complete_field_sheet_fully(client, tech_headers, first_id, first_equipment)
    with factory() as db:
        first_session_id = db.get(FieldSheet, first_sheet_id).lab_signature_session_id

    second_equipment = add_equipment(client, tech_headers, second_id, 1)
    set_service(client, tech_headers, second_id, second_equipment, "traceable")
    second_signed = sign(client, tech_headers, second_id)
    assert second_signed.status_code == 200, second_signed.text
    with factory() as db:
        second_session_id = db.get(LabWorkOrder, second_id).signature_session_id
        assert second_session_id != first_session_id
        first_session = db.get(LabWorkOrderSignatureSession, first_session_id)
        second_session = db.get(LabWorkOrderSignatureSession, second_session_id)
        assert second_session.version > first_session.version
        # La hoja de la primera OT sigue apuntando a su propia sesión.
        assert db.get(FieldSheet, first_sheet_id).lab_signature_session_id == first_session_id


# --------------------------------------------------------------------------
# Grupos, individual, cierre parcial y reapertura (25-31)
# --------------------------------------------------------------------------

def test_group_signing_produces_received_signed_for_cohort(phase3_context):
    """25. Firmar el grupo correctamente produce received_signed para toda
    la cohorte abierta, con una única SignatureSession compartida."""
    client, factory, tokens, _tenants = phase3_context
    admin_headers = auth(tokens["admin"])
    headers = auth(tokens["tech"])
    payload = {**create_payload("Grupo Fase 3"), "quantity": 2}
    group = client.post("/api/lab-work-order-groups", json=payload, headers=admin_headers)
    assert group.status_code == 201, group.text
    members = group.json()["related_work_orders"]
    root_id = group.json()["id"]
    for member in members:
        equipment_id = add_equipment(client, headers, member["id"], 1)
        set_service(client, headers, member["id"], equipment_id, "traceable")
    response = sign(client, headers, root_id, individual=False)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "received_signed"
    session_id = response.json()["signature_session_id"]
    assert all(item["status"] == "received_signed" for item in response.json()["related_work_orders"])
    assert all(item["signature_session_id"] == session_id for item in response.json()["related_work_orders"])


def test_incomplete_group_member_blocks_group_signing(phase3_context):
    """26. Un miembro incompleto del grupo bloquea TODA la firma grupal --
    no hay transición parcial a received_signed para el resto."""
    client, factory, tokens, _tenants = phase3_context
    admin_headers = auth(tokens["admin"])
    headers = auth(tokens["tech"])
    payload = {**create_payload("Grupo incompleto"), "quantity": 2}
    group = client.post("/api/lab-work-order-groups", json=payload, headers=admin_headers)
    assert group.status_code == 201, group.text
    members = group.json()["related_work_orders"]
    root_id = group.json()["id"]
    ready_equipment = add_equipment(client, headers, members[0]["id"], 1)
    set_service(client, headers, members[0]["id"], ready_equipment, "traceable")
    add_equipment(client, headers, members[1]["id"], 1)  # sin servicio: incompleto
    response = sign(client, headers, root_id, individual=False)
    assert response.status_code == 409
    with factory() as db:
        assert all(
            db.get(LabWorkOrder, member["id"]).status == "draft" for member in members
        )


def test_individual_signing_still_works(phase3_context):
    """27. La firma individual legítima (una sola OT de una cohorte) sigue
    funcionando y no afecta a sus hermanas."""
    client, factory, tokens, _tenants = phase3_context
    admin_headers = auth(tokens["admin"])
    headers = auth(tokens["tech"])
    payload = {**create_payload("Individual dentro de grupo"), "quantity": 2}
    group = client.post("/api/lab-work-order-groups", json=payload, headers=admin_headers)
    assert group.status_code == 201, group.text
    members = group.json()["related_work_orders"]
    first_id, second_id = (item["id"] for item in members)
    equipment_id = add_equipment(client, headers, first_id, 1)
    set_service(client, headers, first_id, equipment_id, "traceable")
    response = sign(client, headers, first_id)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "received_signed"
    assert response.json()["signature_scope"] == "individual"
    with factory() as db:
        assert db.get(LabWorkOrder, second_id).status == "draft"
        assert db.get(LabWorkOrder, second_id).signature_session_id is None


def test_closure_cohorts_still_work_for_a_partially_closed_group(phase3_context):
    """28. Las closure cohorts existentes (individual firmado y cerrado
    dentro de un grupo más grande) siguen funcionando bajo la nueva máquina
    de estados."""
    client, factory, tokens, _tenants = phase3_context
    admin_headers = auth(tokens["admin"])
    headers = auth(tokens["tech"])
    payload = {**create_payload("Cohorte de cierre"), "quantity": 2}
    group = client.post("/api/lab-work-order-groups", json=payload, headers=admin_headers)
    assert group.status_code == 201, group.text
    members = group.json()["related_work_orders"]
    first_id, second_id = (item["id"] for item in members)
    equipment_id = add_equipment(client, headers, first_id, 1)
    set_service(client, headers, first_id, equipment_id, "traceable")
    signed = sign(client, headers, first_id)
    assert signed.status_code == 200, signed.text
    complete_field_sheet_fully(client, headers, first_id, equipment_id)
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{first_id}/complete/individual", headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"
    with factory() as db:
        assert db.get(LabWorkOrder, second_id).status == "draft"


def test_partial_close_ticket_still_works_under_new_states(phase3_context):
    """29. El flujo de cierre parcial (ticket sobre una OT del grupo con
    hojas pendientes) sigue funcionando -- ahora gateado por
    received_signed/in_progress en vez de draft."""
    client, factory, tokens, _tenants = phase3_context
    admin_headers = auth(tokens["admin"])
    headers = auth(tokens["tech"])
    payload = {**create_payload("Grupo cierre parcial"), "quantity": 2}
    group = client.post("/api/lab-work-order-groups", json=payload, headers=admin_headers)
    assert group.status_code == 201, group.text
    members = group.json()["related_work_orders"]
    first_id = members[0]["id"]
    with factory() as db:
        from app.models.lab_client import LabClient
        work_order = db.get(LabWorkOrder, first_id)
        client_row = LabClient(
            company="Cliente cierre parcial", address="", attention="",
            normalized_company="cliente cierre parcial", normalized_address="", normalized_attention="",
            operator_client_id=None, created_by_user_id=work_order.created_by_user_id,
        )
        db.add(client_row)
        db.flush()
        work_order.lab_client_id = client_row.id
        db.commit()
    equipment_id = add_equipment(client, headers, first_id, 1)
    set_service(client, headers, first_id, equipment_id, "traceable")
    signed = sign(client, headers, first_id)
    assert signed.status_code == 200, signed.text
    created_sheet = create_field_sheet(client, headers, first_id, equipment_id)
    assert created_sheet.status_code == 201, created_sheet.text
    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-close",
        json={"work_order_id": first_id, "reason": "Prueba", "description": "Hoja pendiente"},
        headers=headers,
    )
    assert ticket.status_code == 201, ticket.text


def test_reopen_preserve_still_completes_without_resigning_reception(phase3_context):
    """30. Reapertura preservando la firma sigue funcionando: no exige
    volver a firmar la recepción para poder cerrar de nuevo."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual", headers=headers,
    )
    assert completed.status_code == 200, completed.text
    original_session_id = completed.json()["signature_session_id"]

    ticket = client.post(
        "/api/mobile/v1/technician/tickets",
        json={
            "work_order_id": order_id, "reason": "Corrección menor",
            "description": "Ajustar una observación de la hoja.",
            "requested_signature_policy": "preserve",
        },
        headers=headers,
    )
    assert ticket.status_code == 201, ticket.text
    approved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket.json()['id']}/approve",
        json={"signature_policy": "preserve"},
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    reopened = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers,
    ).json()
    assert reopened["status"] == "draft"
    assert reopened["signature_preserved"] is True
    assert reopened["signature_session_id"] == original_session_id

    reclosed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual", headers=headers,
    )
    assert reclosed.status_code == 200, reclosed.text
    assert reclosed.json()["status"] == "completed"
    assert reclosed.json()["signature_session_id"] == original_session_id


def test_reopen_invalidate_does_not_overwrite_historical_field_sheet_session(phase3_context):
    """31. Reapertura que invalida la firma NO sobrescribe la sesión
    histórica de una FieldSheet ya creada bajo la sesión anterior -- se
    preserva tal cual; sólo el nuevo trabajo (equipo/servicio/recepción)
    exige una firma nueva."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers, service_type="traceable")
    sheet_id = complete_field_sheet_fully(client, headers, order_id, equipment_id)
    with factory() as db:
        original_session_id = db.get(FieldSheet, sheet_id).lab_signature_session_id
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual", headers=headers,
    )
    assert completed.status_code == 200, completed.text

    ticket = client.post(
        "/api/mobile/v1/technician/tickets",
        json={
            "work_order_id": order_id, "reason": "Corrección estructural",
            "description": "Agregar un equipo adicional que llegó tarde.",
            "requested_signature_policy": "invalidate",
        },
        headers=headers,
    )
    assert ticket.status_code == 201, ticket.text
    approved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket.json()['id']}/approve",
        json={"signature_policy": "invalidate"},
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    reopened = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers,
    ).json()
    assert reopened["status"] == "draft"
    assert reopened["signature_session_id"] is None

    configure_and_resign = sign(client, headers, order_id, technician_name="Técnico LAB nuevo")
    assert configure_and_resign.status_code == 200, configure_and_resign.text
    new_session_id = configure_and_resign.json()["signature_session_id"]
    assert new_session_id != original_session_id

    with factory() as db:
        # La FieldSheet ya capturada conserva su sesión histórica original --
        # nunca se reescribe hacia la nueva sesión de recepción.
        assert db.get(FieldSheet, sheet_id).lab_signature_session_id == original_session_id


# --------------------------------------------------------------------------
# Permisos: Staff vs Capture vs externos (32-36)
# --------------------------------------------------------------------------

def test_capture_role_can_create_field_sheet_after_received_signed(phase3_context):
    """32. Capture puede capturar FieldSheets después de received_signed."""
    client, _factory, tokens, _tenants = phase3_context
    tech_headers = auth(tokens["tech"])
    capture_headers = auth(tokens["capture"])
    order_id, equipment_id = create_and_sign_ready_order(client, tech_headers)
    response = create_field_sheet(client, capture_headers, order_id, equipment_id)
    assert response.status_code == 201, response.text


def test_capture_role_cannot_sign_reception(phase3_context):
    """33. Capture no puede firmar recepción."""
    client, _factory, tokens, _tenants = phase3_context
    tech_headers = auth(tokens["tech"])
    capture_headers = auth(tokens["capture"])
    order_id = create_order(client, tech_headers)
    equipment_id = add_equipment(client, tech_headers, order_id, 1)
    set_service(client, tech_headers, order_id, equipment_id, "traceable")
    response = sign(client, capture_headers, order_id)
    assert response.status_code == 403


def test_capture_role_cannot_edit_reception_or_equipment(phase3_context):
    """34. Capture no puede editar recepción (equipo, servicio, cliente
    receptor, cliente documental) ni siquiera mientras la OT sigue draft."""
    client, _factory, tokens, _tenants = phase3_context
    tech_headers = auth(tokens["tech"])
    capture_headers = auth(tokens["capture"])
    order_id = create_order(client, tech_headers)
    equipment_id = add_equipment(client, tech_headers, order_id, 1)
    assert client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(2), headers=capture_headers,
    ).status_code == 403
    assert client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "traceable", "linked_company_id": None}, headers=capture_headers,
    ).status_code == 403
    assert client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", json={"notes": "intento"},
        headers=capture_headers,
    ).status_code == 403
    assert client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/certificate-client",
        json={"certificate_client_mode": "order"}, headers=capture_headers,
    ).status_code == 403


def test_external_actor_cannot_use_internal_only_actions(phase3_context):
    """35. Un actor externo no gana facultades internas -- p.ej. materializar
    una OT adicional sigue siendo exclusivo de staff MYC aunque el actor
    tenga acceso legítimo a la OT (su propio tenant)."""
    client, factory, tokens, tenants = phase3_context
    headers = auth(tokens["admin"])
    order_id = create_order(client, headers)
    with factory() as db:
        work_order = db.get(LabWorkOrder, order_id)
        work_order.operator_client_id = tenants["client_a"].id
        db.commit()
    ext_headers = external_headers(client, "external_a@client.example.com")
    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/additional", headers=ext_headers,
    )
    assert response.status_code == 403


def test_cross_tenant_scope_still_blocks_external_access(phase3_context):
    """36. Tenant isolation sigue funcionando -- un actor externo de otro
    tenant no puede ni siquiera ver la OT, mucho menos firmar su recepción."""
    client, factory, tokens, tenants = phase3_context
    headers = auth(tokens["admin"])
    order_id = create_order(client, headers)
    with factory() as db:
        work_order = db.get(LabWorkOrder, order_id)
        work_order.operator_client_id = tenants["client_a"].id
        db.commit()
    other_tenant_headers = external_headers(client, "external_b@client.example.com")
    assert client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=other_tenant_headers,
    ).status_code == 404
    assert sign(client, other_tenant_headers, order_id).status_code == 404


# --------------------------------------------------------------------------
# Concurrencia, legacy y regresión Fase 2 (37-45)
# --------------------------------------------------------------------------

def test_stale_edit_version_is_rejected_before_reception(phase3_context):
    """37. expected_edit_version obsoleto sigue siendo rechazado (optimistic
    concurrency preservado) -- ejercitado aquí sobre una OT reabierta, donde
    el versionado de edición vuelve a aplicar."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    client.post(f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual", headers=headers)
    ticket = client.post(
        "/api/mobile/v1/technician/tickets",
        json={
            "work_order_id": order_id, "reason": "Corrección", "description": "Ajuste menor",
            "requested_signature_policy": "preserve",
        },
        headers=headers,
    )
    approved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket.json()['id']}/approve",
        json={"signature_policy": "preserve"}, headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    stale = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}",
        json={"notes": "usando versión vieja", "expected_edit_version": 1},
        headers=headers,
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "REVISION_CONFLICT"


def test_resigning_an_already_signed_ot_is_rejected_not_duplicated(phase3_context):
    """38. Un segundo intento de firma sobre una OT ya recibida es rechazado
    -- no duplica sesión ni firmas."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, _equipment_id = create_and_sign_ready_order(client, headers)
    with factory() as db:
        sessions_before = len(list(db.scalars(select(LabWorkOrderSignatureSession))))
    second_attempt = sign(client, headers, order_id, technician_name="Otro técnico")
    assert second_attempt.status_code == 409
    with factory() as db:
        sessions_after = len(list(db.scalars(select(LabWorkOrderSignatureSession))))
        assert db.get(LabWorkOrder, order_id).status == "received_signed"
    assert sessions_after == sessions_before


def test_legacy_ready_for_signatures_row_can_still_complete(phase3_context):
    """39. Un registro histórico con ready_for_signatures (firmado bajo el
    flujo anterior a Fase 3) conserva un comportamiento de cierre
    compatible: puede completarse exactamente igual que antes, sin
    necesidad de pasar por received_signed/ready_to_close."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    with factory() as db:
        # Simula una fila legacy: la firma ya existía bajo el estado previo a
        # esta fase, antes de que el servicio empezara a usar received_signed.
        work_order = db.get(LabWorkOrder, order_id)
        work_order.status = "ready_for_signatures"
        db.commit()
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual", headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"


def test_phase2_endpoints_still_work_before_reception(phase3_context):
    """40. Los endpoints Fase 2 (alta/edición configurada de equipo) siguen
    funcionando normalmente mientras la OT sigue en draft (antes de la
    recepción)."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id = create_order(client, headers)
    configured = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/configured",
        json={
            "equipment": equipment_payload(1),
            "service": {"service_type": "traceable", "linked_company_id": None},
        },
        headers=headers,
    )
    assert configured.status_code == 201, configured.text
    equipment_id = configured.json()["equipment"][-1]["id"]
    edited = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/configured",
        json={
            "equipment": {**equipment_payload(1, serial_number="SER-1-EDITADO"),
                          "expected_edit_version": configured.json()["edit_version"]},
            "service": {"service_type": "traceable", "linked_company_id": None},
        },
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["equipment"][0]["serial_number"] == "SER-1-EDITADO"


def test_phase2_configured_endpoints_blocked_after_reception(phase3_context):
    """41. Los endpoints Fase 2 (alta/edición configurada de equipo) quedan
    bloqueados después de la recepción firmada."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    blocked_create = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/configured",
        json={
            "equipment": equipment_payload(2),
            "service": {"service_type": "traceable", "linked_company_id": None},
        },
        headers=headers,
    )
    assert blocked_create.status_code == 409
    blocked_edit = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/configured",
        json={
            "equipment": equipment_payload(1, serial_number="SER-1-TARDE"),
            "service": {"service_type": "traceable", "linked_company_id": None},
        },
        headers=headers,
    )
    assert blocked_edit.status_code == 409


def test_myca_myct_allocator_unchanged(phase3_context):
    """42. El allocator MYCA/MYCT no cambia -- mismo rango, mismo formato,
    misma secuencia perpetua no reutilizable."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id = create_order(client, headers)
    equipment_id = add_equipment(client, headers, order_id, 1)
    service = set_service(client, headers, order_id, equipment_id, "accredited")
    month_year = date.today().strftime("%m-%y")
    assert service["equipment"][0]["certificate_folio"] == f"MYCA-{month_year}-4700"
    with factory() as db:
        sequence = db.scalar(
            select(InstitutionalFolioSequence).where(
                InstitutionalFolioSequence.document_type == "lab_certificate",
                InstitutionalFolioSequence.prefix == "MYCA",
            )
        )
        assert sequence.next_value == 4701


def test_linked_folio_ticket_flow_unchanged(phase3_context):
    """43. El flujo de tickets linked_folio no cambia -- se resuelve igual
    que antes de Fase 3, y el folio autorizado se refleja en el equipo."""
    client, factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    with factory() as db:
        linked = LinkedCompany(name="Vinculada Ticket", abbreviation="VT", default_certificate_prefix="VT")
        db.add(linked)
        db.commit()
        linked_id = linked.id
    order_id = create_order(client, headers)
    equipment_id = add_equipment(client, headers, order_id, 1)
    # Cierre UX 2026-09 (item D): PUT .../service ya materializa la solicitud
    # linked_folio automatica -- el POST manual redundante ahora responde 409
    # (ver test_manual_linked_folio_endpoint_does_not_duplicate_automatic_request
    # en test_lab_phase2_integrated_alta.py), asi que se resuelve directamente
    # el ticket automatico ya creado por set_service.
    assigned = set_service(client, headers, order_id, equipment_id, "linked", linked_id)
    ticket_id = assigned["equipment"][-1]["folio_ticket_id"]
    assert ticket_id is not None
    resolved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket_id}/resolve",
        json={"authorized_folio": "VT-001", "comment": "Autorizado"},
        headers=admin_headers,
    )
    assert resolved.status_code == 200, resolved.text
    refreshed = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers,
    ).json()
    assert refreshed["equipment"][0]["certificate_folio"] == "VT-001"
    assert refreshed["equipment"][0]["folio_status"] == "authorized"
    signed = sign(client, headers, order_id)
    assert signed.status_code == 200, signed.text


def test_max_ten_equipment_still_enforced(phase3_context):
    """44. El máximo de 10 equipos por OT sigue vigente."""
    client, _factory, tokens, _tenants = phase3_context
    headers = auth(tokens["tech"])
    order_id = create_order(client, headers)
    for index in range(1, 11):
        add_equipment(client, headers, order_id, index)
    blocked = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(11), headers=headers,
    )
    assert blocked.status_code == 409


def test_anticipated_groups_still_work_end_to_end(phase3_context):
    """45. Los grupos anticipados (creados de antemano, folios reservados en
    bloque) siguen funcionando de punta a punta bajo la nueva máquina de
    estados: equipo -> servicio -> firma de recepción -> captura -> cierre."""
    client, factory, tokens, _tenants = phase3_context
    admin_headers = auth(tokens["admin"])
    headers = auth(tokens["tech"])
    group = client.post(
        "/api/lab-work-order-groups",
        json={**create_payload("Grupo anticipado E2E"), "quantity": 2},
        headers=admin_headers,
    )
    assert group.status_code == 201, group.text
    members = group.json()["related_work_orders"]
    assert [item["folio"] for item in members] == [6400, 6401]
    first_id = members[0]["id"]
    equipment_id = add_equipment(client, headers, first_id, 1)
    set_service(client, headers, first_id, equipment_id, "traceable")
    signed = sign(client, headers, first_id)
    assert signed.status_code == 200, signed.text
    complete_field_sheet_fully(client, headers, first_id, equipment_id)
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{first_id}/complete/individual", headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"
