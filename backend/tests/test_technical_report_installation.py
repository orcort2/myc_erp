"""SG-4A/B/C: captura versionada del reporte de Instalación (capture_values),
autosave por PATCH y evidencia fotográfica (almacenamiento administrado)."""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from app.core.config import settings
from app.models.lab_work_order import LabWorkOrder
from app.models.technical_report import TechnicalReport, TechnicalReportEvidence
from app.schemas.technical_report_installation import (
    INSTALLATION_V1_FIELDS,
    InstallationCaptureValues,
    installation_missing_fields,
)
from test_lab_general_service_equipment import (  # noqa: F401  (fixture sg3 reutilizada)
    BASE,
    _with_context,
    create_order,
    equipment_body,
    general_equipment,
    sg3,
    sign_reception,
)
from app.main import app


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    return tmp_path


def report_url(order_id: int, equipment_id: int, suffix: str = "") -> str:
    return f"{BASE}/{order_id}/equipment/{equipment_id}/technical-report{suffix}"


def open_report(client, headers, *, index: int = 1):
    order = create_order(client, headers, operational_category="general_service")
    equipment = general_equipment(client, headers, order["id"], index)
    assert sign_reception(client, headers, order["id"]).status_code == 200
    created = client.post(report_url(order["id"], equipment["id"]), json={"report_type": "installation"}, headers=headers)
    assert created.status_code == 201, created.text
    return order, equipment, created.json()


def image_bytes(fmt: str = "JPEG", size: tuple[int, int] = (64, 48)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (30, 120, 200)).save(buffer, format=fmt)
    return buffer.getvalue()


def upload(client, headers, order, equipment, *, content: bytes, name="foto.jpg", mime="image/jpeg", evidence_type="before", caption=None):
    data = {"evidence_type": evidence_type}
    if caption is not None:
        data["caption"] = caption
    return client.post(
        report_url(order["id"], equipment["id"], "/evidence"),
        data=data,
        files={"file": (name, content, mime)},
        headers=headers,
    )


def patch_capture(client, headers, order, equipment, values: dict):
    return client.patch(report_url(order["id"], equipment["id"]), json={"capture_values": values}, headers=headers)


# ------------------------------------------------------------------ contrato

def test_installation_v1_contract_is_the_exact_closed_field_list():
    assert INSTALLATION_V1_FIELDS == (
        "installation_date", "installation_location", "initial_condition", "installation_description",
        "activities_performed", "has_incidents", "incident_description", "corrective_action",
        "functional_test_performed", "effectiveness_result", "effectiveness_description",
        "effectiveness_notes", "final_observations",
    )
    assert tuple(InstallationCaptureValues.model_fields) == INSTALLATION_V1_FIELDS
    # Nada de snapshot/folio dentro de capture_values.
    assert not {"client", "work_order", "equipment", "brand", "model", "serial_number", "identification", "folio"} & set(INSTALLATION_V1_FIELDS)


def test_full_validation_rules_for_confirming_the_capture():
    empty = InstallationCaptureValues()
    assert "installation_date" in installation_missing_fields(empty)
    assert "has_incidents" in installation_missing_fields(empty)

    complete = dict(
        installation_date="2026-10-08", installation_location="Planta", initial_condition="Empacado",
        installation_description="Se instaló", activities_performed="Nivelación", has_incidents=False,
        functional_test_performed=False,
    )
    assert installation_missing_fields(InstallationCaptureValues(**complete)) == []
    assert installation_missing_fields(InstallationCaptureValues(**{**complete, "has_incidents": True})) == ["incident_description"]
    with_incident = InstallationCaptureValues(**{**complete, "has_incidents": True, "incident_description": "Tubería dañada"})
    assert installation_missing_fields(with_incident) == []
    functional = InstallationCaptureValues(**{**complete, "functional_test_performed": True})
    assert installation_missing_fields(functional) == ["effectiveness_result"]


# ------------------------------------------------------------------ captura

def test_incomplete_draft_is_saved_and_merged_and_promotes_to_in_progress(sg3):
    client, factory, headers = sg3
    order, equipment, report = open_report(client, headers)
    assert report["status"] == "draft" and report["capture_values"] == {}

    first = patch_capture(client, headers, order, equipment, {"installation_location": "  Planta Norte  "})
    assert first.status_code == 200, first.text
    assert first.json()["capture_values"] == {"installation_location": "Planta Norte"}
    assert first.json()["status"] == "in_progress"

    second = patch_capture(client, headers, order, equipment, {"has_incidents": False, "installation_date": "2026-10-08"})
    assert second.json()["capture_values"] == {
        "installation_location": "Planta Norte", "has_incidents": False, "installation_date": "2026-10-08",
    }
    cleared = patch_capture(client, headers, order, equipment, {"installation_location": None})
    assert "installation_location" not in cleared.json()["capture_values"]


def test_empty_patch_does_not_promote_the_report(sg3):
    client, _factory, headers = sg3
    order, equipment, _report = open_report(client, headers)
    response = patch_capture(client, headers, order, equipment, {})
    assert response.status_code == 200
    assert response.json()["status"] == "draft"


def test_has_incidents_false_allows_empty_incident_fields(sg3):
    client, _factory, headers = sg3
    order, equipment, _report = open_report(client, headers)
    response = patch_capture(client, headers, order, equipment, {"has_incidents": False})
    assert response.status_code == 200
    stored = response.json()["capture_values"]
    assert "incident_description" not in stored and "corrective_action" not in stored


def test_unknown_fields_and_invalid_enum_are_rejected(sg3):
    client, _factory, headers = sg3
    order, equipment, _report = open_report(client, headers)
    for values in (
        {"campo_inventado": "x"},
        {"client_name": "Cliente duplicado"},  # snapshot: no pertenece a capture_values
        {"serial_number": "S-1"},
        {"effectiveness_result": "excelente"},
        {"installation_date": "no-es-fecha"},
        {"has_incidents": "quizá"},
    ):
        response = patch_capture(client, headers, order, equipment, values)
        assert response.status_code == 422, (values, response.text)


def test_no_effectiveness_result_without_a_functional_test(sg3):
    client, _factory, headers = sg3
    order, equipment, _report = open_report(client, headers)
    ok = patch_capture(client, headers, order, equipment, {"functional_test_performed": True, "effectiveness_result": "satisfactory"})
    assert ok.status_code == 200
    # Cambiar a "no se hizo prueba" con un resultado vigente es inconsistente.
    assert patch_capture(client, headers, order, equipment, {"functional_test_performed": False}).status_code == 422
    assert patch_capture(
        client, headers, order, equipment, {"functional_test_performed": False, "effectiveness_result": None}
    ).status_code == 200


@pytest.mark.parametrize(
    "authority",
    [
        {"folio": "MYC-IN99-26-9999"}, {"status": "completed"}, {"report_type": "repair"},
        {"revision_number": 7}, {"signature_session_id": 1}, {"final_pdf_path": "x.pdf"},
        {"performed_by_user_id": 1}, {"completed_at": "2026-10-08T00:00:00Z"}, {"is_current": False},
    ],
)
def test_patch_cannot_touch_authority_fields(sg3, authority):
    client, factory, headers = sg3
    order, equipment, report = open_report(client, headers)
    response = client.patch(
        report_url(order["id"], equipment["id"]),
        json={"capture_values": {"installation_location": "Planta"}, **authority},
        headers=headers,
    )
    assert response.status_code == 422, response.text
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        assert stored.folio == report["folio"] and stored.status == "draft"
        assert stored.capture_values == {} and stored.revision_number == 1


@pytest.mark.parametrize("blocked", ["ready_for_signatures", "completed", "cancelled"])
def test_capture_and_evidence_are_only_editable_in_draft_or_in_progress(sg3, blocked):
    client, factory, headers = sg3
    order, equipment, report = open_report(client, headers)
    assert upload(client, headers, order, equipment, content=image_bytes()).status_code == 201
    with factory() as db:
        db.get(TechnicalReport, report["id"]).status = blocked
        db.commit()
    assert patch_capture(client, headers, order, equipment, {"installation_location": "X"}).status_code == 409
    assert upload(client, headers, order, equipment, content=image_bytes()).status_code == 409
    evidence_id = client.get(report_url(order["id"], equipment["id"]), headers=headers).json()["evidence"][0]["id"]
    assert client.delete(report_url(order["id"], equipment["id"], f"/evidence/{evidence_id}"), headers=headers).status_code == 409


def test_capture_requires_capture_permission_and_internal_actor(sg3):
    client, factory, headers = sg3
    order, equipment, _report = open_report(client, headers)
    for permissions, actor in (({"mobile.access", "technical_reports.read"}, "internal"), ({"mobile.access"}, "internal"),
                               ({"mobile.access", "technical_reports.capture"}, "client")):
        _with_context(factory, permissions, actor_type=actor)
        assert patch_capture(client, headers, order, equipment, {"installation_location": "X"}).status_code == 403
        assert upload(client, headers, order, equipment, content=image_bytes()).status_code == 403
    app.dependency_overrides.pop(__import__("app.core.mobile.security", fromlist=["get_mobile_context"]).get_mobile_context, None)


# ------------------------------------------------------------------ evidencia

def test_jpeg_and_png_evidence_are_stored_with_real_sha_size_and_position(sg3, isolated_storage):
    client, factory, headers = sg3
    order, equipment, report = open_report(client, headers)
    jpeg, png = image_bytes("JPEG"), image_bytes("PNG")
    first = upload(client, headers, order, equipment, content=jpeg, evidence_type="before", caption=" Antes ")
    second = upload(client, headers, order, equipment, content=png, name="otra.png", mime="image/png", evidence_type="after")
    assert first.status_code == 201 and second.status_code == 201, (first.text, second.text)
    assert (first.json()["position"], second.json()["position"]) == (1, 2)
    assert first.json()["sha256"] == hashlib.sha256(jpeg).hexdigest()
    assert first.json()["size_bytes"] == len(jpeg)
    assert first.json()["mime_type"] == "image/jpeg" and second.json()["mime_type"] == "image/png"
    assert first.json()["caption"] == "Antes" and first.json()["evidence_type"] == "before"
    with factory() as db:
        rows = list(db.scalars(select(TechnicalReportEvidence).order_by(TechnicalReportEvidence.position)))
        assert [row.evidence_type for row in rows] == ["before", "after"]
        for row in rows:
            assert row.storage_path.startswith(f"technical-reports/{report['id']}/evidence/")
            assert "foto" not in row.storage_path and "otra" not in row.storage_path  # el nombre del usuario no es autoridad
            assert (isolated_storage / row.storage_path).read_bytes() in (jpeg, png)
        assert db.get(TechnicalReport, report["id"]).status == "in_progress"  # primera captura real


def test_evidence_validation_rejects_bad_content(sg3):
    client, _factory, headers = sg3
    order, equipment, _report = open_report(client, headers)
    assert upload(client, headers, order, equipment, content=image_bytes(), mime="image/gif").status_code == 415
    assert upload(client, headers, order, equipment, content=b"%PDF-1.4 no es imagen", name="a.pdf", mime="application/pdf").status_code == 415
    assert upload(client, headers, order, equipment, content=b"no soy una imagen", mime="image/jpeg").status_code == 415
    assert upload(client, headers, order, equipment, content=image_bytes("PNG"), name="falsa.jpg", mime="image/jpeg").status_code == 415
    assert upload(client, headers, order, equipment, content=b"", mime="image/jpeg").status_code == 422
    assert upload(client, headers, order, equipment, content=image_bytes(), name="../../x.jpg").status_code == 422
    assert upload(client, headers, order, equipment, content=image_bytes(), evidence_type="portada").status_code == 422
    oversized = b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024)
    assert upload(client, headers, order, equipment, content=oversized).status_code == 413
    refreshed = client.get(report_url(order["id"], equipment["id"]), headers=headers).json()
    assert refreshed["evidence"] == [] and refreshed["status"] == "draft"


def test_delete_removes_the_file_and_recompacts_positions(sg3, isolated_storage):
    client, factory, headers = sg3
    order, equipment, _report = open_report(client, headers)
    ids = [upload(client, headers, order, equipment, content=image_bytes(size=(64 + n, 48))).json()["id"] for n in range(3)]
    with factory() as db:
        middle_path = isolated_storage / db.get(TechnicalReportEvidence, ids[1]).storage_path
    assert middle_path.exists()
    response = client.delete(report_url(order["id"], equipment["id"], f"/evidence/{ids[1]}"), headers=headers)
    assert response.status_code == 200, response.text
    remaining = response.json()["evidence"]
    assert [(item["id"], item["position"]) for item in remaining] == [(ids[0], 1), (ids[2], 2)]
    assert not middle_path.exists()
    # Siguiente alta continúa la secuencia compacta.
    assert upload(client, headers, order, equipment, content=image_bytes(size=(90, 48))).json()["position"] == 3
    assert client.delete(report_url(order["id"], equipment["id"], f"/evidence/{ids[1]}"), headers=headers).status_code == 404


def test_evidence_is_scoped_to_the_route_report(sg3):
    client, _factory, headers = sg3
    order_a, equipment_a, _ = open_report(client, headers)
    order_b, equipment_b, _ = open_report(client, headers, index=2)
    mine = upload(client, headers, order_a, equipment_a, content=image_bytes()).json()["id"]
    # Evidencia de A inalcanzable desde la ruta de B (borrado y descarga).
    assert client.delete(report_url(order_b["id"], equipment_b["id"], f"/evidence/{mine}"), headers=headers).status_code == 404
    assert client.get(report_url(order_b["id"], equipment_b["id"], f"/evidence/{mine}/file"), headers=headers).status_code == 404
    # Equipo ajeno a la OT de la ruta.
    assert upload(client, headers, order_a, equipment_b, content=image_bytes()).status_code == 404
    assert client.get(report_url(order_a["id"], equipment_a["id"], f"/evidence/{mine}/file"), headers=headers).status_code == 200


def test_evidence_limit_per_report(sg3):
    client, _factory, headers = sg3
    order, equipment, _report = open_report(client, headers)
    tiny = image_bytes(size=(8, 8))
    for _ in range(20):
        assert upload(client, headers, order, equipment, content=tiny).status_code == 201
    assert upload(client, headers, order, equipment, content=tiny).status_code == 409


def test_read_only_can_download_but_not_modify_and_no_permission_cannot_read(sg3):
    client, factory, headers = sg3
    order, equipment, _report = open_report(client, headers)
    evidence = upload(client, headers, order, equipment, content=image_bytes()).json()
    file_url = report_url(order["id"], equipment["id"], f"/evidence/{evidence['id']}/file")
    _with_context(factory, {"mobile.access", "technical_reports.read"})
    downloaded = client.get(file_url, headers=headers)
    assert downloaded.status_code == 200 and downloaded.headers["content-type"] == "image/jpeg"
    assert client.delete(report_url(order["id"], equipment["id"], f"/evidence/{evidence['id']}"), headers=headers).status_code == 403
    _with_context(factory, {"mobile.access"})
    assert client.get(file_url, headers=headers).status_code == 403
    app.dependency_overrides.pop(__import__("app.core.mobile.security", fromlist=["get_mobile_context"]).get_mobile_context, None)
