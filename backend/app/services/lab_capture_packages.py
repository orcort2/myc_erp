"""Estrategia LAB del handoff documental a Captura (ETS ejecutado en MYC Mobile).

"Captura" en el ERP es un handoff DOCUMENTAL, no captura técnica: el paquete
es PDF-only y contiene exclusivamente las Hojas de Campo finales congeladas
por LAB. No incluye XLSX/Master ni plantilla, no genera certificados, no
reserva ni consume folios y no crea Equipment ERP.

ServiceOrder → ServiceOrderLabLink → grupo LAB → equipo activo → FieldSheet
vigente → ``final_pdf_path`` + ``final_pdf_sha256`` (nunca se regenera).

``LabWorkOrderEquipment.certificate_folio`` es la autoridad del folio: nombra
el archivo dentro de la carpeta de su OT y servirá para el futuro matching del XLSX.

Todas las lecturas son sin efectos secundarios (sin flush/commit).
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import zipfile

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.service_order import ServiceOrder
from app.services.lab_work_orders import equipment_certificate_folio_resolved
from app.services.service_order_mobile_execution import active_lab_link, linked_lab_group
from app.services.storage_service import resolve_storage_path

LAB_FINAL_WORK_ORDER_STATUSES = {"completed", "partially_closed"}

BLOCKER_MESSAGES = {
    "LAB_LINK_REQUIRED": "El ETS no tiene un servicio MYC Mobile vinculado",
    "LAB_NO_ACTIVE_EQUIPMENT": "El servicio MYC Mobile vinculado no tiene equipos activos",
    "LAB_WORK_ORDER_NOT_FINAL": "La OT todavía no tiene cierre técnico en MYC Mobile",
    "LAB_CERTIFICATE_FOLIO_MISSING": "El equipo no tiene folio de certificado",
    "LAB_CERTIFICATE_FOLIO_NOT_READY": "El folio de certificado no está reservado/autorizado",
    "LAB_FIELD_SHEET_MISSING": "El equipo no tiene Hoja de Campo",
    "LAB_FIELD_SHEET_NOT_COMPLETED": "La Hoja de Campo no está completada",
    "LAB_FINAL_PDF_MISSING": "La Hoja de Campo no tiene PDF final congelado disponible",
    "LAB_FINAL_PDF_HASH_MISMATCH": "El PDF final congelado no coincide con su SHA-256",
}


def _blocker(code: str, **context) -> dict:
    return {"code": code, "message": BLOCKER_MESSAGES[code], **context}


def _final_pdf_blocker(sheet) -> str | None:
    if not sheet.final_pdf_path or not sheet.final_pdf_sha256:
        return "LAB_FINAL_PDF_MISSING"
    path = resolve_storage_path(sheet.final_pdf_path)
    if path is None or path.is_symlink() or not path.is_file():
        return "LAB_FINAL_PDF_MISSING"
    if sha256(path.read_bytes()).hexdigest() != sheet.final_pdf_sha256:
        return "LAB_FINAL_PDF_HASH_MISMATCH"
    return None


def _equipment_blockers(equipment: LabWorkOrderEquipment) -> list[str]:
    codes = []
    if not equipment.certificate_folio:
        codes.append("LAB_CERTIFICATE_FOLIO_MISSING")
    elif not equipment_certificate_folio_resolved(equipment):
        codes.append("LAB_CERTIFICATE_FOLIO_NOT_READY")
    sheet = equipment.current_field_sheet
    if sheet is None or not sheet.is_active:
        codes.append("LAB_FIELD_SHEET_MISSING")
    elif sheet.status != "completed":
        codes.append("LAB_FIELD_SHEET_NOT_COMPLETED")
    else:
        pdf_code = _final_pdf_blocker(sheet)
        if pdf_code:
            codes.append(pdf_code)
    return codes


def _operational_members(members: list[LabWorkOrder]) -> list[LabWorkOrder]:
    # Una OT cancelada no forma parte del trabajo técnico a entregar.
    return [item for item in members if item.status != "cancelled"]


def lab_package_summary(db: Session, order: ServiceOrder) -> dict:
    link = active_lab_link(db, order.id)
    summary = {
        "source": "lab",
        "service_order_id": order.id,
        "folio": order.folio,
        "ready": False,
        "ready_total": 0,
        "pending_total": 0,
        "root_folio": None,
        "groups": [],
        "blockers": [],
        # Compatibilidad con el contrato legacy (lista de OT ERP): vacía.
        "work_orders": [],
    }
    if link is None:
        summary["blockers"].append(_blocker("LAB_LINK_REQUIRED"))
        return summary
    members = _operational_members(linked_lab_group(db, link.lab_root_work_order_id))
    summary["root_folio"] = next(
        (item.folio for item in members if item.id == link.lab_root_work_order_id), None
    )
    for work_order in members:
        work_order_final = work_order.status in LAB_FINAL_WORK_ORDER_STATUSES
        group = {
            "work_order_id": work_order.id,
            "work_order_folio": work_order.folio,
            "status": work_order.status,
            "final": work_order_final,
            "ready": 0,
            "pending": 0,
            "equipment": [],
        }
        if not work_order_final:
            summary["blockers"].append(_blocker(
                "LAB_WORK_ORDER_NOT_FINAL",
                work_order_id=work_order.id, work_order_folio=work_order.folio, status=work_order.status,
            ))
        for equipment in work_order.active_equipment:
            codes = _equipment_blockers(equipment)
            if not work_order_final:
                codes = ["LAB_WORK_ORDER_NOT_FINAL", *codes]
            ready = not codes
            group["ready" if ready else "pending"] += 1
            group["equipment"].append({
                "equipment_id": equipment.id,
                "position": equipment.position,
                "instrument": equipment.instrument,
                "identification": equipment.identification,
                "certificate_folio": equipment.certificate_folio,
                "folio_status": equipment.folio_status,
                "field_sheet_status": (
                    equipment.current_field_sheet.status if equipment.current_field_sheet else None
                ),
                "ready": ready,
                "blockers": codes,
            })
            for code in codes:
                if code == "LAB_WORK_ORDER_NOT_FINAL":
                    continue
                summary["blockers"].append(_blocker(
                    code,
                    work_order_id=work_order.id, work_order_folio=work_order.folio,
                    equipment_id=equipment.id, position=equipment.position,
                    instrument=equipment.instrument, certificate_folio=equipment.certificate_folio,
                ))
        summary["groups"].append(group)
        summary["ready_total"] += group["ready"]
        summary["pending_total"] += group["pending"]
    if summary["ready_total"] + summary["pending_total"] == 0:
        summary["blockers"].append(_blocker("LAB_NO_ACTIVE_EQUIPMENT"))
    summary["ready"] = not summary["blockers"]
    return summary


def _folder(value: str) -> str:
    # Import local: capture_packages importa este módulo para despachar.
    from app.services.capture_packages import normalized_filename

    return normalized_filename(value) or value


def lab_service_order_package(db: Session, order: ServiceOrder) -> tuple[bytes, str]:
    """ZIP PDF-only: OT-<folio OT>/Hoja_Campo_<certificate_folio>.pdf.

    El ZIP ya se nombra con el folio ETS: no hay carpeta exterior del ETS ni
    carpeta intermedia por folio de certificado (el folio va en el nombre).

    Todo-o-nada: sólo se entrega cuando la readiness LAB completa está lista;
    un grupo parcialmente incompleto sigue bloqueado."""
    summary = lab_package_summary(db, order)
    if not summary["ready"]:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "LAB_CAPTURE_PACKAGE_BLOCKED",
                "message": "El paquete de Captura MYC Mobile está bloqueado; consulta los bloqueos",
                "blockers": summary["blockers"],
            },
        )
    link = active_lab_link(db, order.id)
    members = _operational_members(linked_lab_group(db, link.lab_root_work_order_id))
    ets = _folder(order.folio or f"ETS-{order.id}")
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for work_order in members:
            for equipment in work_order.active_equipment:
                sheet = equipment.current_field_sheet
                path = resolve_storage_path(sheet.final_pdf_path)
                content = path.read_bytes()
                if sha256(content).hexdigest() != sheet.final_pdf_sha256:
                    raise HTTPException(status_code=409, detail="El PDF final congelado no coincide con su SHA-256")
                folio = _folder(equipment.certificate_folio)
                archive.writestr(f"OT-{work_order.folio}/Hoja_Campo_{folio}.pdf", content)
    return buffer.getvalue(), f"{ets}.zip"
