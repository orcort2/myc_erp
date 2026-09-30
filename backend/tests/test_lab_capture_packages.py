"""Captura LAB-backed: readiness estructurada y paquete PDF-only sin efectos."""
import io
import zipfile

import pytest
from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.service_order import ServiceOrder
from test_service_order_mobile_execution import _counts, _link, _url, ctx  # noqa: F401


# ------------------------------------------------------------------ CAPTURE


def _summary(ctx):
    response = ctx["http"].get(_url(ctx, "/capture-package-summary"), headers=ctx["headers"]["Captura"])
    assert response.status_code == 200
    return response.json()


def _codes(summary):
    return {item["code"] for item in summary["blockers"]}


def test_capture_summary_requires_lab_link(ctx):
    summary = _summary(ctx)
    assert summary["source"] == "lab" and summary["ready"] is False
    assert _codes(summary) == {"LAB_LINK_REQUIRED"}


def test_capture_summary_complete_group_is_ready_and_ignores_tombstone(ctx):
    _link(ctx)
    summary = _summary(ctx)
    assert summary["ready"] is True, summary["blockers"]
    assert (summary["ready_total"], summary["pending_total"]) == (2, 0)
    assert [len(group["equipment"]) for group in summary["groups"]] == [1, 1]


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ({"certificate_folio": None}, "LAB_CERTIFICATE_FOLIO_MISSING"),
        ({"folio_status": "pending"}, "LAB_CERTIFICATE_FOLIO_NOT_READY"),
        ({"sheet": None}, "LAB_FIELD_SHEET_MISSING"),
        ({"sheet_status": "draft"}, "LAB_FIELD_SHEET_NOT_COMPLETED"),
        ({"final_pdf_path": None}, "LAB_FINAL_PDF_MISSING"),
        ({"pdf_file": "missing"}, "LAB_FINAL_PDF_MISSING"),
        ({"pdf_file": "tampered"}, "LAB_FINAL_PDF_HASH_MISMATCH"),
        ({"work_order_status": "in_progress"}, "LAB_WORK_ORDER_NOT_FINAL"),
        ({"work_order_final_pdf": None}, "LAB_WORK_ORDER_FINAL_PDF_MISSING"),
    ],
)
def test_capture_blockers_partially_incomplete_group_stays_blocked(ctx, mutation, code):
    _link(ctx)
    with ctx["factory"]() as db:
        equipment = db.get(LabWorkOrderEquipment, ctx["e2"])
        sheet = equipment.current_field_sheet
        for key, value in mutation.items():
            if key == "sheet":
                sheet.is_current = False
            elif key == "sheet_status":
                sheet.status = value
            elif key == "final_pdf_path":
                sheet.final_pdf_path = value
            elif key == "pdf_file":
                path = ctx["storage"] / sheet.final_pdf_path
                path.unlink() if value == "missing" else path.write_bytes(b"alterado")
            elif key == "work_order_status":
                db.get(LabWorkOrder, ctx["child"]).status = value
            elif key == "work_order_final_pdf":
                db.get(LabWorkOrder, ctx["child"]).final_pdf = value
            else:
                setattr(equipment, key, value)
        db.commit()
    summary = _summary(ctx)
    assert summary["ready"] is False
    assert code in _codes(summary)
    assert summary["ready_total"] == 1  # el resto del grupo sí está listo, pero el ETS sigue bloqueado
    blocked = ctx["http"].get(_url(ctx, "/capture-package"), headers=ctx["headers"]["Captura"])
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "LAB_CAPTURE_PACKAGE_BLOCKED"


def test_capture_package_is_pdf_only_with_lab_folio_and_has_no_side_effects(ctx):
    _link(ctx)
    with ctx["factory"]() as db:
        before = _counts(db)
        order_folio = db.get(ServiceOrder, ctx["order"]).folio
        e1 = db.get(LabWorkOrderEquipment, ctx["e1"])
        expected = (ctx["storage"] / e1.current_field_sheet.final_pdf_path).read_bytes()
        audit_before = db.scalar(select(func.count(AuditLog.id)))
    response = ctx["http"].get(_url(ctx, "/capture-package"), headers=ctx["headers"]["Captura"])
    assert response.status_code == 200, response.text
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = sorted(archive.namelist())
    # Estructura plana: una carpeta por OT; sin carpeta ETS ni carpeta por folio.
    assert names == [
        "OT-6438/Hoja_Campo_MYCT-09-2026-64381.pdf",
        "OT-6438/OT-6438.pdf",
        "OT-6439/Hoja_Campo_MYCT-09-2026-64391.pdf",
        "OT-6439/OT-6439.pdf",
    ]
    assert archive.read("OT-6438/OT-6438.pdf") == b"%PDF-1.4 OT 6438"  # final_pdf persistido
    assert response.headers["content-disposition"] == f'attachment; filename="{order_folio}.zip"'
    assert all(name.endswith(".pdf") for name in names)  # sin XLSX/Master
    assert archive.read(names[0]) == expected  # PDF congelado, nunca regenerado
    with ctx["factory"]() as db:
        assert _counts(db) == before  # sin Certificate, Equipment, folios ni hojas nuevas
        assert db.scalar(select(func.count(AuditLog.id))) == audit_before


def test_capture_upload_and_erp_work_order_package_are_rejected_for_mobile_ets(ctx):
    _link(ctx)
    upload = ctx["http"].post(
        _url(ctx, "/capture-files"), files={"files": ("x.xlsx", b"PK", "application/octet-stream")},
        headers=ctx["headers"]["Administrador"],
    )
    assert upload.status_code == 409
    assert upload.json()["detail"]["code"] == "LAB_CAPTURE_INGESTION_NOT_AVAILABLE"


def test_capture_package_physical_case_single_ot_exact_namelist(ctx):
    """Caso físico validado: una OT, un equipo MYCA."""
    with ctx["factory"]() as db:
        db.get(LabWorkOrder, ctx["child"]).status = "cancelled"  # grupo operativo = sólo OT-6438
        equipment = db.get(LabWorkOrderEquipment, ctx["e1"])
        equipment.service_type = "accredited"
        equipment.certificate_folio = "MYCA-09-26-4721"
        db.commit()
    _link(ctx)
    response = ctx["http"].get(_url(ctx, "/capture-package"), headers=ctx["headers"]["Captura"])
    assert response.status_code == 200, response.text
    assert sorted(zipfile.ZipFile(io.BytesIO(response.content)).namelist()) == [
        "OT-6438/Hoja_Campo_MYCA-09-26-4721.pdf",
        "OT-6438/OT-6438.pdf",
    ]


def test_capture_package_sanitizes_certificate_folio_in_file_name(ctx):
    with ctx["factory"]() as db:
        db.get(LabWorkOrderEquipment, ctx["e1"]).certificate_folio = "MYCA/09:26*4721"
        db.commit()
    _link(ctx)
    response = ctx["http"].get(_url(ctx, "/capture-package"), headers=ctx["headers"]["Captura"])
    assert "OT-6438/Hoja_Campo_MYCA-09-26-4721.pdf" in zipfile.ZipFile(io.BytesIO(response.content)).namelist()
