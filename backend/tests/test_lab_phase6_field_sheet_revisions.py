"""Fase 6 del rediseño LAB: modelo de revisión/versionado de FieldSheet.

Cubre exclusivamente lo que Fase 6 introduce:
- uq_field_sheets_current_lab_equipment (índice único parcial) reemplaza la
  UniqueConstraint plana sobre lab_equipment_id -- ya permite una segunda
  FieldSheet tras reapertura, sin mutar "completed -> draft" sobre la misma
  hoja.
- Una reapertura "invalidate" que además edita un campo crítico del equipo
  (CRITICAL_EQUIPMENT_FIELDS) retira la revisión vigente ya completed
  (is_current=False) sin tocar su status/final_pdf_path/final_pdf_sha256 --
  el documento histórico queda intacto para siempre. create_lab_field_sheet
  abre la revisión siguiente con normalidad (revision_number+1,
  supersedes_field_sheet_id) en cuanto la OT vuelve a estar
  received_signed/in_progress.
- Una reapertura "preserve" nunca retira ni versiona nada: el trabajo
  técnico se conserva tal cual, sin nueva FieldSheet.
- equipment.field_sheet sigue resolviendo exactamente a la revisión vigente
  (is_current=True) -- ningún caller preexistente cambia.

NO reconstruye Fases 1-5 (dominio LAB, equipo integrado, motor FieldSheet,
Mesa Técnica, cierre operativo): esas reglas están cubiertas por sus propios
archivos de test y no cambian aquí, salvo el punto exacto en que Fase 6 los
reutiliza.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.field_sheet import FieldSheet
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
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

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        tech_role = Role(name="Tecnico", description="Técnico")
        admin_role = Role(name="Administrador", description="Administrador")
        no_access_role = Role(name="Sin acceso", description="Sin permisos")
        db.add_all([tech_role, admin_role, no_access_role])
        db.flush()
        users = {}
        for key, role in (("tech", tech_role), ("admin", admin_role), ("none", no_access_role)):
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
            users[key] = user
        db.add_all(users.values())
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
        "is_good_condition": True,
        **extra,
    }


def signatures_payload(*, technician_name: str = "Técnico LAB") -> dict:
    signed_at = datetime.now(timezone.utc).isoformat()
    return {
        "technician": {
            "signer_name": technician_name, "signed_at": signed_at, "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
        "client": {
            "signer_name": "Cliente LAB", "signed_at": signed_at, "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
    }


def create_and_sign_ready_order(client, headers) -> tuple[int, int]:
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=create_payload(), headers=headers
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(1),
        headers=headers,
    )
    assert added.status_code == 201, added.text
    equipment_id = added.json()["equipment"][-1]["id"]
    service = client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "accredited", "linked_company_id": None},
        headers=headers,
    )
    assert service.status_code == 200, service.text
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    return order_id, equipment_id


def complete_field_sheet_fully(client, headers, order_id, equipment_id, *, template_key="general") -> int:
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": template_key},
        headers=headers,
    )
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


def close_order(client, headers, order_id) -> None:
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual", headers=headers,
    )
    assert completed.status_code == 200, completed.text


def reopen_order(client, headers, admin_headers, order_id, *, policy: str) -> None:
    ticket = client.post(
        "/api/mobile/v1/technician/tickets",
        json={
            "work_order_id": order_id,
            "reason": "Corrección" if policy == "preserve" else "Corrección estructural",
            "description": "Ajuste de datos de recepción/equipo." if policy == "preserve"
                else "El equipo requiere corrección de identidad técnica.",
            "requested_signature_policy": policy,
        },
        headers=headers,
    )
    assert ticket.status_code == 201, ticket.text
    approved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket.json()['id']}/approve",
        json={"signature_policy": policy},
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text


def test_reopen_invalidate_with_critical_change_retires_old_revision_and_opens_a_new_one(lab_context):
    """1. reopen invalidate + edición de campo crítico -> la revisión vieja
    (completed) se retira (is_current=False) sin tocar su PDF/SHA; la nueva
    FieldSheet nace como revision_number=2, supersedes_field_sheet_id
    apuntando a la vieja, is_current=True."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    first_sheet_id = complete_field_sheet_fully(client, headers, order_id, equipment_id)
    with factory() as db:
        first = db.get(FieldSheet, first_sheet_id)
        assert first.revision_number == 1
        assert first.is_current is True
        assert first.status == "completed"
        frozen_path = first.final_pdf_path
        frozen_sha = first.final_pdf_sha256
        assert frozen_path and frozen_sha

    close_order(client, headers, order_id)
    reopen_order(client, headers, admin_headers, order_id, policy="invalidate")
    reopened = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers).json()
    assert reopened["status"] == "draft"

    edited = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}",
        json=equipment_payload(1, serial_number="SER-1-CORREGIDO", expected_edit_version=reopened["edit_version"]),
        headers=headers,
    )
    assert edited.status_code == 200, edited.text

    with factory() as db:
        first = db.get(FieldSheet, first_sheet_id)
        assert first.is_current is False
        assert first.status == "completed"
        assert first.final_pdf_path == frozen_path
        assert first.final_pdf_sha256 == frozen_sha
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.field_sheet is None

    resigned = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json=signatures_payload(technician_name="Técnico LAB nuevo"),
        headers=headers,
    )
    assert resigned.status_code == 200, resigned.text
    assert resigned.json()["status"] == "received_signed"

    second_sheet_id = complete_field_sheet_fully(client, headers, order_id, equipment_id)
    assert second_sheet_id != first_sheet_id
    with factory() as db:
        second = db.get(FieldSheet, second_sheet_id)
        assert second.revision_number == 2
        assert second.is_current is True
        assert second.supersedes_field_sheet_id == first_sheet_id
        assert second.status == "completed"
        # La revisión vieja sigue exactamente igual -- nunca se reescribió.
        first = db.get(FieldSheet, first_sheet_id)
        assert first.is_current is False
        assert first.final_pdf_path == frozen_path
        assert first.final_pdf_sha256 == frozen_sha
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.field_sheet.id == second_sheet_id


def test_reopen_preserve_never_retires_or_versions_the_field_sheet(lab_context):
    """2. reopen preserve -- aunque se edite un campo crítico -- nunca
    retira ni versiona la FieldSheet: el trabajo técnico se conserva tal
    cual (sin nueva FieldSheet), coherente con 'preserva trabajo técnico'."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    sheet_id = complete_field_sheet_fully(client, headers, order_id, equipment_id)

    close_order(client, headers, order_id)
    reopen_order(client, headers, admin_headers, order_id, policy="preserve")
    reopened = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers).json()
    assert reopened["status"] == "draft"
    assert reopened["signature_preserved"] is True

    edited = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}",
        json=equipment_payload(1, serial_number="SER-1-CORREGIDO", expected_edit_version=reopened["edit_version"]),
        headers=headers,
    )
    assert edited.status_code == 200, edited.text

    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.is_current is True
        assert sheet.revision_number == 1
        assert sheet.supersedes_field_sheet_id is None
        assert sheet.status == "completed"
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.field_sheet.id == sheet_id

    # Preserve nunca exige re-firma: reclosable directo.
    reclosed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual", headers=headers,
    )
    assert reclosed.status_code == 200, reclosed.text


def test_field_sheet_new_revision_freezes_a_fresh_snapshot_not_the_old_one(lab_context):
    """3. La revisión nueva congela snapshot/renderer propios (no reutiliza
    los de la revisión vieja) -- misma disciplina de congelado ya cerrada en
    Fase 4/078f5fe, ahora también entre revisiones."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    first_sheet_id = complete_field_sheet_fully(client, headers, order_id, equipment_id)

    close_order(client, headers, order_id)
    reopen_order(client, headers, admin_headers, order_id, policy="invalidate")
    reopened = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers).json()
    edited = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}",
        json=equipment_payload(1, brand="Marca Corregida", expected_edit_version=reopened["edit_version"]),
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    resigned = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json=signatures_payload(technician_name="Técnico LAB nuevo"),
        headers=headers,
    )
    assert resigned.status_code == 200, resigned.text
    second_sheet_id = complete_field_sheet_fully(client, headers, order_id, equipment_id)

    with factory() as db:
        first = db.get(FieldSheet, first_sheet_id)
        second = db.get(FieldSheet, second_sheet_id)
        assert second.lab_signature_session_id != first.lab_signature_session_id
        assert second.institutional_snapshot_json is not None
        assert second.template_definition_json is not None
        assert second.pdf_renderer_key == first.pdf_renderer_key
        assert second.pdf_renderer_version == first.pdf_renderer_version
        assert second.capture_values["brand"] == "Marca Corregida"
        assert first.capture_values["brand"] == "MYC Test"


def test_only_one_current_field_sheet_revision_per_lab_equipment_at_the_db_level(lab_context):
    """4. El índice único parcial (uq_field_sheets_current_lab_equipment)
    realmente lo exige a nivel BD, no sólo por convención de servicio."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    complete_field_sheet_fully(client, headers, order_id, equipment_id)
    with factory() as db:
        rogue = FieldSheet(
            lab_equipment_id=equipment_id,
            template_key="general",
            status="draft",
            is_current=True,
            revision_number=2,
        )
        db.add(rogue)
        with pytest.raises(IntegrityError):
            db.commit()


def test_equipment_field_sheet_property_resolves_only_the_current_revision(lab_context):
    """5. equipment.field_sheet (usado por todo el código LAB preexistente)
    sigue resolviendo exactamente la revisión vigente entre varias."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    first_sheet_id = complete_field_sheet_fully(client, headers, order_id, equipment_id)
    close_order(client, headers, order_id)
    reopen_order(client, headers, admin_headers, order_id, policy="invalidate")
    reopened = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers).json()
    edited = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}",
        json=equipment_payload(1, instrument="Instrumento Corregido", expected_edit_version=reopened["edit_version"]),
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert len(equipment.field_sheets) == 1
        assert equipment.field_sheet is None
    resigned = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json=signatures_payload(technician_name="Técnico LAB nuevo"),
        headers=headers,
    )
    assert resigned.status_code == 200, resigned.text
    second_sheet_id = complete_field_sheet_fully(client, headers, order_id, equipment_id)
    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert len(equipment.field_sheets) == 2
        assert {item.id for item in equipment.field_sheets} == {first_sheet_id, second_sheet_id}
        assert equipment.field_sheet.id == second_sheet_id

    tray = client.get(
        "/api/mobile/v1/technician/lab-field-sheets?offset=0&limit=10",
        headers=headers,
    )
    assert tray.status_code == 200, tray.text
    current = next(item for item in tray.json()["items"] if item["equipment_id"] == equipment_id)
    assert current["field_sheet_id"] == second_sheet_id
    assert current["revision_number"] == 2
    assert current["is_current"] is True
    assert current["bucket"] == "completed"


def test_lab_field_sheet_tray_is_aggregated_paginated_and_permission_guarded(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    first_order_id, first_equipment_id = create_and_sign_ready_order(client, headers)
    second_order_id, second_equipment_id = create_and_sign_ready_order(client, headers)

    first_page = client.get(
        "/api/mobile/v1/technician/lab-field-sheets?offset=0&limit=1",
        headers=headers,
    )
    assert first_page.status_code == 200, first_page.text
    payload = first_page.json()
    assert payload["total"] == 2
    assert payload["offset"] == 0
    assert payload["limit"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["bucket"] == "pending"
    assert payload["items"][0]["field_sheet_id"] is None
    assert payload["items"][0]["documentary_client_display"] == "Cliente LAB"

    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{first_order_id}/equipment/{first_equipment_id}/field-sheet",
        json={"template_key": "manometro"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    tray = client.get(
        "/api/mobile/v1/technician/lab-field-sheets?offset=0&limit=10",
        headers=headers,
    )
    assert tray.status_code == 200, tray.text
    entries = {item["equipment_id"]: item for item in tray.json()["items"]}
    assert entries[first_equipment_id]["bucket"] == "in_progress"
    assert entries[first_equipment_id]["template_key"] == "manometro"
    assert entries[first_equipment_id]["template_name"] == "Hoja de Campo Manómetro"
    assert entries[first_equipment_id]["revision_number"] == 1
    assert entries[second_equipment_id]["bucket"] == "pending"

    denied = client.get(
        "/api/mobile/v1/technician/lab-field-sheets",
        headers=auth(tokens["none"]),
    )
    assert denied.status_code == 403


def test_unsupported_prototype_template_is_explicit_and_never_falls_back_to_general(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = create_and_sign_ready_order(client, headers)
    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "valvula_seguridad"},
        headers=headers,
    )
    assert response.status_code == 422
    assert "no soportada" in response.json()["detail"]
    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.field_sheet is None
        assert equipment.field_sheets == []
