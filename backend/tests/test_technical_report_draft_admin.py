"""SG-4I-A: eliminar un borrador de reporte y cambiar su tipo (sólo editable)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.technical_report import TechnicalReport, TechnicalReportEvidence
from app.services import technical_reports
from test_general_service_delivery import (  # noqa: F401  (fixtures y helpers reutilizados)
    BASE,
    COMPLETE,
    _with_context,
    capture,
    deliver,
    finalize,
    isolated_storage,
    order_with_reports,
    report_url,
    reset_override,
    sg3,
)
from test_technical_report_installation import image_bytes, upload  # noqa: F401


def delete_url(order, equipment) -> str:
    return report_url(order["id"], equipment["id"], "/delete-draft")


def discard(client, headers, order, equipment):
    return client.post(delete_url(order, equipment), headers=headers)


def sequence(factory) -> int:
    with factory() as db:
        return db.scalar(select(InstitutionalFolioSequence.next_value).where(InstitutionalFolioSequence.document_type == "technical_report"))


def evidence_files(storage: Path) -> list[Path]:
    root = storage / "technical-reports"
    return [path for path in root.rglob("*") if path.is_file()] if root.exists() else []


@pytest.mark.parametrize("state", ["draft", "in_progress"])
def test_editable_drafts_can_be_deleted(sg3, state):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    if state == "in_progress":
        capture(client, headers, order, equipment)
    response = discard(client, headers, order, equipment)
    assert response.status_code == 200, response.text
    assert response.json() == {"technical_report_id": report["id"], "folio": report["folio"], "report_type": "installation"}
    with factory() as db:
        assert db.get(TechnicalReport, report["id"]) is None
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "technical_report.draft_deleted"))
        assert audit.previous_values["folio"] == report["folio"] and audit.previous_values["status"] == state
    # El equipo vuelve a "sin reporte" y se puede abrir uno nuevo.
    assert client.get(report_url(order["id"], equipment["id"]), headers=headers).status_code == 404
    projected = client.get(f"{BASE}/{order['id']}", headers=headers).json()["equipment"][-1]
    assert projected["technical_report_id"] is None and projected["technical_report_status"] is None
    assert client.post(report_url(order["id"], equipment["id"]), json={"report_type": "installation"}, headers=headers).status_code == 201


def test_evidence_rows_and_files_are_removed(sg3, isolated_storage):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    for kind in ("before", "after"):
        assert upload(client, headers, order, equipment, content=image_bytes(), evidence_type=kind).status_code == 201
    assert len(evidence_files(isolated_storage)) == 2
    assert discard(client, headers, order, equipment).status_code == 200
    assert evidence_files(isolated_storage) == []
    with factory() as db:
        assert db.scalar(select(TechnicalReportEvidence)) is None


def test_the_issued_folio_is_consumed_and_never_reassigned(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    consumed = sequence(factory)
    assert discard(client, headers, order, equipment).status_code == 200
    assert sequence(factory) == consumed, "la secuencia no se decrementa"
    again = client.post(report_url(order["id"], equipment["id"]), json={"report_type": "installation"}, headers=headers).json()
    assert again["folio"] != report["folio"]
    assert sequence(factory) == consumed + 1


@pytest.mark.parametrize("blocked", ["ready_for_signatures", "completed", "cancelled"])
def test_non_editable_reports_cannot_be_deleted(sg3, blocked):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    with factory() as db:
        db.get(TechnicalReport, report["id"]).status = blocked
        db.commit()
    assert discard(client, headers, order, equipment).status_code == 409
    with factory() as db:
        assert db.get(TechnicalReport, report["id"]) is not None


def test_a_delivery_or_a_final_pdf_blocks_deletion(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    assert deliver(client, headers, order).status_code == 201
    with factory() as db:
        db.get(TechnicalReport, report["id"]).status = "in_progress"  # estado editable pero con entrega
        db.commit()
    response = discard(client, headers, order, equipment)
    assert response.status_code == 409 and "entrega" in response.json()["detail"]
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        stored.final_pdf_path = "technical-reports/x/final/x.pdf"
        db.commit()
    assert discard(client, headers, order, equipment).status_code == 409


def test_permissions_scope_and_currency(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    for permissions, actor in (
        ({"mobile.access", "technical_reports.read"}, "internal"),
        ({"mobile.access"}, "internal"),
        ({"mobile.access", "technical_reports.capture"}, "client"),
    ):
        _with_context(factory, permissions, actor_type=actor)
        try:
            assert discard(client, headers, order, equipment).status_code == 403
        finally:
            reset_override()
    other_order, [other_equipment], _ = order_with_reports(client, headers)
    assert client.post(delete_url(order, other_equipment), headers=headers).status_code == 404, "equipo de otra OT"
    with factory() as db:
        db.get(TechnicalReport, report["id"]).is_current = False
        db.commit()
    assert discard(client, headers, order, equipment).status_code == 404, "reporte no vigente"


# --------------------------------------------------------------- cambio de tipo

def retype(client, headers, order, equipment, report_type: str, **extra):
    return client.post(report_url(order["id"], equipment["id"], "/change-type"), json={"report_type": report_type, **extra}, headers=headers)


def test_retype_to_unavailable_types_is_rejected_and_nothing_changes(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    capture(client, headers, order, equipment)
    for target in ("verification", "repair", "maintenance", "sale"):
        response = retype(client, headers, order, equipment, target)
        assert response.status_code == 409 and response.json()["detail"]["code"] == "TECHNICAL_REPORT_TYPE_NOT_AVAILABLE"
    assert retype(client, headers, order, equipment, "installation").status_code == 409  # ya es de ese tipo
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        assert stored.report_type == "installation" and stored.folio == report["folio"] and stored.capture_values


def test_retype_is_ready_for_future_profiles_and_never_reinterprets_the_capture(sg3, isolated_storage, monkeypatch):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    capture(client, headers, order, equipment)
    assert upload(client, headers, order, equipment, content=image_bytes()).status_code == 201
    monkeypatch.setattr(technical_reports, "ENABLED_TECHNICAL_REPORT_TYPES", {"installation", "verification"})
    monkeypatch.setitem(technical_reports.TECHNICAL_REPORT_SEQUENCE_PREFIXES, "verification", "MYC-VE")
    # Con evidencias exige confirmación explícita y no borra nada en silencio.
    response = retype(client, headers, order, equipment, "verification")
    assert response.status_code == 409 and response.json()["detail"]["code"] == "TECHNICAL_REPORT_RETYPE_REQUIRES_CONFIRMATION"
    assert len(evidence_files(isolated_storage)) == 1
    done = retype(client, headers, order, equipment, "verification", confirm_discard_evidence=True)
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["report_type"] == "verification" and body["folio"].startswith("MYC-VE") and body["folio"] != report["folio"]
    assert body["capture_values"] == {} and body["status"] == "draft" and body["evidence"] == []
    assert evidence_files(isolated_storage) == []


def test_retype_rejects_finalized_reports(sg3, monkeypatch):
    client, factory, headers = sg3
    order, [equipment], _ = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    monkeypatch.setattr(technical_reports, "ENABLED_TECHNICAL_REPORT_TYPES", {"installation", "verification"})
    assert retype(client, headers, order, equipment, "verification").status_code == 409
