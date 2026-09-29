"""Acciones administrativas ERP sobre MYC Mobile: wrappers del dominio LAB.

El ERP gobierna (enviar a corrección, cancelar/restaurar OT) pero nunca edita
valores técnicos; cada acción delega en el mismo servicio que usa Mobile.
"""
from sqlalchemy import func, select

from app.main import app
from app.models.audit_log import AuditLog
from app.models.field_sheet import FieldSheet
from app.models.lab_work_order import LabWorkOrder
from test_service_order_mobile_execution import _link, _url, ctx  # noqa: F401


def test_erp_exposes_no_technical_write_route_for_lab_field_sheets():
    """Un admin ERP NO puede modificar resultados técnicos LAB: no existe
    ninguna ruta ERP de escritura sobre la proyección salvo acciones
    administrativas explícitas."""
    from app.security.api_access import assert_all_routes_classified

    writes = {
        (operation.method, operation.path)
        for operation in assert_all_routes_classified(app)
        if "/mobile-execution" in operation.path and operation.method != "GET"
    }
    assert writes == {
        ("POST", "/api/service-orders/{service_order_id}/mobile-execution/equipment/{equipment_id}/request-correction"),
        ("POST", "/api/service-orders/{service_order_id}/mobile-execution/work-orders/{work_order_id}/cancel"),
        ("POST", "/api/service-orders/{service_order_id}/mobile-execution/work-orders/{work_order_id}/restore"),
    }


# -------------------------------------------------------------------- ADMIN


def _correction(ctx, equipment_key, role, **payload):
    return ctx["http"].post(
        _url(ctx, f"/mobile-execution/equipment/{ctx[equipment_key]}/request-correction"),
        json={"reason": "Calidad detectó error de captura", **payload},
        headers=ctx["headers"][role],
    )


def test_request_correction_on_closed_ot_opens_revision_via_domain_and_preserves_n(ctx):
    _link(ctx)
    with ctx["factory"]() as db:
        original = db.scalar(select(FieldSheet).where(FieldSheet.lab_equipment_id == ctx["e1"]))
        original_values = (original.status, original.final_pdf_path, original.final_pdf_sha256, original.results)
    response = _correction(ctx, "e1", "Calidad")
    assert response.status_code == 200, response.text
    root = next(wo for wo in response.json()["work_orders"] if wo["is_root"])
    assert root["status"] == "draft"  # OT reabierta por el dominio existente
    assert root["equipment"][0]["field_sheet"]["revision_number"] == 2
    assert root["equipment"][0]["field_sheet"]["status"] == "draft"
    with ctx["factory"]() as db:
        sheets = db.scalars(
            select(FieldSheet).where(FieldSheet.lab_equipment_id == ctx["e1"]).order_by(FieldSheet.revision_number)
        ).all()
        n, n1 = sheets
        assert (n.status, n.final_pdf_path, n.final_pdf_sha256, n.results) == original_values
        assert n.is_current is False and n1.is_current is True
        assert n1.supersedes_field_sheet_id == n.id and n1.results == "valor técnico secreto"
        assert (ctx["storage"] / n.final_pdf_path).is_file()  # PDF histórico intacto
        trace = db.scalar(select(AuditLog).where(AuditLog.action == "service_order.mobile_correction_requested"))
        assert trace.user_id == ctx["users"]["Calidad"]
        assert trace.entity_id == ctx["order"]
        assert trace.new_values["reason"] == "Calidad detectó error de captura"
        assert trace.new_values["mode"] == "work_order_reopen" and trace.new_values["origin"] == "erp"
        domain = db.scalar(select(AuditLog).where(AuditLog.action == "lab_work_order.reopened_directly"))
        assert domain.new_values["equipment_id"] == ctx["e1"]
        assert domain.new_values["retired_revision_number"] == 1


def test_request_correction_on_open_ot_uses_direct_field_sheet_reopen(ctx):
    _link(ctx)
    with ctx["factory"]() as db:
        db.get(LabWorkOrder, ctx["child"]).status = "ready_to_close"
        db.commit()
    # Calidad no posee lab_folios.resolve: el dominio rechaza y nada cambia.
    denied = _correction(ctx, "e2", "Calidad")
    assert denied.status_code == 403
    with ctx["factory"]() as db:
        assert db.scalar(select(func.count(FieldSheet.id)).where(FieldSheet.lab_equipment_id == ctx["e2"])) == 1
        assert db.scalar(select(AuditLog).where(AuditLog.action == "service_order.mobile_correction_requested")) is None
    response = _correction(ctx, "e2", "Administrador")
    assert response.status_code == 200, response.text
    child = next(wo for wo in response.json()["work_orders"] if wo["id"] == ctx["child"])
    assert child["status"] == "in_progress"
    assert child["equipment"][0]["field_sheet"]["revision_number"] == 2
    with ctx["factory"]() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "lab_field_sheet.reopened_directly")) is not None


def test_request_correction_requires_reason_permission_and_completed_sheet(ctx):
    _link(ctx)
    assert _correction(ctx, "e1", "Tecnico").status_code == 403  # técnico puro
    assert _correction(ctx, "e1", "Captura").status_code == 403
    assert _correction(ctx, "e1", "Calidad", reason="   ").status_code == 422
    assert _correction(ctx, "retired", "Administrador").status_code == 404
    assert _correction(ctx, "e1", "Calidad").status_code == 200
    again = _correction(ctx, "e1", "Calidad")  # N+1 ya es editable
    assert again.status_code == 409 and again.json()["detail"]["code"] == "LAB_FIELD_SHEET_NOT_COMPLETED"


def test_cancel_and_restore_reuse_lab_domain_and_permissions(ctx):
    _link(ctx)
    base = _url(ctx, f"/mobile-execution/work-orders/{ctx['child']}")
    http = ctx["http"]
    assert http.post(f"{base}/cancel", json={"reason": "Duplicada"}, headers=ctx["headers"]["Calidad"]).status_code == 403
    assert http.post(f"{base}/cancel", json={"reason": "Duplicada"}, headers=ctx["headers"]["Tecnico"]).status_code == 403
    cancelled = http.post(f"{base}/cancel", json={"reason": "Duplicada"}, headers=ctx["headers"]["Administrador"])
    assert cancelled.status_code == 200
    assert next(wo for wo in cancelled.json()["work_orders"] if wo["id"] == ctx["child"])["status"] == "cancelled"
    restored = http.post(f"{base}/restore", headers=ctx["headers"]["Administrador"])
    assert restored.status_code == 200
    assert next(wo for wo in restored.json()["work_orders"] if wo["id"] == ctx["child"])["status"] == "completed"
    with ctx["factory"]() as db:
        actions = set(db.scalars(select(AuditLog.action)).all())
    assert {"lab_work_order.cancelled", "lab_work_order.restored",
            "service_order.mobile_work_order_cancelled", "service_order.mobile_work_order_restored"} <= actions
    # Una OT fuera del grupo vinculado no es administrable desde este ETS.
    foreign = _url(ctx, f"/mobile-execution/work-orders/{ctx['child']}", "other")
    assert http.post(f"{foreign}/cancel", json={"reason": "x"}, headers=ctx["headers"]["Administrador"]).status_code == 409
