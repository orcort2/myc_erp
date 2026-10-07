"""SG-4G: PDF institucional del Reporte de Instalación y cierre documental
(`ready_for_signatures` + entrega vigente -> PDF final + `completed`)."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest
from pypdf import PdfReader
from sqlalchemy import select

from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.technical_report import TechnicalReport
from app.services import technical_reports
from app.services.technical_report_pdfs import INSTALLATION_REPORT_RENDERER_VERSION
from app.services.technical_reports import CLIENT_CONFORMITY_TEXT_INSTALLATION
from test_general_service_delivery import (  # noqa: F401  (fixtures y helpers reutilizados)
    BASE,
    COMPLETE,
    _with_context,
    capture,
    create_order,
    deliver,
    delivery_payload,
    delivery_status,
    finalize,
    isolated_storage,
    order_with_reports,
    patch_capture,
    report_url,
    reset_override,
    sg3,
)
from test_technical_report_installation import image_bytes, upload  # noqa: F401


def finalize_url(order, equipment) -> str:
    return report_url(order["id"], equipment["id"], "/finalize")


def pdf_url(order, equipment) -> str:
    return report_url(order["id"], equipment["id"], "/pdf")


def run_finalize(client, headers, order, equipment):
    return client.post(finalize_url(order, equipment), headers=headers)


def final_files(storage: Path, report_id: int) -> list[Path]:
    folder = storage / "technical-reports" / str(report_id) / "final"
    return sorted(folder.glob("*.pdf")) if folder.exists() else []


def delivered_report(client, headers, *, photos: dict[str, int] | None = None, extra: dict | None = None):
    """OT con un equipo, reporte finalizado (con fotos) y entrega registrada."""
    order, [equipment], [report] = order_with_reports(client, headers)
    values = {**COMPLETE, **(extra or {})}
    assert patch_capture(client, headers, order, equipment, values).status_code == 200
    for kind, count in (photos or {}).items():
        for index in range(count):
            size = (640 + 40 * index, 480 + 20 * index)
            response = upload(
                client, headers, order, equipment,
                content=image_bytes(size=size), evidence_type=kind, caption=f"{kind} {index + 1}",
            )
            assert response.status_code == 201, response.text
    confirmed = client.post(report_url(order["id"], equipment["id"], "/confirm-capture"), headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    assert deliver(client, headers, order).status_code == 201
    return order, equipment, report


# ------------------------------------------------------------ precondiciones

def test_finalize_requires_a_valid_delivery(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    response = run_finalize(client, headers, order, equipment)
    assert response.status_code == 409 and "entrega" in response.json()["detail"]
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        assert stored.status == "ready_for_signatures" and stored.final_pdf_path is None


def test_voided_delivery_is_rejected(sg3):
    client, factory, headers = sg3
    order, equipment, report = delivered_report(client, headers)
    with factory() as db:
        db.scalar(select(LabWorkOrderDelivery)).status = "voided"
        db.commit()
    assert run_finalize(client, headers, order, equipment).status_code == 409
    with factory() as db:
        assert db.get(TechnicalReport, report["id"]).status == "ready_for_signatures"


def test_delivery_that_does_not_include_the_equipment_is_rejected(sg3):
    client, factory, headers = sg3
    order, [first, second], _ = order_with_reports(client, headers, count=2)
    finalize(client, headers, order, first)
    finalize(client, headers, order, second)
    with factory() as db:
        # Entrega vigente que sólo incluye al primer equipo.
        ticket = client.post(
            "/api/mobile/v1/technician/tickets/partial-delivery",
            json={"work_order_id": order["id"], "requested_equipment_ids": [first["id"]], "reason": "Urgente", "description": "Cliente la requiere"},
            headers=headers,
        ).json()
        from app.models.operational_ticket import OperationalTicket

        db.get(OperationalTicket, ticket["id"]).status = "approved"
        db.commit()
    assert client.post(f"{BASE}/{order['id']}/delivery/partial/{ticket['id']}", json=delivery_payload(), headers=headers).status_code == 201
    assert run_finalize(client, headers, order, second).status_code == 409
    assert run_finalize(client, headers, order, first).status_code == 200


@pytest.mark.parametrize("state", ["draft", "in_progress"])
def test_unfinished_reports_cannot_be_finalized(sg3, state):
    client, _factory, headers = sg3
    order, [equipment], _ = order_with_reports(client, headers)
    if state == "in_progress":
        capture(client, headers, order, equipment)
    assert run_finalize(client, headers, order, equipment).status_code == 409


def test_non_current_report_and_other_report_types_are_rejected(sg3):
    client, factory, headers = sg3
    order, equipment, report = delivered_report(client, headers)
    with factory() as db:
        db.get(TechnicalReport, report["id"]).report_type = "repair"
        db.commit()
    assert run_finalize(client, headers, order, equipment).status_code == 409
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        stored.report_type = "installation"
        stored.is_current = False
        db.commit()
    assert run_finalize(client, headers, order, equipment).status_code == 404


def test_finalize_permissions(sg3):
    client, factory, headers = sg3
    order, equipment, report = delivered_report(client, headers)
    for permissions, actor in (
        ({"mobile.access", "technical_reports.read"}, "internal"),
        ({"mobile.access"}, "internal"),
        ({"mobile.access", "technical_reports.capture"}, "client"),
    ):
        _with_context(factory, permissions, actor_type=actor)
        try:
            assert run_finalize(client, headers, order, equipment).status_code == 403
        finally:
            reset_override()
    with factory() as db:
        assert db.get(TechnicalReport, report["id"]).status == "ready_for_signatures"


# ------------------------------------------------------------ éxito + snapshot

def test_finalize_completes_the_report_with_a_frozen_pdf(sg3, isolated_storage):
    client, factory, headers = sg3
    order, equipment, report = delivered_report(
        client, headers, photos={"before": 2, "during": 1, "after": 2},
        extra={"final_observations": "Todo quedó operando", "functional_test_performed": True,
               "effectiveness_result": "satisfactory_with_observations", "effectiveness_description": "Prueba de 30 min"},
    )
    response = run_finalize(client, headers, order, equipment)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed" and body["completed_at"] is not None
    assert body["pdf_renderer_version"] == INSTALLATION_REPORT_RENDERER_VERSION == 1
    assert body["folio"] == report["folio"] and body["revision_number"] == 1
    assert body["final_pdf_path"].startswith(f"technical-reports/{report['id']}/final/")
    [pdf_file] = final_files(isolated_storage, report["id"])
    content = pdf_file.read_bytes()
    assert hashlib.sha256(content).hexdigest() == body["final_pdf_sha256"]
    assert body["final_pdf_generated_at"] is not None
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        assert stored.status == "completed" and stored.signature_session_id is None
        snapshot = stored.document_snapshot
        delivery = db.scalar(select(LabWorkOrderDelivery))
        item = db.scalar(select(LabDeliveryItem))
        assert snapshot["document"]["folio"] == report["folio"] and snapshot["document"]["renderer_version"] == 1
        assert snapshot["work_order"]["folio"] == order["folio"] and snapshot["client"]["name"] == "Cliente SG"
        assert snapshot["equipment"]["serial_number"] == "SER-1"
        assert snapshot["capture_values"]["installation_location"] == "Planta Norte"
        assert snapshot["capture_values"]["effectiveness_result"] == "satisfactory_with_observations"
        assert snapshot["technician"]["performed_by_name_snapshot"] == "LAB tech"
        assert snapshot["client_conformity_text"] == CLIENT_CONFORMITY_TEXT_INSTALLATION
        assert snapshot["delivery"]["delivery_id"] == delivery.id and snapshot["delivery"]["delivery_item_id"] == item.id
        assert snapshot["delivery"]["recipient_name"] == "Persona Recibe" and snapshot["delivery"]["delivered_by_name"] == "LAB tech"
        assert len(snapshot["delivery"]["recipient_signature_sha256"]) == 64
        evidence = snapshot["evidence"]
        assert [(e["evidence_type"], e["position"]) for e in evidence] == [
            ("before", 1), ("before", 2), ("during", 3), ("after", 4), ("after", 5)
        ]
        assert all(len(e["sha256"]) == 64 and e["storage_path"] and e["mime_type"] == "image/jpeg" for e in evidence)
    # Descargable por la ruta de lectura.
    download = client.get(pdf_url(order, equipment), headers=headers)
    assert download.status_code == 200 and download.content == content
    assert download.headers["content-type"] == "application/pdf"
    assert f"Reporte-instalacion-{report['folio']}-r1.pdf" in download.headers["content-disposition"]


def test_pdf_content_is_the_institutional_installation_document(sg3):
    client, _factory, headers = sg3
    order, equipment, report = delivered_report(
        client, headers, photos={"before": 1, "during": 1, "incident": 1, "after": 1},
        extra={"has_incidents": True, "incident_description": "Tubería dañada", "corrective_action": "Se reemplazó",
               "functional_test_performed": True, "effectiveness_result": "unsatisfactory"},
    )
    assert run_finalize(client, headers, order, equipment).status_code == 200
    reader = PdfReader(io.BytesIO(client.get(pdf_url(order, equipment), headers=headers).content))
    text = "\n".join(page.extract_text() for page in reader.pages)
    for expected in (
        "REPORTE DE INSTALACIÓN", report["folio"], "Cliente SG", "Equipo 1", "SER-1", "Planta Norte",
        "Tubería dañada", "Se reemplazó", "No satisfactorio", CLIENT_CONFORMITY_TEXT_INSTALLATION[:40],
        "Entregado por", "Recibido por", "Persona Recibe", "LAB tech", "Evidencia inicial", "Evidencia final", "REVISIÓN",
    ):
        assert expected in text, expected
    assert "unsatisfactory" not in text and "satisfactory_with_observations" not in text
    images = [image for page in reader.pages for image in page.images]
    assert len(images) >= 6, "4 fotografías + 2 firmas"


def test_without_incidents_the_pdf_states_it_instead_of_an_empty_section(sg3):
    client, _factory, headers = sg3
    order, equipment, _ = delivered_report(client, headers)
    assert run_finalize(client, headers, order, equipment).status_code == 200
    reader = PdfReader(io.BytesIO(client.get(pdf_url(order, equipment), headers=headers).content))
    assert "No se reportaron incidencias durante la instalación." in " ".join(page.extract_text() for page in reader.pages)


def test_second_finalize_returns_the_same_document_without_regenerating(sg3, isolated_storage):
    client, factory, headers = sg3
    order, equipment, report = delivered_report(client, headers)
    first = run_finalize(client, headers, order, equipment).json()
    second = run_finalize(client, headers, order, equipment)
    assert second.status_code == 200
    assert second.json()["final_pdf_sha256"] == first["final_pdf_sha256"]
    assert second.json()["final_pdf_path"] == first["final_pdf_path"]
    # SQLite devuelve la fecha sin zona al releerla; el instante es el mismo.
    assert second.json()["final_pdf_generated_at"].rstrip("Z") == first["final_pdf_generated_at"].rstrip("Z")
    assert len(final_files(isolated_storage, report["id"])) == 1


def test_completed_report_is_not_affected_by_later_changes_and_stays_immutable(sg3):
    client, factory, headers = sg3
    order, equipment, report = delivered_report(client, headers)
    assert run_finalize(client, headers, order, equipment).status_code == 200
    before = client.get(pdf_url(order, equipment), headers=headers).content
    with factory() as db:
        from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment

        db.get(LabWorkOrder, order["id"]).client_name = "Otro Cliente"
        db.get(LabWorkOrderEquipment, equipment["id"]).instrument = "Otro equipo"
        db.commit()
    assert client.get(pdf_url(order, equipment), headers=headers).content == before
    assert patch_capture(client, headers, order, equipment, {"installation_location": "Otra"}).status_code == 409
    assert upload(client, headers, order, equipment, content=image_bytes()).status_code == 409


def test_pdf_is_not_available_until_the_report_is_completed(sg3):
    client, _factory, headers = sg3
    order, equipment, _ = delivered_report(client, headers)
    assert client.get(pdf_url(order, equipment), headers=headers).status_code == 404
    _with_context(sg3[1], {"mobile.access"}, actor_type="internal")
    try:
        assert client.get(pdf_url(order, equipment), headers=headers).status_code == 403
    finally:
        reset_override()


def test_delivery_voucher_and_calibration_are_unaffected(sg3):
    client, _factory, headers = sg3
    order, equipment, _ = delivered_report(client, headers)
    assert run_finalize(client, headers, order, equipment).status_code == 200
    status = delivery_status(client, headers, order)
    voucher = client.get(f"{BASE}/{order['id']}/delivery/{status['exhibitions'][0]['id']}/pdf", headers=headers)
    assert voucher.status_code == 200 and voucher.content.startswith(b"%PDF")
    assert client.get(f"{BASE}/{order['id']}", headers=headers).json()["status"] == "in_progress", "la OT no se cierra"
    calibration = create_order(client, headers)
    assert client.post(report_url(calibration["id"], 1, "/finalize"), headers=headers).status_code == 404


# ------------------------------------------------------------ atomicidad

def test_missing_evidence_file_rolls_everything_back(sg3, isolated_storage):
    client, factory, headers = sg3
    order, equipment, report = delivered_report(client, headers, photos={"before": 1})
    with factory() as db:
        path = db.get(TechnicalReport, report["id"]).evidence[0].storage_path
    (isolated_storage / path).unlink()
    response = run_finalize(client, headers, order, equipment)
    assert response.status_code == 409 and "evidencia" in response.json()["detail"]
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        assert stored.status == "ready_for_signatures" and stored.final_pdf_path is None and stored.completed_at is None
    assert final_files(isolated_storage, report["id"]) == []


def test_evidence_that_does_not_match_its_record_is_rejected(sg3, isolated_storage):
    client, factory, headers = sg3
    order, equipment, report = delivered_report(client, headers, photos={"before": 1})
    with factory() as db:
        path = db.get(TechnicalReport, report["id"]).evidence[0].storage_path
    (isolated_storage / path).write_bytes(image_bytes(size=(10, 10)))
    assert run_finalize(client, headers, order, equipment).status_code == 409
    with factory() as db:
        assert db.get(TechnicalReport, report["id"]).status == "ready_for_signatures"


def test_invalid_delivery_signature_rolls_back(sg3, isolated_storage):
    client, factory, headers = sg3
    order, equipment, report = delivered_report(client, headers)
    with factory() as db:
        db.scalar(select(LabWorkOrderDelivery)).recipient_signature_data_url = "data:image/png;base64,AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        db.commit()
    assert run_finalize(client, headers, order, equipment).status_code == 409
    with factory() as db:
        assert db.get(TechnicalReport, report["id"]).final_pdf_path is None
    assert final_files(isolated_storage, report["id"]) == []


def test_renderer_failure_rolls_back(sg3, isolated_storage, monkeypatch):
    client, factory, headers = sg3
    order, equipment, report = delivered_report(client, headers)

    def boom(*_args, **_kwargs):
        raise RuntimeError("renderer roto")

    monkeypatch.setattr(technical_reports, "render_installation_report_pdf", boom)
    with pytest.raises(RuntimeError):
        run_finalize(client, headers, order, equipment)
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        assert stored.status == "ready_for_signatures" and stored.final_pdf_path is None and stored.document_snapshot.get("document") is None
    assert final_files(isolated_storage, report["id"]) == []


def test_pdf_write_failure_rolls_back(sg3, isolated_storage, monkeypatch):
    client, factory, headers = sg3
    order, equipment, report = delivered_report(client, headers)

    def no_disk(**_kwargs):
        raise OSError("disco lleno")

    monkeypatch.setattr(technical_reports, "save_validated_content", no_disk)
    with pytest.raises(OSError):
        run_finalize(client, headers, order, equipment)
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        assert stored.status == "ready_for_signatures" and stored.final_pdf_path is None
    assert final_files(isolated_storage, report["id"]) == []


def test_failure_after_the_file_was_written_removes_the_file(sg3, isolated_storage, monkeypatch):
    client, factory, headers = sg3
    order, equipment, report = delivered_report(client, headers)
    original = technical_reports.save_validated_content
    written: list[Path] = []

    def spy(**kwargs):
        stored = original(**kwargs)
        written.append(stored.absolute_path)
        return stored

    def failing_audit(*_args, **_kwargs):
        raise RuntimeError("falla posterior a la escritura")

    monkeypatch.setattr(technical_reports, "save_validated_content", spy)
    monkeypatch.setattr(technical_reports, "write_audit_log", failing_audit)
    with pytest.raises(RuntimeError):
        run_finalize(client, headers, order, equipment)
    assert written and not written[0].exists(), "el archivo huérfano se eliminó"
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        assert stored.status == "ready_for_signatures" and stored.final_pdf_path is None and stored.final_pdf_sha256 is None
    assert final_files(isolated_storage, report["id"]) == []
