"""SG-4J-A1: modelo TechnicalIntervention, vínculos con entregas, compatibilidad
con Instalación y backfill histórico (lógica de la migración a4b7c1d9e3f2)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import IntegrityError

from app.models.audit_log import AuditLog
from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.technical_intervention import TechnicalIntervention, TechnicalInterventionDelivery
from app.models.technical_report import TechnicalReport, TechnicalReportEvidence
from app.services import technical_reports
from test_general_service_closure import complete, ready_chain  # noqa: F401
from test_general_service_delivery import (  # noqa: F401  (fixtures y helpers reutilizados)
    BASE,
    capture,
    deliver,
    delivery_payload,
    finalize,
    isolated_storage,
    order_with_reports,
    report_url,
    sg3,
)
from test_technical_report_installation import image_bytes, upload  # noqa: F401

_MIGRATION = Path(__file__).parents[1] / "migrations/versions/a4b7c1d9e3f2_add_technical_interventions.py"
_spec = importlib.util.spec_from_file_location("sg4j_a1_migration", _MIGRATION)
migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migration)


@pytest.fixture()
def legacy_schema():
    """Estado previo a SG-4J-A3 (intervention_id nullable) para simular datos
    anteriores a la migración de backfill. Debe instanciarse ANTES de `sg3`."""
    from app.core.db import Base

    column = Base.metadata.tables["technical_reports"].c.intervention_id
    column.nullable = True
    try:
        yield
    finally:
        column.nullable = False


def row(id, equipment=1, report_type="installation", folio=None, status="draft", revision=1, current=True, supersedes=None):
    return SimpleNamespace(
        id=id, lab_equipment_id=equipment, report_type=report_type, folio=folio or f"MYC-IN10-26-{id:04d}",
        status=status, revision_number=revision, is_current=current, supersedes_report_id=supersedes,
        intervention_id=None, document_snapshot=None, created_at=None,
    )


# --------------------------------------------------------------- cadenas históricas (lógica pura)

def test_a_chain_r1_to_r3_is_reconstructed_in_order_and_isolated_from_other_equipment():
    rows = [
        row(3, revision=3, supersedes=2),
        row(1, revision=1, current=False),
        row(2, revision=2, current=False, supersedes=1),
        row(9, equipment=7, folio="MYC-IN10-26-0009"),
    ]
    chains = migration.build_chains(rows)
    assert [[report.id for report in chain] for chain in chains] == [[1, 2, 3], [9]]


@pytest.mark.parametrize("rows, message", [
    ([row(1, supersedes=1)], "a sí mismo"),
    ([row(1, supersedes=99)], "no existe"),
    ([row(1, current=False), row(2, supersedes=1, revision=2), row(3, supersedes=1, revision=2)], "varias revisiones sucesoras"),
    ([row(1, supersedes=2, revision=2), row(2, supersedes=1)], "ciclo sin raíz"),
    ([row(1, current=False), row(2, equipment=5, supersedes=1, revision=2)], "mezcla equipos"),
    ([row(1, current=False), row(2, report_type="repair", supersedes=1, revision=2)], "mezcla tipos"),
    ([row(1, current=False), row(2, supersedes=1, revision=3)], "no consecutivas"),
    ([row(1), row(2, supersedes=1, revision=2)], "varias revisiones vigentes"),
    ([row(1, current=True), row(2, supersedes=1, revision=2, current=False)], "no es la última"),
])
def test_corrupt_historical_chains_are_rejected_not_repaired(rows, message):
    with pytest.raises(migration.InconsistentTechnicalReportChain, match=message):
        migration.build_chains(rows)


# --------------------------------------------------------------- modelo + creación transparente

def test_creating_a_report_creates_its_intervention_with_the_same_folio(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        intervention = db.get(TechnicalIntervention, stored.intervention_id)
        assert intervention.folio == stored.folio == report["folio"]
        assert intervention.intervention_type == "installation" and intervention.status == "open"
        assert intervention.lab_equipment_id == equipment["id"] and intervention.created_by_user_id is not None
        assert [item.id for item in intervention.reports] == [stored.id] and intervention.current_report.id == stored.id
        # El flujo actual de Instalación sigue intacto.
        assert db.get(type(stored.lab_equipment), equipment["id"]).current_technical_report.id == stored.id
    assert client.get(report_url(order["id"], equipment["id"]), headers=headers).json()["folio"] == report["folio"]


def test_one_equipment_can_hold_several_interventions_but_a_revision_number_is_unique_per_intervention(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    with factory() as db:
        first = db.get(TechnicalIntervention, db.get(TechnicalReport, report["id"]).intervention_id)
        second = TechnicalIntervention(
            lab_equipment_id=equipment["id"], intervention_type="installation", folio="MYC-IN10-26-7777", status="open",
        )
        db.add(second)
        db.commit()  # mismo equipo y mismo tipo: permitido a nivel de modelo
        assert db.scalar(select(func.count()).select_from(TechnicalIntervention)) == 2
        # Una segunda "revisión 1" de la misma intervención viola la unicidad.
        original = db.get(TechnicalReport, report["id"])
        db.add(TechnicalReport(
            intervention_id=first.id, lab_equipment_id=equipment["id"], report_type="installation", folio="MYC-IN10-26-8888",
            status="draft", capture_values={}, revision_number=original.revision_number, is_current=False,
        ))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_delivery_links_cover_several_interventions_history_and_the_exact_pdf_delivery(sg3):
    client, factory, headers = sg3
    order, equipments, reports = ready_chain(client, headers, count=2)
    with factory() as db:
        delivery_id = db.scalar(select(LabWorkOrderDelivery.id))
        links = list(db.scalars(select(TechnicalInterventionDelivery).order_by(TechnicalInterventionDelivery.id)))
        assert len(links) == 2 and {link.delivery_id for link in links} == {delivery_id}, "varias intervenciones, una entrega"
        for link in links:
            report = db.get(TechnicalReport, link.technical_report_id)
            assert report.intervention_id == link.intervention_id
            assert report.document_snapshot["delivery"]["delivery_id"] == link.delivery_id, "el vínculo coincide con el snapshot del PDF"
            assert link.delivery_item_id is not None
            assert db.get(TechnicalIntervention, link.intervention_id).status == "completed"


def test_voided_deliveries_keep_their_links(sg3):
    client, factory, headers = sg3
    from test_general_service_package import admin_headers

    order, [equipment], [report] = ready_chain(client, headers)
    with factory() as db:
        delivery_id = db.scalar(select(LabWorkOrderDelivery.id))
    assert client.post(f"{BASE}/{order['id']}/delivery/{delivery_id}/void", json={"reason": "Error"}, headers=admin_headers(factory)).status_code == 200
    with factory() as db:
        link = db.scalar(select(TechnicalInterventionDelivery))
        assert link.delivery_id == delivery_id and db.get(LabWorkOrderDelivery, delivery_id).status == "voided"


def test_deleting_a_draft_removes_its_intervention_but_the_folio_stays_consumed(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    assert client.post(report_url(order["id"], equipment["id"], "/delete-draft"), headers=headers).status_code == 200
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(TechnicalIntervention)) == 0
        assert db.scalar(select(func.count()).select_from(TechnicalReport)) == 0
    again = client.post(report_url(order["id"], equipment["id"]), json={"report_type": "installation"}, headers=headers).json()
    assert again["folio"] != report["folio"]
    with factory() as db:
        assert db.scalar(select(TechnicalIntervention.folio)) == again["folio"]


def test_retyping_keeps_the_intervention_in_sync(sg3, monkeypatch):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    monkeypatch.setattr(technical_reports, "ENABLED_TECHNICAL_REPORT_TYPES", {"installation", "verification"})
    monkeypatch.setitem(technical_reports.TECHNICAL_REPORT_SEQUENCE_PREFIXES, "verification", "MYC-VE")
    done = client.post(report_url(order["id"], equipment["id"], "/change-type"), json={"report_type": "verification"}, headers=headers)
    assert done.status_code == 200, done.text
    with factory() as db:
        intervention = db.scalar(select(TechnicalIntervention))
        stored = db.get(TechnicalReport, report["id"])
        assert (intervention.intervention_type, intervention.folio) == ("verification", stored.folio)


# --------------------------------------------------------------- backfill (lógica de la migración)

def _legacy_state(factory):
    """Simula el estado previo a la migración: reportes sin intervención y sin
    tablas nuevas pobladas. Devuelve la foto de lo que NO debe cambiar."""
    with factory() as db:
        before = _documents_snapshot(db)
        db.execute(update(TechnicalReport).values(intervention_id=None))
        db.execute(delete(TechnicalInterventionDelivery))
        db.execute(delete(TechnicalIntervention))
        db.commit()
    return before


def _documents_snapshot(db) -> dict:
    reports = {
        report.id: (
            report.folio, report.revision_number, report.status, report.is_current, report.final_pdf_path,
            report.final_pdf_sha256, report.pdf_renderer_version, report.completed_at, report.document_snapshot,
            report.capture_values, report.client_conformity_text_snapshot,
        )
        for report in db.scalars(select(TechnicalReport))
    }
    evidence = {item.id: (item.technical_report_id, item.sha256, item.storage_path, item.position) for item in db.scalars(select(TechnicalReportEvidence))}
    deliveries = {item.id: (item.status, item.delivery_method, item.recipient_name, item.voucher_pdf_sha256) for item in db.scalars(select(LabWorkOrderDelivery))}
    return {"reports": reports, "evidence": evidence, "deliveries": deliveries}


def run_backfill(factory) -> dict:
    with factory() as db:
        result = migration.backfill(db.connection())
        db.commit()
    return result


def test_backfill_creates_one_intervention_per_installation_preserving_every_document(legacy_schema, sg3, isolated_storage):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    capture(client, headers, order, equipment)
    assert upload(client, headers, order, equipment, content=image_bytes()).status_code == 201
    finalize(client, headers, order, equipment)
    assert deliver(client, headers, order).status_code == 201
    assert client.post(report_url(order["id"], equipment["id"], "/finalize"), headers=headers).status_code == 200
    audits_before = None
    with factory() as db:
        audits_before = db.scalar(select(func.count()).select_from(AuditLog))
    before = _legacy_state(factory)
    result = run_backfill(factory)
    assert result == {"interventions": 1, "reports": 1, "delivery_links": 1}
    with factory() as db:
        after = _documents_snapshot(db)
        assert after == before, "folios, PDFs, SHA, evidencias, capturas y entregas no cambian"
        stored = db.get(TechnicalReport, report["id"])
        intervention = db.get(TechnicalIntervention, stored.intervention_id)
        assert intervention.folio == report["folio"] and intervention.status == "completed"
        assert intervention.created_by_user_id is not None, "el actor sale de la auditoría de creación"
        link = db.scalar(select(TechnicalInterventionDelivery))
        assert link.technical_report_id == stored.id and link.delivery_id == stored.document_snapshot["delivery"]["delivery_id"]
        assert db.scalar(select(func.count()).select_from(AuditLog)) == audits_before, "no se escribe auditoría ni se toca la existente"
        assert db.execute(text("PRAGMA foreign_key_check")).all() == []


def test_backfill_handles_reports_without_revision_history_or_delivery(legacy_schema, sg3):
    client, factory, headers = sg3
    order, [first, second], [r1, r2] = order_with_reports(client, headers, count=2)
    capture(client, headers, order, first)
    _legacy_state(factory)
    result = run_backfill(factory)
    assert result == {"interventions": 2, "reports": 2, "delivery_links": 0}
    with factory() as db:
        assert {i.status for i in db.scalars(select(TechnicalIntervention))} == {"open"}
        assert db.scalar(select(func.count()).select_from(TechnicalReport).where(TechnicalReport.intervention_id.is_(None))) == 0


def test_backfill_is_deterministic_and_resumable(legacy_schema, sg3):
    client, factory, headers = sg3
    order, equipments, reports = ready_chain(client, headers, count=2)
    _legacy_state(factory)
    first = run_backfill(factory)
    with factory() as db:
        mapping = {r.id: (r.intervention_id) for r in db.scalars(select(TechnicalReport))}
    second = run_backfill(factory)  # reanudar/repetir no duplica nada
    assert first["interventions"] == 2 and second == {"interventions": 0, "reports": 2, "delivery_links": 0}
    with factory() as db:
        assert {r.id: r.intervention_id for r in db.scalars(select(TechnicalReport))} == mapping
        assert db.scalar(select(func.count()).select_from(TechnicalIntervention)) == 2
        assert db.scalar(select(func.count()).select_from(TechnicalInterventionDelivery)) == 2
