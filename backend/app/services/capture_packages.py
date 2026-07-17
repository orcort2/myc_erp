"""Generation and ingestion of calibration capture packages.

All selection is intentionally server-side: a browser never decides whether an
instrument is eligible or which template/version it receives.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from unicodedata import normalize
import shutil
import zipfile

from fastapi import HTTPException, UploadFile
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.certificate import Certificate, CertificateCaptureFile
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.models.controlled_document import ControlledDocument, ControlledDocumentVersion
from app.models.service_order import ServiceOrder, ServiceWorkOrder
from app.services.field_sheet_pdfs import generate_field_sheet_pdf
from app.services.storage_service import build_storage_path, resolve_storage_path


EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}


def normalized_filename(value: str) -> str:
    value = normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    value = " ".join(value.upper().split())
    return "".join("-" if char in r'\\/:*?\"<>|' else char for char in value).strip()


def _ets_name(order: ServiceOrder) -> str:
    return normalized_filename(order.folio or f"ETS-{order.id}") or f"ETS-{order.id}"


def _work_order_folder(order: ServiceOrder, work_order: ServiceWorkOrder) -> str:
    return f"{_ets_name(order)} - OT-{work_order.work_order_number:04d}"


def equipment_base_name(certificate: Certificate, field_sheet: FieldSheet) -> str:
    equipment = certificate.equipment
    if not certificate.expected_folio and not certificate.folio:
        raise ValueError("Falta folio de certificado")
    if not equipment.name:
        raise ValueError("Falta nombre de equipo")
    if not equipment.internal_id:
        raise ValueError("Falta identificación")
    if not field_sheet.next_calibration_date:
        raise ValueError("Falta fecha de próxima calibración")
    return normalized_filename(
        f"{certificate.expected_folio or certificate.folio} {equipment.name} "
        f"{equipment.internal_id} {field_sheet.next_calibration_date:%Y.%m.%d}"
    )


@dataclass
class EligibleItem:
    equipment: Equipment
    field_sheet: FieldSheet | None
    certificate: Certificate | None
    reason: str | None = None

    @property
    def ready(self) -> bool:
        return self.reason is None


def _load_equipment(db: Session, *, service_order_id: int, work_order_id: int | None = None) -> list[Equipment]:
    query = select(Equipment).where(Equipment.service_order_id == service_order_id, Equipment.is_active.is_(True)).options(
        selectinload(Equipment.certificates), selectinload(Equipment.field_sheets)
    )
    if work_order_id is not None:
        query = query.where(Equipment.work_order_id == work_order_id)
    return list(db.scalars(query).all())


def eligibility_for_equipment(db: Session, equipment: Equipment) -> EligibleItem:
    # A snapshot exists only for calibration equipment configured with the master.
    if not equipment.calibration_scope:
        return EligibleItem(equipment, None, None, "El servicio no pertenece a Calibración")
    field_sheet = next((item for item in equipment.field_sheets if item.is_active), None)
    certificate = next((item for item in equipment.certificates if item.is_active), None)
    if field_sheet is None:
        return EligibleItem(equipment, None, certificate, "No tiene Hoja de Campo")
    if field_sheet.status != "completed":
        return EligibleItem(equipment, field_sheet, certificate, "La Hoja de Campo no está completada")
    if certificate is None or not (certificate.expected_folio or certificate.folio):
        return EligibleItem(equipment, field_sheet, certificate, "Falta folio de certificado asignado")
    if not equipment.name:
        return EligibleItem(equipment, field_sheet, certificate, "Falta nombre de equipo")
    if not equipment.internal_id:
        return EligibleItem(equipment, field_sheet, certificate, "Falta identificación")
    if not field_sheet.next_calibration_date:
        return EligibleItem(equipment, field_sheet, certificate, "Falta fecha de próxima calibración")
    if not equipment.certificate_master_document_id:
        return EligibleItem(equipment, field_sheet, certificate, "Falta plantilla esperada de certificado")
    if not equipment.certificate_master_version_id or not equipment.certificate_template_path_snapshot:
        return EligibleItem(equipment, field_sheet, certificate, "La versión o snapshot de plantilla no está disponible")
    master = db.get(ControlledDocument, equipment.certificate_master_document_id)
    version = db.get(ControlledDocumentVersion, equipment.certificate_master_version_id)
    if master is None or master.status != "active":
        return EligibleItem(equipment, field_sheet, certificate, "La plantilla está inactiva")
    if version is None or version.status != "active":
        return EligibleItem(equipment, field_sheet, certificate, "Falta versión activa de plantilla")
    if version.expires_on and version.expires_on < date.today():
        return EligibleItem(equipment, field_sheet, certificate, "La plantilla está caducada")
    path = resolve_storage_path(equipment.certificate_template_path_snapshot)
    if path is None or not path.is_file():
        return EligibleItem(equipment, field_sheet, certificate, "El archivo snapshot de plantilla no está disponible")
    if path.suffix.lower() != ".xlsx":
        return EligibleItem(equipment, field_sheet, certificate, "El archivo snapshot no es XLSX")
    if equipment.certificate_template_checksum_snapshot and sha256(path.read_bytes()).hexdigest() != equipment.certificate_template_checksum_snapshot:
        return EligibleItem(equipment, field_sheet, certificate, "El hash del archivo snapshot no coincide")
    return EligibleItem(equipment, field_sheet, certificate)


def package_summary(db: Session, service_order_id: int) -> dict:
    order = db.get(ServiceOrder, service_order_id)
    if order is None or not order.is_active:
        raise HTTPException(status_code=404, detail="ETS no encontrado")
    groups = []
    for work_order in db.scalars(select(ServiceWorkOrder).where(ServiceWorkOrder.service_order_id == order.id, ServiceWorkOrder.is_active.is_(True)).order_by(ServiceWorkOrder.sequence)).all():
        items = _eligible_with_pdf(db, _load_equipment(db, service_order_id=order.id, work_order_id=work_order.id))
        groups.append({"work_order_id": work_order.id, "work_order_number": work_order.work_order_number,
                       "ready": sum(item.ready for item in items), "pending": sum(not item.ready for item in items),
                       "blocked": [{"equipment_id": item.equipment.id, "equipment_name": item.equipment.name, "reason": item.reason} for item in items if not item.ready]})
    return {"service_order_id": order.id, "folio": order.folio, "work_orders": groups,
            "ready_total": sum(group["ready"] for group in groups)}


def _render_pair(db: Session, item: EligibleItem) -> tuple[str, bytes, str, bytes]:
    assert item.field_sheet and item.certificate
    base = equipment_base_name(item.certificate, item.field_sheet)
    pdf, _ = generate_field_sheet_pdf(db, item.field_sheet.id)
    template = resolve_storage_path(item.equipment.certificate_template_path_snapshot)
    assert template is not None
    extension = template.suffix.lower()
    if extension not in EXCEL_EXTENSIONS:
        raise HTTPException(status_code=422, detail="La plantilla snapshot no tiene una extensión Excel aceptada")
    excel = template.read_bytes()
    # The exact delivered Excel name is persisted and remains the sole identity
    # key for later upload; do not recreate it during ingestion.
    item.equipment.certificate_template_filename_snapshot = f"{base}{extension}"
    return f"{base}.pdf", pdf, f"{base}{extension}", excel


def _eligible_with_pdf(db: Session, equipment: list[Equipment]) -> list[EligibleItem]:
    rows = []
    for equipment_item in equipment:
        item = eligibility_for_equipment(db, equipment_item)
        if item.ready:
            try:
                generate_field_sheet_pdf(db, item.field_sheet.id)  # genuine final check
            except Exception:
                item.reason = "No se pudo generar el PDF de la Hoja de Campo"
        rows.append(item)
    return rows


def work_order_package(db: Session, service_order_id: int, work_order_id: int) -> tuple[bytes, str, str]:
    order = db.get(ServiceOrder, service_order_id)
    work_order = db.get(ServiceWorkOrder, work_order_id)
    if order is None or work_order is None or work_order.service_order_id != order.id:
        raise HTTPException(status_code=404, detail="ETS u Orden de Trabajo no encontrada")
    ready = [item for item in _eligible_with_pdf(db, _load_equipment(db, service_order_id=order.id, work_order_id=work_order.id)) if item.ready]
    if not ready:
        raise HTTPException(status_code=409, detail="No hay equipos elegibles para el paquete de Captura")
    folder = _work_order_folder(order, work_order)
    if len(ready) == 1:
        pdf_name, pdf, excel_name, excel = _render_pair(db, ready[0])
        boundary = "MYC-CAPTURE-PACKAGE"
        body = b"".join([
            f"--{boundary}\r\nContent-Type: application/pdf\r\nContent-Disposition: attachment; filename=\"{pdf_name}\"\r\n\r\n".encode(), pdf, b"\r\n",
            f"--{boundary}\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\nContent-Disposition: attachment; filename=\"{excel_name}\"\r\n\r\n".encode(), excel, b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        db.commit()
        return body, f"{folder}.multipart", f"multipart/mixed; boundary={boundary}"
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in ready:
            pdf_name, pdf, excel_name, excel = _render_pair(db, item)
            archive.writestr(f"{folder}/{pdf_name}", pdf)
            archive.writestr(f"{folder}/{excel_name}", excel)
    db.commit()
    return buffer.getvalue(), f"{folder}.zip", "application/zip"


def service_order_package(db: Session, service_order_id: int) -> tuple[bytes, str]:
    order = db.get(ServiceOrder, service_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="ETS no encontrado")
    buffer = BytesIO()
    any_file = False
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for work_order in db.scalars(select(ServiceWorkOrder).where(ServiceWorkOrder.service_order_id == order.id, ServiceWorkOrder.is_active.is_(True))).all():
            folder = _work_order_folder(order, work_order)
            for item in _eligible_with_pdf(db, _load_equipment(db, service_order_id=order.id, work_order_id=work_order.id)):
                if not item.ready:
                    continue
                pdf_name, pdf, excel_name, excel = _render_pair(db, item)
                archive.writestr(f"{_ets_name(order)}/{folder}/{pdf_name}", pdf)
                archive.writestr(f"{_ets_name(order)}/{folder}/{excel_name}", excel)
                any_file = True
    if not any_file:
        raise HTTPException(status_code=409, detail="No hay equipos elegibles; consulta el resumen de bloqueos")
    db.commit()
    return buffer.getvalue(), f"{_ets_name(order)}.zip"


def _expected_values(certificate: Certificate) -> dict[str, str]:
    sheet = certificate.field_sheet
    equipment = certificate.equipment
    client = certificate.service_order.client
    return {"folio": certificate.expected_folio or certificate.folio, "cliente": client.commercial_name or client.legal_name or "",
            "equipo": equipment.name or "", "identificacion": equipment.internal_id or "", "marca": equipment.brand or "",
            "modelo": equipment.model or "", "serie": equipment.serial_number or "", "fecha_calibracion": str(sheet.calibration_date or "") if sheet else "",
            "proxima_calibracion": str(sheet.next_calibration_date or "") if sheet else "", "servicio": equipment.calibration_scope or ""}


def _validate_excel(raw: bytes, extension: str, certificate: Certificate) -> dict:
    if extension not in {".xlsx", ".xlsm"}:
        return {key: {"status": "no_aplicable"} for key in _expected_values(certificate)}
    workbook = load_workbook(BytesIO(raw), read_only=True, data_only=True, keep_vba=extension == ".xlsm")
    observed = " ".join(str(cell.value or "") for sheet in workbook.worksheets for row in sheet.iter_rows() for cell in row)
    results = {}
    for key, expected in _expected_values(certificate).items():
        if not expected:
            results[key] = {"status": "no_aplicable"}
        elif expected.casefold() in observed.casefold():
            results[key] = {"status": "coincide", "expected": expected}
        else:
            results[key] = {"status": "no_encontrado", "expected": expected}
    return results


def upload_capture_files(db: Session, service_order_id: int, files: list[UploadFile], *, user_id: int | None) -> dict:
    order = db.get(ServiceOrder, service_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="ETS no encontrado")
    expected = {item.certificate_template_filename_snapshot: cert for item in _load_equipment(db, service_order_id=order.id) for cert in item.certificates if item.certificate_template_filename_snapshot and cert.is_active}
    candidates: list[tuple[str, bytes]] = []
    for upload in files:
        raw = upload.file.read()
        if (upload.filename or "").lower().endswith(".zip"):
            with zipfile.ZipFile(BytesIO(raw)) as archive:
                candidates.extend((Path(info.filename).name, archive.read(info)) for info in archive.infolist() if not info.is_dir())
        else:
            candidates.append((Path(upload.filename or "").name, raw))
    results = []
    for filename, raw in candidates:
        suffix = Path(filename).suffix.lower()
        if suffix not in EXCEL_EXTENSIONS or Path(filename).name.startswith("~$"):
            continue
        certificate = expected.get(filename)
        record = CertificateCaptureFile(service_order_id=order.id, certificate_id=certificate.id if certificate else None,
            original_filename=filename, identification_status="identified" if certificate else "unidentified", uploaded_by_id=user_id)
        target = build_storage_path(directory=f"capture/{order.id}", filename=f"{record.id or 'new'}-{filename}")
        target.write_bytes(raw)
        record.stored_path = target.relative_to(target.parents[2]).as_posix() if False else f"capture/{order.id}/{target.name}"
        record.validation_results = _validate_excel(raw, suffix, certificate) if certificate else {"file": {"status": "no_identificado", "message": "El nombre no coincide con un Excel entregado por el ERP"}}
        db.add(record)
        results.append({"filename": filename, "status": record.identification_status, "validation": record.validation_results})
    db.commit()
    return {"processed": results, "count": len(results)}


def list_capture_files(db: Session, service_order_id: int) -> list[CertificateCaptureFile]:
    return list(db.scalars(select(CertificateCaptureFile).where(
        CertificateCaptureFile.service_order_id == service_order_id
    ).order_by(CertificateCaptureFile.created_at.desc())).all())
