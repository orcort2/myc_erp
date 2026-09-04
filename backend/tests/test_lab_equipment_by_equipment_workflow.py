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
