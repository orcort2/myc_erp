from __future__ import annotations

import hashlib
import io

from fastapi import HTTPException
from pypdf import PdfReader, PdfWriter
from sqlalchemy.orm import Session

from app.models.lab_work_order import LabWorkOrder
from app.models.user import User
from app.services.audit_logs import write_audit_log
from app.services.field_sheet_pdfs import generate_field_sheet_pdf
from app.services.lab_work_order_pdfs import generate_lab_work_order_pdf
from app.services.lab_work_orders import (
    _ensure_general_service_technical_completion,
    _get,
    _group,
    _technical_report_pdf_problem,
)
from app.services.technical_interventions import equipment_interventions, load_delivery_index
from app.services.storage_service import resolve_storage_path
from app.services.technical_report_pdfs import installation_report_filename


def _append_pdf(writer: PdfWriter, content: bytes) -> None:
    reader = PdfReader(io.BytesIO(content))
    for page in reader.pages:
        writer.add_page(page)


def _package_document_error(detail: str, items: list[dict] | None = None) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={"code": "LAB_PACKAGE_DOCUMENT_MISSING", "message": detail, "items": items or []},
    )


def _document_meta(kind: str, content: bytes, **extra) -> dict:
    return {"type": kind, **extra, "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)}


def _general_service_documents(db: Session, order: LabWorkOrder) -> list[tuple[bytes, dict]]:
    """Documentos FINALES de una OT de Servicio General, en orden de lectura:
    PDF de la OT, Reporte(s) de instalación vigentes y acuse(s) de entrega
    vigentes (los anulados y los reportes no vigentes nunca entran). Nunca
    compone un paquete parcial: si falta o está corrupto algo obligatorio, 409
    estructurado. Las fotografías ya viven dentro del PDF del reporte."""
    if order.status not in {"completed", "partially_closed"} or not order.final_pdf:
        raise _package_document_error(
            f"La OT {order.folio} aún no está cerrada: no existe su PDF final.",
            [{"work_order_id": order.id, "work_order_folio": order.folio, "document": "work_order"}],
        )
    # Mismo criterio que el cierre: reporte completed + PDF válido + entrega vigente.
    _ensure_general_service_technical_completion(db, [order])
    documents: list[tuple[bytes, dict]] = [
        (order.final_pdf, _document_meta("work_order", order.final_pdf, work_order_id=order.id, folio=order.folio, revision=order.revision_number))
    ]
    # Una carga de entregas vigentes por OT; orden estable (posición del equipo,
    # id de intervención); cada reporte y cada acuse entra una sola vez.
    equipment_list = sorted(order.active_equipment, key=lambda item: item.position)
    index = load_delivery_index(db, equipment_list)
    deliveries: dict[int, object] = {}
    seen_reports: set[int] = set()
    for equipment in equipment_list:
        for ref in equipment_interventions(equipment):
            report = ref.report
            assert report is not None  # garantizado por la validación anterior
            if report.id in seen_reports:
                continue
            seen_reports.add(report.id)
            problem = _technical_report_pdf_problem(report, verify_file=True)
            if problem is not None:
                raise _package_document_error(problem)
            content = resolve_storage_path(report.final_pdf_path).read_bytes()
            documents.append((content, _document_meta(
                "technical_report", content, report_type=report.report_type, folio=report.folio,
                revision=report.revision_number, equipment_id=equipment.id, intervention_id=ref.intervention_id,
                filename=installation_report_filename({"document": {"folio": report.folio, "revision_number": report.revision_number}}),
            )))
            for delivery, _item in index.for_ref(ref, equipment):
                deliveries[delivery.id] = delivery
    for delivery in sorted(deliveries.values(), key=lambda item: item.exhibition_number):
        voucher = delivery.voucher_pdf
        if not voucher or hashlib.sha256(voucher).hexdigest() != delivery.voucher_pdf_sha256:
            raise _package_document_error(f"El acuse de entrega de la exhibición {delivery.exhibition_number} no está disponible.")
        documents.append((voucher, _document_meta(
            "delivery_voucher", voucher, delivery_id=delivery.id, exhibition_number=delivery.exhibition_number,
            folio=order.folio,
        )))
    return documents


def generate_lab_package(
    db: Session,
    work_order_id: int,
    user: User,
    *,
    group: bool,
) -> tuple[bytes, str]:
    selected = _get(db, work_order_id)
    orders = _group(db, selected) if group else [selected]
    orders = sorted(orders, key=lambda item: item.sequence_number)
    writer = PdfWriter()
    manifest: list[dict] = []
    for order in orders:
        if order.operational_category == "general_service":
            # SG-4I: OT + TechnicalReport(s) + acuse(s); nunca FieldSheets.
            for content, meta in _general_service_documents(db, order):
                _append_pdf(writer, content)
                manifest.append(meta)
            continue
        order_pdf = order.final_pdf or generate_lab_work_order_pdf(order)[0]
        _append_pdf(writer, order_pdf)
        for equipment in sorted(order.equipment, key=lambda item: item.position):
            if equipment.field_sheet is None:
                continue
            sheet_pdf, _ = generate_field_sheet_pdf(db, equipment.field_sheet.id)
            _append_pdf(writer, sheet_pdf)
    output = io.BytesIO()
    writer.write(output)
    content = output.getvalue()
    if not content:
        raise HTTPException(status_code=409, detail="No fue posible componer el paquete LAB")
    write_audit_log(
        db,
        action="lab_package.downloaded",
        entity="lab_work_orders",
        entity_id=selected.id,
        user_id=user.id,
        new_values={
            "scope": "group" if group else "individual",
            "work_order_ids": [item.id for item in orders],
            "folios": [item.folio for item in orders],
            **({"documents": manifest} if manifest else {}),
        },
    )
    db.commit()
    filename = (
        f"Paquete_LAB_Grupo_{orders[0].folio}.pdf"
        if group
        else f"Paquete_LAB_OT_{selected.folio}.pdf"
    )
    return content, filename
