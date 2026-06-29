from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from shutil import copyfileobj
from tempfile import SpooledTemporaryFile

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.folios import FolioRequest, generate_folio
from app.models.certificate import Certificate
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.models.service_order import ServiceOrder
from app.schemas.certificate import (
    CertificateBulkUploadRead,
    CertificateCreate,
    CertificatePdfUploadRead,
    CertificateStatusChange,
    CertificateUpdate,
)
from app.services.audit_logs import write_audit_log
from app.services.certificate_matching_engine import validate_certificate_pdf_match


TERMINAL_STATUSES = {"released_to_client", "released", "cancelled"}
CAPTURE_READY_STATUSES = {"expected", "field_sheet_ready", "capture_pending", "quality_rejected", "correction_requested"}
QUALITY_READY_STATUSES = {"ready_for_quality", "quality_review"}
QUALITY_APPROVED_STATUSES = {"quality_approved", "approved", "pdf_pending", "pdf_uploaded"}

LEGACY_STATUS_MAP = {
    "generated": "capture_in_progress",
    "quality_review": "quality_review",
    "approved": "quality_approved",
    "released": "released_to_client",
    "correction_requested": "quality_rejected",
}

ALLOWED_TRANSITIONS = {
    "draft": {"expected", "capture_pending", "cancelled", "suspended"},
    "expected": {"field_sheet_ready", "capture_pending", "capture_in_progress", "cancelled", "suspended"},
    "field_sheet_ready": {"capture_pending", "capture_in_progress", "cancelled", "suspended"},
    "capture_pending": {"capture_in_progress", "ready_for_quality", "cancelled", "suspended"},
    "capture_in_progress": {"ready_for_quality", "quality_rejected", "cancelled", "suspended"},
    "ready_for_quality": {"quality_review", "quality_approved", "quality_rejected", "cancelled", "suspended"},
    "quality_review": {"quality_approved", "quality_rejected", "cancelled", "suspended"},
    "quality_rejected": {"capture_in_progress", "ready_for_quality", "cancelled", "suspended"},
    "quality_approved": {"pdf_pending", "pdf_uploaded", "released_to_client", "suspended"},
    "pdf_pending": {"pdf_uploaded", "released_to_client", "suspended"},
    "pdf_uploaded": {"released_to_client", "suspended"},
    "released_to_client": set(),
    "cancelled": set(),
    "suspended": {"capture_pending", "cancelled"},
    # Legacy compatibility
    "generated": {"quality_review", "quality_rejected", "cancelled", "suspended"},
    "correction_requested": {"capture_in_progress", "ready_for_quality", "cancelled", "suspended"},
    "approved": {"pdf_pending", "pdf_uploaded", "released_to_client", "suspended"},
    "released": set(),
}


def _with_relations():
    return (
        selectinload(Certificate.service_order),
        selectinload(Certificate.equipment),
        selectinload(Certificate.field_sheet),
    )


def _json_safe(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _next_certificate_folio(
    db: Session, *, certificate_type: str, issued_on: date
) -> str:
    service_type = "acreditado" if certificate_type == "acreditado" else "trazable"
    prefix = "MYCA" if service_type == "acreditado" else "MYCT"
    prefix = f"{prefix}-{issued_on:%m}-{issued_on:%Y}-"
    last_folio = db.scalar(
        select(Certificate.folio)
        .where(Certificate.folio.like(f"{prefix}%"))
        .order_by(Certificate.folio.desc())
        .limit(1)
    )
    sequence = 1 if not last_folio else int(last_folio.rsplit("-", 1)[-1]) + 1
    return generate_folio(
        FolioRequest(
            document_type="certificado",
            service_type=service_type,
            issued_on=issued_on,
            sequence=sequence,
        )
    )


def _validate_certificate_links(db: Session, payload: CertificateCreate) -> None:
    service_order = db.scalar(
        select(ServiceOrder).where(
            ServiceOrder.id == payload.service_order_id,
            ServiceOrder.is_active.is_(True),
        )
    )
    if service_order is None:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada")
    if service_order.status in {"closed", "cancelled"}:
        raise HTTPException(status_code=409, detail="No se puede crear certificado para una orden cerrada o cancelada")

    equipment = db.scalar(
        select(Equipment).where(
            Equipment.id == payload.equipment_id,
            Equipment.is_active.is_(True),
        )
    )
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    if equipment.service_order_id != payload.service_order_id:
        raise HTTPException(status_code=409, detail="El equipo no pertenece a la orden de servicio indicada")

    if payload.field_sheet_id is not None:
        field_sheet = db.scalar(
            select(FieldSheet).where(
                FieldSheet.id == payload.field_sheet_id,
                FieldSheet.is_active.is_(True),
            )
        )
        if field_sheet is None:
            raise HTTPException(status_code=404, detail="Hoja de campo no encontrada")
        if field_sheet.equipment_id != payload.equipment_id:
            raise HTTPException(status_code=409, detail="La hoja de campo no pertenece al equipo indicado")


def _ensure_no_active_certificate(db: Session, field_sheet_id: int | None) -> None:
    if field_sheet_id is None:
        return
    exists = db.scalar(
        select(Certificate.id).where(
            Certificate.field_sheet_id == field_sheet_id,
            Certificate.is_active.is_(True),
        )
    )
    if exists is not None:
        raise HTTPException(status_code=409, detail="La hoja de campo ya tiene un certificado activo")


def list_certificates(
    db: Session,
    *,
    service_order_id: int | None = None,
    equipment_id: int | None = None,
    client_visible: bool | None = None,
    include_inactive: bool = False,
) -> list[Certificate]:
    query = select(Certificate).options(*_with_relations()).order_by(Certificate.created_at.desc())
    if service_order_id is not None:
        query = query.where(Certificate.service_order_id == service_order_id)
    if equipment_id is not None:
        query = query.where(Certificate.equipment_id == equipment_id)
    if client_visible is not None:
        query = query.where(Certificate.client_visible.is_(client_visible))
    if not include_inactive:
        query = query.where(Certificate.is_active.is_(True))
    return list(db.scalars(query).all())


def get_certificate(db: Session, certificate_id: int) -> Certificate:
    certificate = db.scalar(
        select(Certificate).where(Certificate.id == certificate_id).options(*_with_relations())
    )
    if certificate is None or not certificate.is_active:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    return certificate


def create_certificate(
    db: Session, payload: CertificateCreate, *, user_id: int | None = None
) -> Certificate:
    _validate_certificate_links(db, payload)
    _ensure_no_active_certificate(db, payload.field_sheet_id)
    issued_on = payload.issued_on or date.today()
    folio = payload.expected_folio or _next_certificate_folio(
        db,
        certificate_type=payload.certificate_type,
        issued_on=issued_on,
    )
    certificate = Certificate(
        **payload.model_dump(exclude={"issued_on", "expected_folio"}),
        folio=folio,
        expected_folio=folio,
        issued_on=issued_on,
        status="expected",
        external_source="excel",
        match_status="pending",
        client_visible=False,
    )
    db.add(certificate)
    db.flush()
    write_audit_log(
        db,
        action="certificate.expected_created",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        new_values={
            "folio": certificate.folio,
            "expected_folio": certificate.expected_folio,
            "service_order_id": certificate.service_order_id,
            "equipment_id": certificate.equipment_id,
            "field_sheet_id": certificate.field_sheet_id,
            "status": certificate.status,
        },
    )
    db.commit()
    return get_certificate(db, certificate.id)


def update_certificate(
    db: Session,
    certificate_id: int,
    payload: CertificateUpdate,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    if certificate.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail="No se puede editar un certificado liberado o cancelado")
    updates = payload.model_dump(exclude_unset=True)
    previous_values = {key: getattr(certificate, key) for key in updates}
    for key, value in updates.items():
        setattr(certificate, key, value)
        if key == "expected_folio" and value:
            certificate.folio = value
    write_audit_log(
        db,
        action="certificate.updated",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        previous_values=_json_safe(previous_values),
        new_values=_json_safe(updates),
    )
    db.commit()
    return get_certificate(db, certificate.id)


def _set_status(
    db: Session,
    certificate: Certificate,
    new_status: str,
    *,
    action: str,
    user_id: int | None = None,
    comment: str | None = None,
    extra_values: dict | None = None,
) -> Certificate:
    previous_status = certificate.status
    certificate.status = new_status
    write_audit_log(
        db,
        action=action,
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": new_status, **(extra_values or {})},
        comment=comment,
    )
    db.commit()
    return get_certificate(db, certificate.id)


def change_status(
    db: Session,
    certificate_id: int,
    new_status: str,
    payload: CertificateStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Certificate:
    new_status = LEGACY_STATUS_MAP.get(new_status, new_status)
    certificate = get_certificate(db, certificate_id)
    allowed = ALLOWED_TRANSITIONS.get(certificate.status, set())
    if new_status not in allowed and certificate.status != new_status:
        raise HTTPException(status_code=409, detail=f"Transicion no permitida: {certificate.status} -> {new_status}")
    if new_status == "capture_in_progress":
        return start_capture(db, certificate_id, payload, user_id=user_id)
    if new_status == "ready_for_quality":
        return send_to_quality(db, certificate_id, payload, user_id=user_id)
    if new_status == "quality_approved":
        return quality_approve(db, certificate_id, payload, user_id=user_id)
    if new_status == "quality_rejected":
        return quality_reject(db, certificate_id, payload, user_id=user_id)
    if new_status == "released_to_client":
        return release_to_client(db, certificate_id, payload, user_id=user_id)
    if new_status == "pdf_pending":
        certificate.status = "pdf_pending"
        db.commit()
        return get_certificate(db, certificate.id)
    return _set_status(
        db,
        certificate,
        new_status,
        action=f"certificate.{new_status}",
        user_id=user_id,
        comment=payload.comment if payload else None,
    )


def start_capture(
    db: Session,
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    if certificate.status not in CAPTURE_READY_STATUSES:
        raise HTTPException(status_code=409, detail="El certificado no esta listo para captura")
    now = datetime.now(timezone.utc)
    certificate.capture_started_at = certificate.capture_started_at or now
    certificate.capture_started_by_id = certificate.capture_started_by_id or user_id
    return _set_status(
        db,
        certificate,
        "capture_in_progress",
        action="certificate.capture_started",
        user_id=user_id,
        comment=payload.comment if payload else None,
        extra_values={"capture_started_at": now.isoformat()},
    )


def send_to_quality(
    db: Session,
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    if certificate.status not in {"capture_in_progress", "capture_pending", "quality_rejected", "correction_requested"}:
        raise HTTPException(status_code=409, detail="El certificado no puede enviarse a calidad desde este estado")
    now = datetime.now(timezone.utc)
    certificate.sent_to_quality_at = now
    certificate.sent_to_quality_by_id = user_id
    return _set_status(
        db,
        certificate,
        "ready_for_quality",
        action="certificate.sent_to_quality",
        user_id=user_id,
        comment=payload.comment if payload else None,
        extra_values={"sent_to_quality_at": now.isoformat()},
    )


def quality_approve(
    db: Session,
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    if certificate.status not in QUALITY_READY_STATUSES:
        raise HTTPException(status_code=409, detail="El certificado no esta en revision de calidad")
    now = datetime.now(timezone.utc)
    certificate.quality_reviewed_at = now
    certificate.quality_reviewed_by_id = user_id
    certificate.quality_rejection_reason = None
    next_status = "pdf_uploaded" if certificate.final_pdf_path else "pdf_pending"
    return _set_status(
        db,
        certificate,
        next_status,
        action="certificate.quality_approved",
        user_id=user_id,
        comment=payload.comment if payload else None,
        extra_values={"quality_reviewed_at": now.isoformat()},
    )


def quality_reject(
    db: Session,
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    if certificate.status not in QUALITY_READY_STATUSES | {"quality_approved", "pdf_pending", "pdf_uploaded"}:
        raise HTTPException(status_code=409, detail="El certificado no puede rechazarse desde este estado")
    now = datetime.now(timezone.utc)
    certificate.quality_reviewed_at = now
    certificate.quality_reviewed_by_id = user_id
    certificate.quality_rejection_reason = (payload.reason or payload.comment) if payload else None
    return _set_status(
        db,
        certificate,
        "quality_rejected",
        action="certificate.quality_rejected",
        user_id=user_id,
        comment=payload.comment if payload else None,
        extra_values={"quality_rejection_reason": certificate.quality_rejection_reason},
    )


def _safe_filename(name: str) -> str:
    return "".join(char if char.isalnum() or char in ".-_" else "_" for char in name).strip("._") or "certificado.pdf"


def _storage_dir(certificate: Certificate) -> Path:
    key = str(certificate.service_order.work_order_number if certificate.service_order else certificate.service_order_id)
    storage_root = Path(settings.storage_root)
    if not storage_root.is_absolute():
        storage_root = Path(__file__).resolve().parents[3] / storage_root
    path = storage_root / "certificados" / key
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_upload(certificate: Certificate, upload: UploadFile) -> tuple[str, str]:
    original = upload.filename or "certificado.pdf"
    if not original.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Solo se permiten archivos PDF")
    filename = f"{certificate.expected_folio or certificate.folio}_{_safe_filename(original)}"
    target = _storage_dir(certificate) / filename
    with target.open("wb") as buffer:
        copyfileobj(upload.file, buffer)
    return str(target), original


def upload_certificate_pdf(
    db: Session,
    certificate_id: int,
    upload: UploadFile,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    path, original = _save_upload(certificate, upload)
    now = datetime.now(timezone.utc)
    certificate.final_pdf_path = path
    certificate.final_pdf_original_filename = original
    certificate.final_pdf_uploaded_at = now
    certificate.final_pdf_uploaded_by_id = user_id
    certificate.status = "pdf_uploaded" if certificate.status in QUALITY_APPROVED_STATUSES else certificate.status
    result = validate_certificate_pdf_match(certificate, original)
    certificate.match_status = result["status"]
    certificate.match_details = result
    write_audit_log(
        db,
        action="certificate.pdf_uploaded",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        new_values={
            "filename": original,
            "match_status": certificate.match_status,
            "status": certificate.status,
        },
    )
    write_audit_log(
        db,
        action="certificate.pdf_match_validated",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        new_values={"match_status": certificate.match_status, "score": result["score"]},
    )
    db.commit()
    return get_certificate(db, certificate.id)


def validate_pdf_match(
    db: Session,
    certificate_id: int,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    result = validate_certificate_pdf_match(certificate)
    certificate.match_status = result["status"]
    certificate.match_details = result
    write_audit_log(
        db,
        action="certificate.pdf_match_validated",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        new_values={"match_status": certificate.match_status, "score": result["score"]},
    )
    db.commit()
    return get_certificate(db, certificate.id)


def manual_accept_match(
    db: Session,
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    details = certificate.match_details or {}
    details["manual_acceptance"] = {
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "comment": payload.comment if payload else None,
    }
    certificate.match_status = "manual_accepted"
    certificate.match_details = details
    write_audit_log(
        db,
        action="certificate.pdf_match_manual_accepted",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        new_values={"match_status": certificate.match_status},
        comment=payload.comment if payload else None,
    )
    db.commit()
    return get_certificate(db, certificate.id)


def release_to_client(
    db: Session,
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    if certificate.status not in QUALITY_APPROVED_STATUSES:
        raise HTTPException(status_code=409, detail="Solo certificados aprobados por calidad pueden liberarse")
    if not certificate.final_pdf_path:
        raise HTTPException(status_code=409, detail="No se puede liberar sin PDF final")
    if certificate.match_status not in {"matched", "manual_accepted", "warning"}:
        raise HTTPException(status_code=409, detail="El PDF no tiene match aceptable")
    now = datetime.now(timezone.utc)
    certificate.client_visible = True
    certificate.released_to_client_at = now
    certificate.released_to_client_by_id = user_id
    certificate.released_on = date.today()
    return _set_status(
        db,
        certificate,
        "released_to_client",
        action="certificate.released_to_client",
        user_id=user_id,
        comment=payload.comment if payload else None,
        extra_values={"client_visible": True, "released_to_client_at": now.isoformat()},
    )


def request_correction(
    db: Session,
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Certificate:
    return quality_reject(db, certificate_id, payload, user_id=user_id)


def bulk_upload_certificate_pdfs(
    db: Session,
    service_order_id: int,
    uploads: list[UploadFile],
    *,
    user_id: int | None = None,
) -> CertificateBulkUploadRead:
    certificates = list_certificates(db, service_order_id=service_order_id)
    pending = [item for item in certificates if item.status != "released_to_client"]
    results: list[CertificatePdfUploadRead] = []
    used: set[int] = set()
    for upload in uploads:
        filename = upload.filename or ""
        candidates = sorted(
            [item for item in pending if item.id not in used],
            key=lambda item: validate_certificate_pdf_match(item, filename)["score"],
            reverse=True,
        )
        if not candidates:
            continue
        best = candidates[0]
        # Reset file pointer in case future upload implementations read before saving.
        upload.file.seek(0)
        updated = upload_certificate_pdf(db, best.id, upload, user_id=user_id)
        used.add(best.id)
        results.append(
            CertificatePdfUploadRead(
                certificate_id=updated.id,
                filename=filename,
                match_status=updated.match_status,
                match_details=updated.match_details or {},
            )
        )
    matched = len([item for item in results if item.match_status == "matched"])
    warnings = len([item for item in results if item.match_status in {"warning", "manual_accepted"}])
    mismatches = len([item for item in results if item.match_status == "mismatch"])
    summary = CertificateBulkUploadRead(
        service_order_id=service_order_id,
        expected=len(certificates),
        uploaded=len(uploads),
        matched=matched,
        warnings=warnings,
        mismatches=mismatches,
        missing=max(len(certificates) - len(used), 0),
        results=results,
    )
    write_audit_log(
        db,
        action="certificate.bulk_pdf_upload",
        entity="service_orders",
        entity_id=service_order_id,
        user_id=user_id,
        new_values=summary.model_dump(exclude={"results"}),
    )
    db.commit()
    return summary


def deactivate_certificate(
    db: Session, certificate_id: int, *, user_id: int | None = None
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    if certificate.status in {"released_to_client", "released"}:
        raise HTTPException(status_code=409, detail="No se puede cancelar un certificado liberado")
    certificate.is_active = False
    certificate.status = "cancelled"
    certificate.client_visible = False
    certificate.deleted_at = datetime.now(timezone.utc)
    certificate.deleted_by = user_id
    write_audit_log(
        db,
        action="certificate.deactivated",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        previous_values={"is_active": True},
        new_values={"is_active": False, "status": "cancelled"},
    )
    db.commit()
    return certificate
