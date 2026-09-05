"""Flujo LAB "equipo por equipo": workflow_mode persistente y la operación
final atómica finalize_equipment_by_equipment_work_order.

Cubre exclusivamente lo que este encargo introduce:
- workflow_mode ("group" default/backfill, "equipment_by_equipment" nuevo)
  es autoridad backend persistente en LabWorkOrder, nunca inferida ni
  dependiente de un evento Mobile efímero.
- "group" conserva el flujo histórico intacto -- ninguna excepción nueva
  aplica sin workflow_mode == "equipment_by_equipment" explícito.
- "equipment_by_equipment" permite captura real de FieldSheet en draft
  (antes de firmar recepción), pero prohíbe formalizar (completar) una hoja
  individualmente pre-firma -- eso sólo lo hace la operación final.
- finalize_equipment_by_equipment_work_order es atómica: firma única
  Cliente+Técnico -> completa cada FieldSheet ya capturada -> cierra la OT
  -> registra una entrega FULL con esas mismas firmas, todo en un solo
  commit. Un fallo en cualquier paso no deja firma/hoja/OT/entrega parcial.
- El caso productivo crítico: una OT "group" con equipos ya existentes puede
  cambiar a "equipment_by_equipment" sin recrear ni un solo equipo, y esos
  equipos existentes quedan operativos de inmediato bajo el nuevo flujo.

NO reconstruye Fases 1-6 ni el fix de tombstone de equipo (6fb8e2c): esas
reglas están cubiertas por sus propios archivos de test y no cambian aquí,
salvo el punto exacto en que este flujo las reutiliza.
"""

from __future__ import annotations

import base64
import io
import os
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.field_sheet import FieldSheet
from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment, LabWorkOrderSignatureSession
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.user import Role, User
from app.services.storage_service import resolve_storage_path

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
        capture_role = Role(name="Captura", description="Captura")
        db.add_all([tech_role, admin_role, capture_role])
        db.flush()
        users = {}
        for key, role in (("tech", tech_role), ("admin", admin_role), ("capture", capture_role)):
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


def create_payload(client_name: str = "Cliente LAB", **overrides) -> dict:
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
        **overrides,
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


def signatures_payload() -> dict:
    signed_at = datetime.now(timezone.utc).isoformat()
    return {
        "technician": {
            "signer_name": "Técnico LAB", "signed_at": signed_at, "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
        "client": {
            "signer_name": "Cliente LAB", "signed_at": signed_at, "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
    }


def _create_order(client, headers, *, workflow_mode: str = "equipment_by_equipment", **overrides) -> dict:
    response = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload(workflow_mode=workflow_mode, **overrides),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _add_equipment(client, headers, order_id: int, index: int, *, service_type: str | None = "traceable", **extra) -> dict:
    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(index, **extra),
        headers=headers,
    )
    assert added.status_code == 201, added.text
    order = added.json()
    equipment_id = order["equipment"][-1]["id"]
    if service_type is not None:
        service = client.put(
            f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
            json={"service_type": service_type, "linked_company_id": None},
            headers=headers,
        )
        assert service.status_code == 200, service.text
        order = service.json()
    return order


def _capture_field_sheet_ready(client, headers, order_id: int, equipment_id: int, *, template_key: str = "general") -> dict:
    """Crea y captura de verdad una FieldSheet hasta dejarla lista para
    completarse (_validate_ready_to_complete pasaría), pero SIN completarla
    -- eso es exactamente lo que el flujo equipo-por-equipo permite pre-firma
    (sección 8 del encargo): captura real, no sólo "preparar" una hoja
    vacía."""
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": template_key},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    sheet = created.json()
    rows = [
        {
            "id": row["id"],
            "section_key": row["section_key"],
            "row_number": row["row_number"],
            "row_data": {"result": "1.00"} if index == 0 else row["row_data"],
        }
        for index, row in enumerate(sheet["results_rows"])
    ]
    patched = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"final_condition": "BUENA", "observations": "Captura real de campo", "results_rows": rows},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    return patched.json()


def _prevalidate(client, headers, order_id: int):
    return client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment-by-equipment/prevalidate",
        headers=headers,
    )


def _finalize(client, headers, order_id: int, *, expected_edit_version: int | None = None):
    payload = signatures_payload()
    if expected_edit_version is not None:
        payload["expected_edit_version"] = expected_edit_version
    return client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment-by-equipment/finalize",
        json=payload,
        headers=headers,
    )


def _pdf_text(pdf_bytes: bytes) -> str:
    return "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf_bytes)).pages)


def _create_group(client, headers, *, quantity: int, workflow_mode: str, client_name: str = "Cliente Grupo") -> dict:
    response = client.post(
        "/api/mobile/v1/technician/lab-work-orders/groups",
        json=create_payload(client_name=client_name, workflow_mode=workflow_mode, quantity=quantity),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _get_order(client, headers, order_id: int) -> dict:
    response = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _group_prevalidate(client, headers, order_id: int):
    return client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signature-group/prevalidate",
        headers=headers,
    )


def _group_finalize(client, headers, order_id: int, *, expected_edit_version: int | None = None):
    payload = signatures_payload()
    if expected_edit_version is not None:
        payload["expected_edit_version"] = expected_edit_version
    return client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signature-group/finalize",
        json=payload,
        headers=headers,
    )


def _change_workflow_mode(client, headers, order_id: int, *, new_workflow_mode: str, reason: str = "Motivo de prueba"):
    return client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/workflow-mode",
        json={"new_workflow_mode": new_workflow_mode, "reason": reason},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# 1-3: default/backfill, creación de ambos modos
# ---------------------------------------------------------------------------


def test_legacy_and_default_orders_use_group_workflow_mode(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    response = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload(),  # sin workflow_mode explícito
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["workflow_mode"] == "group"
    with factory() as db:
        row = db.get(LabWorkOrder, response.json()["id"])
        assert row.workflow_mode == "group"


def test_create_work_order_with_equipment_by_equipment_mode(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers, workflow_mode="equipment_by_equipment")
    assert order["workflow_mode"] == "equipment_by_equipment"
    assert order["status"] == "draft"


# ---------------------------------------------------------------------------
# 4-5: group preserva el flujo histórico
# ---------------------------------------------------------------------------


def test_group_mode_still_blocks_pre_signature_field_sheet_capture(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers, workflow_mode="group")
    order = _add_equipment(client, headers, order["id"], 1)
    equipment_id = order["equipment"][0]["id"]
    blocked = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"] == "La OT no admite captura técnica"

    # El resto del flujo group sigue exactamente igual: firmar primero.
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/signatures/individual",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    assert signed.json()["status"] == "received_signed"
    allowed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert allowed.status_code == 201, allowed.text


def test_group_mode_rejects_equipment_by_equipment_endpoints(lab_context):
    """Los endpoints nuevos (prevalidate/finalize) son exclusivos de
    equipment_by_equipment -- un intento sobre una OT group es rechazado
    explícitamente, no ignorado silenciosamente."""
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers, workflow_mode="group")
    prevalidated = _prevalidate(client, headers, order["id"])
    assert prevalidated.status_code == 409, prevalidated.text
    finalized = _finalize(client, headers, order["id"])
    assert finalized.status_code == 409, finalized.text


# ---------------------------------------------------------------------------
# 6-10: captura real pre-firma, sin fingir recepción
# ---------------------------------------------------------------------------


def test_equipment_by_equipment_allows_real_pre_signature_capture_and_repeated_saves(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers)
    order = _add_equipment(client, headers, order["id"], 1)
    equipment_id = order["equipment"][0]["id"]

    sheet = _capture_field_sheet_ready(client, headers, order["id"], equipment_id)
    assert sheet["status"] == "in_progress"
    assert sheet["observations"] == "Captura real de campo"

    # Puede seguir editando/guardando varias veces mientras siga editable.
    resaved = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/equipment/{equipment_id}/field-sheet",
        json={"observations": "Captura corregida en campo"},
        headers=headers,
    )
    assert resaved.status_code == 200, resaved.text
    assert resaved.json()["observations"] == "Captura corregida en campo"

    with factory() as db:
        row = db.get(LabWorkOrder, order["id"])
        assert row.status == "draft", "no debe fingirse received_signed pre-firma"
        sheet_row = db.get(FieldSheet, sheet["id"])
        assert sheet_row.lab_signature_session_id is None
        assert sheet_row.status != "completed"


# ---------------------------------------------------------------------------
# 11-13: completion manual pre-firma prohibido, sin PDF final
# ---------------------------------------------------------------------------


def test_equipment_by_equipment_blocks_manual_completion_pre_signature(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers)
    order = _add_equipment(client, headers, order["id"], 1)
    equipment_id = order["equipment"][0]["id"]
    sheet = _capture_field_sheet_ready(client, headers, order["id"], equipment_id)

    blocked = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert blocked.status_code == 409, blocked.text

    with factory() as db:
        sheet_row = db.get(FieldSheet, sheet["id"])
        assert sheet_row.status != "completed"
        assert sheet_row.final_pdf_path is None
        assert sheet_row.final_pdf_sha256 is None
        row = db.get(LabWorkOrder, order["id"])
        assert row.status == "draft"
        assert row.final_pdf is None


# ---------------------------------------------------------------------------
# 15-18: múltiples equipos, plantillas distintas, reload
# ---------------------------------------------------------------------------


def test_equipment_by_equipment_supports_multiple_equipment_with_different_templates_and_reload(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers)
    order_id = order["id"]
    order = _add_equipment(client, headers, order_id, 1)
    first_equipment_id = order["equipment"][0]["id"]
    order = _add_equipment(client, headers, order_id, 2)
    second_equipment_id = order["equipment"][1]["id"]

    first_sheet = _capture_field_sheet_ready(client, headers, order_id, first_equipment_id, template_key="general")
    second_sheet = _capture_field_sheet_ready(client, headers, order_id, second_equipment_id, template_key="manometro")
    assert first_sheet["template_key"] == "general"
    assert second_sheet["template_key"] == "manometro"

    # "Cerrar/reabrir Mobile" == releer desde cero; el estado se reconstruye
    # exclusivamente desde backend, nunca desde un evento de creación.
    reloaded = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers)
    assert reloaded.status_code == 200, reloaded.text
    detail = reloaded.json()
    assert detail["workflow_mode"] == "equipment_by_equipment"
    by_id = {item["id"]: item for item in detail["equipment"]}
    assert by_id[first_equipment_id]["field_sheet_id"] == first_sheet["id"]
    assert by_id[first_equipment_id]["field_sheet_status"] == "in_progress"
    assert by_id[second_equipment_id]["field_sheet_id"] == second_sheet["id"]
    assert by_id[second_equipment_id]["field_sheet_status"] == "in_progress"


# ---------------------------------------------------------------------------
# 19-23: prevalidación
# ---------------------------------------------------------------------------


def test_prevalidation_blocks_missing_sheet_incomplete_sheet_and_unresolved_folio(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers)
    order_id = order["id"]

    # Equipo 1: sin ninguna hoja seleccionada.
    order = _add_equipment(client, headers, order_id, 1)
    equipment_without_sheet = order["equipment"][0]["id"]

    # Equipo 2: hoja creada pero incompleta (sin resultados).
    order = _add_equipment(client, headers, order_id, 2)
    equipment_with_incomplete_sheet = order["equipment"][1]["id"]
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_with_incomplete_sheet}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    # Equipo 3: folio Vinculado sin resolver (Técnico no tiene lab_folios.resolve).
    order = _add_equipment(client, headers, order_id, 3, service_type="linked")
    equipment_with_pending_folio = order["equipment"][2]["id"]
    detail = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers).json()
    assert next(
        item for item in detail["equipment"] if item["id"] == equipment_with_pending_folio
    )["folio_status"] == "pending"
    _capture_field_sheet_ready(client, headers, order_id, equipment_with_pending_folio)

    prevalidated = _prevalidate(client, headers, order_id)
    assert prevalidated.status_code == 200, prevalidated.text
    body = prevalidated.json()
    assert body["ready"] is False
    equipment_ids_with_blockers = {item["equipment_id"] for item in body["blockers"]}
    assert equipment_without_sheet in equipment_ids_with_blockers
    assert equipment_with_incomplete_sheet in equipment_ids_with_blockers
    assert equipment_with_pending_folio in equipment_ids_with_blockers

    finalized = _finalize(client, headers, order_id)
    assert finalized.status_code == 409, finalized.text
    assert finalized.json()["detail"]["code"] == "LAB_EQUIPMENT_BY_EQUIPMENT_BLOCKERS"


def test_prevalidation_passes_and_finalize_opens_once_all_equipment_are_ready(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers)
    order_id = order["id"]
    order = _add_equipment(client, headers, order_id, 1)
    equipment_id = order["equipment"][0]["id"]
    _capture_field_sheet_ready(client, headers, order_id, equipment_id)

    prevalidated = _prevalidate(client, headers, order_id)
    assert prevalidated.status_code == 200, prevalidated.text
    assert prevalidated.json() == {"ready": True, "blockers": []}

    finalized = _finalize(client, headers, order_id)
    assert finalized.status_code == 200, finalized.text
    assert finalized.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# 24-30: finalize -- firma única, completion, cierre, notification
# ---------------------------------------------------------------------------


def test_finalize_creates_single_signature_session_completes_sheets_closes_ot_and_notifies_capture(lab_context, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers)
    order_id = order["id"]
    order = _add_equipment(client, headers, order_id, 1)
    first_equipment_id = order["equipment"][0]["id"]
    order = _add_equipment(client, headers, order_id, 2)
    second_equipment_id = order["equipment"][1]["id"]
    first_sheet = _capture_field_sheet_ready(client, headers, order_id, first_equipment_id)
    second_sheet = _capture_field_sheet_ready(client, headers, order_id, second_equipment_id)

    finalized = _finalize(client, headers, order_id)
    assert finalized.status_code == 200, finalized.text
    result = finalized.json()
    assert result["status"] == "completed"
    assert result["signature_session_id"] is not None
    assert result["final_pdf_sha256"] is not None

    with factory() as db:
        sessions = list(db.scalars(select(LabWorkOrderSignatureSession)))
        assert len(sessions) == 1

        first_row = db.get(FieldSheet, first_sheet["id"])
        second_row = db.get(FieldSheet, second_sheet["id"])
        for row in (first_row, second_row):
            assert row.status == "completed"
            assert row.lab_signature_session_id == result["signature_session_id"]
            assert row.final_pdf_path is not None
            assert row.final_pdf_sha256 is not None

        order_row = db.get(LabWorkOrder, order_id)
        assert order_row.status == "completed"
        assert order_row.final_pdf is not None
        assert order_row.final_pdf_sha256 is not None

        from app.models.notification import Notification

        capture_user = db.scalar(select(User).where(User.username == "lab-capture"))
        notifications = list(
            db.scalars(
                select(Notification).where(
                    Notification.recipient_user_id == capture_user.id,
                    Notification.entity_id == order_id,
                )
            )
        )
        assert len(notifications) == 1
        assert notifications[0].notification_type == "work_order.completed"


# ---------------------------------------------------------------------------
# 31-38: entrega FULL automática, mismas firmas, snapshots, group_complete
# ---------------------------------------------------------------------------


def test_finalize_creates_full_delivery_reusing_the_same_signatures(lab_context, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers)
    order_id = order["id"]
    order = _add_equipment(client, headers, order_id, 1)
    equipment_id = order["equipment"][0]["id"]
    _capture_field_sheet_ready(client, headers, order_id, equipment_id)

    finalized = _finalize(client, headers, order_id)
    assert finalized.status_code == 200, finalized.text

    delivery_status = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/delivery", headers=headers
    )
    assert delivery_status.status_code == 200, delivery_status.text
    status_body = delivery_status.json()
    assert status_body["group_complete"] is True
    assert status_body["pending_equipment"] == []
    assert status_body["final_receipt_available"] is True
    assert len(status_body["exhibitions"]) == 1
    exhibition = status_body["exhibitions"][0]
    assert exhibition["delivery_method"] == "direct"
    assert exhibition["recipient_name"] == "Cliente LAB"
    assert exhibition["voucher_available"] is True

    with factory() as db:
        delivery_row = db.get(LabWorkOrderDelivery, exhibition["id"])
        assert delivery_row.status == "completed"
        assert delivery_row.delivered_by_signature_data_url == PNG_DATA_URL
        assert delivery_row.recipient_signature_data_url == PNG_DATA_URL
        assert delivery_row.voucher_pdf_sha256 is not None

        items = list(db.scalars(select(LabDeliveryItem).where(LabDeliveryItem.delivery_id == delivery_row.id)))
        assert len(items) == 1
        assert items[0].equipment_id == equipment_id
        assert items[0].instrument_snapshot == "Instrumento 1"

        order_row = db.get(LabWorkOrder, order_id)
        assert order_row.departure_date is not None


# ---------------------------------------------------------------------------
# 39-40: idempotencia ante retry
# ---------------------------------------------------------------------------


def test_finalize_is_idempotent_on_retry(lab_context, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers)
    order_id = order["id"]
    order = _add_equipment(client, headers, order_id, 1)
    equipment_id = order["equipment"][0]["id"]
    _capture_field_sheet_ready(client, headers, order_id, equipment_id)

    first = _finalize(client, headers, order_id)
    assert first.status_code == 200, first.text
    second = _finalize(client, headers, order_id)
    assert second.status_code == 200, second.text
    assert second.json()["signature_session_id"] == first.json()["signature_session_id"]
    assert second.json()["final_pdf_sha256"] == first.json()["final_pdf_sha256"]

    with factory() as db:
        sessions = list(db.scalars(select(LabWorkOrderSignatureSession)))
        assert len(sessions) == 1
        deliveries = list(db.scalars(select(LabWorkOrderDelivery)))
        assert len(deliveries) == 1


# ---------------------------------------------------------------------------
# 41-44: rollback atómico ante fallo, limpieza de archivos
# ---------------------------------------------------------------------------


def test_finalize_rolls_back_signature_and_completion_if_delivery_fails(lab_context, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers)
    order_id = order["id"]
    order = _add_equipment(client, headers, order_id, 1)
    equipment_id = order["equipment"][0]["id"]
    sheet = _capture_field_sheet_ready(client, headers, order_id, equipment_id)

    import app.services.lab_work_order_deliveries as deliveries_module

    real_create_delivery_event = deliveries_module._create_delivery_event

    def _explode(*_args, **_kwargs):
        raise RuntimeError("simulated delivery failure")

    monkeypatch.setattr(deliveries_module, "_create_delivery_event", _explode)

    with pytest.raises(RuntimeError):
        from app.services.lab_work_orders import finalize_equipment_by_equipment_work_order
        from app.schemas.lab_work_order import LabSignatureGroupWrite

        with factory() as db:
            payload = LabSignatureGroupWrite(**signatures_payload())
            technician = db.scalar(select(User).where(User.username == "lab-tech"))
            finalize_equipment_by_equipment_work_order(db, order_id, payload, technician)

    with factory() as db:
        order_row = db.get(LabWorkOrder, order_id)
        assert order_row.status == "draft"
        assert order_row.signature_session_id is None
        assert order_row.final_pdf is None
        sheet_row = db.get(FieldSheet, sheet["id"])
        assert sheet_row.status != "completed"
        assert sheet_row.final_pdf_path is None
        assert list(db.scalars(select(LabWorkOrderSignatureSession))) == []
        assert list(db.scalars(select(LabWorkOrderDelivery))) == []

    # El endpoint HTTP normal sigue disponible después -- nada quedó a medias.
    monkeypatch.setattr(deliveries_module, "_create_delivery_event", real_create_delivery_event)
    retried = _finalize(client, headers, order_id)
    assert retried.status_code == 200, retried.text


def test_finalize_cleans_up_orphaned_field_sheet_pdf_when_the_second_equipment_fails(lab_context, monkeypatch, tmp_path):
    """Mismo patrón que
    test_close_with_confirm_draft_completion_rolls_back_atomically_if_a_pdf_write_fails
    en test_lab_phase5_operational_closure.py, aplicado a
    finalize_equipment_by_equipment_work_order: si la primera hoja congela su
    PDF con éxito y la segunda falla, el artefacto huérfano de la primera se
    borra y la firma tampoco queda persistida."""
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers)
    order_id = order["id"]
    equipment_ids = []
    sheet_ids = []
    for index in (1, 2):
        order = _add_equipment(client, headers, order_id, index)
        equipment_id = order["equipment"][-1]["id"]
        equipment_ids.append(equipment_id)
        sheet = _capture_field_sheet_ready(client, headers, order_id, equipment_id)
        sheet_ids.append(sheet["id"])

    import app.services.field_sheet_pdfs as field_sheet_pdfs_module

    real_freeze = field_sheet_pdfs_module.freeze_final_field_sheet_pdf
    calls = {"count": 0}
    written_paths: list[str] = []

    def _freeze_second_call_explodes(db, field_sheet):
        calls["count"] += 1
        if calls["count"] == 1:
            result = real_freeze(db, field_sheet)
            written_paths.append(field_sheet.final_pdf_path)
            return result
        raise RuntimeError("simulated failure while freezing the second field sheet's PDF")

    monkeypatch.setattr(field_sheet_pdfs_module, "freeze_final_field_sheet_pdf", _freeze_second_call_explodes)

    with pytest.raises(RuntimeError):
        from app.services.lab_work_orders import finalize_equipment_by_equipment_work_order
        from app.schemas.lab_work_order import LabSignatureGroupWrite

        with factory() as db:
            payload = LabSignatureGroupWrite(**signatures_payload())
            technician = db.scalar(select(User).where(User.username == "lab-tech"))
            finalize_equipment_by_equipment_work_order(db, order_id, payload, technician)

    assert calls["count"] == 2
    assert len(written_paths) == 1

    with factory() as db:
        order_row = db.get(LabWorkOrder, order_id)
        assert order_row.status == "draft"
        assert order_row.signature_session_id is None
        for sheet_id in sheet_ids:
            sheet_row = db.get(FieldSheet, sheet_id)
            assert sheet_row.status != "completed"
            assert sheet_row.final_pdf_path is None
            assert sheet_row.final_pdf_sha256 is None

    orphan = resolve_storage_path(written_paths[0])
    assert orphan is None or not orphan.is_file()


# ---------------------------------------------------------------------------
# 45: tombstones ignorados
# ---------------------------------------------------------------------------


def test_finalize_ignores_retired_equipment(lab_context, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers)
    order_id = order["id"]
    order = _add_equipment(client, headers, order_id, 1)
    retired_id = order["equipment"][0]["id"]
    order = _add_equipment(client, headers, order_id, 2)
    kept_id = order["equipment"][1]["id"]
    _capture_field_sheet_ready(client, headers, order_id, kept_id)

    deleted = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{retired_id}",
        headers=headers,
    )
    assert deleted.status_code == 200, deleted.text

    prevalidated = _prevalidate(client, headers, order_id)
    assert prevalidated.status_code == 200, prevalidated.text
    assert prevalidated.json() == {"ready": True, "blockers": []}

    finalized = _finalize(client, headers, order_id)
    assert finalized.status_code == 200, finalized.text
    assert kept_id not in [] and finalized.json()["status"] == "completed"

    with factory() as db:
        retired_row = db.get(LabWorkOrderEquipment, retired_id)
        assert retired_row.is_active is False
        assert retired_row.field_sheet is None
        deliveries = list(db.scalars(select(LabDeliveryItem)))
        assert [item.equipment_id for item in deliveries] == [kept_id]


# ---------------------------------------------------------------------------
# 47: group no regresiona (regresión explícita, además de la suite completa)
# ---------------------------------------------------------------------------


def test_group_mode_end_to_end_flow_is_unaffected(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers, workflow_mode="group")
    order_id = order["id"]
    order = _add_equipment(client, headers, order_id, 1)
    equipment_id = order["equipment"][0]["id"]
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"

    delivery = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/delivery",
        json={
            "delivery_method": "direct",
            "delivered_by_signature_data_url": PNG_DATA_URL,
            "recipient_name": "Cliente Receptor",
            "recipient_signature_data_url": PNG_DATA_URL,
            "notes": None,
        },
        headers=headers,
    )
    assert delivery.status_code == 201, delivery.text


# ---------------------------------------------------------------------------
# Caso productivo crítico (sección 24/38 del encargo): OT "group" con 5
# equipos ya existentes, conversión manual de workflow_mode, sin recrear
# ningún equipo, flujo equipo-por-equipo funcional de inmediato.
# ---------------------------------------------------------------------------


def test_five_preexisting_group_equipment_convert_to_equipment_by_equipment_without_recreation(
    lab_context, monkeypatch, tmp_path,
):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers, workflow_mode="group", client_name="Cliente Productivo")
    order_id = order["id"]
    original_snapshot = []
    for index in range(1, 6):
        order = _add_equipment(client, headers, order_id, index)
    for item in order["equipment"]:
        original_snapshot.append(dict(item))
    assert len(original_snapshot) == 5
    original_ids = sorted(item["id"] for item in original_snapshot)

    with factory() as db:
        assert db.scalar(select(FieldSheet)) is None
        row = db.get(LabWorkOrder, order_id)
        assert row.workflow_mode == "group"
        # La intervención productiva real: UPDATE directo de una sola
        # columna, sin tocar equipment/fieldsheets/IDs -- exactamente lo que
        # el contrato debe soportar (sección 4 del encargo).
        row.workflow_mode = "equipment_by_equipment"
        db.commit()

    reloaded = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers)
    assert reloaded.status_code == 200, reloaded.text
    detail = reloaded.json()
    assert detail["workflow_mode"] == "equipment_by_equipment"
    reloaded_ids = sorted(item["id"] for item in detail["equipment"])
    assert reloaded_ids == original_ids, "0 equipos recreados/eliminados"
    assert len(detail["equipment"]) == 5

    reloaded_by_id = {item["id"]: item for item in detail["equipment"]}
    for original in original_snapshot:
        current = reloaded_by_id[original["id"]]
        for field in (
            "position", "instrument", "brand", "serial_number", "identification",
            "service_type", "report_number", "certificate_folio", "folio_status", "observations",
        ):
            assert current[field] == original[field], field
        # Con field_sheet_id aún None, cada uno debe ofrecer "Seleccionar
        # Hoja de Campo" (bucket sin hoja) desde el primer reload.
        assert current["field_sheet_id"] is None
        assert current["field_sheet_status"] is None

    for equipment_id in reloaded_ids:
        _capture_field_sheet_ready(client, headers, order_id, equipment_id)

    prevalidated = _prevalidate(client, headers, order_id)
    assert prevalidated.status_code == 200, prevalidated.text
    assert prevalidated.json() == {"ready": True, "blockers": []}

    finalized = _finalize(client, headers, order_id)
    assert finalized.status_code == 200, finalized.text
    result = finalized.json()
    assert result["status"] == "completed"
    assert len(result["equipment"]) == 5

    with factory() as db:
        completed_sheets = list(db.scalars(select(FieldSheet).where(FieldSheet.status == "completed")))
        assert len(completed_sheets) == 5
        for sheet in completed_sheets:
            assert sheet.final_pdf_path is not None
            assert sheet.final_pdf_sha256 is not None
        order_row = db.get(LabWorkOrder, order_id)
        assert order_row.status == "completed"
        for equipment_id in original_ids:
            row = db.get(LabWorkOrderEquipment, equipment_id)
            assert row.id in original_ids  # nunca un id nuevo

        items = list(
            db.scalars(
                select(LabDeliveryItem).join(
                    LabWorkOrderDelivery, LabDeliveryItem.delivery_id == LabWorkOrderDelivery.id
                ).where(LabWorkOrderDelivery.root_work_order_id == order_id)
            )
        )
        assert sorted(item.equipment_id for item in items) == original_ids

    delivery_status = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/delivery", headers=headers
    )
    assert delivery_status.json()["group_complete"] is True


# ---------------------------------------------------------------------------
# Cierre "grupos mixtos" (2026-09-04): workflow_mode independiente por OT,
# signature_scope independiente de workflow_mode, entrega independiente de
# ambos, cambio administrativo de modalidad, y firma grupal que puede mezclar
# miembros 'group'/'equipment_by_equipment'.
# ---------------------------------------------------------------------------


def test_group_creation_applies_the_chosen_workflow_mode_to_every_materialized_member(lab_context):
    """Sección 3: elegir una modalidad al crear un grupo de N OT aplica ESA
    MISMA modalidad a las N filas materializadas en esa sola operación."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    root = _create_group(client, headers, quantity=3, workflow_mode="equipment_by_equipment")
    member_ids = [item["id"] for item in root["related_work_orders"]]
    assert len(member_ids) == 3
    for member_id in member_ids:
        assert _get_order(client, headers, member_id)["workflow_mode"] == "equipment_by_equipment"


def test_additional_work_order_can_choose_a_workflow_mode_independent_of_its_source(lab_context):
    """Sección 4: 'Asignar OT extra' deja elegir CUALQUIERA de las dos
    modalidades para la OT nueva, sin heredar forzosamente la de la fuente --
    corrección explícita sobre el cierre anterior (workflow_mode=source.workflow_mode)."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    source = _create_order(client, headers, workflow_mode="group")
    for index in range(1, 11):
        source = _add_equipment(client, headers, source["id"], index)
    assert len(source["equipment"]) == 10

    additional = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{source['id']}/additional",
        params={"workflow_mode": "equipment_by_equipment"},
        headers=headers,
    )
    assert additional.status_code == 201, additional.text
    body = additional.json()
    assert body["workflow_mode"] == "equipment_by_equipment"

    with factory() as db:
        assert db.get(LabWorkOrder, source["id"]).workflow_mode == "group"
        assert db.get(LabWorkOrder, body["id"]).workflow_mode == "equipment_by_equipment"

    # Sin el parámetro explícito, sigue heredando (compatibilidad hacia
    # atrás) -- nunca se rompe el comportamiento por defecto ya existente.
    # Una OT distinta (no encadenada a la anterior) para no chocar con
    # "sólo la última OT del grupo puede generar una adicional".
    other_source = _create_order(client, headers, workflow_mode="equipment_by_equipment")
    for index in range(1, 11):
        other_source = _add_equipment(client, headers, other_source["id"], index)
    inherited = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{other_source['id']}/additional", headers=headers,
    )
    assert inherited.status_code == 201, inherited.text
    assert inherited.json()["workflow_mode"] == "equipment_by_equipment"


def test_mixed_root_allows_different_workflow_mode_per_sibling_without_cascading(lab_context):
    """Sección 5: un mismo root_work_order_id puede mezclar 'group' y
    'equipment_by_equipment' libremente -- ninguna validación cascada."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    root = _create_group(client, headers, quantity=3, workflow_mode="equipment_by_equipment")
    member_ids = [item["id"] for item in root["related_work_orders"]]

    changed = _change_workflow_mode(
        client, admin_headers, member_ids[2], new_workflow_mode="group",
        reason="Equipo trasladado al laboratorio para su análisis",
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["workflow_mode"] == "group"

    modes = {member_id: _get_order(client, headers, member_id)["workflow_mode"] for member_id in member_ids}
    assert modes[member_ids[0]] == "equipment_by_equipment"
    assert modes[member_ids[1]] == "equipment_by_equipment"
    assert modes[member_ids[2]] == "group"


def test_change_workflow_mode_requires_a_non_blank_reason(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order = _create_order(client, headers, workflow_mode="group")

    blank = _change_workflow_mode(client, admin_headers, order["id"], new_workflow_mode="equipment_by_equipment", reason="   ")
    assert blank.status_code == 422, blank.text

    missing = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/workflow-mode",
        json={"new_workflow_mode": "equipment_by_equipment"},
        headers=admin_headers,
    )
    assert missing.status_code == 422, missing.text


def test_change_workflow_mode_is_forbidden_for_technician_and_capture(lab_context):
    """La acción administrativa nunca se otorga a Técnico ni a Captura por
    defecto -- ocultar el botón en Mobile no basta, backend es la autoridad."""
    client, _factory, tokens = lab_context
    order = _create_order(client, auth(tokens["tech"]), workflow_mode="group")
    for role_key in ("tech", "capture"):
        response = _change_workflow_mode(
            client, auth(tokens[role_key]), order["id"], new_workflow_mode="equipment_by_equipment",
        )
        assert response.status_code == 403, response.text


def test_change_workflow_mode_rejects_the_same_modality(lab_context):
    client, _factory, tokens = lab_context
    order = _create_order(client, auth(tokens["tech"]), workflow_mode="group")
    response = _change_workflow_mode(client, auth(tokens["admin"]), order["id"], new_workflow_mode="group")
    assert response.status_code == 409, response.text


def test_change_workflow_mode_group_to_ebe_preserves_equipment_and_writes_audit_log(lab_context):
    """Secciones 6-9/11/39: preserva ID de OT, equipos (posición, instrumento,
    marca, serie, identificación, service_type, folios, observaciones) y
    escribe un AuditLog con work_order_id/previous/new/reason/actor/timestamp."""
    from app.models.audit_log import AuditLog

    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers, workflow_mode="group")
    order = _add_equipment(client, headers, order["id"], 1, observations="Equipo con detalle visible")
    equipment_before = order["equipment"][0]

    changed = _change_workflow_mode(
        client, auth(tokens["admin"]), order["id"], new_workflow_mode="equipment_by_equipment",
        reason="Cliente solicitó captura equipo por equipo",
    )
    assert changed.status_code == 200, changed.text
    body = changed.json()
    assert body["id"] == order["id"]
    assert body["workflow_mode"] == "equipment_by_equipment"
    equipment_after = body["equipment"][0]
    for field in (
        "id", "position", "instrument", "brand", "serial_number", "identification",
        "service_type", "certificate_folio", "folio_status", "observations",
    ):
        assert equipment_after[field] == equipment_before[field], field

    with factory() as db:
        admin_user = db.scalar(select(User).where(User.username == "lab-admin"))
        entries = list(
            db.scalars(
                select(AuditLog)
                .where(AuditLog.action == "lab_work_order.workflow_mode_changed")
                .order_by(AuditLog.id.desc())
            )
        )
        assert len(entries) == 1
        entry = entries[0]
        assert entry.entity_id == order["id"]
        assert entry.user_id == admin_user.id
        assert entry.previous_values == {"workflow_mode": "group"}
        assert entry.new_values["workflow_mode"] == "equipment_by_equipment"
        assert entry.new_values["reason"] == "Cliente solicitó captura equipo por equipo"
        assert entry.created_at is not None


def test_change_workflow_mode_blocked_once_reception_is_signed(lab_context):
    """Sección 9: nunca reescribe historia ya formalizada -- una vez firmada
    la recepción, el cambio se rechaza (no es un atajo de reapertura)."""
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers, workflow_mode="group")
    order = _add_equipment(client, headers, order["id"], 1)
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/signatures/individual",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    assert signed.json()["status"] == "received_signed"

    blocked = _change_workflow_mode(
        client, auth(tokens["admin"]), order["id"], new_workflow_mode="equipment_by_equipment",
    )
    assert blocked.status_code == 409, blocked.text


def test_change_workflow_mode_ebe_to_group_preserves_existing_field_sheet_and_blocks_capture_until_reception_signed(
    lab_context,
):
    """Sección 10/35: convertir equipment_by_equipment -> group NO borra ni
    recrea la FieldSheet ya capturada -- mismo ID, misma captura, mismo
    estado draft/in_progress. Tras el cambio, la OT es 'group': la captura
    posterior sigue bloqueada hasta firmar recepción; una vez firmada, el
    técnico continúa la MISMA hoja (nunca captura dos veces)."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers, workflow_mode="equipment_by_equipment")
    order = _add_equipment(client, headers, order["id"], 1)
    equipment_id = order["equipment"][0]["id"]
    sheet = _capture_field_sheet_ready(client, headers, order["id"], equipment_id)
    sheet_id = sheet["id"]
    assert sheet["status"] == "in_progress"

    changed = _change_workflow_mode(
        client, auth(tokens["admin"]), order["id"], new_workflow_mode="group",
        reason="Se decidió tramitar el equipo dentro del flujo regular de grupo",
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["workflow_mode"] == "group"

    loaded = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    )
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["id"] == sheet_id
    assert loaded.json()["status"] == "in_progress"
    assert loaded.json()["observations"] == sheet["observations"]

    # Ahora "group": la captura ADICIONAL sigue bloqueada sin recepción
    # firmada -- nunca completar/formalizar a mitad de camino.
    still_blocked = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/equipment/{equipment_id}/field-sheet",
        json={"final_condition": "BUENA", "observations": "intento pre-firma"},
        headers=headers,
    )
    assert still_blocked.status_code == 409, still_blocked.text
    assert still_blocked.json()["detail"] == "La OT no admite captura técnica"

    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/signatures/individual",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    assert signed.json()["status"] in {"received_signed", "in_progress"}

    continued = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order['id']}/equipment/{equipment_id}/field-sheet",
        json={"final_condition": "BUENA", "observations": "Captura continuada tras firmar"},
        headers=headers,
    )
    assert continued.status_code == 200, continued.text
    assert continued.json()["id"] == sheet_id, "misma hoja, nunca una nueva"
    assert continued.json()["observations"] == "Captura continuada tras firmar"


def test_change_workflow_mode_group_to_ebe_and_back_never_recreates_equipment(lab_context):
    """Sección 11: group -> equipment_by_equipment -> group conserva ID de
    equipos/OT en ambos sentidos -- nunca recreación."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order = _create_order(client, headers, workflow_mode="group")
    order = _add_equipment(client, headers, order["id"], 1)
    order = _add_equipment(client, headers, order["id"], 2)
    original_ids = sorted(item["id"] for item in order["equipment"])

    to_ebe = _change_workflow_mode(client, admin_headers, order["id"], new_workflow_mode="equipment_by_equipment")
    assert to_ebe.status_code == 200, to_ebe.text
    assert sorted(item["id"] for item in to_ebe.json()["equipment"]) == original_ids

    back_to_group = _change_workflow_mode(client, admin_headers, order["id"], new_workflow_mode="group")
    assert back_to_group.status_code == 200, back_to_group.text
    assert sorted(item["id"] for item in back_to_group.json()["equipment"]) == original_ids
    assert back_to_group.json()["id"] == order["id"]


def _setup_mixed_trio(client, factory, tokens, *, capture_ebe: bool = True):
    """3 OT compartiendo un root: OT1/OT2 quedan equipment_by_equipment con
    captura real lista para completarse (si capture_ebe), OT3 se convierte a
    'group' por acción administrativa -- exactamente el caso obligatorio de
    la sección 36."""
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    root = _create_group(client, headers, quantity=3, workflow_mode="equipment_by_equipment", client_name="Cliente Mixto")
    member_ids = [item["id"] for item in root["related_work_orders"]]
    ot1_id, ot2_id, ot3_id = member_ids

    for order_id in (ot1_id, ot2_id, ot3_id):
        _add_equipment(client, headers, order_id, order_id)

    if capture_ebe:
        for order_id in (ot1_id, ot2_id):
            equipment_id = _get_order(client, headers, order_id)["equipment"][0]["id"]
            _capture_field_sheet_ready(client, headers, order_id, equipment_id)

    changed = _change_workflow_mode(
        client, admin_headers, ot3_id, new_workflow_mode="group",
        reason="Equipo trasladado al laboratorio.",
    )
    assert changed.status_code == 200, changed.text
    ot3_equipment_id = _get_order(client, headers, ot3_id)["equipment"][0]["id"]
    return ot1_id, ot2_id, ot3_id, ot3_equipment_id


def test_mixed_group_signature_produces_one_session_and_differing_outcomes_per_workflow_mode(
    lab_context, monkeypatch, tmp_path,
):
    """Sección 16/36 -- el caso obligatorio del cierre "grupos mixtos": OT1 y
    OT2 (equipment_by_equipment, captura ya lista) + OT3 (convertida a
    'group' por acción administrativa). UNA sola firma cierra/entrega OT1 y
    OT2 y sólo formaliza recepción de OT3, que sigue su flujo normal
    después -- "una firma NO implica el mismo estado final para todas"."""
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    ot1_id, ot2_id, ot3_id, ot3_equipment_id = _setup_mixed_trio(client, factory, tokens)

    prevalidated = _group_prevalidate(client, headers, ot1_id)
    assert prevalidated.status_code == 200, prevalidated.text
    assert prevalidated.json() == {"ready": True, "blockers": []}

    finalized = _group_finalize(client, headers, ot1_id)
    assert finalized.status_code == 200, finalized.text

    ot1 = _get_order(client, headers, ot1_id)
    ot2 = _get_order(client, headers, ot2_id)
    ot3 = _get_order(client, headers, ot3_id)
    assert ot1["status"] == "completed"
    assert ot2["status"] == "completed"
    assert ot3["status"] == "received_signed"
    assert ot3["workflow_mode"] == "group"

    with factory() as db:
        sessions = list(db.scalars(select(LabWorkOrderSignatureSession)))
        assert len(sessions) == 1
        session_id = sessions[0].id
        for order_id in (ot1_id, ot2_id, ot3_id):
            row = db.get(LabWorkOrder, order_id)
            assert row.signature_session_id == session_id, "una sola sesión compartida por los tres"

        deliveries = list(db.scalars(select(LabWorkOrderDelivery)))
        assert len(deliveries) == 1
        items = list(
            db.scalars(select(LabDeliveryItem).where(LabDeliveryItem.delivery_id == deliveries[0].id))
        )
        delivered_equipment_ids = {item.equipment_id for item in items}
        assert ot3_equipment_id not in delivered_equipment_ids, "OT3 sigue físicamente en el laboratorio"
        ot1_equipment_id = ot1["equipment"][0]["id"]
        ot2_equipment_id = ot2["equipment"][0]["id"]
        assert delivered_equipment_ids == {ot1_equipment_id, ot2_equipment_id}

        # Nunca se genera el recibo final de grupo mientras OT3 siga
        # pendiente en el laboratorio -- ver _finalize_delivery/_pending_equipment.
        from app.models.lab_delivery_group_receipt import LabDeliveryGroupReceipt
        assert db.scalar(select(LabDeliveryGroupReceipt)) is None

    # OT3 continúa su flujo normal de group después: captura -> cierre -> entrega.
    ot3_sheet = _capture_field_sheet_ready(client, headers, ot3_id, ot3_equipment_id)
    completed_sheet = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{ot3_id}/equipment/{ot3_equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert completed_sheet.status_code == 200, completed_sheet.text
    closed = client.post(f"/api/mobile/v1/technician/lab-work-orders/{ot3_id}/complete", headers=headers)
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "completed"


def test_mixed_group_prevalidate_and_finalize_block_on_an_incomplete_ebe_member(lab_context):
    """Sección 18/37: si CUALQUIER miembro EBE no está listo, ni prevalidate
    ni finalize proceden -- ninguna mutación ocurre."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    ot1_id, ot2_id, ot3_id, _ot3_equipment_id = _setup_mixed_trio(client, factory, tokens, capture_ebe=False)

    prevalidated = _group_prevalidate(client, headers, ot1_id)
    assert prevalidated.status_code == 200, prevalidated.text
    body = prevalidated.json()
    assert body["ready"] is False
    assert len(body["blockers"]) >= 2  # OT1 y OT2 sin FieldSheet
    for blocker in body["blockers"]:
        assert blocker["work_order_id"] in (ot1_id, ot2_id)
        assert blocker["workflow_mode"] == "equipment_by_equipment"

    finalized = _group_finalize(client, headers, ot1_id)
    assert finalized.status_code == 409, finalized.text
    assert finalized.json()["detail"]["code"] == "LAB_EQUIPMENT_BY_EQUIPMENT_BLOCKERS"

    with factory() as db:
        for order_id in (ot1_id, ot2_id, ot3_id):
            row = db.get(LabWorkOrder, order_id)
            assert row.signature_session_id is None
            assert row.status == "draft"
        assert db.scalar(select(LabWorkOrderSignatureSession)) is None


def test_mixed_group_finalize_rolls_back_completely_if_delivery_fails(lab_context, monkeypatch, tmp_path):
    """Sección 20/38: un fallo a mitad de la finalización grupal mixta (aquí,
    en la entrega) revierte firma + hojas completadas + cierre de OT1/OT2 --
    nunca un estado parcial, ni firma huérfana, ni PDF huérfano en disco."""
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    ot1_id, ot2_id, ot3_id, _ot3_equipment_id = _setup_mixed_trio(client, factory, tokens)

    import app.services.lab_work_order_deliveries as deliveries_module

    real_create_delivery_event = deliveries_module._create_delivery_event

    def _explode(*_args, **_kwargs):
        raise RuntimeError("fallo inyectado en la entrega")

    monkeypatch.setattr(deliveries_module, "_create_delivery_event", _explode)

    with factory() as db:
        sheet_ids = [
            row.id for row in db.scalars(
                select(FieldSheet).join(
                    LabWorkOrderEquipment, FieldSheet.lab_equipment_id == LabWorkOrderEquipment.id
                ).where(LabWorkOrderEquipment.work_order_id.in_([ot1_id, ot2_id]))
            )
        ]
    assert len(sheet_ids) == 2

    with pytest.raises(RuntimeError):
        from app.services.lab_work_orders import finalize_lab_signature_group
        from app.schemas.lab_work_order import LabSignatureGroupWrite

        with factory() as db:
            payload = LabSignatureGroupWrite(**signatures_payload())
            technician = db.scalar(select(User).where(User.username == "lab-tech"))
            finalize_lab_signature_group(db, ot1_id, payload, technician)

    with factory() as db:
        for order_id in (ot1_id, ot2_id, ot3_id):
            row = db.get(LabWorkOrder, order_id)
            assert row.status == "draft"
            assert row.signature_session_id is None
        assert db.scalar(select(LabWorkOrderSignatureSession)) is None
        assert db.scalar(select(LabWorkOrderDelivery)) is None
        for sheet_id in sheet_ids:
            sheet = db.get(FieldSheet, sheet_id)
            assert sheet.status != "completed"
            assert sheet.final_pdf_path is None

    # El endpoint HTTP normal sigue disponible después -- nada quedó a medias.
    monkeypatch.setattr(deliveries_module, "_create_delivery_event", real_create_delivery_event)
    retried = _group_finalize(client, headers, ot1_id)
    assert retried.status_code == 200, retried.text


def test_mixed_group_finalize_is_idempotent_on_retry(lab_context, monkeypatch, tmp_path):
    """Sección 24: reintentar tras un éxito no crea una segunda sesión de
    firma ni una segunda entrega."""
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    ot1_id, ot2_id, ot3_id, _ot3_equipment_id = _setup_mixed_trio(client, factory, tokens)

    first = _group_finalize(client, headers, ot1_id)
    assert first.status_code == 200, first.text
    retried = _group_finalize(client, headers, ot1_id)
    assert retried.status_code == 200, retried.text

    with factory() as db:
        assert len(list(db.scalars(select(LabWorkOrderSignatureSession)))) == 1
        assert len(list(db.scalars(select(LabWorkOrderDelivery)))) == 1


def test_pure_equipment_by_equipment_group_signs_once_and_all_members_complete_and_deliver(
    lab_context, monkeypatch, tmp_path,
):
    """Escenario obligatorio A (sección 63): grupo puro de 3 EBE, todos
    listos, cierra con una sola firma grupal -- los tres completed/entregados."""
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    root = _create_group(client, headers, quantity=3, workflow_mode="equipment_by_equipment")
    member_ids = [item["id"] for item in root["related_work_orders"]]
    equipment_ids = {}
    for order_id in member_ids:
        order = _add_equipment(client, headers, order_id, order_id)
        equipment_id = order["equipment"][0]["id"]
        equipment_ids[order_id] = equipment_id
        _capture_field_sheet_ready(client, headers, order_id, equipment_id)

    prevalidated = _group_prevalidate(client, headers, member_ids[0])
    assert prevalidated.status_code == 200, prevalidated.text
    assert prevalidated.json() == {"ready": True, "blockers": []}

    finalized = _group_finalize(client, headers, member_ids[0])
    assert finalized.status_code == 200, finalized.text

    with factory() as db:
        for order_id in member_ids:
            row = db.get(LabWorkOrder, order_id)
            assert row.status == "completed"
        assert len(list(db.scalars(select(LabWorkOrderSignatureSession)))) == 1
        deliveries = list(db.scalars(select(LabWorkOrderDelivery)))
        assert len(deliveries) == 1
        items = list(db.scalars(select(LabDeliveryItem).where(LabDeliveryItem.delivery_id == deliveries[0].id)))
        assert sorted(item.equipment_id for item in items) == sorted(equipment_ids.values())


# ---------------------------------------------------------------------------
# Regresión PostgreSQL obligatoria (sección 39): constraints reales,
# atomicidad y el mismo caso productivo de 5 equipos contra un motor real.
# ---------------------------------------------------------------------------


@pytest.fixture()
def postgres_lab_context():
    database_url = os.getenv("LAB_POSTGRES_TEST_URL")
    if not database_url:
        pytest.skip("requiere LAB_POSTGRES_TEST_URL para probar constraints PostgreSQL reales")

    from sqlalchemy import text as sa_text

    schema = f"lab_equipment_by_equipment_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(sa_text(f'CREATE SCHEMA "{schema}"'))

    engine = create_engine(database_url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        roles = {name: Role(name=name, description=name) for name in ("Tecnico", "Administrador", "Captura")}
        db.add_all(roles.values())
        db.flush()
        users = {}
        for key, role_name in (("tech", "Tecnico"), ("admin", "Administrador"), ("capture", "Captura")):
            role = roles[role_name]
            user = User(
                username=f"pg-eqbyeq-{key}",
                email=f"pg-eqbyeq-{key}@example.test",
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


def test_postgresql_five_preexisting_equipment_convert_and_finalize_atomically(
    postgres_lab_context, monkeypatch, tmp_path,
):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = postgres_lab_context
    headers = auth(tokens["tech"])
    order = _create_order(client, headers, workflow_mode="group")
    order_id = order["id"]
    for index in range(1, 6):
        order = _add_equipment(client, headers, order_id, index)
    original_ids = sorted(item["id"] for item in order["equipment"])
    assert len(original_ids) == 5

    with factory() as db:
        row = db.get(LabWorkOrder, order_id)
        row.workflow_mode = "equipment_by_equipment"
        db.commit()

    for equipment_id in original_ids:
        _capture_field_sheet_ready(client, headers, order_id, equipment_id)

    finalized = _finalize(client, headers, order_id)
    assert finalized.status_code == 200, finalized.text
    assert finalized.json()["status"] == "completed"

    with factory() as db:
        completed_sheets = list(db.scalars(select(FieldSheet).where(FieldSheet.status == "completed")))
        assert len(completed_sheets) == 5
        assert sorted(row.lab_equipment_id for row in completed_sheets) == original_ids
        sessions = list(db.scalars(select(LabWorkOrderSignatureSession)))
        assert len(sessions) == 1
        deliveries = list(db.scalars(select(LabWorkOrderDelivery)))
        assert len(deliveries) == 1
        items = list(db.scalars(select(LabDeliveryItem).where(LabDeliveryItem.delivery_id == deliveries[0].id)))
        assert sorted(item.equipment_id for item in items) == original_ids

    # Retry: no debe violar ninguna constraint real (FK/unique de sesión de
    # firma, índice único de position, etc.) ni duplicar nada.
    retried = _finalize(client, headers, order_id)
    assert retried.status_code == 200, retried.text
    with factory() as db:
        assert len(list(db.scalars(select(LabWorkOrderSignatureSession)))) == 1
        assert len(list(db.scalars(select(LabWorkOrderDelivery)))) == 1


def test_postgresql_mixed_group_signature_produces_one_session_and_differing_outcomes(
    postgres_lab_context, monkeypatch, tmp_path,
):
    """Mismo caso obligatorio de la sección 36 (OT1/OT2 equipment_by_equipment
    + OT3 convertida a group por acción administrativa, UNA sola firma
    grupal), reverificado contra PostgreSQL real: constraints de sesión de
    firma/entrega, atomicidad de la transacción y retry idempotente."""
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = postgres_lab_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])

    root = _create_group(client, headers, quantity=3, workflow_mode="equipment_by_equipment", client_name="Cliente Mixto PG")
    member_ids = [item["id"] for item in root["related_work_orders"]]
    ot1_id, ot2_id, ot3_id = member_ids
    for order_id in member_ids:
        _add_equipment(client, headers, order_id, order_id)
    for order_id in (ot1_id, ot2_id):
        equipment_id = _get_order(client, headers, order_id)["equipment"][0]["id"]
        _capture_field_sheet_ready(client, headers, order_id, equipment_id)
    changed = _change_workflow_mode(
        client, admin_headers, ot3_id, new_workflow_mode="group",
        reason="Equipo trasladado al laboratorio.",
    )
    assert changed.status_code == 200, changed.text
    ot3_equipment_id = _get_order(client, headers, ot3_id)["equipment"][0]["id"]

    finalized = _group_finalize(client, headers, ot1_id)
    assert finalized.status_code == 200, finalized.text

    with factory() as db:
        assert db.get(LabWorkOrder, ot1_id).status == "completed"
        assert db.get(LabWorkOrder, ot2_id).status == "completed"
        ot3_row = db.get(LabWorkOrder, ot3_id)
        assert ot3_row.status == "received_signed"
        assert ot3_row.workflow_mode == "group"
        assert len(list(db.scalars(select(LabWorkOrderSignatureSession)))) == 1
        deliveries = list(db.scalars(select(LabWorkOrderDelivery)))
        assert len(deliveries) == 1
        items = list(db.scalars(select(LabDeliveryItem).where(LabDeliveryItem.delivery_id == deliveries[0].id)))
        assert ot3_equipment_id not in {item.equipment_id for item in items}

    retried = _group_finalize(client, headers, ot1_id)
    assert retried.status_code == 200, retried.text
    with factory() as db:
        assert len(list(db.scalars(select(LabWorkOrderSignatureSession)))) == 1
        assert len(list(db.scalars(select(LabWorkOrderDelivery)))) == 1
