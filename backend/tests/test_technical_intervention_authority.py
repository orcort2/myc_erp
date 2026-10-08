"""SG-4J-A2: autoridad técnica por intervención (obligatoriedad, revisión vigente,
entregas que la respaldan, cierre, entrega y paquete). Sin cambiar la
experiencia: hoy una intervención por equipo, un reporte vigente por intervención."""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from pypdf import PdfReader
from sqlalchemy import delete, event, select

from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.technical_intervention import TechnicalIntervention, TechnicalInterventionDelivery
from app.models.technical_report import TechnicalReport
from app.services import lab_work_orders as lwo
from app.services.lab_work_order_deliveries import equipment_delivery_block_reason
from app.services.technical_interventions import (
    DeliveryIndex,
    InterventionRef,
    current_revision,
    delivery_backed_interventions,
    equipment_interventions,
    has_single_intervention,
    is_mandatory,
    load_delivery_index,
)
from test_general_service_closure import assert_general_service_error, complete, ready_chain  # noqa: F401
from test_general_service_delivery import (  # noqa: F401  (fixtures y helpers reutilizados)
    BASE,
    deliver,
    finalize,
    isolated_storage,
    order_with_reports,
    report_url,
    sg3,
)
from test_general_service_package import closed_order, package, pages_text  # noqa: F401


def report(id, revision=1, current=True, status="completed", intervention_id=1, delivery_id=None, pdf=True):
    return SimpleNamespace(
        id=id, revision_number=revision, is_current=current, status=status, intervention_id=intervention_id, folio=f"MYC-IN10-26-{id:04d}",
        final_pdf_path="x.pdf" if pdf else None, final_pdf_sha256="a" * 64 if pdf else None,
        final_pdf_generated_at="2026-10-08" if pdf else None,
        document_snapshot={"delivery": {"delivery_id": delivery_id}} if delivery_id else None,
    )


def intervention(id, status="open", reports=()):
    return SimpleNamespace(id=id, status=status, reports=list(reports), folio=f"MYC-IN10-26-{id:04d}")


def equipment(*interventions, legacy=None, id=1):
    return SimpleNamespace(id=id, technical_interventions=list(interventions), current_technical_report=legacy)


# --------------------------------------------------------------- obligatoriedad y revisión vigente

def test_mandatory_means_open_or_completed_and_cancelled_never_blocks():
    assert [is_mandatory(intervention(1, status)) for status in ("open", "completed", "cancelled")] == [True, True, False]


def test_current_revision_is_deterministic():
    assert current_revision(intervention(1)) is None
    assert current_revision(intervention(1, reports=[report(1, current=False)])) is None
    anomalous = intervention(1, reports=[report(3, revision=2, current=True), report(2, revision=3, current=True), report(1, revision=1, current=False)])
    assert current_revision(anomalous).revision_number == 3, "mayor revisión vigente; sin elegir al azar"


def test_equipment_interventions_are_ordered_filtered_and_fall_back_to_legacy_rows():
    first, second, cancelled = intervention(5, reports=[report(5)]), intervention(2, reports=[report(2, intervention_id=2)]), intervention(9, "cancelled")
    refs = equipment_interventions(equipment(first, cancelled, second))
    assert [ref.intervention_id for ref in refs] == [2, 5], "por id, sin canceladas"
    assert equipment_interventions(equipment(cancelled)) == []
    legacy = report(7, intervention_id=None)
    assert [ref.report for ref in equipment_interventions(equipment(legacy=legacy))] == [legacy]
    assert equipment_interventions(equipment(legacy=report(8, intervention_id=3))) == [], "con intervención no hay respaldo implícito"


def test_delivery_index_prefers_links_and_only_falls_back_by_equipment_when_unambiguous():
    delivery_a, delivery_b = SimpleNamespace(id=1), SimpleNamespace(id=2)
    single = equipment(intervention(1))
    index = DeliveryIndex(by_intervention={1: [(delivery_a, None)]}, by_equipment={1: [(delivery_b, None)]})
    assert index.for_ref(InterventionRef(single.technical_interventions[0], None), single) == [(delivery_a, None)], "el vínculo manda"
    unlinked = DeliveryIndex(by_equipment={1: [(delivery_b, None)]})
    assert unlinked.for_ref(InterventionRef(single.technical_interventions[0], None), single) == [(delivery_b, None)], "una intervención: respaldo por equipo"
    double = equipment(intervention(1), intervention(2))
    assert unlinked.for_ref(InterventionRef(double.technical_interventions[0], None), double) == [], "con varias intervenciones no se adivina"
    assert has_single_intervention(equipment(intervention(1), intervention(2, "cancelled")))
    assert not has_single_intervention(double)


def _blockers(refs, index, eq=None):
    base = {"work_order_id": 1, "work_order_folio": 6400, "equipment_id": 1, "equipment_position": 1, "equipment": "E"}
    eq = eq or equipment(*[ref.intervention for ref in refs])
    return [b for ref in refs for b in lwo._intervention_blockers(base, ref, eq, index, verify_files=False)]


def test_every_mandatory_intervention_must_be_complete_for_the_equipment_to_close():
    delivery = SimpleNamespace(id=10)
    done = InterventionRef(intervention(1), report(1, delivery_id=10))
    draft = InterventionRef(intervention(2), report(2, status="draft", intervention_id=2))
    index = DeliveryIndex(by_intervention={1: [(delivery, None)]})
    assert _blockers([done], index) == []
    blockers = _blockers([done, draft], index)
    assert [(b["intervention_id"], b["code"]) for b in blockers] == [(2, "TECHNICAL_REPORT_INCOMPLETE")]
    no_revision = InterventionRef(intervention(3), None)
    assert _blockers([no_revision], index)[0]["reason"] == "Sin reporte técnico"
    no_pdf = InterventionRef(intervention(4), report(4, pdf=False, intervention_id=4))
    assert _blockers([no_pdf], index)[0]["code"] == "TECHNICAL_REPORT_DOCUMENT_INVALID"
    other_delivery = InterventionRef(intervention(1), report(1, delivery_id=99))
    assert _blockers([other_delivery], index)[0]["code"] == "TECHNICAL_REPORT_REVISION_REQUIRED"


# --------------------------------------------------------------- integración (SQLite)

def _add_intervention(factory, equipment_id: int, status: str, folio: str):
    with factory() as db:
        extra = TechnicalIntervention(lab_equipment_id=equipment_id, intervention_type="installation", folio=folio, status=status)
        db.add(extra)
        db.commit()
        return extra.id


def test_an_extra_open_intervention_without_a_report_blocks_closure_until_it_is_cancelled(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = ready_chain(client, headers)
    extra_id = _add_intervention(factory, equipment["id"], "open", "MYC-IN10-26-7001")
    detail = assert_general_service_error(complete(client, headers, order), "TECHNICAL_REPORT_INCOMPLETE")
    assert [(item["intervention_id"], item["reason"]) for item in detail["items"]] == [(extra_id, "Sin reporte técnico")]
    with factory() as db:
        db.get(TechnicalIntervention, extra_id).status = "cancelled"
        db.commit()
    assert complete(client, headers, order).status_code == 200, "una intervención cancelada nunca bloquea"


def test_delivery_eligibility_requires_all_mandatory_interventions(sg3):
    client, factory, headers = sg3
    order, [equipment], _ = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    with factory() as db:
        equipment_row = db.get(LabWorkOrderEquipment, equipment["id"])
        assert equipment_delivery_block_reason(equipment_row) is None
    extra_id = _add_intervention(factory, equipment["id"], "open", "MYC-IN10-26-7002")
    with factory() as db:
        equipment_row = db.get(LabWorkOrderEquipment, equipment["id"])
        assert equipment_delivery_block_reason(equipment_row) == "Sin reporte técnico"
    response = deliver(client, headers, order)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "LAB_DELIVERY_REPORT_NOT_READY"


def test_a_delivery_identifies_the_interventions_it_backs_and_legacy_unlinked_deliveries_still_work(sg3):
    client, factory, headers = sg3
    order, equipments, reports = ready_chain(client, headers, count=2)
    with factory() as db:
        delivery_id = db.scalar(select(LabWorkOrderDelivery.id))
        backed = delivery_backed_interventions(db, delivery_id)
        assert [item.folio for item in backed] == sorted(r["folio"] for r in reports)
        assert db.scalar(select(TechnicalInterventionDelivery.id)) is not None
        # Entrega anterior a los vínculos (A1): sin filas de vínculo se resuelve por equipo.
        db.execute(TechnicalInterventionDelivery.__table__.update().values(technical_report_id=None))
        db.execute(delete(TechnicalInterventionDelivery))
        db.commit()
        assert [item.folio for item in delivery_backed_interventions(db, delivery_id)] == sorted(r["folio"] for r in reports)
    assert complete(client, headers, order).status_code == 200, "el cierre no depende de que existan los vínculos"
    assert package(client, headers, order).status_code == 200


def test_authority_queries_do_not_grow_with_the_number_of_equipment(sg3):
    client, factory, headers = sg3
    single_order, _eq, _r = ready_chain(client, headers, count=1)
    many_order, _eq2, _r2 = ready_chain(client, headers, count=4)

    def count_queries(order_id: int) -> int:
        statements: list[str] = []
        with factory() as db:
            order = db.get(LabWorkOrder, order_id)
            _ = [e.technical_interventions for e in order.active_equipment]  # carga previa de relaciones
            engine = db.get_bind()

            def before(conn, cursor, statement, *args):
                statements.append(statement)

            event.listen(engine, "before_cursor_execute", before)
            try:
                assert lwo.work_order_technical_blockers(db, [order], verify_files=False) == []
            finally:
                event.remove(engine, "before_cursor_execute", before)
        return len(statements)

    assert count_queries(many_order["id"]) == count_queries(single_order["id"]), "una carga de entregas por OT, sin N+1"


def test_package_order_is_stable_dedupes_vouchers_and_ignores_cancelled_interventions(sg3):
    client, factory, headers = sg3
    order, equipments, reports = closed_order(client, headers, count=3)
    _add_intervention(factory, equipments[0]["id"], "cancelled", "MYC-IN10-26-7003")
    first = package(client, headers, order)
    second = package(client, headers, order)
    assert first.status_code == 200 and pages_text(first.content) == pages_text(second.content), "orden estable"
    texts = pages_text(first.content)
    assert sum("ACUSE DE ENTREGA DE EQUIPOS" in text for text in texts) == 1, "un acuse aunque lo respalden 3 intervenciones"
    positions = [next(i for i, text in enumerate(texts) if report["folio"] in text and "REPORTE DE INSTALACIÓN" in text) for report in reports]
    assert positions == sorted(positions), "reportes en el orden de los equipos"
    from app.models.audit_log import AuditLog

    with factory() as db:
        docs = db.scalar(select(AuditLog).where(AuditLog.action == "lab_package.downloaded").order_by(AuditLog.id)).new_values["documents"]
    reports_meta = [doc for doc in docs if doc["type"] == "technical_report"]
    assert [doc["folio"] for doc in reports_meta] == [r["folio"] for r in reports]
    assert all(doc["intervention_id"] is not None for doc in reports_meta)


def test_finalize_resolves_the_delivery_through_the_intervention(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = order_with_reports(client, headers)
    finalize(client, headers, order, equipment)
    assert deliver(client, headers, order).status_code == 201
    assert client.post(report_url(order["id"], equipment["id"], "/finalize"), headers=headers).status_code == 200
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        link = db.scalar(select(TechnicalInterventionDelivery))
        assert link.technical_report_id == stored.id and link.intervention_id == stored.intervention_id
        assert stored.document_snapshot["delivery"]["delivery_id"] == link.delivery_id
