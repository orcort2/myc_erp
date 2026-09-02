"""Fase 5 del rediseño LAB: cierre operativo, permisos Jr/Sr y paquete
documental.

Cubre exclusivamente lo que Fase 5 introduce/verifica:
- ready_to_close -> completed es autoritativo (backend, no Mobile), validado
  (FieldSheets completas + folios resueltos) e idempotente (retry seguro).
- Una OT completed queda operativamente congelada: ninguna mutación
  ordinaria (equipo, cliente, servicio, folio, FieldSheet, firma, recepción)
  procede -- sólo el flujo de Tickets/reapertura ya existente.
- El paquete documental (lab_packages.py) es documentalmente estable para
  una OT cerrada: dos descargas producen el mismo artefacto.
- Un grupo firmado no admite nueva OT/equipo por vía ordinaria.
- work_orders.close (nuevo en esta fase) es cierre técnico EXCLUSIVAMENTE
  interno de MYC -- corregido tras auditoría externa: ningún actor
  externo/portal (Operativo Jr NI Sr) lo recibe. Hoy sólo staff interno vía
  lab_work_orders.use puede cerrar; la asignación fina a un rol interno
  "Operativo Sr" formal queda pendiente de que el catálogo interno
  (app/core/permissions.py) lo defina -- no se improvisa aquí.
- Captura conserva su frontera ya cerrada (Fase 3): captura técnica sin
  mutación administrativa, y ahora tampoco cierre.

NO reconstruye Fases 1-4 (dominio LAB, equipo integrado, motor FieldSheet,
Mesa Técnica): esas reglas están cubiertas por sus propios archivos de test
y no cambian aquí, salvo el punto exacto en que Fase 5 los reutiliza.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.client_portal_membership import ClientPortalMembership
from app.models.client_portal_membership_role import ClientPortalMembershipRole
from app.models.client_portal_role import ClientPortalRole
from app.models.field_sheet import FieldSheet
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.linked_company import LinkedCompany
from app.models.user import Role, User
from app.schemas.lab_client import LabClientCreate
from app.services.lab_clients import create_lab_client
from app.services.portal.permission_service import ensure_portal_catalog


PASSWORD = "MobilePass123"

PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
).decode()


@pytest.fixture()
def phase5_context():
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
        db.add(client_a)
        db.commit()
        ensure_portal_catalog(db)

        external_users = {}
        for key, role_code in (("jr", "external_operator_jr"), ("sr", "external_operator_sr")):
            user = User(
                username=f"external_{key}@client.example.com",
                email=f"external_{key}@client.example.com",
                full_name=f"External {key}",
                hashed_password=hash_password(PASSWORD),
                account_type="client_portal",
                status="active",
                email_verified_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.flush()
            role = db.scalar(select(ClientPortalRole).where(ClientPortalRole.code == role_code))
            membership = ClientPortalMembership(client_id=client_a.id, user_id=user.id, status="active")
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
        yield client, factory, tokens, {"client_a": client_a}
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


def make_lab_client_id(factory) -> int:
    """La frontera de completitud de FieldSheets/folios que Fase 5 endurece
    (_missing_completed_sheets/_unresolved_folio_equipment) sólo aplica a OT
    del flujo evolucionado (lab_client_id IS NOT NULL) -- las OT históricas
    sin cliente LAB quedan exentas a propósito (ver lab_work_orders.py). Los
    tests que ejercen esa frontera deben crear una OT con lab_client_id real,
    no una históricamente exenta."""
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        lab_client = create_lab_client(
            db, LabClientCreate(company="Cliente LAB Fase 5", address="Calle 1", attention="Ing. Prueba"),
            admin, operator_client_id=None,
        )
        return lab_client.id


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
    lab_client_id: int | None = None,
) -> tuple[int, int]:
    order_id = create_order(client, headers, client_name=name, lab_client_id=lab_client_id)
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


def db_status(factory, order_id: int) -> str:
    with factory() as db:
        return db.get(LabWorkOrder, order_id).status


def close_individual(client, headers, order_id, *, confirm_draft_completion: bool = False):
    query = "?confirm_draft_completion=true" if confirm_draft_completion else ""
    return client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual{query}", headers=headers,
    )


# --------------------------------------------------------------------------
# Readiness de cierre (1-4)
# --------------------------------------------------------------------------


def test_ready_to_close_with_everything_valid_reaches_completed(phase5_context):
    """1. ready_to_close + todo válido -> completed, con PDF final congelado.
    Usa lab_client_id (flujo evolucionado) para que las dos fronteras nuevas
    de esta fase (FieldSheets completas y folios resueltos) estén realmente
    en juego -- no exentas por ser una OT histórica -- y confirmar que un
    folio 'traceable' ya reservado (no sólo 'authorized') no bloquea el
    cierre."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["tech"])
    lab_client_id = make_lab_client_id(factory)
    order_id, equipment_id = create_and_sign_ready_order(client, headers, lab_client_id=lab_client_id)
    with factory() as db:
        assert db.get(LabWorkOrderEquipment, equipment_id).folio_status == "reserved"
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    assert db_status(factory, order_id) == "ready_to_close"
    completed = close_individual(client, headers, order_id)
    assert completed.status_code == 200, completed.text
    body = completed.json()
    assert body["status"] == "completed"
    with factory() as db:
        row = db.get(LabWorkOrder, order_id)
        assert row.final_pdf
        assert row.final_pdf_sha256 and len(row.final_pdf_sha256) == 64
        assert row.completed_at is not None


def test_close_rejected_with_pending_field_sheet(phase5_context):
    """2. Cierre UX 2026-09: una FieldSheet en borrador ya NO bloquea el
    cierre con un error terminal -- pide confirmación (el usuario decide si
    completar y cerrar), sin mutar el estado hasta que confirme."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["tech"])
    lab_client_id = make_lab_client_id(factory)
    order_id, equipment_id = create_and_sign_ready_order(client, headers, lab_client_id=lab_client_id)
    created = create_field_sheet(client, headers, order_id, equipment_id)
    assert created.status_code == 201, created.text
    response = close_individual(client, headers, order_id)
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "LAB_DRAFT_SHEETS_REQUIRE_CONFIRMATION"
    assert detail["items"][0]["equipment_id"] == equipment_id
    assert db_status(factory, order_id) == "in_progress"


def test_close_with_confirm_draft_completion_autocompletes_and_closes_atomically(phase5_context):
    """22. Cerrar con drafts válidos + confirmación: confirm_draft_completion
    completa la hoja borrador y cierra la OT en la MISMA llamada (no dos
    requests independientes) -- el resultado es completed con PDF final."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["tech"])
    lab_client_id = make_lab_client_id(factory)
    order_id, equipment_id = create_and_sign_ready_order(client, headers, lab_client_id=lab_client_id)
    created = create_field_sheet(client, headers, order_id, equipment_id)
    assert created.status_code == 201, created.text
    sheet_id = created.json()["id"]
    rows = [
        {
            "id": row["id"], "section_key": row["section_key"], "row_number": row["row_number"],
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

    response = close_individual(client, headers, order_id, confirm_draft_completion=True)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"
    with factory() as db:
        order = db.get(LabWorkOrder, order_id)
        assert order.status == "completed"
        assert order.final_pdf
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.status == "completed"
        assert sheet.final_pdf_path is not None


def test_close_with_confirm_draft_completion_rejects_invalid_draft_without_partial_close(phase5_context):
    """22. Cerrar con draft inválido -> no cierre parcial: si la hoja
    borrador no pasa validación (faltan datos técnicos requeridos), ni la
    hoja se completa ni la OT cierra -- se devuelven los blockers exactos."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["tech"])
    lab_client_id = make_lab_client_id(factory)
    order_id, equipment_id = create_and_sign_ready_order(client, headers, lab_client_id=lab_client_id)
    created = create_field_sheet(client, headers, order_id, equipment_id)
    assert created.status_code == 201, created.text
    sheet_id = created.json()["id"]

    response = close_individual(client, headers, order_id, confirm_draft_completion=True)
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "LAB_DRAFT_SHEETS_INVALID"
    assert detail["items"][0]["equipment_id"] == equipment_id
    assert "missing_fields" in detail["items"][0]
    with factory() as db:
        order = db.get(LabWorkOrder, order_id)
        assert order.status == "in_progress"
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.status == "draft"
        assert sheet.final_pdf_path is None


def test_close_rejected_with_missing_field_sheet(phase5_context):
    """3. Un equipo activo sin ninguna FieldSheet bloquea el cierre igual
    que una incompleta -- 'requerida y ausente' también cuenta."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["tech"])
    lab_client_id = make_lab_client_id(factory)
    order_id = create_order(client, headers, lab_client_id=lab_client_id)
    equipment_id = add_equipment(client, headers, order_id, 1)
    set_service(client, headers, order_id, equipment_id, "traceable")
    signed = sign(client, headers, order_id)
    assert signed.status_code == 200, signed.text
    response = close_individual(client, headers, order_id)
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "LAB_FIELD_SHEETS_INCOMPLETE"
    assert detail["items"][0]["field_sheet_status"] == "missing"
    assert db_status(factory, order_id) == "received_signed"


def test_close_rejected_with_unresolved_linked_folio(phase5_context):
    """4. Fase 5: un equipo Vinculado con FieldSheet completed pero folio
    todavía no autorizado bloquea el cierre staff -- la captura externa
    (Fase 3) puede avanzar con folio pendiente, pero el cierre autoritativo
    exige el folio ya resuelto."""
    client, factory, tokens, tenants = phase5_context
    headers = auth(tokens["tech"])
    lab_client_id = make_lab_client_id(factory)
    with factory() as db:
        linked = LinkedCompany(name="Vinculada", abbreviation="VIN", default_certificate_prefix="VIN")
        db.add(linked)
        db.commit()
        linked_id = linked.id
    order_id = create_order(client, headers, lab_client_id=lab_client_id)
    equipment_id = add_equipment(client, headers, order_id, 1)
    set_service(client, headers, order_id, equipment_id, "linked", linked_id)
    signed = sign(client, headers, order_id)
    assert signed.status_code == 200, signed.text
    with factory() as db:
        db.get(LabWorkOrder, order_id).operator_client_id = tenants["client_a"].id
        db.commit()
    ext_sr_headers = external_headers(client, "external_sr@client.example.com")
    # La captura externa SÍ puede completar la hoja con folio Vinculado
    # pendiente (Fase 3, deliberado) -- eso no es lo que se está probando.
    completed_sheet = complete_field_sheet_fully(client, ext_sr_headers, order_id, equipment_id)
    assert completed_sheet
    with factory() as db:
        assert db.get(LabWorkOrderEquipment, equipment_id).folio_status == "pending"
    response = close_individual(client, headers, order_id)
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "LAB_FOLIOS_UNRESOLVED"
    assert detail["items"][0]["equipment_id"] == equipment_id
    assert detail["items"][0]["folio_status"] == "pending"
    assert db_status(factory, order_id) == "ready_to_close"


# --------------------------------------------------------------------------
# Idempotencia e inmutabilidad post-cierre (5-9)
# --------------------------------------------------------------------------


def test_completed_close_retry_is_idempotent(phase5_context):
    """5. Un retry de cierre sobre una OT ya completed es un no-op seguro:
    mismo PDF/SHA, sin duplicar auditoría, sin volver a resolver tickets."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    first = close_individual(client, headers, order_id)
    assert first.status_code == 200, first.text
    with factory() as db:
        row = db.get(LabWorkOrder, order_id)
        sha_before = row.final_pdf_sha256
        completed_at_before = row.completed_at
        audit_count_before = len(list(db.scalars(
            select(AuditLog).where(AuditLog.action == "lab_work_order.individual_completed")
        )))
    second = close_individual(client, headers, order_id)
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "completed"
    with factory() as db:
        row = db.get(LabWorkOrder, order_id)
        assert row.final_pdf_sha256 == sha_before
        assert row.completed_at == completed_at_before
        audit_count_after = len(list(db.scalars(
            select(AuditLog).where(AuditLog.action == "lab_work_order.individual_completed")
        )))
    assert audit_count_after == audit_count_before


def test_completed_order_rejects_ordinary_mutations(phase5_context):
    """6. Una OT completed rechaza toda mutación ordinaria -- backend, no
    sólo Mobile. Cubre equipo, cliente receptor, cliente documental,
    servicio y re-firma."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    completed = close_individual(client, headers, order_id)
    assert completed.status_code == 200, completed.text

    assert client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(2), headers=headers,
    ).status_code == 409
    assert client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}",
        headers=headers,
    ).status_code == 409
    assert client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}",
        json={"client_name": "Otro receptor"}, headers=headers,
    ).status_code == 409
    assert client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/certificate-client",
        json={"certificate_client_mode": "different", "final_client_company_snapshot": "Tardío"},
        headers=headers,
    ).status_code == 409
    assert client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "accredited", "linked_company_id": None}, headers=headers,
    ).status_code == 409
    assert sign(client, headers, order_id).status_code == 409


def test_completed_order_rejects_new_field_sheet_creation(phase5_context):
    """7. Una OT completed rechaza crear una FieldSheet adicional -- ni
    siquiera para un equipo ya existente que la traía completed."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    completed = close_individual(client, headers, order_id)
    assert completed.status_code == 200, completed.text
    response = create_field_sheet(client, headers, order_id, equipment_id)
    assert response.status_code == 409, response.text


def test_completed_field_sheet_still_rejects_edits(phase5_context):
    """8. Complemento de 7: la FieldSheet completed de una OT ya cerrada
    tampoco admite PATCH -- misma frontera de Fase 4, reverificada aquí."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    completed = close_individual(client, headers, order_id)
    assert completed.status_code == 200, completed.text
    response = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"observations": "Intento post-cierre"},
        headers=headers,
    )
    assert response.status_code == 409, response.text


def test_signed_group_blocks_new_ot_and_equipment_via_ordinary_path(phase5_context):
    """9. Un grupo firmado no admite nueva OT adicional ni nuevo equipo por
    vía ordinaria -- sólo Tickets/reapertura podría reabrirlo."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    additional = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/additional", headers=headers,
    )
    assert additional.status_code == 409, additional.text
    add_more = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(2), headers=headers,
    )
    assert add_more.status_code == 409, add_more.text


# --------------------------------------------------------------------------
# Paquete documental (10)
# --------------------------------------------------------------------------


def test_closed_package_is_byte_stable_across_downloads(phase5_context):
    """10. Una OT cerrada produce documentación estable: dos descargas del
    paquete son byte-idénticas, sin regenerarse con información mutable."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    completed = close_individual(client, headers, order_id)
    assert completed.status_code == 200, completed.text

    first = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/package", headers=headers,
    )
    assert first.status_code == 200, first.text
    second = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/package", headers=headers,
    )
    assert second.status_code == 200, second.text
    assert first.content == second.content
    assert len(first.content) > 0


# --------------------------------------------------------------------------
# Permisos Jr/Sr/Capture/Admin/External (11-15)
# --------------------------------------------------------------------------


def test_external_operator_jr_cannot_close(phase5_context):
    """11. Operativo Jr conserva operación ordinaria (llega hasta
    ready_to_close) pero no autoridad de cierre técnico."""
    client, factory, tokens, tenants = phase5_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    with factory() as db:
        db.get(LabWorkOrder, order_id).operator_client_id = tenants["client_a"].id
        db.commit()
    jr_headers = external_headers(client, "external_jr@client.example.com")
    # Jr sí puede seguir operando (capturar FieldSheets) sobre su propia OT.
    created = create_field_sheet(client, jr_headers, order_id, equipment_id)
    assert created.status_code == 201, created.text
    response = close_individual(client, jr_headers, order_id)
    assert response.status_code == 403, response.text
    assert db_status(factory, order_id) == "in_progress"


def test_external_operator_sr_cannot_close(phase5_context):
    """12. Corregido post-auditoría externa: work_orders.close es cierre
    técnico interno de MYC, nunca una facultad de actor externo/portal.
    Operativo Sr externo conserva operación ordinaria sobre su propia OT
    pero NUNCA autoridad de cierre -- ni Jr ni Sr externos la tienen."""
    client, factory, tokens, tenants = phase5_context
    headers = auth(tokens["tech"])
    order_id, _equipment_id = create_and_sign_ready_order(client, headers)
    with factory() as db:
        db.get(LabWorkOrder, order_id).operator_client_id = tenants["client_a"].id
        db.commit()
    sr_headers = external_headers(client, "external_sr@client.example.com")
    response = close_individual(client, sr_headers, order_id)
    assert response.status_code == 403, response.text
    assert db_status(factory, order_id) == "received_signed"


def test_capture_role_cannot_close(phase5_context):
    """13. Captura mantiene su frontera ya cerrada (sólo captura técnica de
    FieldSheets, ninguna autoridad administrativa) -- ahora tampoco cierre."""
    client, factory, tokens, _tenants = phase5_context
    tech_headers = auth(tokens["tech"])
    capture_headers = auth(tokens["capture"])
    order_id, equipment_id = create_and_sign_ready_order(client, tech_headers)
    complete_field_sheet_fully(client, tech_headers, order_id, equipment_id)
    response = close_individual(client, capture_headers, order_id)
    assert response.status_code == 403, response.text
    assert db_status(factory, order_id) == "ready_to_close"


def test_staff_tecnico_retains_close_authority(phase5_context):
    """14. Staff interno (Tecnico, vía lab_work_orders.use) conserva su
    autoridad de cierre existente -- Fase 5 no la restringe."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    response = close_individual(client, headers, order_id)
    assert response.status_code == 200, response.text


def test_external_operator_sr_does_not_gain_internal_admin_capabilities(phase5_context):
    """15. Sr no se convierte en admin global: sigue sin poder materializar
    una OT adicional (exclusivo de staff interno, Fase 3)."""
    client, factory, tokens, tenants = phase5_context
    headers = auth(tokens["tech"])
    order_id, _equipment_id = create_and_sign_ready_order(client, headers)
    with factory() as db:
        db.get(LabWorkOrder, order_id).operator_client_id = tenants["client_a"].id
        db.commit()
    sr_headers = external_headers(client, "external_sr@client.example.com")
    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/additional", headers=sr_headers,
    )
    assert response.status_code == 403, response.text


# --------------------------------------------------------------------------
# Cierre UX 2026-09: cancelar/restaurar incluso desde completed, y
# reapertura administrativa directa sin ticket artificial (16-22)
# --------------------------------------------------------------------------


def test_admin_cancels_an_open_work_order(phase5_context):
    """16. Admin cancela una OT abierta (in_progress)."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["admin"])
    order_id, _equipment_id = create_and_sign_ready_order(client, headers)
    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/cancel",
        json={"reason": "Ya no se requiere el servicio"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["previous_status"] == "received_signed"


def test_admin_cancels_a_completed_work_order_preserving_everything(phase5_context):
    """16. Admin cancela una OT completed/cerrada -- ya no exige reapertura
    previa. Firmas, PDF final y FieldSheet completed quedan intactos."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["admin"])
    lab_client_id = make_lab_client_id(factory)
    order_id, equipment_id = create_and_sign_ready_order(client, headers, lab_client_id=lab_client_id)
    sheet_id = complete_field_sheet_fully(client, headers, order_id, equipment_id)
    closed = close_individual(client, headers, order_id)
    assert closed.status_code == 200, closed.text
    with factory() as db:
        order = db.get(LabWorkOrder, order_id)
        original_pdf_sha = order.final_pdf_sha256
        original_signature_session_id = order.signature_session_id
    with factory() as db:
        original_sheet_pdf_sha = db.get(FieldSheet, sheet_id).final_pdf_sha256

    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/cancel",
        json={"reason": "Corrección administrativa post-cierre"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["previous_status"] == "completed"
    with factory() as db:
        order = db.get(LabWorkOrder, order_id)
        assert order.final_pdf_sha256 == original_pdf_sha
        assert order.signature_session_id == original_signature_session_id
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.status == "completed"
        assert sheet.final_pdf_sha256 == original_sheet_pdf_sha
    audit = _latest_audit(factory, "lab_work_order.cancelled", order_id)
    assert audit.new_values["previous_status"] == "completed"


def test_restore_returns_a_cancelled_work_order_to_its_exact_previous_status(phase5_context):
    """17. restore vuelve exactamente al estado anterior -- completed ->
    cancelled -> restore -> completed, NUNCA a draft/in_progress como si
    fuera una reapertura técnica."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["admin"])
    lab_client_id = make_lab_client_id(factory)
    order_id, equipment_id = create_and_sign_ready_order(client, headers, lab_client_id=lab_client_id)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    closed = close_individual(client, headers, order_id)
    assert closed.status_code == 200, closed.text
    cancelled = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/cancel",
        json={"reason": "Prueba de restauración"},
        headers=headers,
    )
    assert cancelled.status_code == 200, cancelled.text

    restored = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/restore", headers=headers,
    )
    assert restored.status_code == 200, restored.text
    body = restored.json()
    assert body["status"] == "completed"
    assert body["previous_status"] is None
    assert body["cancelled_at"] is None
    assert body["cancellation_reason"] is None


def test_restore_rejects_a_work_order_that_is_not_cancelled(phase5_context):
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["admin"])
    order_id, _equipment_id = create_and_sign_ready_order(client, headers)
    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/restore", headers=headers,
    )
    assert response.status_code == 409, response.text


def test_user_without_permission_cannot_cancel_or_restore(phase5_context):
    """18. Usuario sin lab_work_orders.cancel no cancela ni restaura --
    backend sigue siendo la autoridad, no sólo la UI."""
    client, factory, tokens, _tenants = phase5_context
    admin_headers = auth(tokens["admin"])
    tech_headers = auth(tokens["tech"])
    order_id, _equipment_id = create_and_sign_ready_order(client, admin_headers)
    denied_cancel = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/cancel",
        json={"reason": "Intento sin permiso"},
        headers=tech_headers,
    )
    assert denied_cancel.status_code == 403, denied_cancel.text

    cancelled = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/cancel",
        json={"reason": "Cancelación válida por admin"},
        headers=admin_headers,
    )
    assert cancelled.status_code == 200, cancelled.text
    denied_restore = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/restore", headers=tech_headers,
    )
    assert denied_restore.status_code == 403, denied_restore.text


def test_admin_reopens_a_closed_work_order_directly_without_a_ticket(phase5_context):
    """19. Admin con work_orders.reopen ejecuta la reapertura directamente
    -- una sola llamada, sin crear ni pasar por un ticket."""
    client, factory, tokens, _tenants = phase5_context
    headers = auth(tokens["admin"])
    lab_client_id = make_lab_client_id(factory)
    order_id, equipment_id = create_and_sign_ready_order(client, headers, lab_client_id=lab_client_id)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    closed = close_individual(client, headers, order_id)
    assert closed.status_code == 200, closed.text

    from app.models.operational_ticket import OperationalTicket
    with factory() as db:
        tickets_before = db.scalar(select(func.count()).select_from(OperationalTicket))

    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/reopen",
        json={"requested_signature_policy": "preserve", "reason": "Corrección de datos técnicos"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "draft"
    with factory() as db:
        order = db.get(LabWorkOrder, order_id)
        assert order.reopen_ticket_id is None
        assert order.reopened_by_user_id is not None
        assert len(order.revisions) == 1
        assert order.revisions[0].reopen_ticket_id is None
        tickets_after = db.scalar(select(func.count()).select_from(OperationalTicket))
    assert tickets_after == tickets_before
    audit = _latest_audit(factory, "lab_work_order.reopened_directly", order_id)
    assert audit.user_id is not None


def test_user_without_reopen_permission_cannot_reopen_directly(phase5_context):
    """20. Sin work_orders.reopen, el endpoint directo rechaza -- el único
    camino que le queda es solicitar (ticket), no ejecutar."""
    client, factory, tokens, _tenants = phase5_context
    admin_headers = auth(tokens["admin"])
    tech_headers = auth(tokens["tech"])
    lab_client_id = make_lab_client_id(factory)
    order_id, equipment_id = create_and_sign_ready_order(client, admin_headers, lab_client_id=lab_client_id)
    complete_field_sheet_fully(client, admin_headers, order_id, equipment_id)
    closed = close_individual(client, admin_headers, order_id)
    assert closed.status_code == 200, closed.text

    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/reopen",
        json={"requested_signature_policy": "preserve", "reason": "Intento sin permiso"},
        headers=tech_headers,
    )
    assert response.status_code == 403, response.text


def _latest_audit(factory, action: str, entity_id: int):
    with factory() as db:
        return db.scalar(
            select(AuditLog)
            .where(AuditLog.action == action, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.id.desc())
        )


