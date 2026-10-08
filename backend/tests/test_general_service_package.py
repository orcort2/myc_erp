"""SG-4I-B: paquete documental final de Servicio General (OT + Reporte(s) de
instalación + acuse(s) de entrega) y export global con TechnicalReports. El
paquete de calibración (OT + FieldSheets) no cambia."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile

from pypdf import PdfReader
from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.field_sheet import FieldSheet
from app.models.lab_work_order import LabWorkOrder
from app.models.lab_delivery_item import LabDeliveryItem
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.operational_ticket import OperationalTicket
from app.models.technical_report import TechnicalReport
from test_general_service_closure import complete, ready_chain, run_finalize  # noqa: F401
from test_general_service_delivery import (  # noqa: F401  (fixtures y helpers reutilizados)
    BASE,
    _with_context,
    deliver,
    delivery_payload,
    finalize,
    isolated_storage,
    order_with_reports,
    report_url,
    reset_override,
    sg3,
)


def package(client, headers, order):
    return client.get(f"{BASE}/{order['id']}/package", headers=headers)


def closed_order(client, headers, count: int = 1):
    order, equipments, reports = ready_chain(client, headers, count=count)
    assert complete(client, headers, order).status_code == 200
    return order, equipments, reports


def pages_text(content: bytes) -> list[str]:
    return [page.extract_text() for page in PdfReader(io.BytesIO(content)).pages]


def count_in(texts: list[str], needle: str) -> int:
    return sum(needle in text for text in texts)


def admin_headers(factory):
    from app.core.security import create_access_token
    from app.models.user import Role, User

    with factory() as db:
        role = Role(name="Administrador", description="Administrador")
        db.add(role)
        db.flush()
        user = User(username="lab-admin", email="lab-admin@example.test", full_name="LAB admin", hashed_password="unused",
                    account_type="internal", status="active", is_active=True, role_id=role.id, roles=[role])
        db.add(user)
        db.commit()
        token = create_access_token(str(user.id), extra_claims={"roles": ["Administrador"], "auth_context": "internal"})
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------- contenido

def test_closed_general_service_package_has_ot_report_and_delivery_voucher_in_order(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = closed_order(client, headers)
    response = package(client, headers, order)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert f"Paquete_LAB_OT_{order['folio']}.pdf" in response.headers["content-disposition"]
    texts = pages_text(response.content)
    assert count_in(texts, "REPORTE DE INSTALACIÓN") >= 1 and count_in(texts, report["folio"]) >= 1
    assert count_in(texts, "ACUSE DE ENTREGA DE EQUIPOS") == 1
    first_report = next(i for i, text in enumerate(texts) if "REPORTE DE INSTALACIÓN" in text)
    voucher = next(i for i, text in enumerate(texts) if "ACUSE DE ENTREGA DE EQUIPOS" in text)
    assert 0 < first_report < voucher, "OT, luego reporte, luego acuse"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(FieldSheet)) == 0  # no se inventan hojas


def test_manifest_in_the_audit_log_identifies_every_document(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = closed_order(client, headers)
    assert package(client, headers, order).status_code == 200
    with factory() as db:
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "lab_package.downloaded"))
        docs = audit.new_values["documents"]
        stored_order = db.get(LabWorkOrder, order["id"])
        stored_report = db.get(TechnicalReport, report["id"])
        delivery = db.scalar(select(LabWorkOrderDelivery))
    assert [doc["type"] for doc in docs] == ["work_order", "technical_report", "delivery_voucher"]
    assert docs[0]["sha256"] == hashlib.sha256(stored_order.final_pdf).hexdigest() and docs[0]["size_bytes"] == len(stored_order.final_pdf)
    assert docs[1]["folio"] == report["folio"] and docs[1]["revision"] == 1 and docs[1]["report_type"] == "installation"
    assert docs[1]["sha256"] == stored_report.final_pdf_sha256
    assert docs[1]["filename"] == f"Reporte-instalacion-{report['folio']}-r1.pdf"
    assert docs[2]["sha256"] == delivery.voucher_pdf_sha256 and docs[2]["exhibition_number"] == 1
    assert len({doc["sha256"] for doc in docs}) == 3, "sin documentos duplicados"


def test_multiple_equipment_include_one_report_each_and_a_single_shared_voucher(sg3):
    client, _factory, headers = sg3
    order, equipments, reports = closed_order(client, headers, count=3)
    texts = pages_text(package(client, headers, order).content)
    for report in reports:
        assert count_in(texts, report["folio"]) >= 1
    assert count_in(texts, "ACUSE DE ENTREGA DE EQUIPOS") == 1, "una sola exhibición, un solo acuse"


def test_historical_partial_delivery_includes_each_current_voucher(sg3):
    client, factory, headers = sg3
    order, [first, second], reports = order_with_reports(client, headers, count=2)
    finalize(client, headers, order, first)
    finalize(client, headers, order, second)
    ticket = client.post(
        "/api/mobile/v1/technician/tickets/partial-delivery",
        json={"work_order_id": order["id"], "requested_equipment_ids": [first["id"]], "reason": "Urgente", "description": "Cliente la requiere"},
        headers=headers,
    ).json()
    with factory() as db:
        db.get(OperationalTicket, ticket["id"]).status = "approved"
        db.commit()
    assert client.post(f"{BASE}/{order['id']}/delivery/partial/{ticket['id']}", json=delivery_payload(), headers=headers).status_code == 201
    assert deliver(client, headers, order).status_code == 201
    for equipment in (first, second):
        assert run_finalize(client, headers, order, equipment).status_code == 200
    assert complete(client, headers, order).status_code == 200
    texts = pages_text(package(client, headers, order).content)
    assert count_in(texts, "ACUSE DE ENTREGA DE EQUIPOS") == 2
    assert count_in(texts, "Exhibición 1") == 1 and count_in(texts, "Exhibición 2") == 1
    assert count_in(texts, "esta entrega parcial") == 1


def test_package_never_mixes_a_report_with_a_different_delivery(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = closed_order(client, headers)
    texts = pages_text(package(client, headers, order).content)
    assert count_in(texts, report["folio"]) >= 2, "el folio MYC-IN sale en la OT y en el reporte"
    with factory() as db:
        original = db.scalar(select(LabWorkOrderDelivery))
        original_id = original.id
        original.status = "voided"
        # Dato inconsistente: una entrega nueva respaldando un reporte generado con la anterior.
        replacement = LabWorkOrderDelivery(
            root_work_order_id=original.root_work_order_id, root_work_order_id_snapshot=original.root_work_order_id_snapshot,
            root_work_order_folio_snapshot=original.root_work_order_folio_snapshot, exhibition_number=2,
            delivery_type="full", delivery_method="direct", status="completed", delivered_at=original.delivered_at,
            delivered_by_user_id=original.delivered_by_user_id, delivered_by_signature_data_url=original.delivered_by_signature_data_url,
            recipient_name="Otro Receptor", recipient_signature_data_url=original.recipient_signature_data_url,
            voucher_pdf=original.voucher_pdf, voucher_pdf_sha256=original.voucher_pdf_sha256,
        )
        db.add(replacement)
        db.flush()
        item = db.scalar(select(LabDeliveryItem).where(LabDeliveryItem.delivery_id == original_id))
        db.add(LabDeliveryItem(
            delivery_id=replacement.id, work_order_id=item.work_order_id, equipment_id=item.equipment_id,
            work_order_id_snapshot=item.work_order_id_snapshot, work_order_folio_snapshot=item.work_order_folio_snapshot,
            equipment_id_snapshot=item.equipment_id_snapshot, position_snapshot=item.position_snapshot,
            instrument_snapshot=item.instrument_snapshot, brand_snapshot=item.brand_snapshot,
            identification_snapshot=item.identification_snapshot, serial_number_snapshot=item.serial_number_snapshot,
        ))
        db.commit()
    response = package(client, headers, order)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "TECHNICAL_REPORT_REVISION_REQUIRED"


def test_voided_backing_delivery_blocks_the_package_of_a_closed_order(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = closed_order(client, headers)
    with factory() as db:
        delivery_id = db.scalar(select(LabWorkOrderDelivery.id))
    assert client.post(f"{BASE}/{order['id']}/delivery/{delivery_id}/void", json={"reason": "Error de captura"}, headers=admin_headers(factory)).status_code == 200
    response = package(client, headers, order)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "TECHNICAL_REPORT_REVISION_REQUIRED"


# --------------------------------------------------------------- rechazos

def test_package_is_rejected_when_the_order_is_not_closed(sg3):
    client, _factory, headers = sg3
    order, _equipments, _ = ready_chain(client, headers)  # ready_to_close, sin PDF de OT
    response = package(client, headers, order)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "LAB_PACKAGE_DOCUMENT_MISSING"


def test_missing_or_corrupt_report_pdf_rejects_the_whole_package(sg3, isolated_storage):
    client, factory, headers = sg3
    order, [equipment], [report] = closed_order(client, headers)
    with factory() as db:
        path = isolated_storage / db.get(TechnicalReport, report["id"]).final_pdf_path
    original = path.read_bytes()
    path.write_bytes(original + b"corrupt")
    response = package(client, headers, order)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "TECHNICAL_REPORT_DOCUMENT_INVALID"
    assert "SHA-256" in response.json()["detail"]["items"][0]["reason"]
    path.unlink()
    response = package(client, headers, order)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "TECHNICAL_REPORT_DOCUMENT_INVALID"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "lab_package.downloaded")) == 0


def test_missing_delivery_voucher_rejects_the_package(sg3):
    client, factory, headers = sg3
    order, _equipments, _ = closed_order(client, headers)
    with factory() as db:
        db.scalar(select(LabWorkOrderDelivery)).voucher_pdf = None
        db.commit()
    response = package(client, headers, order)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "LAB_PACKAGE_DOCUMENT_MISSING"


def test_package_permissions_are_preserved(sg3):
    client, factory, headers = sg3
    order, _equipments, _ = closed_order(client, headers)
    _with_context(factory, {"mobile.access"}, actor_type="internal")
    try:
        assert package(client, headers, order).status_code == 403
    finally:
        reset_override()


# --------------------------------------------------------------- export_all

def test_export_all_includes_technical_reports_with_pdf_and_delivery_reference(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = closed_order(client, headers)
    _with_context(factory, {"mobile.access", "lab_work_orders.export"}, actor_type="internal")
    try:
        response = client.get(f"{BASE}/export", headers=headers)
    finally:
        reset_override()
    assert response.status_code == 200, response.text
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = archive.namelist()
    assert len(names) == len(set(names)), "sin archivos duplicados"
    pdf_name = f"technical_reports/{report['folio']}-r1.pdf"
    assert pdf_name in names and "technical_reports.json" in names and f"pdf/OT-{order['folio']}.pdf" in names
    rows = json.loads(archive.read("technical_reports.json"))
    assert len(rows) == 1
    row = rows[0]
    assert row["folio"] == report["folio"] and row["is_current"] is True and row["status"] == "completed"
    assert row["pdf_status"] == "ok" and row["pdf_path"] == pdf_name
    assert row["deliveries"][0]["status"] == "completed" and row["deliveries"][0]["recipient_name"] == "Persona Recibe"
    assert row["performed_by_name"] == "LAB tech"
    manifest = json.loads(archive.read("manifest.json"))
    entry = next(item for item in manifest["files"] if item["path"] == pdf_name)
    content = archive.read(pdf_name)
    assert entry == {
        "type": "technical_report", "report_type": "installation", "folio": report["folio"], "revision": 1,
        "path": pdf_name, "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content),
    }
    assert manifest["work_order_count"] == 1 and manifest["equipment_count"] == 1


def test_export_all_without_technical_reports_is_unchanged(sg3):
    client, factory, headers = sg3
    from test_lab_general_service_equipment import create_order

    create_order(client, headers)  # calibración
    _with_context(factory, {"mobile.access", "lab_work_orders.export"}, actor_type="internal")
    try:
        archive = zipfile.ZipFile(io.BytesIO(client.get(f"{BASE}/export", headers=headers).content))
    finally:
        reset_override()
    assert "technical_reports.json" not in archive.namelist()
    assert not [name for name in archive.namelist() if name.startswith("technical_reports/")]


def test_a_non_current_report_is_never_packaged(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = closed_order(client, headers)
    with factory() as db:
        db.get(TechnicalReport, report["id"]).is_current = False
        db.commit()
    response = package(client, headers, order)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "TECHNICAL_REPORT_INCOMPLETE"


# --------------------------------------------------------------- verificación focal SG-4I

def test_same_frozen_delivery_closes_and_packages_normally(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = ready_chain(client, headers)
    with factory() as db:
        stored = db.get(TechnicalReport, report["id"])
        delivery_id = db.scalar(select(LabWorkOrderDelivery.id))
        assert stored.status == "completed" and stored.document_snapshot["delivery"]["delivery_id"] == delivery_id
    assert complete(client, headers, order).status_code == 200
    assert package(client, headers, order).status_code == 200


def test_every_equipment_folio_is_printed_in_the_work_order_pages_of_the_package(sg3):
    client, factory, headers = sg3
    order, equipments, reports = closed_order(client, headers, count=3)
    with factory() as db:
        ot_pages = len(PdfReader(io.BytesIO(db.get(LabWorkOrder, order["id"]).final_pdf)).pages)
    content = package(client, headers, order).content
    ot_text = "\n".join(pages_text(content)[:ot_pages])
    assert "REPORTE DE INSTALACIÓN" not in ot_text, "las primeras páginas son sólo la OT"
    for report in reports:
        assert report["folio"] in ot_text, report["folio"]
    assert "None" not in ot_text


def test_a_replaced_delivery_blocks_the_close_too(sg3):
    client, factory, headers = sg3
    order, [equipment], [report] = ready_chain(client, headers)
    with factory() as db:
        original = db.scalar(select(LabWorkOrderDelivery))
        original_id = original.id
        original.status = "voided"
        replacement = LabWorkOrderDelivery(
            root_work_order_id=original.root_work_order_id, root_work_order_id_snapshot=original.root_work_order_id_snapshot,
            root_work_order_folio_snapshot=original.root_work_order_folio_snapshot, exhibition_number=2,
            delivery_type="full", delivery_method="direct", status="completed", delivered_at=original.delivered_at,
            delivered_by_user_id=original.delivered_by_user_id, delivered_by_signature_data_url=original.delivered_by_signature_data_url,
            recipient_name="Otro Receptor", recipient_signature_data_url=original.recipient_signature_data_url,
            voucher_pdf=original.voucher_pdf, voucher_pdf_sha256=original.voucher_pdf_sha256,
        )
        db.add(replacement)
        db.flush()
        item = db.scalar(select(LabDeliveryItem).where(LabDeliveryItem.delivery_id == original_id))
        db.add(LabDeliveryItem(
            delivery_id=replacement.id, work_order_id=item.work_order_id, equipment_id=item.equipment_id,
            work_order_id_snapshot=item.work_order_id_snapshot, work_order_folio_snapshot=item.work_order_folio_snapshot,
            equipment_id_snapshot=item.equipment_id_snapshot, position_snapshot=item.position_snapshot,
            instrument_snapshot=item.instrument_snapshot, brand_snapshot=item.brand_snapshot,
            identification_snapshot=item.identification_snapshot, serial_number_snapshot=item.serial_number_snapshot,
        ))
        db.commit()
    response = complete(client, headers, order)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "TECHNICAL_REPORT_REVISION_REQUIRED"
    with factory() as db:
        assert db.get(LabWorkOrder, order["id"]).status != "completed"


def test_calibration_work_order_pdf_keeps_its_certificate_folio():
    from test_lab_work_order_observations import _equipment, _pdf_text, _work_order
    from app.services.lab_work_order_pdfs import generate_lab_work_order_pdf

    equipment = _equipment(1, "Manómetro", "MAN-02", None)
    equipment.certificate_folio = "MYCA-10-26-0042"
    work_order = _work_order(notes=None, equipment=[equipment])
    work_order.operational_category = "calibration"
    assert "MYCA-10-26-0042" in _pdf_text(generate_lab_work_order_pdf(work_order)[0])
