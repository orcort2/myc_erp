"""SG-4D/E: validación completa de Installation y confirmación de captura
(`in_progress -> ready_for_signatures`, técnico responsable, inmutabilidad)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.main import app
from app.models.technical_report import TechnicalReport
from app.models.user import User
from test_lab_general_service_equipment import (  # noqa: F401  (fixture sg3 reutilizada)
    BASE,
    _with_context,
    create_order,
    general_equipment,
    sg3,
    sign_reception,
)
from test_technical_report_installation import (  # noqa: F401
    image_bytes,
    isolated_storage,
    open_report,
    patch_capture,
    report_url,
    upload,
)

COMPLETE = {
    "installation_date": "2026-10-08",
    "installation_location": "Planta Norte",
    "initial_condition": "Equipo empacado",
    "installation_description": "Se instaló y niveló",
    "activities_performed": "Nivelación y conexión",
    "has_incidents": False,
    "functional_test_performed": False,
}


def confirm_url(order, equipment) -> str:
    return report_url(order["id"], equipment["id"], "/confirm-capture")


def confirm(client, headers, order, equipment):
    return client.post(confirm_url(order, equipment), headers=headers)


def ready_report(client, headers, extra: dict | None = None):
    order, equipment, report = open_report(client, headers)
    assert patch_capture(client, headers, order, equipment, {**COMPLETE, **(extra or {})}).status_code == 200
    return order, equipment, report


def reset_override():
    from app.core.mobile.security import get_mobile_context

    app.dependency_overrides.pop(get_mobile_context, None)


# ------------------------------------------------------------------ SG-4D

@pytest.mark.parametrize("missing", [
    "installation_date", "installation_location", "initial_condition",
    "installation_description", "activities_performed", "has_incidents", "functional_test_performed",
])
def test_each_required_field_blocks_confirmation(sg3, missing):
    client, factory, headers = sg3
    order, equipment, report = ready_report(client, headers)
    assert patch_capture(client, headers, order, equipment, {missing: None}).status_code == 200
    response = confirm(client, headers, order, equipment)
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "TECHNICAL_REPORT_INCOMPLETE"
    assert detail["missing_fields"] == [missing]
    assert detail["message"].startswith("Faltan: ")
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        assert stored.status == "in_progress" and stored.performed_by_user_id is None and stored.performed_at is None


def test_incidents_true_requires_a_description(sg3):
    client, _factory, headers = sg3
    order, equipment, _report = ready_report(client, headers, {"has_incidents": True})
    response = confirm(client, headers, order, equipment)
    assert response.status_code == 422
    assert response.json()["detail"]["missing_fields"] == ["incident_description"]
    assert patch_capture(client, headers, order, equipment, {"incident_description": "Tubería dañada"}).status_code == 200
    assert confirm(client, headers, order, equipment).status_code == 200


def test_incidents_false_is_rejected_when_incident_evidence_exists(sg3):
    client, factory, headers = sg3
    order, equipment, report = ready_report(client, headers, {"has_incidents": True, "incident_description": "Golpe"})
    assert upload(client, headers, order, equipment, content=image_bytes(), evidence_type="incident").status_code == 201
    # El autosave sí acepta el borrador contradictorio; la confirmación no.
    assert patch_capture(client, headers, order, equipment, {"has_incidents": False}).status_code == 200
    response = confirm(client, headers, order, equipment)
    assert response.status_code == 422, response.text
    assert "evidencias de incidencia" in response.json()["detail"]["message"]
    with factory() as db:
        assert db.get(TechnicalReport, report["id"]).status == "in_progress"


def test_functional_test_true_requires_an_effectiveness_result(sg3):
    client, _factory, headers = sg3
    order, equipment, _report = ready_report(client, headers, {"functional_test_performed": True})
    response = confirm(client, headers, order, equipment)
    assert response.status_code == 422
    assert response.json()["detail"]["missing_fields"] == ["effectiveness_result"]
    for value in ("satisfactory", "satisfactory_with_observations", "unsatisfactory"):
        assert patch_capture(client, headers, order, equipment, {"effectiveness_result": value}).status_code == 200
    assert confirm(client, headers, order, equipment).status_code == 200


def test_functional_test_false_cannot_keep_a_contradictory_result(sg3):
    client, factory, headers = sg3
    order, equipment, report = ready_report(client, headers)
    # Un valor contradictorio no puede entrar ni por autosave...
    assert patch_capture(client, headers, order, equipment, {"effectiveness_result": "satisfactory"}).status_code == 422
    # ...ni sobrevivir a la confirmación si llegara a la base por otra vía.
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        stored.capture_values = {**stored.capture_values, "effectiveness_result": "satisfactory"}
        db.commit()
    response = confirm(client, headers, order, equipment)
    assert response.status_code == 422, response.text
    assert "prueba funcional" in response.json()["detail"]["message"]
    with factory() as db:
        assert db.get(TechnicalReport, report["id"]).status == "in_progress"


# ------------------------------------------------------------------ SG-4E

def test_valid_confirmation_freezes_the_responsible_technician_and_changes_state(sg3):
    client, factory, headers = sg3
    order, equipment, report = ready_report(client, headers)
    response = confirm(client, headers, order, equipment)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready_for_signatures"
    assert body["performed_by_name_snapshot"] == "LAB tech"
    assert body["performed_at"] is not None
    assert body["folio"] == report["folio"] and body["revision_number"] == 1
    with factory() as db:
        user = db.scalar(select(User))
        stored = db.get(TechnicalReport, report["id"])
        assert stored.performed_by_user_id == user.id
        assert stored.completed_at is None and stored.signature_session_id is None and stored.final_pdf_path is None
    # Lo proyecta la OT.
    projected = client.get(f"{BASE}/{order['id']}", headers=headers).json()["equipment"][-1]
    assert projected["technical_report_status"] == "ready_for_signatures"


def test_responsible_technician_is_the_authenticated_actor_not_the_work_order_creator(sg3):
    client, factory, headers = sg3
    order, equipment, report = ready_report(client, headers)
    with factory() as db:
        from app.models.user import Role

        role = db.scalar(select(Role))
        other = User(
            username="otro-tecnico", email="otro@example.test", full_name="Otro Técnico",
            hashed_password="unused", account_type="internal", status="active", is_active=True,
            role_id=role.id, roles=[role],
        )
        db.add(other)
        db.commit()
        other_id = other.id
    from app.core.mobile.security import MobileSecurityContext, get_mobile_context

    with factory() as db:
        other_user = db.get(User, other_id)
    app.dependency_overrides[get_mobile_context] = lambda: MobileSecurityContext(
        user=other_user, actor_type="internal", permissions=frozenset({"mobile.access", "technical_reports.capture"}), client_id=None
    )
    try:
        response = confirm(client, headers, order, equipment)
    finally:
        reset_override()
    assert response.status_code == 200, response.text
    assert response.json()["performed_by_name_snapshot"] == "Otro Técnico"
    with factory() as db:
        assert db.get(TechnicalReport, report["id"]).performed_by_user_id == other_id


def test_a_second_confirmation_does_not_mutate_again(sg3):
    client, factory, headers = sg3
    order, equipment, report = ready_report(client, headers)
    first = confirm(client, headers, order, equipment).json()
    second = confirm(client, headers, order, equipment)
    assert second.status_code == 409
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        assert stored.performed_at.replace(tzinfo=None) == __import__("datetime").datetime.fromisoformat(first["performed_at"]).replace(tzinfo=None)
        assert stored.status == "ready_for_signatures"


def test_after_confirmation_everything_is_immutable(sg3):
    client, factory, headers = sg3
    order, equipment, report = ready_report(client, headers)
    photo = upload(client, headers, order, equipment, content=image_bytes()).json()
    assert confirm(client, headers, order, equipment).status_code == 200
    assert patch_capture(client, headers, order, equipment, {"installation_location": "Otra"}).status_code == 409
    assert upload(client, headers, order, equipment, content=image_bytes()).status_code == 409
    assert client.delete(report_url(order["id"], equipment["id"], f"/evidence/{photo['id']}"), headers=headers).status_code == 409
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        assert stored.status == "ready_for_signatures"
        assert stored.capture_values["installation_location"] == "Planta Norte"
        assert stored.folio == report["folio"] and stored.report_type == "installation" and stored.revision_number == 1
        assert len(stored.evidence) == 1


def test_draft_reports_cannot_be_confirmed(sg3):
    client, _factory, headers = sg3
    order, equipment, _report = open_report(client, headers)
    response = confirm(client, headers, order, equipment)
    assert response.status_code == 409
    assert "Aún no hay captura" in response.json()["detail"]


@pytest.mark.parametrize("blocked", ["completed", "cancelled"])
def test_non_editable_states_cannot_be_confirmed(sg3, blocked):
    client, factory, headers = sg3
    order, equipment, report = ready_report(client, headers)
    with factory() as db:
        db.get(TechnicalReport, report["id"]).status = blocked
        db.commit()
    assert confirm(client, headers, order, equipment).status_code == 409


def test_confirmation_requires_internal_actor_and_capture_permission(sg3):
    client, factory, headers = sg3
    order, equipment, report = ready_report(client, headers)
    for permissions, actor in (
        ({"mobile.access", "technical_reports.read"}, "internal"),
        ({"mobile.access"}, "internal"),
        ({"mobile.access", "technical_reports.capture"}, "client"),
    ):
        _with_context(factory, permissions, actor_type=actor)
        try:
            assert confirm(client, headers, order, equipment).status_code == 403
        finally:
            reset_override()
    with factory() as db:
        assert db.get(TechnicalReport, report["id"]).status == "in_progress"


def test_confirmation_is_scoped_to_the_route_current_report(sg3):
    client, factory, headers = sg3
    order_a, equipment_a, _ = ready_report(client, headers)
    order_b, equipment_b, report_b = open_report(client, headers, index=2)
    # Equipo de otra OT en la ruta -> no alcanzable.
    assert client.post(report_url(order_a["id"], equipment_b["id"], "/confirm-capture"), headers=headers).status_code == 404
    # Reporte que ya no es el vigente del equipo -> no hay nada que confirmar.
    assert patch_capture(client, headers, order_b, equipment_b, {**COMPLETE}).status_code == 200
    with factory() as db:
        db.get(TechnicalReport, report_b["id"]).is_current = False
        db.commit()
    assert confirm(client, headers, order_b, equipment_b).status_code == 404
    # El otro reporte vigente no se vio afectado.
    assert confirm(client, headers, order_a, equipment_a).status_code == 200
