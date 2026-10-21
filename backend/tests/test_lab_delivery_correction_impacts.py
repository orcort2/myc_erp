"""Fase 3B: impacto administrativo de una corrección sobre equipos ya entregados.

Una corrección técnica NO invalida automáticamente la entrega física: el ERP
declara explícitamente none / documentation_reissue / delivery_invalidated y
sólo los dos últimos se persisten (LabDeliveryItemCorrectionImpact).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.audit_log import AuditLog
from app.models.field_sheet import FieldSheet
from app.models.lab_delivery_group_receipt import LabDeliveryGroupReceipt
from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_delivery_item_correction_impact import LabDeliveryItemCorrectionImpact as Impact
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.user import User
from app.services import lab_delivery_correction_impacts as impacts_service
from app.services.lab_work_orders import complete_corrections
from app.services.operational_tickets import reopen_work_order_directly
from test_service_order_mobile_administration import _correction
from test_service_order_mobile_execution import Lab, _link, _url, ctx  # noqa: F401


def _deliver(ctx, equipment_ids, *, exhibition=1, status="completed", receipt=False, delivered_at=None):
    """Delivery real (filas de dominio) con voucher congelado. Devuelve ids."""
    with ctx["factory"]() as db:
        root = db.get(LabWorkOrder, ctx["root"])
        voucher = f"%PDF-1.4 voucher {exhibition}".encode()
        delivery = LabWorkOrderDelivery(
            root_work_order_id=root.id, root_work_order_id_snapshot=root.id,
            root_work_order_folio_snapshot=root.folio, exhibition_number=exhibition,
            delivery_type="partial", delivery_method="direct", status=status,
            delivered_at=delivered_at or datetime.now(timezone.utc),
            delivered_by_user_id=ctx["users"]["Administrador"],
            delivered_by_signature_data_url="data:image/png;base64,AA==",
            recipient_name="Cliente", recipient_signature_data_url="data:image/png;base64,AA==",
            voucher_pdf=voucher, voucher_pdf_sha256=sha256(voucher).hexdigest(),
        )
        db.add(delivery)
        db.flush()
        item_ids = {}
        for equipment_id in equipment_ids:
            equipment = db.get(LabWorkOrderEquipment, equipment_id)
            item = LabDeliveryItem(
                delivery_id=delivery.id, work_order_id=equipment.work_order_id, equipment_id=equipment.id,
                work_order_id_snapshot=equipment.work_order_id,
                work_order_folio_snapshot=equipment.work_order.folio, equipment_id_snapshot=equipment.id,
                position_snapshot=equipment.position, instrument_snapshot=equipment.instrument,
                brand_snapshot=equipment.brand, identification_snapshot=equipment.identification,
                serial_number_snapshot=equipment.serial_number,
                certificate_folio_snapshot=equipment.certificate_folio,
            )
            db.add(item)
            db.flush()
            item_ids[equipment_id] = item.id
        receipt_id = None
        if receipt:
            pdf = b"%PDF-1.4 acuse final"
            row = LabDeliveryGroupReceipt(
                root_work_order_id=root.id, root_work_order_id_snapshot=root.id,
                root_work_order_folio_snapshot=root.folio, version=1, exhibitions_count=exhibition,
                generated_at=datetime.now(timezone.utc), generated_by_user_id=ctx["users"]["Administrador"],
                pdf=pdf, pdf_sha256=sha256(pdf).hexdigest(),
            )
            db.add(row)
            db.flush()
            receipt_id = row.id
        db.commit()
        return {"delivery_id": delivery.id, "items": item_ids, "receipt_id": receipt_id}


def _impacts(ctx):
    with ctx["factory"]() as db:
        return list(db.scalars(select(Impact).order_by(Impact.id)))


def _freeze(ctx, delivery_id):
    with ctx["factory"]() as db:
        delivery = db.get(LabWorkOrderDelivery, delivery_id)
        items = db.scalars(select(LabDeliveryItem).where(LabDeliveryItem.delivery_id == delivery_id)).all()
        return (
            delivery.status, delivery.voucher_pdf, delivery.voucher_pdf_sha256,
            sorted(
                (i.id, i.instrument_snapshot, i.brand_snapshot, i.identification_snapshot,
                 i.serial_number_snapshot, i.certificate_folio_snapshot, i.work_order_id_snapshot,
                 i.equipment_id_snapshot, i.position_snapshot)
                for i in items
            ),
        )


def _equipment_by_id(body, equipment_id):
    return next(
        eq for wo in body["work_orders"] for eq in wo["equipment"] if eq["id"] == equipment_id
    )


# ------------------------------------------------------------------ 1, 13


def test_undelivered_equipment_keeps_legacy_flow_and_rejects_real_impacts(ctx):
    _link(ctx)
    rejected = _correction(ctx, "e1", "Calidad", delivery_impact="documentation_reissue")
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "DELIVERY_IMPACT_NOT_APPLICABLE"
    assert _correction(ctx, "e1", "Calidad", delivery_impact="delivery_invalidated").status_code == 422
    assert _impacts(ctx) == []
    ok = _correction(ctx, "e1", "Calidad", delivery_impact="none")
    assert ok.status_code == 200, ok.text
    assert _equipment_by_id(ok.json(), ctx["e1"])["delivery"]["delivered"] is False
    assert _impacts(ctx) == []


def test_undelivered_equipment_omitting_delivery_impact_is_legacy(ctx):
    _link(ctx)
    assert _correction(ctx, "e1", "Calidad").status_code == 200


# ------------------------------------------------------------------ 2


def test_delivered_equipment_requires_explicit_decision(ctx):
    _link(ctx)
    _deliver(ctx, [ctx["e1"]])
    missing = _correction(ctx, "e1", "Calidad")
    assert missing.status_code == 422
    assert missing.json()["detail"]["code"] == "DELIVERY_IMPACT_REQUIRED"
    with ctx["factory"]() as db:  # nada cambió
        assert db.get(LabWorkOrder, ctx["root"]).status == "completed"


def test_delivered_with_none_reopens_and_keeps_delivery_completed_without_impact(ctx):
    _link(ctx)
    delivered = _deliver(ctx, [ctx["e1"]], receipt=True)
    before = _freeze(ctx, delivered["delivery_id"])
    response = _correction(ctx, "e1", "Calidad", delivery_impact="none")
    assert response.status_code == 200, response.text
    body = response.json()
    assert next(wo for wo in body["work_orders"] if wo["is_root"])["status"] == "draft"
    equipment = _equipment_by_id(body, ctx["e1"])
    assert equipment["delivery"]["delivered"] is True
    assert equipment["delivery"]["active_correction_impact"] is None
    assert body["has_pending_delivery_impacts"] is False
    assert _impacts(ctx) == []
    assert _freeze(ctx, delivered["delivery_id"]) == before
    with ctx["factory"]() as db:
        assert db.get(LabDeliveryGroupReceipt, delivered["receipt_id"]).superseded_at is None
        assert db.scalar(
            select(AuditLog).where(AuditLog.action == "lab_delivery_item.correction_impact_created")
        ) is None


# ------------------------------------------------------------------ 3, 4, 6, 7, 8, 9


def test_documentation_reissue_creates_pending_impact_and_keeps_receipt(ctx):
    _link(ctx)
    delivered = _deliver(ctx, [ctx["e1"]], receipt=True)
    before = _freeze(ctx, delivered["delivery_id"])
    response = _correction(ctx, "e1", "Calidad", delivery_impact="documentation_reissue")
    assert response.status_code == 200, response.text
    [impact] = _impacts(ctx)
    item_id = delivered["items"][ctx["e1"]]
    assert (impact.delivery_item_id, impact.impact_type, impact.status) == (
        item_id, "documentation_reissue", "pending",
    )
    assert impact.reason == "Calidad detectó error de captura"
    assert impact.created_by_user_id == ctx["users"]["Calidad"]
    assert impact.work_order_id_snapshot == ctx["root"] and impact.equipment_id_snapshot == ctx["e1"]
    assert impact.source_field_sheet_revision_number == 1 and impact.source_field_sheet_id is not None
    assert impact.source_work_order_revision_id is not None
    assert impact.resolved_at is None and impact.resolved_by_user_id is None
    # Delivery/voucher/snapshots y acuse final intactos (sólo reemisión pendiente).
    assert _freeze(ctx, delivered["delivery_id"]) == before
    with ctx["factory"]() as db:
        assert db.get(LabDeliveryGroupReceipt, delivered["receipt_id"]).superseded_at is None
        event = db.scalar(
            select(AuditLog).where(AuditLog.action == "lab_delivery_item.correction_impact_created")
        )
        assert event.new_values == {
            "delivery_id": delivered["delivery_id"], "delivery_item_id": item_id,
            "work_order_id": ctx["root"], "equipment_id": ctx["e1"],
            "impact_type": "documentation_reissue", "reason": "Calidad detectó error de captura",
            "actor": ctx["users"]["Calidad"],
        }
        assert event.user_id == ctx["users"]["Calidad"]
        trace = db.scalar(select(AuditLog).where(AuditLog.action == "service_order.mobile_correction_requested"))
        assert trace.new_values["delivery_impact"] == "documentation_reissue"
    body = response.json()
    delivery = _equipment_by_id(body, ctx["e1"])["delivery"]
    assert delivery["delivery_item_id"] == item_id and delivery["delivery_id"] == delivered["delivery_id"]
    assert delivery["exhibition_number"] == 1
    assert delivery["active_correction_impact"] == {
        "id": impact.id, "impact_type": "documentation_reissue", "status": "pending",
    }
    assert body["has_pending_delivery_impacts"] is True
    assert (body["pending_documentation_reissues"], body["pending_delivery_invalidations"]) == (1, 0)


def test_delivery_invalidated_creates_pending_impact_and_supersedes_receipt_without_voiding(ctx):
    _link(ctx)
    delivered = _deliver(ctx, [ctx["e1"]], receipt=True)
    before = _freeze(ctx, delivered["delivery_id"])
    with ctx["factory"]() as db:
        receipt = db.get(LabDeliveryGroupReceipt, delivered["receipt_id"])
        receipt_pdf = (receipt.pdf, receipt.pdf_sha256, receipt.version)
    response = _correction(ctx, "e1", "Calidad", delivery_impact="delivery_invalidated")
    assert response.status_code == 200, response.text
    [impact] = _impacts(ctx)
    assert (impact.impact_type, impact.status) == ("delivery_invalidated", "pending")
    assert _freeze(ctx, delivered["delivery_id"]) == before  # NO void, NO cambios
    with ctx["factory"]() as db:
        receipt = db.get(LabDeliveryGroupReceipt, delivered["receipt_id"])
        assert receipt.superseded_at is not None
        assert (receipt.pdf, receipt.pdf_sha256, receipt.version) == receipt_pdf  # sin borrar ni regenerar
        assert db.scalar(select(func.count(LabDeliveryGroupReceipt.id))) == 1
    assert (response.json()["pending_documentation_reissues"],
            response.json()["pending_delivery_invalidations"]) == (0, 1)


# ------------------------------------------------------------------ 5, 15


def test_invalidating_one_item_does_not_touch_siblings_in_same_delivery(ctx):
    _link(ctx)
    with ctx["factory"]() as db:
        lab = Lab(db, db.get(User, ctx["users"]["Administrador"]), ctx["storage"])
        root = db.get(LabWorkOrder, ctx["root"])
        b = lab.equipment(root, 2).id
        c = lab.equipment(root, 3).id
        db.commit()
    delivered = _deliver(ctx, [ctx["e1"], b, c])
    before = _freeze(ctx, delivered["delivery_id"])
    response = _correction(ctx, "e1", "Calidad", delivery_impact="delivery_invalidated")
    assert response.status_code == 200, response.text
    [impact] = _impacts(ctx)
    assert impact.delivery_item_id == delivered["items"][ctx["e1"]]
    body = response.json()
    for other in (b, c):
        delivery = _equipment_by_id(body, other)["delivery"]
        assert delivery["delivered"] is True and delivery["active_correction_impact"] is None
    assert _freeze(ctx, delivered["delivery_id"]) == before
    with ctx["factory"]() as db:
        statuses = {i.id: i for i in db.scalars(select(LabDeliveryItem))}
        assert set(statuses) == set(delivered["items"].values())


def test_partial_delivery_keeps_item_level_semantics(ctx):
    _link(ctx)
    _deliver(ctx, [ctx["e1"]])  # e2 NO entregado
    # e2 no entregado: no acepta impacto real.
    assert _correction(ctx, "e2", "Administrador", delivery_impact="documentation_reissue").status_code == 422
    # e1 entregado: exige decisión.
    assert _correction(ctx, "e1", "Calidad").status_code == 422
    body = ctx["http"].get(_url(ctx, "/mobile-execution"), headers=ctx["headers"]["Calidad"]).json()
    assert _equipment_by_id(body, ctx["e1"])["delivery"]["delivered"] is True
    assert _equipment_by_id(body, ctx["e2"])["delivery"]["delivered"] is False
    assert _impacts(ctx) == []


# ------------------------------------------------------------------ 10


def test_complete_corrections_does_not_resolve_pending_impact(ctx):
    _link(ctx)
    _deliver(ctx, [ctx["e1"]], receipt=True)
    assert _correction(ctx, "e1", "Calidad", delivery_impact="delivery_invalidated").status_code == 200
    with ctx["factory"]() as db:
        complete_corrections(db, ctx["root"], db.get(User, ctx["users"]["Calidad"]))
    [impact] = _impacts(ctx)
    assert impact.status == "pending" and impact.resolved_at is None and impact.resolved_by_user_id is None
    with ctx["factory"]() as db:
        assert db.scalar(
            select(AuditLog).where(AuditLog.action == "lab_delivery_item.correction_impact_resolved")
        ) is None


# ------------------------------------------------------------------ 11, 12, 18


def test_reopen_failure_rolls_back_impact_receipt_and_trace(ctx, monkeypatch):
    from fastapi import HTTPException

    from app.services import operational_tickets

    _link(ctx)
    delivered = _deliver(ctx, [ctx["e1"]], receipt=True)

    def boom(*args, **kwargs):
        raise HTTPException(status_code=409, detail="fallo simulado")

    monkeypatch.setattr(operational_tickets, "_reopen_closed_cohort", boom)
    response = _correction(ctx, "e1", "Calidad", delivery_impact="delivery_invalidated")
    assert response.status_code == 409
    assert _impacts(ctx) == []
    with ctx["factory"]() as db:
        assert db.get(LabDeliveryGroupReceipt, delivered["receipt_id"]).superseded_at is None
        assert db.scalar(select(func.count(AuditLog.id)).where(
            AuditLog.action.in_(("lab_delivery_item.correction_impact_created",
                                 "service_order.mobile_correction_requested")))) == 0
        assert db.get(LabWorkOrder, ctx["root"]).status == "completed"


def _projection_revision(ctx):
    body = ctx["http"].get(_url(ctx, "/mobile-execution"), headers=ctx["headers"]["Calidad"]).json()
    return body["cohort_revision"]


def _set_edit_versions(ctx, **versions):
    with ctx["factory"]() as db:
        for key, value in versions.items():
            db.get(LabWorkOrder, ctx[key]).edit_version = value
        db.commit()


def test_projection_exposes_the_exact_cohort_revision_the_backend_validates(ctx):
    from app.services.service_order_mobile_execution import cohort_revision, linked_lab_group

    _link(ctx)
    revision = _projection_revision(ctx)
    assert len(revision) == 64
    with ctx["factory"]() as db:
        assert revision == cohort_revision(linked_lab_group(db, ctx["root"]))
    detail = ctx["http"].get(
        _url(ctx, f"/mobile-execution/equipment/{ctx['e1']}/field-sheet"), headers=ctx["headers"]["Calidad"]
    ).json()
    assert detail["cohort_revision"] == revision


def test_cohort_revision_changes_with_any_member_and_ignores_load_order():
    from types import SimpleNamespace

    from app.services.service_order_mobile_execution import cohort_revision

    def members(*pairs):
        return [SimpleNamespace(id=i, edit_version=v) for i, v in pairs]

    base = cohort_revision(members((6401, 7), (6402, 5), (6403, 3)))
    assert base == cohort_revision(members((6403, 3), (6401, 7), (6402, 5)))  # orden SQL distinto
    assert base != cohort_revision(members((6401, 7), (6402, 6), (6403, 3)))
    assert base != cohort_revision(members((6401, 8), (6402, 5), (6403, 3)))
    assert base != cohort_revision(members((6401, 7), (6402, 5), (6403, 4)))
    assert base != cohort_revision(members((6401, 7), (6402, 5)))  # miembro ausente
    assert base != cohort_revision(members((6401, 5), (6402, 7), (6403, 3)))  # mismo max/suma, otro par


def test_max_edit_version_blind_spot_is_detected_7_5_to_7_6(ctx):
    """REGRESIÓN CRÍTICA: A=7, B=5 -> B pasa a 6; max sigue 7 pero la cohorte cambió."""
    _link(ctx)
    delivered = _deliver(ctx, [ctx["e1"]], receipt=True)
    _set_edit_versions(ctx, root=7, child=5)
    r1 = _projection_revision(ctx)
    _set_edit_versions(ctx, child=6)
    with ctx["factory"]() as db:
        assert max(db.get(LabWorkOrder, i).edit_version for i in (ctx["root"], ctx["child"])) == 7
    stale = _correction(ctx, "e1", "Calidad", delivery_impact="delivery_invalidated", expected_cohort_revision=r1)
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "COHORT_REVISION_CONFLICT"
    assert _impacts(ctx) == []
    with ctx["factory"]() as db:
        assert db.get(LabDeliveryGroupReceipt, delivered["receipt_id"]).superseded_at is None
        assert db.get(LabWorkOrder, ctx["root"]).status == "completed"
    assert _projection_revision(ctx) != r1


def test_stale_cohort_revision_creates_no_impact_no_reopen_no_supersede(ctx):
    _link(ctx)
    delivered = _deliver(ctx, [ctx["e1"]], receipt=True)
    revision = _projection_revision(ctx)
    before = _freeze(ctx, delivered["delivery_id"])
    stale = _correction(ctx, "e1", "Calidad", delivery_impact="delivery_invalidated", expected_cohort_revision="0" * 64)
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "COHORT_REVISION_CONFLICT"
    assert _impacts(ctx) == []
    with ctx["factory"]() as db:
        assert db.get(LabDeliveryGroupReceipt, delivered["receipt_id"]).superseded_at is None  # sin supersede
        for work_order_id in (ctx["root"], ctx["child"]):  # sin reopen
            work_order = db.get(LabWorkOrder, work_order_id)
            assert work_order.status == "completed" and work_order.revision_number == 1
        assert db.scalar(select(func.count(FieldSheet.id)).where(FieldSheet.lab_equipment_id == ctx["e1"])) == 1
        assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action.in_((
            "lab_delivery_item.correction_impact_created", "service_order.mobile_correction_requested",
            "lab_work_order.reopened_directly")))) == 0
    assert _freeze(ctx, delivered["delivery_id"]) == before
    assert _projection_revision(ctx) == revision  # nada cambió
    ok = _correction(ctx, "e1", "Calidad", delivery_impact="documentation_reissue", expected_cohort_revision=revision)
    assert ok.status_code == 200, ok.text
    assert ok.json()["cohort_revision"] != revision  # la reapertura cambió la cohorte


def test_source_field_sheet_fk_restrict_protects_history_and_reopen_still_works(ctx):
    from sqlalchemy import delete

    _link(ctx)
    delivered = _deliver(ctx, [ctx["e1"]])
    assert _correction(ctx, "e1", "Calidad", delivery_impact="documentation_reissue").status_code == 200
    [first] = _impacts(ctx)
    # Segundo ciclo de corrección: N+1 se completa, la OT se cierra y se vuelve a corregir.
    with ctx["factory"]() as db:
        sheet2 = db.scalar(select(FieldSheet).where(
            FieldSheet.lab_equipment_id == ctx["e1"], FieldSheet.is_current.is_(True)))
        assert sheet2.id != first.source_field_sheet_id and sheet2.revision_number == 2
        sheet2.status = "completed"
        for work_order_id in (ctx["root"], ctx["child"]):
            work_order = db.get(LabWorkOrder, work_order_id)
            work_order.status = "completed"
            work_order.completed_at = datetime.now(timezone.utc)
            work_order.final_pdf = b"%PDF-1.4 cierre 2"
        db.commit()
    again = _correction(ctx, "e1", "Calidad", delivery_impact="documentation_reissue")
    assert again.status_code == 200, again.text
    impacts = _impacts(ctx)
    assert len(impacts) == 2 and impacts[0].source_field_sheet_id != impacts[1].source_field_sheet_id
    assert {i.source_field_sheet_revision_number for i in impacts} == {1, 2}
    snapshot = [(i.id, i.status, i.source_field_sheet_id, i.reason) for i in impacts]
    # Hard-delete de la hoja fuente: RESTRICT lo impide; el histórico queda intacto.
    with ctx["factory"]() as db:
        with pytest.raises(IntegrityError):
            db.execute(delete(FieldSheet).where(FieldSheet.id == first.source_field_sheet_id))
            db.flush()
        db.rollback()
    with ctx["factory"]() as db:
        assert db.get(FieldSheet, first.source_field_sheet_id) is not None
        assert [(i.id, i.status, i.source_field_sheet_id, i.reason) for i in db.scalars(select(Impact).order_by(Impact.id))] == snapshot
        assert db.get(LabDeliveryItem, delivered["items"][ctx["e1"]]) is not None


def test_source_field_sheet_is_mandatory_at_service_and_db_level(ctx):
    delivered = _deliver(ctx, [ctx["e1"]])
    assert Impact.__table__.c.source_field_sheet_id.nullable is False
    assert Impact.__table__.c.source_field_sheet_revision_number.nullable is False
    with ctx["factory"]() as db:
        db.add(Impact(
            delivery_item_id=delivered["items"][ctx["e1"]], work_order_id_snapshot=1, equipment_id_snapshot=1,
            impact_type="documentation_reissue", status="pending", reason="x",
            created_by_user_id=ctx["users"]["Calidad"], source_field_sheet_id=None,
            source_field_sheet_revision_number=None,
        ))
        with pytest.raises(IntegrityError):
            db.flush()


def test_pending_invalidation_blocks_new_final_receipt_but_keeps_physical_completeness(ctx):
    from app.services.lab_work_order_deliveries import (
        _generate_final_receipt,
        get_lab_delivery_group_status,
    )

    _link(ctx)
    delivered = _deliver(ctx, [ctx["e1"], ctx["e2"]], receipt=True)
    assert _correction(ctx, "e1", "Calidad", delivery_impact="delivery_invalidated").status_code == 200
    with ctx["factory"]() as db:
        admin = db.get(User, ctx["users"]["Administrador"])
        status = get_lab_delivery_group_status(db, ctx["root"])
        assert status.group_complete is True  # historia física intacta
        assert status.final_receipt_available is False  # el anterior quedó superseded
        assert db.get(LabDeliveryGroupReceipt, delivered["receipt_id"]).superseded_at is not None
        assert status.final_receipt_blocked_reason == "DELIVERY_INVALIDATION_PENDING"
        assert status.exhibitions[0].final_receipt_available is False
        assert status.exhibitions[0].final_receipt_blocked_reason == "DELIVERY_INVALIDATION_PENDING"
        assert _generate_final_receipt(db, root_work_order=db.get(LabWorkOrder, ctx["root"]), user=admin) is False
        db.commit()
        assert db.scalar(select(func.count(LabDeliveryGroupReceipt.id))) == 1  # NO se generó otro
        assert db.scalar(select(AuditLog).where(AuditLog.action == "lab_work_order.delivery_group_completed")) is None


def test_pending_documentation_reissue_does_not_block_final_receipt_generation(ctx):
    from app.services.lab_work_order_deliveries import has_pending_delivery_invalidation

    _link(ctx)
    _deliver(ctx, [ctx["e1"]], receipt=True)
    assert _correction(ctx, "e1", "Calidad", delivery_impact="documentation_reissue").status_code == 200
    with ctx["factory"]() as db:
        assert has_pending_delivery_invalidation(db, ctx["root"]) is False


def test_permissions_still_apply_and_leave_no_impact(ctx):
    _link(ctx)
    _deliver(ctx, [ctx["e1"]], receipt=True)
    for role in ("Tecnico", "Captura"):
        denied = _correction(ctx, "e1", role, delivery_impact="delivery_invalidated")
        assert denied.status_code == 403
    assert _impacts(ctx) == []
    with ctx["factory"]() as db:
        assert db.scalar(select(LabDeliveryGroupReceipt.superseded_at)) is None


# ------------------------------------------------------------------ 14


def test_no_duplicate_pending_impact_for_same_correction(ctx):
    _link(ctx)
    delivered = _deliver(ctx, [ctx["e1"]])
    assert _correction(ctx, "e1", "Calidad", delivery_impact="documentation_reissue").status_code == 200
    again = _correction(ctx, "e1", "Calidad", delivery_impact="documentation_reissue")
    assert again.status_code == 409  # N+1 ya editable
    assert len(_impacts(ctx)) == 1
    [existing] = _impacts(ctx)
    with ctx["factory"]() as db:
        item = db.get(LabDeliveryItem, delivered["items"][ctx["e1"]])
        user = db.get(User, ctx["users"]["Calidad"])
        with pytest.raises(Exception) as guard:  # guard transaccional
            impacts_service.create_correction_impact(
                db, delivery_item=item, impact_type="delivery_invalidated", reason="dup", user=user,
                source_field_sheet_id=existing.source_field_sheet_id,
                source_field_sheet_revision_number=1,
            )
        assert getattr(guard.value, "status_code", None) == 409
        db.rollback()
    # y el índice único parcial lo respalda a nivel de BD
    with ctx["factory"]() as db:
        db.add(Impact(
            delivery_item_id=existing.delivery_item_id, work_order_id_snapshot=1, equipment_id_snapshot=1,
            impact_type="documentation_reissue", status="pending", reason="x",
            created_by_user_id=ctx["users"]["Calidad"], source_field_sheet_id=existing.source_field_sheet_id,
        ))
        with pytest.raises(IntegrityError):
            db.flush()


def test_db_constraints_reject_unknown_type_and_status(ctx):
    delivered = _deliver(ctx, [ctx["e1"]])
    for kwargs in ({"impact_type": "none"}, {"status": "bogus"}):
        with ctx["factory"]() as db:
            values = dict(
                delivery_item_id=delivered["items"][ctx["e1"]], work_order_id_snapshot=1,
                equipment_id_snapshot=1, impact_type="documentation_reissue", status="pending",
                reason="x", created_by_user_id=ctx["users"]["Calidad"],
            )
            values.update(kwargs)
            db.add(Impact(**values))
            with pytest.raises(IntegrityError):
                db.flush()


# ------------------------------------------------------------------ 16


def test_tombstone_keeps_delivery_item_and_impact(ctx):
    _link(ctx)
    delivered = _deliver(ctx, [ctx["e1"]])
    assert _correction(ctx, "e1", "Calidad", delivery_impact="documentation_reissue").status_code == 200
    item_id = delivered["items"][ctx["e1"]]
    with ctx["factory"]() as db:
        snapshot = db.get(LabDeliveryItem, item_id).instrument_snapshot
        db.get(LabWorkOrderEquipment, ctx["e1"]).is_active = False  # tombstone
        db.commit()
    with ctx["factory"]() as db:
        item = db.get(LabDeliveryItem, item_id)
        assert item is not None and item.instrument_snapshot == snapshot
        assert [i.status for i in item.correction_impacts] == ["pending"]
        # FK RESTRICT: no se puede borrar el item con impactos históricos.
        db.delete(item)
        with pytest.raises(IntegrityError):
            db.flush()


# ------------------------------------------------------------------ 17


def test_projection_get_never_mutates(ctx):
    _link(ctx)
    _deliver(ctx, [ctx["e1"]], receipt=True)
    assert _correction(ctx, "e1", "Calidad", delivery_impact="delivery_invalidated").status_code == 200

    def state():
        with ctx["factory"]() as db:
            return (
                db.scalar(select(func.count(AuditLog.id))),
                [(i.id, i.status, i.updated_at) for i in db.scalars(select(Impact))],
                db.scalar(select(LabDeliveryGroupReceipt.superseded_at)),
            )

    before = state()
    for _ in range(2):
        assert ctx["http"].get(_url(ctx, "/mobile-execution"), headers=ctx["headers"]["Calidad"]).status_code == 200
        assert ctx["http"].get(
            _url(ctx, f"/mobile-execution/equipment/{ctx['e1']}/field-sheet"), headers=ctx["headers"]["Calidad"]
        ).status_code == 200
    assert state() == before


# ------------------------------------------------------------------ helpers / guard


def test_ambiguous_completed_deliveries_are_rejected_like_canonical_lab(ctx):
    from fastapi import HTTPException
    _deliver(ctx, [ctx["e1"]], exhibition=1, status="voided")
    _deliver(ctx, [ctx["e1"]], exhibition=2)
    _deliver(ctx, [ctx["e1"]], exhibition=3)
    with ctx["factory"]() as db:
        for query in (
            lambda: impacts_service.get_active_delivery_item_for_equipment(db, ctx["e1"]),
            lambda: impacts_service.get_active_delivery_items_by_equipment(db, [ctx["e1"]]),
        ):
            with pytest.raises(HTTPException) as error:
                query()
            assert error.value.status_code == 409
        assert impacts_service.get_active_delivery_item_for_equipment(db, ctx["e2"]) is None


def test_group_administrative_state_is_pure():
    state = impacts_service.group_administrative_state(
        ["documentation_reissue", "delivery_invalidated", "delivery_invalidated"]
    )
    assert (state.has_pending_delivery_impacts, state.pending_documentation_reissues,
            state.pending_delivery_invalidations) == (True, 1, 2)
    assert impacts_service.group_administrative_state([]).has_pending_delivery_impacts is False
    assert impacts_service.final_receipt_effect("documentation_reissue") == "keep"
    assert impacts_service.final_receipt_effect("delivery_invalidated") == "supersede"


def test_direct_reopen_of_delivered_equipment_requires_established_impact(ctx):
    """Sin pasar por el contrato ERP (p.ej. reapertura directa de Mobile) un
    equipo entregado no puede reabrirse sin impacto establecido."""
    from fastapi import HTTPException

    delivered = _deliver(ctx, [ctx["e1"]], receipt=True)
    with ctx["factory"]() as db:
        admin = db.get(User, ctx["users"]["Administrador"])
        with pytest.raises(HTTPException) as blocked:
            reopen_work_order_directly(
                db, ctx["root"], admin, signature_policy="preserve", reason="x", equipment_id=None,
            )
        assert blocked.value.status_code == 409
        db.rollback()
        assert db.get(LabWorkOrder, ctx["root"]).status == "completed"
    assert _freeze(ctx, delivered["delivery_id"])[0] == "completed"

# Integration contract across every public reopening route.
REOPEN_ROUTES = ("direct", "ticket", "sheet_direct", "sheet_ticket")


def _route(ctx, route):
    from app.core.security import create_access_token
    from app.models.operational_ticket import OperationalTicket
    for role, user_id in ctx["users"].items():
        token = create_access_token(str(user_id), extra_claims={"roles": [role], "auth_context": "internal"})
        ctx["headers"][role] = {"Authorization": f"Bearer {token}"}
    if route.startswith("sheet"):
        with ctx["factory"]() as db:
            for order_id in (ctx["root"], ctx["child"]):
                db.get(LabWorkOrder, order_id).status = "in_progress"
            db.commit()
    if route == "direct":
        return f'/api/mobile/v1/technician/lab-work-orders/{ctx["root"]}/reopen', {
            "requested_signature_policy": "preserve", "reason": "Corrección administrativa",
            "correction_equipment_ids": [ctx["e1"]],
        }
    if route == "sheet_direct":
        return f'/api/mobile/v1/technician/lab-work-orders/{ctx["root"]}/equipment/{ctx["e1"]}/field-sheet/reopen', {
            "reason": "Corrección administrativa",
        }
    with ctx["factory"]() as db:
        ticket = OperationalTicket(
            type="field_sheet_reopen" if route == "sheet_ticket" else "reopen_work_order",
            status="pending", work_order_id=ctx["root"], equipment_id=ctx["e1"],
            requested_by_user_id=ctx["users"]["Tecnico"], reason="Corrección requerida",
            description="Revisar captura", requested_signature_policy="preserve",
        )
        db.add(ticket)
        db.commit()
        ticket_id = ticket.id
    action = "resolve" if route == "sheet_ticket" else "approve"
    return f'/api/mobile/v1/technician/tickets/{ticket_id}/{action}', (
        {"comment": "Corrección autorizada"} if route == "sheet_ticket"
        else {"signature_policy": "preserve", "comment": "Corrección autorizada"}
    )


@pytest.mark.parametrize("route", REOPEN_ROUTES)
def test_all_routes_require_fresh_decision_and_reject_boolean_bypass(ctx, route):
    _deliver(ctx, [ctx["e1"]], receipt=True)
    url, payload = _route(ctx, route)
    headers = ctx["headers"]["Administrador"]
    denied = ctx["http"].post(url, json=payload, headers=headers)
    assert denied.status_code == 409, denied.text
    assert "DELIVERY_IMPACT_REQUIRED" in denied.text
    bypass = ctx["http"].post(url, json={**payload, "delivery_impact_declared": True}, headers=headers)
    assert bypass.status_code == 422, bypass.text
    allowed = ctx["http"].post(url, json={**payload, "delivery_impacts": {str(ctx["e1"]): "none"}}, headers=headers)
    assert allowed.status_code == 200, allowed.text
    assert not _impacts(ctx)
    with ctx["factory"]() as db:
        decision = db.scalar(select(AuditLog).where(AuditLog.action == "lab_delivery_item.correction_decided"))
        assert decision.user_id == ctx["users"]["Administrador"]
        assert decision.new_values["delivery_impact"] == "none"


@pytest.mark.parametrize("route", REOPEN_ROUTES)
def test_all_routes_reject_stale_revision_and_preserve_history(ctx, route):
    delivered = _deliver(ctx, [ctx["e1"]], receipt=True)
    before = _freeze(ctx, delivered["delivery_id"])
    url, payload = _route(ctx, route)
    response = ctx["http"].post(url, json={**payload, "expected_cohort_revision": "stale",
        "delivery_impacts": {str(ctx["e1"]): "delivery_invalidated"}}, headers=ctx["headers"]["Administrador"])
    assert response.status_code == 409, response.text
    assert "COHORT_REVISION_CONFLICT" in response.text
    assert not _impacts(ctx)
    assert _freeze(ctx, delivered["delivery_id"]) == before


def test_whole_cohort_needs_all_delivered_equipment_decisions(ctx):
    _deliver(ctx, [ctx["e1"], ctx["e2"]], receipt=True)
    url, payload = _route(ctx, "direct")
    headers = ctx["headers"]["Administrador"]
    response = ctx["http"].post(url, json={**payload, "delivery_impacts": {str(ctx["e1"]): "delivery_invalidated"}}, headers=headers)
    assert response.status_code == 409
    assert not _impacts(ctx)
    response = ctx["http"].post(url, json={**payload, "delivery_impacts": {
        str(ctx["e1"]): "documentation_reissue", str(ctx["e2"]): "none",
    }}, headers=headers)
    assert response.status_code == 200, response.text
    assert len(_impacts(ctx)) == 1
    assert _impacts(ctx)[0].source_work_order_revision_id is not None


@pytest.mark.parametrize("route", REOPEN_ROUTES)
def test_all_routes_reject_outside_equipment_and_insufficient_permissions(ctx, route):
    _deliver(ctx, [ctx["e1"]])
    url, payload = _route(ctx, route)
    response = ctx["http"].post(url, json={**payload, "delivery_impacts": {"999999": "none"}}, headers=ctx["headers"]["Administrador"])
    assert response.status_code == 422, response.text
    response = ctx["http"].post(url, json={**payload, "delivery_impacts": {str(ctx["e1"]): "none"}}, headers=ctx["headers"]["Comercial"])
    assert response.status_code == 403, response.text
    assert not _impacts(ctx)


def _transaction_snapshot(ctx):
    from app.models.lab_work_order_revision import LabWorkOrderRevision
    from app.models.notification import Notification
    from app.models.operational_ticket import OperationalTicket
    with ctx["factory"]() as db:
        return (
            [(o.id, o.status, o.edit_version, o.revision_number, o.final_pdf) for o in db.scalars(select(LabWorkOrder).order_by(LabWorkOrder.id))],
            [(s.id, s.is_current, s.status, s.revision_number, s.final_pdf_sha256) for s in db.scalars(select(FieldSheet).order_by(FieldSheet.id))],
            [(r.id, r.superseded_at, r.pdf, r.pdf_sha256) for r in db.scalars(select(LabDeliveryGroupReceipt).order_by(LabDeliveryGroupReceipt.id))],
            [(t.id, t.status, t.reviewed_by_user_id) for t in db.scalars(select(OperationalTicket).order_by(OperationalTicket.id))],
            [db.scalar(select(func.count()).select_from(model)) for model in (Impact, AuditLog, LabWorkOrderRevision, Notification)],
        )


@pytest.mark.parametrize("route", REOPEN_ROUTES)
def test_all_routes_rollback_decision_impact_receipt_and_audit_on_commit_failure(ctx, route, monkeypatch):
    from sqlalchemy.orm import Session
    delivered = _deliver(ctx, [ctx["e1"]], receipt=True)
    url, payload = _route(ctx, route)
    before = _transaction_snapshot(ctx)
    history = _freeze(ctx, delivered["delivery_id"])
    def fail_commit(self):
        self.flush()  # fail after real DML, proving rollback rather than prevalidation
        raise RuntimeError("injected commit failure")
    monkeypatch.setattr(Session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="injected commit failure"):
        ctx["http"].post(url, json={**payload, "delivery_impacts": {str(ctx["e1"]): "delivery_invalidated"}}, headers=ctx["headers"]["Administrador"])
    assert _transaction_snapshot(ctx) == before
    assert _freeze(ctx, delivered["delivery_id"]) == history


@pytest.mark.parametrize("failure", ("impact_audit", "clone", "revision_link", "reopen_audit"))
def test_ets_rolls_back_every_stage_before_commit(ctx, monkeypatch, failure):
    from app.services import operational_tickets
    _link(ctx)
    _deliver(ctx, [ctx["e1"]], receipt=True)
    before = _transaction_snapshot(ctx)
    def boom(*args, **kwargs):
        raise RuntimeError("injected stage failure")
    if failure == "impact_audit":
        original_audit = impacts_service.write_audit_log
        def fail_impact_audit(*args, **kwargs):
            if kwargs.get("action") == "lab_delivery_item.correction_impact_created":
                boom()
            return original_audit(*args, **kwargs)
        monkeypatch.setattr(impacts_service, "write_audit_log", fail_impact_audit)
    elif failure == "clone":
        monkeypatch.setattr(operational_tickets, "_clone_field_sheet_for_correction", boom)
    elif failure == "revision_link":
        monkeypatch.setattr(operational_tickets, "attach_source_revision", boom)
    else:
        monkeypatch.setattr(operational_tickets, "write_audit_log", boom)
    with pytest.raises(RuntimeError, match="injected stage failure"):
        _correction(ctx, "e1", "Administrador", delivery_impact="delivery_invalidated")
    assert _transaction_snapshot(ctx) == before


def test_old_pending_impact_never_authorizes_another_reopening(ctx):
    delivered = _deliver(ctx, [ctx["e1"]])
    with ctx["factory"]() as db:
        sheet = db.scalar(select(FieldSheet).where(FieldSheet.lab_equipment_id == ctx["e1"]))
        impacts_service.create_correction_impact(db, delivery_item=db.get(LabDeliveryItem, delivered["items"][ctx["e1"]]),
            impact_type="documentation_reissue", reason="Decisión anterior", user=db.get(User, ctx["users"]["Administrador"]),
            source_field_sheet_id=sheet.id, source_field_sheet_revision_number=sheet.revision_number)
        db.commit()
    url, payload = _route(ctx, "direct")
    response = ctx["http"].post(url, json=payload, headers=ctx["headers"]["Administrador"])
    assert response.status_code == 409


@pytest.mark.parametrize("route", ("ticket", "sheet_ticket"))
def test_delivery_decision_does_not_allow_ticket_self_approval(ctx, route):
    from app.models.operational_ticket import OperationalTicket
    _deliver(ctx, [ctx["e1"]])
    url, payload = _route(ctx, route)
    with ctx["factory"]() as db:
        ticket = db.scalar(select(OperationalTicket))
        ticket.requested_by_user_id = ctx["users"]["Administrador"]
        db.commit()
    response = ctx["http"].post(url, json={**payload, "delivery_impacts": {str(ctx["e1"]): "none"}}, headers=ctx["headers"]["Administrador"])
    assert response.status_code == 403
    assert "TICKET_SELF_APPROVAL_FORBIDDEN" in response.text
    assert not _impacts(ctx)


def test_documentary_edit_cannot_implicitly_reopen_delivered_sheet(ctx):
    from fastapi import HTTPException
    from app.services.lab_work_orders import _refresh_current_field_sheet_projection
    _deliver(ctx, [ctx["e1"]])
    before = _transaction_snapshot(ctx)
    with ctx["factory"]() as db:
        equipment = db.get(LabWorkOrderEquipment, ctx["e1"])
        equipment.instrument = "Identidad corregida"
        with pytest.raises(HTTPException) as error:
            _refresh_current_field_sheet_projection(db, equipment, db.get(User, ctx["users"]["Administrador"]))
        assert error.value.detail["code"] == "DELIVERY_IMPACT_REQUIRED"
        db.rollback()
    assert _transaction_snapshot(ctx) == before


def test_whole_cohort_opens_declared_sheets_and_pending_survives_tombstone(ctx):
    _link(ctx)
    _deliver(ctx, [ctx["e1"], ctx["e2"]], receipt=True)
    url, payload = _route(ctx, "direct")
    response = ctx["http"].post(url, json={**payload, "correction_equipment_ids": [ctx["e1"], ctx["e2"]], "delivery_impacts": {
        str(ctx["e1"]): "delivery_invalidated", str(ctx["e2"]): "none",
    }}, headers=ctx["headers"]["Administrador"])
    assert response.status_code == 200, response.text
    with ctx["factory"]() as db:
        for equipment_id in (ctx["e1"], ctx["e2"]):
            equipment = db.get(LabWorkOrderEquipment, equipment_id)
            assert equipment.current_field_sheet.status == "draft"
            assert equipment.current_field_sheet.revision_number == 2
        db.get(LabWorkOrderEquipment, ctx["e1"]).is_active = False
        db.commit()
    from app.services.service_order_mobile_execution import get_mobile_execution_projection
    with ctx["factory"]() as db:
        projection = get_mobile_execution_projection(db, ctx["order"])
        assert projection.pending_delivery_invalidations == 1
        assert projection.has_pending_delivery_impacts


@pytest.mark.parametrize("route", ["ets", "direct", "ticket"])
@pytest.mark.parametrize("decision", ["none", "documentation_reissue", "delivery_invalidated"])
def test_explicit_partial_selection_and_successive_undelivered_correction(ctx, decision, route):
    _link(ctx)
    delivered = _deliver(ctx, [ctx["e1"]], receipt=True)
    frozen = _freeze(ctx, delivered["delivery_id"])
    url, payload = _route(ctx, "direct")
    response = ctx["http"].post(url, json={**payload,
        "delivery_impacts": {str(ctx["e1"]): decision},
        "correction_equipment_ids": [ctx["e1"]],
    }, headers=ctx["headers"]["Administrador"])
    assert response.status_code == 200, response.text
    with ctx["factory"]() as db:
        assert db.get(LabWorkOrderEquipment, ctx["e1"]).field_sheet.revision_number == 2
        assert db.get(LabWorkOrderEquipment, ctx["e2"]).field_sheet.revision_number == 1
        versions = {i.id: i.revision_number for i in db.scalars(select(LabWorkOrder))}
    if route == "ets":
        # Calidad can reopen a closed OT but lacks the separate folio permission.
        assert _correction(ctx, "e2", "Calidad").status_code == 403
        response = _correction(ctx, "e2", "Administrador")
    elif route == "direct":
        response = ctx["http"].post(
            f'/api/mobile/v1/technician/lab-work-orders/{ctx["child"]}/equipment/{ctx["e2"]}/field-sheet/reopen',
            json={"reason": "Corrección posterior"}, headers=ctx["headers"]["Administrador"])
    else:
        request = ctx["http"].post('/api/mobile/v1/technician/tickets/field-sheet-reopen',
            json={"work_order_id": ctx["child"], "equipment_id": ctx["e2"],
                  "reason": "Corrección posterior", "description": "Corregir hoja adicional"},
            headers=ctx["headers"]["Tecnico"])
        assert request.status_code == 201, request.text
        response = ctx["http"].post(f'/api/mobile/v1/technician/tickets/{request.json()["id"]}/resolve',
            json={"comment": "Autorizado"}, headers=ctx["headers"]["Administrador"])
    assert response.status_code == 200, response.text
    with ctx["factory"]() as db:
        assert db.get(LabWorkOrderEquipment, ctx["e2"]).field_sheet.revision_number == 2
        assert {i.id: i.revision_number for i in db.scalars(select(LabWorkOrder))} == versions
    from app.schemas.field_sheet import FieldSheetUpdate
    from app.services.lab_field_sheets import update_lab_field_sheet
    with ctx["factory"]() as db:
        updated = update_lab_field_sheet(db, ctx["child"], ctx["e2"],
            FieldSheetUpdate(results="Corrección posterior capturada"), db.get(User, ctx["users"]["Administrador"]))
        assert updated.results == "Corrección posterior capturada"
    assert _freeze(ctx, delivered["delivery_id"]) == frozen


def test_partial_technical_selection_does_not_infer_scope_from_none(ctx):
    _deliver(ctx, [ctx["e1"], ctx["e2"]], receipt=True)
    url, payload = _route(ctx, "direct")
    response = ctx["http"].post(url, json={**payload,
        "delivery_impacts": {str(ctx["e1"]): "none", str(ctx["e2"]): "documentation_reissue"},
        "correction_equipment_ids": [ctx["e1"]],
    }, headers=ctx["headers"]["Administrador"])
    assert response.status_code == 200, response.text
    with ctx["factory"]() as db:
        assert db.get(LabWorkOrderEquipment, ctx["e1"]).field_sheet.revision_number == 2
        assert db.get(LabWorkOrderEquipment, ctx["e2"]).field_sheet.revision_number == 1
        decisions = list(db.scalars(select(AuditLog).where(AuditLog.action == "lab_delivery_item.correction_decided")))
        assert len(decisions) == 2
        assert any(row.new_values["delivery_impact"] == "none" for row in decisions)


@pytest.mark.parametrize("selection", [[999999], "duplicate", "no_source"])
def test_invalid_technical_selection_rolls_back_everything(ctx, selection):
    _deliver(ctx, [ctx["e1"]], receipt=True)
    url, payload = _route(ctx, "direct")
    if selection == "duplicate":
        selection = [ctx["e1"], ctx["e1"]]
    elif selection == "no_source":
        with ctx["factory"]() as db:
            db.get(LabWorkOrderEquipment, ctx["e2"]).field_sheet.status = "draft"
            db.commit()
        selection = [ctx["e2"]]
    before = _transaction_snapshot(ctx)
    response = ctx["http"].post(url, json={**payload,
        "delivery_impacts": {str(ctx["e1"]): "delivery_invalidated"},
        "correction_equipment_ids": selection,
    }, headers=ctx["headers"]["Administrador"])
    assert response.status_code in {409, 422}, response.text
    assert _transaction_snapshot(ctx) == before


def test_draft_markers_without_historical_revision_do_not_authorize(ctx):
    _link(ctx)
    with ctx["factory"]() as db:
        order = db.get(LabWorkOrder, ctx["root"])
        order.status = "draft"
        order.reopened_at = datetime.now(timezone.utc)
        order.reopened_by_user_id = ctx["users"]["Administrador"]
        order.revision_number = 2
        db.commit()
    before = _transaction_snapshot(ctx)
    assert _correction(ctx, "e1", "Calidad").status_code == 409
    assert _transaction_snapshot(ctx) == before


def test_model_has_pending_server_default():
    assert Impact.__table__.c.status.server_default.arg == "pending"


def test_physical_last_exhibition_commits_when_final_receipt_is_blocked(ctx):
    from app.services.lab_work_order_deliveries import _finalize_delivery, _read_delivery, get_lab_delivery_group_status
    _link(ctx)
    first = _deliver(ctx, [ctx["e1"]])
    assert _correction(ctx, "e1", "Calidad", delivery_impact="delivery_invalidated").status_code == 200
    last = _deliver(ctx, [ctx["e2"]], exhibition=2)
    frozen = _freeze(ctx, first["delivery_id"])
    with ctx["factory"]() as db:
        delivery = db.get(LabWorkOrderDelivery, last["delivery_id"])
        _finalize_delivery(db, root_work_order=db.get(LabWorkOrder, ctx["root"]),
            members=list(db.scalars(select(LabWorkOrder))), delivery=delivery,
            user=db.get(User, ctx["users"]["Administrador"]))
        db.commit()
        response = _read_delivery(db, delivery)
        assert response.status == "completed"
        assert response.voucher_available
        assert response.final_receipt_available is False
        assert response.final_receipt_blocked_reason == "DELIVERY_INVALIDATION_PENDING"
        assert get_lab_delivery_group_status(db, ctx["root"]).group_complete
        assert db.scalar(select(func.count(LabDeliveryGroupReceipt.id))) == 0
    assert _freeze(ctx, first["delivery_id"]) == frozen


def test_successive_correction_rolls_back_after_flush(ctx, monkeypatch):
    from app.services.lab_field_sheets import reopen_lab_field_sheet_directly
    with ctx["factory"]() as db:
        reopen_work_order_directly(db, ctx["root"], db.get(User, ctx["users"]["Administrador"]),
            signature_policy="preserve", reason="Sesión autorizada", equipment_id=ctx["e1"])
    before = _transaction_snapshot(ctx)
    with ctx["factory"]() as db:
        def fail():
            db.flush()
            raise RuntimeError("simulated failure after flush")
        monkeypatch.setattr(db, "commit", fail)
        with pytest.raises(RuntimeError, match="after flush"):
            reopen_lab_field_sheet_directly(db, ctx["child"], ctx["e2"],
                db.get(User, ctx["users"]["Administrador"]), reason="Corrección posterior")
    assert _transaction_snapshot(ctx) == before


def test_delivered_full_reopening_requires_explicit_technical_selection(ctx):
    _deliver(ctx, [ctx["e1"]])
    url, payload = _route(ctx, "direct")
    del payload["correction_equipment_ids"]
    before = _transaction_snapshot(ctx)
    response = ctx["http"].post(url, json={**payload, "delivery_impacts": {str(ctx["e1"]): "none"}},
        headers=ctx["headers"]["Administrador"])
    assert response.status_code == 422
    assert response.json()["detail"] == "CORRECTION_SELECTION_REQUIRED"
    assert _transaction_snapshot(ctx) == before
