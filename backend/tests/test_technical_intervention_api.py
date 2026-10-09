"""SG-4J-A4: API por intervención (listar, detalle, alta explícita, revisiones,
cancelación) y política de los endpoints heredados por equipo con varias
intervenciones."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.technical_intervention import TechnicalIntervention, TechnicalInterventionDelivery
from app.models.technical_report import TechnicalReport
from test_general_service_closure import assert_general_service_error, complete, ready_chain  # noqa: F401
from test_general_service_delivery import (  # noqa: F401  (fixtures y helpers reutilizados)
    BASE,
    COMPLETE,
    _with_context,
    capture,
    create_order,
    deliver,
    finalize,
    general_equipment,
    isolated_storage,
    order_with_reports,
    report_url,
    reset_override,
    sg3,
    sign_reception,
)
from test_technical_report_installation import image_bytes, upload  # noqa: F401


def url(order, equipment, suffix: str = "") -> str:
    return f"{BASE}/{order['id']}/equipment/{equipment['id']}/technical-interventions{suffix}"


def create(client, headers, order, equipment, report_type="installation"):
    return client.post(url(order, equipment), json={"report_type": report_type}, headers=headers)


def listing(client, headers, order, equipment, **params):
    response = client.get(url(order, equipment), params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


# --------------------------------------------------------------- consulta

def test_list_and_detail_expose_state_type_folio_and_current_revision(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    items = listing(client, headers, order, equipment)
    assert len(items) == 1
    item = items[0]
    assert item["folio"] == report["folio"] and item["intervention_type"] == "installation" and item["status"] == "open"
    assert item["mandatory"] is True and item["lab_equipment_id"] == equipment["id"] and item["work_order_id"] == order["id"]
    assert item["revisions_count"] == 1 and item["created_by_user_id"] is not None
    revision = item["current_revision"]
    assert revision["id"] == report["id"] and revision["revision_number"] == 1 and revision["is_current"] and revision["status"] == "draft"
    assert revision["pdf_available"] is False and revision["delivery_id"] is None
    detail = client.get(url(order, equipment, f"/{item['id']}"), headers=headers).json()
    assert detail["id"] == item["id"] and detail["deliveries"] == []


def test_revisions_expose_documentary_metadata_and_the_exact_delivery(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = ready_chain(client, headers)
    [item] = listing(client, headers, order, equipment)
    [revision] = client.get(url(order, equipment, f"/{item['id']}/revisions"), headers=headers).json()
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        link = db.scalar(select(TechnicalInterventionDelivery))
    assert revision["final_pdf_sha256"] == stored.final_pdf_sha256 and revision["pdf_available"] is True
    assert revision["pdf_renderer_version"] == 1 and revision["status"] == "completed" and revision["completed_at"]
    assert revision["delivery_id"] == link.delivery_id == stored.document_snapshot["delivery"]["delivery_id"]
    detail = client.get(url(order, equipment, f"/{item['id']}"), headers=headers).json()
    assert detail["status"] == "completed" and detail["deliveries"][0]["technical_report_id"] == report["id"]
    assert detail["deliveries"][0]["delivery_status"] == "completed"
    assert "capture_values" not in revision and "evidence" not in revision, "sólo metadatos documentales"


def test_status_filter_and_isolation_between_orders_and_equipment(sg3):
    client, factory, headers = sg3
    order_a, [equipment_a], _ = order_with_reports(client, headers)
    order_b, [equipment_b], _ = order_with_reports(client, headers)
    [item_a] = listing(client, headers, order_a, equipment_a)
    assert listing(client, headers, order_a, equipment_a, status="cancelled") == []
    # Equipo de otra OT en la ruta; intervención de otro equipo; inexistente.
    assert client.get(url(order_a, equipment_b), headers=headers).status_code == 404
    assert client.get(url(order_b, equipment_b, f"/{item_a['id']}"), headers=headers).status_code == 404
    assert client.get(url(order_b, equipment_b, f"/{item_a['id']}/revisions"), headers=headers).status_code == 404
    assert client.get(url(order_a, equipment_a, "/999999"), headers=headers).status_code == 404
    assert client.post(url(order_b, equipment_b, f"/{item_a['id']}/cancel"), json={"reason": "no aplica"}, headers=headers).status_code == 404
    with factory() as db:
        assert db.get(TechnicalIntervention, item_a["id"]).status == "open"


# --------------------------------------------------------------- alta explícita

def test_creating_an_intervention_adds_a_new_folio_and_r1_without_touching_existing_reports(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    capture(client, headers, order, equipment)
    with factory() as db:
        before = db.get(TechnicalReport, report["id"])
        before_state = (before.folio, before.status, before.capture_values, before.revision_number, before.intervention_id, before.is_current)
    response = create(client, headers, order, equipment)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["intervention_type"] == "installation" and body["status"] == "open" and body["folio"] != report["folio"]
    assert body["revisions_count"] == 1 and body["current_revision"]["revision_number"] == 1 and body["current_revision"]["status"] == "draft"
    assert [item["id"] for item in listing(client, headers, order, equipment)][0] != body["id"]
    assert len(listing(client, headers, order, equipment)) == 2, "dos intervenciones del mismo tipo"
    with factory() as db:
        after = db.get(TechnicalReport, report["id"])
        assert (after.folio, after.status, after.capture_values, after.revision_number, after.intervention_id, after.is_current) == before_state
        assert db.scalar(select(func.count()).select_from(TechnicalReport)) == 2, "ninguna R2, ningún reporte histórico tocado"
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "technical_intervention.created", AuditLog.entity_id == body["id"]))
        assert audit.user_id is not None and audit.new_values["folio"] == body["folio"]


def test_creation_validates_category_state_type_and_equipment(sg3):
    client, factory, headers = sg3
    calibration = create_order(client, headers)  # calibración
    from test_lab_general_service_equipment import equipment_body

    cal_equipment = client.post(f"{BASE}/{calibration['id']}/equipment/configured", json={"equipment": equipment_body(1, service_type="accredited")}, headers=headers)
    # Calibración no admite intervenciones técnicas (409), con o sin equipo válido.
    assert client.post(f"{BASE}/{calibration['id']}/equipment/1/technical-interventions", json={"report_type": "installation"}, headers=headers).status_code in {404, 409}
    order = create_order(client, headers, operational_category="general_service")
    equipment = general_equipment(client, headers, order["id"])
    assert create(client, headers, order, equipment).status_code == 409, "sin recepción firmada"
    assert sign_reception(client, headers, order["id"]).status_code == 200
    unavailable = create(client, headers, order, equipment, "repair")
    assert unavailable.status_code == 409 and "no está habilitado" in unavailable.json()["detail"]
    assert client.post(url(order, equipment), json={"report_type": "otro"}, headers=headers).status_code == 422
    assert client.post(url(order, equipment), json={"report_type": "installation", "status": "completed"}, headers=headers).status_code == 422
    assert create(client, headers, order, equipment).status_code == 201


def test_folios_are_unique_and_the_sequence_never_goes_back(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    folios = [report["folio"]] + [create(client, headers, order, equipment).json()["folio"] for _ in range(3)]
    assert len(set(folios)) == 4 and folios == sorted(folios)


def test_the_new_intervention_blocks_delivery_until_it_is_ready_and_cancelling_it_unblocks(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    second = create(client, headers, order, equipment).json()
    blocked = deliver(client, headers, order)
    assert blocked.status_code == 409 and blocked.json()["detail"]["code"] == "LAB_DELIVERY_REPORT_NOT_READY"
    assert client.post(url(order, equipment, f"/{second['id']}/cancel"), json={"reason": "Alta por error"}, headers=headers).status_code == 200
    assert deliver(client, headers, order).status_code == 201


# --------------------------------------------------------------- cancelación y estados

def test_cancel_preserves_history_audits_and_stops_the_intervention_from_being_mandatory(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    second = create(client, headers, order, equipment).json()
    cancelled = client.post(url(order, equipment, f"/{second['id']}/cancel"), json={"reason": "Alta por error"}, headers=headers)
    assert cancelled.status_code == 200, cancelled.text
    body = cancelled.json()
    assert body["status"] == "cancelled" and body["mandatory"] is False and body["current_revision"]["status"] == "cancelled"
    assert [item["id"] for item in listing(client, headers, order, equipment, status="cancelled")] == [second["id"]], "el historial se conserva"
    with factory() as db:
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "technical_intervention.cancelled"))
        assert audit.user_id is not None and audit.previous_values["status"] == "open" and audit.new_values["reason"] == "Alta por error"
        assert db.get(TechnicalReport, second["current_revision"]["id"]).status == "cancelled"
    again = client.post(url(order, equipment, f"/{second['id']}/cancel"), json={"reason": "otra vez"}, headers=headers)
    assert again.status_code == 409
    assert client.post(url(order, equipment, f"/{second['id']}/cancel"), json={"reason": "x"}, headers=headers).status_code == 422


@pytest.mark.parametrize("stage", ["ready", "delivered", "completed"])
def test_only_interventions_in_capture_without_delivery_can_be_cancelled(sg3, stage):
    client, factory, headers = sg3
    if stage == "completed":
        order, [equipment], _ = ready_chain(client, headers)
    else:
        order, [equipment], _ = order_with_reports(client, headers)
        finalize(client, headers, order, equipment)
        if stage == "delivered":
            assert deliver(client, headers, order).status_code == 201
    [item] = listing(client, headers, order, equipment)
    response = client.post(url(order, equipment, f"/{item['id']}/cancel"), json={"reason": "No procede"}, headers=headers)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "TECHNICAL_INTERVENTION_NOT_CANCELLABLE"
    with factory() as db:
        assert db.get(TechnicalIntervention, item["id"]).status in {"open", "completed"}


def test_a_cancelled_intervention_never_blocks_the_close(sg3):
    client, factory, headers = sg3
    order, [equipment], _ = ready_chain(client, headers)
    # Se agrega y cancela otra intervención después de finalizar la primera.
    assert client.get(f"{BASE}/{order['id']}", headers=headers).json()["status"] == "ready_to_close"
    extra = create(client, headers, order, equipment).json()
    assert client.get(f"{BASE}/{order['id']}", headers=headers).json()["status"] == "in_progress", "la nueva intervención revoca ready_to_close"
    assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_INCOMPLETE")
    assert client.post(url(order, equipment, f"/{extra['id']}/cancel"), json={"reason": "Alta por error"}, headers=headers).status_code == 200
    assert complete(client, headers, order).status_code == 200


# --------------------------------------------------------------- permisos

def test_permissions_actor_and_scope(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    [item] = listing(client, headers, order, equipment)
    cases = [
        ({"mobile.access", "technical_reports.read"}, "internal", True, False),
        ({"mobile.access", "technical_reports.capture"}, "client", True, False),
        ({"mobile.access"}, "internal", False, False),
    ]
    for permissions, actor, can_read, can_write in cases:
        _with_context(factory, permissions, actor_type=actor)
        try:
            assert (client.get(url(order, equipment), headers=headers).status_code == 200) is can_read
            assert (client.get(url(order, equipment, f"/{item['id']}"), headers=headers).status_code == 200) is can_read
            assert (client.get(url(order, equipment, f"/{item['id']}/revisions"), headers=headers).status_code == 200) is can_read
            assert create(client, headers, order, equipment).status_code == 403
            assert client.post(url(order, equipment, f"/{item['id']}/cancel"), json={"reason": "No procede"}, headers=headers).status_code == 403
        finally:
            reset_override()
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(TechnicalIntervention)) == 1


# --------------------------------------------------------------- política de endpoints heredados

LEGACY_WRITES = [
    ("patch", "", {"capture_values": {"installation_location": "X"}}),
    ("post", "/confirm-capture", None),
    ("post", "/finalize", None),
    ("post", "/delete-draft", None),
    ("post", "/change-type", {"report_type": "verification"}),
]


def test_legacy_writes_are_refused_when_the_equipment_has_several_interventions(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    capture(client, headers, order, equipment)
    second = create(client, headers, order, equipment).json()
    for method, suffix, body in LEGACY_WRITES:
        response = getattr(client, method)(report_url(order["id"], equipment["id"], suffix), headers=headers, **({"json": body} if body else {}))
        assert response.status_code == 409 and response.json()["detail"]["code"] == "TECHNICAL_INTERVENTION_AMBIGUOUS", (method, suffix)
    evidence = upload(client, headers, order, equipment, content=image_bytes())
    assert evidence.status_code == 409 and evidence.json()["detail"]["code"] == "TECHNICAL_INTERVENTION_AMBIGUOUS"
    assert client.post(report_url(order["id"], equipment["id"]), json={"report_type": "installation"}, headers=headers).status_code == 409
    # La lectura heredada sigue resolviendo la intervención principal (la de menor id), sin cambios.
    body = client.get(report_url(order["id"], equipment["id"]), headers=headers).json()
    assert body["id"] == report["id"] and body["capture_values"]["installation_location"] == "Planta Norte"
    with factory() as db:  # nada se modificó
        assert db.get(TechnicalReport, report["id"]).capture_values["installation_location"] == "Planta Norte"
    # Cancelada la segunda, el flujo heredado vuelve a funcionar.
    assert client.post(url(order, equipment, f"/{second['id']}/cancel"), json={"reason": "Alta por error"}, headers=headers).status_code == 200
    assert client.post(report_url(order["id"], equipment["id"], "/confirm-capture"), headers=headers).status_code == 200


def test_legacy_flow_with_a_single_intervention_is_unchanged(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = ready_chain(client, headers)
    assert complete(client, headers, order).status_code == 200
    assert client.get(report_url(order["id"], equipment["id"]), headers=headers).json()["status"] == "completed"
