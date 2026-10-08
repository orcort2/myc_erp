"""SG-4F: Servicio General se integra con la entrega LAB existente
(LabWorkOrderDelivery / LabDeliveryItem). Elegibilidad category-aware: un
equipo de Servicio General sólo se entrega con su TechnicalReport vigente en
`ready_for_signatures` (captura finalizada). Las firmas viven en la entrega."""

from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import func, select

from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.operational_ticket import OperationalTicket
from app.models.technical_report import TechnicalReport
from app.models.audit_log import AuditLog
from app.services.technical_reports import CLIENT_CONFORMITY_TEXT_INSTALLATION
from test_lab_general_service_equipment import (  # noqa: F401  (fixture sg3 reutilizada)
    BASE,
    PNG_DATA_URL,
    _with_context,
    create_order,
    general_equipment,
    sg3,
    sign_reception,
)
from test_technical_report_confirmation import COMPLETE, reset_override  # noqa: F401
from test_technical_report_installation import (  # noqa: F401
    image_bytes,
    isolated_storage,
    patch_capture,
    report_url,
)


def delivery_payload(**extra) -> dict:
    return {
        "delivery_method": "direct",
        "delivered_by_signature_data_url": PNG_DATA_URL,
        "recipient_name": "Persona Recibe",
        "recipient_signature_data_url": PNG_DATA_URL,
        "notes": None,
        **extra,
    }


def deliver(client, headers, order, payload: dict | None = None):
    return client.post(f"{BASE}/{order['id']}/delivery", json=payload or delivery_payload(), headers=headers)


def delivery_status(client, headers, order) -> dict:
    response = client.get(f"{BASE}/{order['id']}/delivery", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def order_with_reports(client, headers, count: int = 1):
    """OT general_service con recepción firmada, `count` equipos y un
    TechnicalReport draft por equipo."""
    order = create_order(client, headers, operational_category="general_service")
    equipments = [general_equipment(client, headers, order["id"], index) for index in range(1, count + 1)]
    assert sign_reception(client, headers, order["id"]).status_code == 200
    reports = []
    for equipment in equipments:
        created = client.post(report_url(order["id"], equipment["id"]), json={"report_type": "installation"}, headers=headers)
        assert created.status_code == 201, created.text
        reports.append(created.json())
    return order, equipments, reports


def capture(client, headers, order, equipment):
    assert patch_capture(client, headers, order, equipment, COMPLETE).status_code == 200


def finalize(client, headers, order, equipment):
    capture(client, headers, order, equipment)
    response = client.post(report_url(order["id"], equipment["id"], "/confirm-capture"), headers=headers)
    assert response.status_code == 200, response.text


def pending_by_equipment(client, headers, order) -> dict[int, dict]:
    return {item["equipment_id"]: item for item in delivery_status(client, headers, order)["pending_equipment"]}


# --------------------------------------------------------------- elegibilidad

def test_equipment_without_a_technical_report_is_not_eligible(sg3):
    client, _factory, headers = sg3
    order = create_order(client, headers, operational_category="general_service")
    equipment = general_equipment(client, headers, order["id"])
    assert sign_reception(client, headers, order["id"]).status_code == 200
    item = pending_by_equipment(client, headers, order)[equipment["id"]]
    assert item["delivery_eligible"] is False and item["delivery_blocked_reason"] == "Sin reporte técnico"
    response = deliver(client, headers, order)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "LAB_DELIVERY_REPORT_NOT_READY"


def test_draft_and_in_progress_reports_are_not_eligible(sg3):
    client, _factory, headers = sg3
    order, [equipment], _reports = order_with_reports(client, headers)
    for stage in ("draft", "in_progress"):
        if stage == "in_progress":
            capture(client, headers, order, equipment)
        item = pending_by_equipment(client, headers, order)[equipment["id"]]
        assert item["delivery_eligible"] is False, stage
        assert item["delivery_blocked_reason"] == "El reporte técnico aún no está finalizado"
        assert deliver(client, headers, order).status_code == 409, stage


def test_cancelled_report_is_not_eligible(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    with factory() as db:
        db.get(TechnicalReport, report["id"]).status = "cancelled"
        db.commit()
    assert pending_by_equipment(client, headers, order)[equipment["id"]]["delivery_eligible"] is False
    assert deliver(client, headers, order).status_code == 409


def test_a_report_that_is_not_current_does_not_make_the_equipment_eligible(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    with factory() as db:
        db.get(TechnicalReport, report["id"]).is_current = False
        db.commit()
    item = pending_by_equipment(client, headers, order)[equipment["id"]]
    assert item["delivery_eligible"] is False and item["delivery_blocked_reason"] == "Sin reporte técnico"
    assert deliver(client, headers, order).status_code == 409


def test_ready_report_is_eligible_and_exposes_the_frozen_conformity(sg3):
    client, _factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    item = pending_by_equipment(client, headers, order)[equipment["id"]]
    assert item["delivery_eligible"] is True and item["delivery_blocked_reason"] is None
    assert item["technical_report_folio"] == report["folio"]
    assert item["client_conformity_text"] == CLIENT_CONFORMITY_TEXT_INSTALLATION


# --------------------------------------------------------------- entrega

def test_valid_delivery_persists_signatures_and_items_in_the_delivery_not_the_report(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    response = deliver(client, headers, order)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["delivery_type"] == "full" and body["recipient_name"] == "Persona Recibe"
    assert [item["equipment_id"] for item in body["items"]] == [equipment["id"]]
    assert body["items"][0]["certificate_folio_snapshot"] == report["folio"]
    with factory() as db:
        delivery = db.scalar(select(LabWorkOrderDelivery))
        assert delivery.delivered_by_signature_data_url == PNG_DATA_URL
        assert delivery.recipient_signature_data_url == PNG_DATA_URL
        assert delivery.delivered_by.full_name == "LAB tech" and delivery.status == "completed"
        assert [item.equipment_id for item in db.scalars(select(LabDeliveryItem))] == [equipment["id"]]
        stored = db.get(TechnicalReport, report["id"])
        # El reporte NO se completa ni recibe firmas propias por la entrega.
        assert stored.status == "ready_for_signatures"
        assert stored.signature_session_id is None and stored.completed_at is None and stored.final_pdf_path is None
        assert stored.client_conformity_text_snapshot == CLIENT_CONFORMITY_TEXT_INSTALLATION
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "lab_work_order.delivery_completed"))
        assert audit.new_values["technical_report_ids"] == [report["id"]]
    # Entrega registrada: el equipo ya no está pendiente y la OT no se cierra sola.
    status = delivery_status(client, headers, order)
    assert status["pending_equipment"] == [] and status["group_complete"] is True
    assert client.get(f"{BASE}/{order['id']}", headers=headers).json()["status"] == "in_progress"


def test_the_delivery_voucher_pdf_is_still_generated(sg3):
    client, _factory, headers = sg3
    order, [equipment], _ = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    delivery = deliver(client, headers, order).json()
    assert delivery["voucher_available"] is True
    pdf = client.get(f"{BASE}/{order['id']}/delivery/{delivery['id']}/pdf", headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert client.get(f"{BASE}/{order['id']}/delivery/final-receipt/pdf", headers=headers).status_code == 200


def test_full_delivery_is_blocked_while_any_pending_equipment_is_not_ready(sg3):
    client, factory, headers = sg3
    order, [ready, in_capture], _ = order_with_reports(client, headers, count=2)
    finalize(client, headers, order, ready)
    capture(client, headers, order, in_capture)
    response = deliver(client, headers, order)
    assert response.status_code == 409
    assert [item["equipment_id"] for item in response.json()["detail"]["items"]] == [in_capture["id"]]
    with factory() as db:
        assert db.scalar(select(LabWorkOrderDelivery)) is None


def test_partial_delivery_of_ready_equipment_leaves_the_rest_pending(sg3):
    client, factory, headers = sg3
    order, [first, second, third], _ = order_with_reports(client, headers, count=3)
    finalize(client, headers, order, first)
    finalize(client, headers, order, second)
    capture(client, headers, order, third)
    # La solicitud sólo admite equipos con reporte finalizado.
    blocked = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={"work_order_id": order["id"], "requested_equipment_ids": [third["id"]], "reason": "Urgente", "description": "Cliente la requiere"},
        headers=headers,
    )
    assert blocked.status_code == 409 and blocked.json()["detail"]["code"] == "LAB_DELIVERY_REPORT_NOT_READY"
    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={"work_order_id": order["id"], "requested_equipment_ids": [first["id"]], "reason": "Urgente", "description": "Cliente la requiere"},
        headers=headers,
    )
    assert ticket.status_code in (200, 201), ticket.text
    with factory() as db:
        row = db.get(OperationalTicket, ticket.json()["id"])
        row.status = "approved"
        db.commit()
    executed = client.post(f"{BASE}/{order['id']}/delivery/partial/{ticket.json()['id']}", json=delivery_payload(), headers=headers)
    assert executed.status_code == 201, executed.text
    assert executed.json()["delivery_type"] == "partial"
    assert [item["equipment_id"] for item in executed.json()["items"]] == [first["id"]]
    status = delivery_status(client, headers, order)
    assert status["delivered_equipment"] == 1 and status["total_equipment"] == 3 and status["group_complete"] is False
    pending = {item["equipment_id"]: item for item in status["pending_equipment"]}
    assert set(pending) == {second["id"], third["id"]}, "el entregado no vuelve a aparecer"
    assert pending[second["id"]]["delivery_eligible"] is True and pending[third["id"]]["delivery_eligible"] is False
    with factory() as db:
        assert all(report.status == "ready_for_signatures" for report in db.scalars(select(TechnicalReport)) if report.lab_equipment_id != third["id"])


def test_partial_execution_re_checks_report_eligibility(sg3):
    client, factory, headers = sg3
    order, [first, second], reports = order_with_reports(client, headers, count=2)
    finalize(client, headers, order, first)
    finalize(client, headers, order, second)
    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={"work_order_id": order["id"], "requested_equipment_ids": [first["id"]], "reason": "Urgente", "description": "Cliente la requiere"},
        headers=headers,
    ).json()
    with factory() as db:
        db.get(OperationalTicket, ticket["id"]).status = "approved"
        db.get(TechnicalReport, reports[0]["id"]).status = "cancelled"
        db.commit()
    assert client.post(f"{BASE}/{order['id']}/delivery/partial/{ticket['id']}", json=delivery_payload(), headers=headers).status_code == 409
    with factory() as db:
        assert db.scalar(select(LabWorkOrderDelivery)) is None


# --------------------------------------------------------------- permisos / calibración

def test_delivery_permissions_are_preserved(sg3):
    client, factory, headers = sg3
    order, [equipment], _ = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    for permissions, actor in (
        ({"mobile.access"}, "internal"),
        ({"mobile.access", "technical_reports.capture"}, "internal"),
        ({"mobile.access", "lab_work_orders.use"}, "client"),
    ):
        _with_context(factory, permissions, actor_type=actor)
        try:
            assert deliver(client, headers, order).status_code == 403
        finally:
            reset_override()
    with factory() as db:
        assert db.scalar(select(LabWorkOrderDelivery)) is None


def test_field_sheet_capture_permission_is_not_what_authorizes_general_service_delivery(sg3):
    client, factory, headers = sg3
    order, [equipment], _ = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    _with_context(factory, {"mobile.access", "field_sheets.capture"}, actor_type="internal")
    try:
        assert deliver(client, headers, order).status_code == 403
    finally:
        reset_override()


def test_calibration_delivery_rules_are_unchanged(sg3):
    client, factory, headers = sg3
    order = create_order(client, headers)  # calibration
    # Sigue exigiendo OT cerrada y no consulta TechnicalReports.
    response = deliver(client, headers, order)
    assert response.status_code == 409
    assert "cerradas" in response.json()["detail"]
    status = delivery_status(client, headers, order)
    assert all(item["delivery_eligible"] is True and item["technical_report_folio"] is None for item in status["pending_equipment"])


# --------------------------------------------------------------- SG-4I: reporte completado no se reentrega

def _admin_headers(factory):
    from app.core.security import create_access_token
    from app.models.user import Role, User

    with factory() as db:
        role = Role(name="Administrador", description="Administrador")
        db.add(role)
        db.flush()
        user = User(username="lab-admin", email="lab-admin@example.test", full_name="LAB admin", hashed_password="unused",
                    account_type="internal", status="active", is_active=True, role_id=role.id, roles=[role])
        db.add(user)
        db.commit()
        token = create_access_token(str(user.id), extra_claims={"roles": ["Administrador"], "auth_context": "internal"})
    return {"Authorization": f"Bearer {token}"}


def test_a_completed_report_is_not_redeliverable_after_its_delivery_is_voided(sg3, isolated_storage):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    assert deliver(client, headers, order).status_code == 201
    assert client.post(report_url(order["id"], equipment["id"], "/finalize"), headers=headers).status_code == 200
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        before = (stored.status, stored.revision_number, stored.final_pdf_sha256, stored.final_pdf_path, stored.document_snapshot["delivery"]["delivery_id"])
        pdf_bytes = (isolated_storage / stored.final_pdf_path).read_bytes()
        delivery_id = db.scalar(select(LabWorkOrderDelivery.id))
    voided = client.post(f"{BASE}/{order['id']}/delivery/{delivery_id}/void", json={"reason": "Error de captura"}, headers=_admin_headers(factory))
    assert voided.status_code == 200, voided.text
    # El equipo vuelve a pendiente pero NO es elegible.
    item = pending_by_equipment(client, headers, order)[equipment["id"]]
    assert item["delivery_eligible"] is False and "revisión" in item["delivery_blocked_reason"]
    response = deliver(client, headers, order)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "TECHNICAL_REPORT_REVISION_REQUIRED" and "revisión del reporte" in detail["message"]
    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={"work_order_id": order["id"], "requested_equipment_ids": [equipment["id"]], "reason": "Urgente", "description": "Cliente la requiere"},
        headers=headers,
    )
    assert ticket.status_code == 409 and ticket.json()["detail"]["code"] == "TECHNICAL_REPORT_REVISION_REQUIRED"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(LabWorkOrderDelivery)) == 1, "no se creó una entrega nueva"
        stored = db.get(TechnicalReport, report["id"])
        assert (stored.status, stored.revision_number, stored.final_pdf_sha256, stored.final_pdf_path, stored.document_snapshot["delivery"]["delivery_id"]) == before
        assert (isolated_storage / stored.final_pdf_path).read_bytes() == pdf_bytes, "el PDF original sigue intacto"
        assert hashlib.sha256(pdf_bytes).hexdigest() == stored.final_pdf_sha256
