"""SG-4H: cierre category-aware. Un equipo de Servicio General está
técnicamente completo con TechnicalReport vigente `completed` + PDF final
válido + entrega `completed` vigente; la OT pasa a `ready_to_close` y
`/complete` re-valida todo. Nunca se exige FieldSheet, MYCA/MYCT ni se
interpreta la firma de recepción como entrega."""

from __future__ import annotations

import hashlib

from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.field_sheet import FieldSheet
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.operational_ticket import OperationalTicket
from app.models.technical_report import TechnicalReport
from test_general_service_delivery import (  # noqa: F401  (fixtures y helpers reutilizados)
    BASE,
    COMPLETE,
    _with_context,
    capture,
    create_order,
    deliver,
    delivery_payload,
    finalize,
    isolated_storage,
    order_with_reports,
    patch_capture,
    report_url,
    reset_override,
    sg3,
)

FAILURE_CODES = {"TECHNICAL_REPORT_INCOMPLETE", "TECHNICAL_REPORT_DOCUMENT_INVALID", "TECHNICAL_REPORT_DELIVERY_INCOMPLETE", "TECHNICAL_REPORT_REVISION_REQUIRED"}


def complete(client, headers, order):
    return client.post(f"{BASE}/{order['id']}/complete", headers=headers)


def order_status(client, headers, order) -> str:
    return client.get(f"{BASE}/{order['id']}", headers=headers).json()["status"]


def list_item(client, headers, order) -> dict:
    items = client.get(BASE, headers=headers).json()
    return next(item for item in items if item["id"] == order["id"])


def run_finalize(client, headers, order, equipment):
    return client.post(report_url(order["id"], equipment["id"], "/finalize"), headers=headers)


def ready_chain(client, headers, count: int = 1):
    """Todos los equipos: reporte finalizado -> entrega -> reporte final (PDF)."""
    order, equipments, reports = order_with_reports(client, headers, count=count)
    for equipment in equipments:
        finalize(client, headers, order, equipment)
    assert deliver(client, headers, order).status_code == 201
    for equipment in equipments:
        assert run_finalize(client, headers, order, equipment).status_code == 200
    return order, equipments, reports


def assert_general_service_error(response, code: str):
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == code, detail
    assert detail["code"] in FAILURE_CODES and detail["message"] and detail["items"]
    assert "FIELD" not in response.text.upper().replace("FIELDS", "") or "field_sheet" not in response.text.lower()
    assert "LAB_FIELD_SHEETS_INCOMPLETE" not in response.text
    return detail


# --------------------------------------------------------------- bloqueos

def test_without_a_technical_report_the_order_cannot_close_and_no_field_sheet_error_appears(sg3):
    client, _factory, headers = sg3
    order = create_order(client, headers, operational_category="general_service")
    from test_lab_general_service_equipment import general_equipment, sign_reception

    general_equipment(client, headers, order["id"])
    assert sign_reception(client, headers, order["id"]).status_code == 200  # la recepción firmada NO basta
    detail = assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_INCOMPLETE")
    assert detail["items"][0]["reason"] == "Sin reporte técnico"
    assert list_item(client, headers, order)["completed_equipment_count"] == 0


def test_unfinished_reports_do_not_make_the_order_ready(sg3):
    client, _factory, headers = sg3
    order, [equipment], _ = order_with_reports(client, headers)
    assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_INCOMPLETE")  # draft
    capture(client, headers, order, equipment)
    assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_INCOMPLETE")  # in_progress
    assert order_status(client, headers, order) == "in_progress"


def test_ready_for_signatures_without_delivery_or_without_final_report_is_not_ready(sg3):
    client, _factory, headers = sg3
    order, [equipment], _ = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_INCOMPLETE")  # sin entrega
    assert deliver(client, headers, order).status_code == 201
    detail = assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_INCOMPLETE")  # entrega sin PDF/completed
    assert "no está completado" in detail["items"][0]["reason"]
    assert order_status(client, headers, order) == "in_progress"


def _force_completed(factory, report_id: int, storage, *, with_pdf: bool):
    with factory() as db:
        report = db.get(TechnicalReport, report_id)
        report.status = "completed"
        if with_pdf:
            content = b"%PDF-1.4 fixture"
            target = storage / "technical-reports" / str(report_id) / "final" / "fixture.pdf"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            report.final_pdf_path = f"technical-reports/{report_id}/final/fixture.pdf"
            report.final_pdf_sha256 = hashlib.sha256(content).hexdigest()
            from datetime import datetime, timezone

            report.final_pdf_generated_at = datetime.now(timezone.utc)
        db.commit()


def test_completed_report_without_delivery_is_not_ready_even_with_a_valid_pdf(sg3, isolated_storage):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    _force_completed(factory, report["id"], isolated_storage, with_pdf=False)
    assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_DOCUMENT_INVALID")  # completed sin PDF
    _force_completed(factory, report["id"], isolated_storage, with_pdf=True)
    assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_DELIVERY_INCOMPLETE")  # PDF válido sin entrega


# --------------------------------------------------------------- completitud + ready_to_close

def test_complete_equipment_makes_the_order_ready_to_close_and_counts_it(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = ready_chain(client, headers)
    assert order_status(client, headers, order) == "ready_to_close"
    item = list_item(client, headers, order)
    assert item["completed_equipment_count"] == 1 and item["equipment_count"] == 1
    with factory() as db:
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "lab_work_order.ready_to_close"))
        assert audit.new_values == {"status": "ready_to_close"} and audit.previous_values == {"status": "in_progress"}


def test_a_pending_equipment_keeps_the_order_open_and_the_counter_exact(sg3):
    client, _factory, headers = sg3
    order, [first, second, third], _ = order_with_reports(client, headers, count=3)
    for equipment in (first, second, third):
        finalize(client, headers, order, equipment)
    assert deliver(client, headers, order).status_code == 201
    for equipment in (first, third):
        assert run_finalize(client, headers, order, equipment).status_code == 200
    assert order_status(client, headers, order) == "in_progress"
    assert list_item(client, headers, order)["completed_equipment_count"] == 2
    detail = assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_INCOMPLETE")
    assert [item["equipment_id"] for item in detail["items"]] == [second["id"]]
    assert run_finalize(client, headers, order, second).status_code == 200
    assert order_status(client, headers, order) == "ready_to_close"
    assert list_item(client, headers, order)["completed_equipment_count"] == 3


def test_inactive_equipment_does_not_block(sg3):
    client, factory, headers = sg3
    order, [first, second], _ = order_with_reports(client, headers, count=2)
    finalize(client, headers, order, first)
    with factory() as db:
        db.get(LabWorkOrderEquipment, second["id"]).is_active = False
        db.commit()
    assert deliver(client, headers, order).status_code == 201
    assert run_finalize(client, headers, order, first).status_code == 200
    assert order_status(client, headers, order) == "ready_to_close"
    assert list_item(client, headers, order)["completed_equipment_count"] == 1


def test_partial_delivery_counts_only_the_delivered_equipment(sg3):
    client, factory, headers = sg3
    order, [first, second], _ = order_with_reports(client, headers, count=2)
    finalize(client, headers, order, first)
    finalize(client, headers, order, second)
    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={"work_order_id": order["id"], "requested_equipment_ids": [first["id"]], "reason": "Urgente", "description": "Cliente la requiere"},
        headers=headers,
    ).json()
    with factory() as db:
        db.get(OperationalTicket, ticket["id"]).status = "approved"
        db.commit()
    assert client.post(f"{BASE}/{order['id']}/delivery/partial/{ticket['id']}", json=delivery_payload(), headers=headers).status_code == 201
    assert run_finalize(client, headers, order, first).status_code == 200
    # El segundo equipo aún no está entregado: su reporte final exige entrega.
    assert run_finalize(client, headers, order, second).status_code == 409
    assert order_status(client, headers, order) == "in_progress"
    assert list_item(client, headers, order)["completed_equipment_count"] == 1
    assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_INCOMPLETE")
    assert deliver(client, headers, order).status_code == 201
    assert run_finalize(client, headers, order, second).status_code == 200
    assert order_status(client, headers, order) == "ready_to_close"


def test_voiding_the_backing_delivery_revokes_readiness_and_blocks_close(sg3):
    client, factory, headers = sg3
    order, [equipment], _ = ready_chain(client, headers)
    with factory() as db:
        delivery_id = db.scalar(select(LabWorkOrderDelivery.id))
    from app.core.security import create_access_token
    from app.models.user import Role, User

    with factory() as db:
        role = Role(name="Administrador", description="Administrador")
        db.add(role)
        db.flush()
        admin = User(
            username="lab-admin", email="lab-admin@example.test", full_name="LAB admin", hashed_password="unused",
            account_type="internal", status="active", is_active=True, role_id=role.id, roles=[role],
        )
        db.add(admin)
        db.commit()
        token = create_access_token(str(admin.id), extra_claims={"roles": ["Administrador"], "auth_context": "internal"})
    admin_headers = {"Authorization": f"Bearer {token}"}
    voided = client.post(f"{BASE}/{order['id']}/delivery/{delivery_id}/void", json={"reason": "Error de captura"}, headers=admin_headers)
    assert voided.status_code == 200, voided.text
    assert order_status(client, headers, order) == "in_progress"
    assert list_item(client, headers, order)["completed_equipment_count"] == 0
    # El PDF final se generó con esa entrega: ahora exige revisión (SG-4J), no una entrega nueva.
    detail = assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_REVISION_REQUIRED")
    assert "revisión" in detail["message"]
    with factory() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "lab_work_order.ready_to_close_revoked")) is not None


def test_non_current_report_does_not_count(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = ready_chain(client, headers)
    with factory() as db:
        db.get(TechnicalReport, report["id"]).is_current = False
        db.commit()
    assert list_item(client, headers, order)["completed_equipment_count"] == 0
    assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_INCOMPLETE")


def test_missing_or_corrupt_final_pdf_blocks_the_close_without_regenerating(sg3, isolated_storage):
    client, factory, headers = sg3
    order, [equipment], [report] = ready_chain(client, headers)
    with factory() as db:
        path = isolated_storage / db.get(TechnicalReport, report["id"]).final_pdf_path
    original = path.read_bytes()
    path.write_bytes(original + b"corrupt")
    detail = assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_DOCUMENT_INVALID")
    assert "SHA-256" in detail["items"][0]["reason"]
    path.unlink()
    detail = assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_DOCUMENT_INVALID")
    assert "no está disponible" in detail["items"][0]["reason"]
    assert not path.exists(), "no se regenera automáticamente"
    # El listado usa la verificación barata (no re-hashea archivos); el cierre sí verifica.
    with factory() as db:
        assert db.get(TechnicalReport, report["id"]).status == "completed"


# --------------------------------------------------------------- /complete

def test_complete_closes_a_general_service_order_without_field_sheets_or_metrological_data(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = ready_chain(client, headers)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(FieldSheet)) == 0
        assert db.get(LabWorkOrderEquipment, equipment["id"]).service_type is None
        sha_before = db.get(TechnicalReport, report["id"]).final_pdf_sha256
    response = complete(client, headers, order)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    with factory() as db:
        stored = db.get(LabWorkOrder, order["id"])
        assert stored.completed_at is not None and stored.final_pdf and stored.final_pdf_sha256
        assert db.get(TechnicalReport, report["id"]).final_pdf_sha256 == sha_before, "el reporte no se toca"
        assert db.scalar(select(func.count()).select_from(FieldSheet)) == 0
        assert db.scalar(select(AuditLog).where(AuditLog.action == "lab_work_order.group_completed")) is not None
    # Idempotencia histórica: un segundo /complete devuelve la OT ya cerrada.
    again = complete(client, headers, order)
    assert again.status_code == 200 and again.json()["status"] == "completed"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "lab_work_order.group_completed")) == 1


def test_complete_re_validates_even_if_the_status_is_stale_ready_to_close(sg3):
    client, factory, headers = sg3
    order, [equipment], _ = ready_chain(client, headers)
    assert order_status(client, headers, order) == "ready_to_close"
    with factory() as db:
        db.scalar(select(LabWorkOrderDelivery)).status = "voided"  # sin pasar por la anulación oficial
        db.commit()
    assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_REVISION_REQUIRED")
    with factory() as db:
        assert db.get(LabWorkOrder, order["id"]).status == "ready_to_close"  # nada se cerró


def test_complete_heals_a_missed_transition_when_everything_is_in_place(sg3):
    client, factory, headers = sg3
    order, [equipment], _ = ready_chain(client, headers)
    with factory() as db:
        db.get(LabWorkOrder, order["id"]).status = "in_progress"
        db.commit()
    assert complete(client, headers, order).json()["status"] == "completed"


def test_close_permissions_are_preserved(sg3):
    client, factory, headers = sg3
    order, [equipment], _ = ready_chain(client, headers)
    _with_context(factory, {"mobile.access"}, actor_type="internal")
    try:
        assert complete(client, headers, order).status_code == 403
    finally:
        reset_override()
    assert order_status(client, headers, order) == "ready_to_close"


def test_the_work_order_pdf_prints_the_installation_report_folio(sg3):
    client, factory, headers = sg3
    order, equipments, reports = closed_order_for_pdf(client, headers)
    pdf = client.get(f"{BASE}/{order['id']}/pdf", headers=headers)
    assert pdf.status_code == 200, pdf.text
    import io
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf.content)).pages)
    for report in reports:
        assert report["folio"] in text, "el N° de informe de cada equipo es el folio MYC-IN del reporte"
    assert "None" not in text


def closed_order_for_pdf(client, headers):
    order, equipments, reports = ready_chain(client, headers, count=2)
    assert complete(client, headers, order).status_code == 200
    return order, equipments, reports
