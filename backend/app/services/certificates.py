from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.folios import FolioRequest, generate_folio
from app.models.certificate import Certificate, CertificateCaptureFile, CertificatePdfVersion
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.models.invoice import Invoice
from app.models.service_order import ServiceOrder
from app.schemas.certificate import (
    CertificateBatchActionItemRead,
    CertificateBatchActionRead,
    CertificateBulkUploadRead,
    CertificateCreate,
    CertificatePdfUploadRead,
    CertificateStatusChange,
    CertificateUpdate,
)
from app.services.audit_logs import write_audit_log
from app.services.certificate_authentication import authenticate_certificate_pdf
from app.services.certificate_matching_engine import validate_certificate_pdf_match
from app.services.storage_service import delete_if_unreferenced, resolve_storage_path, safe_filename, save_upload


TERMINAL_STATUSES = {"released_to_client", "released", "cancelled"}
CAPTURE_READY_STATUSES = {"expected", "field_sheet_ready", "capture_pending", "quality_rejected", "correction_requested", "returned_to_technician"}
QUALITY_READY_STATUSES = {"ready_for_quality", "quality_review"}
QUALITY_APPROVED_STATUSES = {"quality_approved", "approved"}
AUTHENTICATED_STATUSES = {"authenticated"}

LEGACY_STATUS_MAP = {
    "generated": "capture_in_progress",
    "quality_review": "quality_review",
    "approved": "quality_approved",
    "released": "released_to_client",
    "quality_rejected": "correction_requested",
    "returned_to_technician": "correction_requested",
}

ALLOWED_TRANSITIONS = {
    "draft": {"expected", "capture_pending", "cancelled", "suspended"},
    "expected": {"field_sheet_ready", "capture_pending", "capture_in_progress", "cancelled", "suspended"},
    "field_sheet_ready": {"capture_pending", "capture_in_progress", "cancelled", "suspended"},
    "capture_pending": {"capture_in_progress", "ready_for_quality", "cancelled", "suspended"},
    "capture_in_progress": {"quality_review", "quality_rejected", "cancelled", "suspended"},
    "ready_for_quality": {"quality_review", "quality_approved", "match_validated", "correction_requested", "cancelled", "suspended"},
    "quality_review": {"quality_approved", "match_validated", "correction_requested", "cancelled", "suspended"},
    "match_validated": {"quality_approved", "correction_requested", "cancelled", "suspended"},
    "quality_rejected": {"capture_in_progress", "ready_for_quality", "cancelled", "suspended"},
    "returned_to_technician": {"capture_in_progress", "ready_for_quality", "cancelled", "suspended"},
    "quality_approved": {"authenticated", "pdf_pending", "pdf_uploaded", "suspended"},
    "pdf_pending": {"pdf_uploaded", "authenticated", "suspended"},
    "pdf_uploaded": {"ready_for_quality", "authenticated", "suspended"},
    "authenticated": {"released_to_client", "suspended"},
    "released_to_client": set(),
    "cancelled": set(),
    "suspended": {"capture_pending", "cancelled"},
    # Legacy compatibility
    "generated": {"quality_review", "quality_rejected", "cancelled", "suspended"},
    "correction_requested": {"capture_in_progress", "ready_for_quality", "cancelled", "suspended"},
    "approved": {"authenticated", "suspended"},
    "released": set(),
}


def _with_relations():
    return (
        selectinload(Certificate.service_order),
        selectinload(Certificate.equipment),
        selectinload(Certificate.field_sheet),
        selectinload(Certificate.pdf_versions),
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
    if certificate_type == "acreditado":
        service_type = "acreditado"
        prefix = "MYCA"
    elif certificate_type == "vinculado":
        service_type = "vinculado"
        prefix = "MYCV"
    else:
        service_type = "trazable"
        prefix = "MYCT"
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


def get_service_order_release_readiness(db: Session, service_order_id: int) -> dict:
    """Single source of truth for the financial gate before client release."""
    service_order = db.get(ServiceOrder, service_order_id)
    if service_order is None or not service_order.is_active:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada")
    if not service_order.requires_payment:
        return {
            "release_allowed": True,
            "payment_status": "not_required",
            "reason": "La orden no requiere pago para liberar certificados.",
        }

    invoices = list(
        db.scalars(
            select(Invoice).where(
                Invoice.service_order_id == service_order_id,
                Invoice.is_active.is_(True),
                Invoice.status != "cancelled",
            )
        ).all()
    )
    if not invoices:
        return {
            "release_allowed": False,
            "payment_status": "pending",
            "reason": "No se puede liberar: no existe una factura liquidada para este ETS.",
        }

    unpaid = [invoice for invoice in invoices if invoice.status != "paid" or getattr(invoice, "balance_due", 0) > 0]
    if unpaid:
        return {
            "release_allowed": False,
            "payment_status": "pending",
            "reason": "No se puede liberar: pago pendiente.",
        }
    return {
        "release_allowed": True,
        "payment_status": "paid",
        "reason": "Pago confirmado para las facturas activas del ETS.",
    }


def _ensure_payment_allows_release(db: Session, certificate: Certificate, *, user_id: int | None = None) -> None:
    readiness = get_service_order_release_readiness(db, certificate.service_order_id)
    if readiness["release_allowed"]:
        return
    write_audit_log(
        db,
        action="certificate.release_blocked",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        previous_values={"status": certificate.status},
        new_values={"payment_status": readiness["payment_status"], "reason": readiness["reason"]},
        comment=readiness["reason"],
    )
    db.commit()
    raise HTTPException(
        status_code=409,
        detail={"code": "payment_pending", "message": readiness["reason"]},
    )


def _authenticated_document_exists(certificate: Certificate) -> bool:
    path = resolve_storage_path(certificate.authenticated_pdf_path)
    if path is None:
        return False
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _release_conflict(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": message})


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


def _ensure_no_active_certificate_for_equipment(
    db: Session,
    service_order_id: int,
    equipment_id: int,
) -> None:
    exists = db.scalar(
        select(Certificate.id).where(
            Certificate.service_order_id == service_order_id,
            Certificate.equipment_id == equipment_id,
            Certificate.is_active.is_(True),
        )
    )
    if exists is not None:
        raise HTTPException(
            status_code=409,
            detail="El equipo ya tiene un certificado activo",
        )


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
    _ensure_no_active_certificate_for_equipment(
        db,
        payload.service_order_id,
        payload.equipment_id,
    )
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
    if new_status == "quality_review":
        return send_to_quality(db, certificate_id, payload, user_id=user_id)
    if new_status == "ready_for_quality":
        return send_to_quality(db, certificate_id, payload, user_id=user_id)
    if new_status == "quality_approved":
        return quality_approve(db, certificate_id, payload, user_id=user_id)
    if new_status == "correction_requested":
        return return_to_technician(db, certificate_id, payload, user_id=user_id)
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


def capture_master_readiness(db: Session, certificate: Certificate | int) -> dict:
    if isinstance(certificate, int):
        certificate = get_certificate(db, certificate)
    equipment = certificate.equipment
    master_expected = bool(
        equipment
        and equipment.certificate_master_document_id
        and equipment.certificate_master_version_id
        and equipment.certificate_template_path_snapshot
    )
    capture_file = db.scalar(
        select(CertificateCaptureFile)
        .where(
            CertificateCaptureFile.certificate_id == certificate.id,
            CertificateCaptureFile.identification_status == "identified",
        )
        .order_by(CertificateCaptureFile.created_at.desc(), CertificateCaptureFile.id.desc())
        .limit(1)
    )
    warnings = []
    mismatches = []
    for key, result in ((capture_file.validation_results if capture_file else {}) or {}).items():
        status = result.get("status") if isinstance(result, dict) else None
        item = {"field": key, **result} if isinstance(result, dict) else {"field": key, "status": status}
        if status == "no_encontrado":
            warnings.append(item)
        elif status in {"mismatch", "no_coincide"}:
            mismatches.append(item)
    ready = master_expected and capture_file is not None and not mismatches
    if not master_expected:
        reason = "El certificado no tiene un Master esperado"
    elif capture_file is None:
        reason = "El Master esperado no está identificado"
    elif mismatches:
        reason = "El Master identificado contiene diferencias bloqueantes"
    else:
        reason = None
    return {
        "certificate_id": certificate.id,
        "service_order_id": certificate.service_order_id,
        "master_expected": master_expected,
        "identified": capture_file is not None,
        "ready": ready,
        "reason": reason,
        "warnings": warnings,
        "mismatches": mismatches,
        "master": None if capture_file is None else {
            "id": capture_file.id,
            "filename": capture_file.original_filename,
            "stored_path": capture_file.stored_path,
            "status": capture_file.identification_status,
            "validation": capture_file.validation_results,
            "uploaded_by_id": capture_file.uploaded_by_id,
            "created_at": capture_file.created_at,
        },
    }


def list_capture_master_readiness(db: Session, *, service_order_id: int | None = None) -> list[dict]:
    query = select(Certificate).where(Certificate.is_active.is_(True)).options(*_with_relations())
    if service_order_id is not None:
        query = query.where(Certificate.service_order_id == service_order_id)
    return [capture_master_readiness(db, certificate) for certificate in db.scalars(query.order_by(Certificate.id)).unique().all()]


def send_to_quality(
    db: Session,
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    readiness = capture_master_readiness(db, certificate)
    if not readiness["ready"]:
        raise HTTPException(status_code=409, detail=readiness["reason"])
    now = datetime.now(timezone.utc)
    if certificate.status != "capture_in_progress":
        if certificate.status not in CAPTURE_READY_STATUSES:
            raise HTTPException(status_code=409, detail="El certificado no puede enviarse a calidad desde este estado")
        previous_status = certificate.status
        certificate.status = "capture_in_progress"
        certificate.capture_started_at = certificate.capture_started_at or now
        certificate.capture_started_by_id = certificate.capture_started_by_id or user_id
        write_audit_log(
            db,
            action="certificate.capture_started",
            entity="certificates",
            entity_id=certificate.id,
            user_id=user_id,
            previous_values={"status": previous_status},
            new_values={
                "status": "capture_in_progress",
                "capture_started_at": certificate.capture_started_at.isoformat(),
                "capture_master_file_id": readiness["master"]["id"],
            },
            comment="Normalización al enviar un Master identificado a Calidad",
        )
    certificate.sent_to_quality_at = now
    certificate.sent_to_quality_by_id = user_id
    if certificate.service_order and certificate.service_order.status in {"capture", "technical_review", "in_progress"}:
        certificate.service_order.status = "quality_review"
    return _set_status(
        db,
        certificate,
        "quality_review",
        action="certificate.sent_to_quality",
        user_id=user_id,
        comment=payload.comment if payload else None,
        extra_values={
            "sent_to_quality_at": now.isoformat(),
            "capture_master_file_id": readiness["master"]["id"],
            "capture_master_filename": readiness["master"]["filename"],
        },
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
        raise HTTPException(status_code=409, detail="El certificado no está en revisión de Calidad")
    readiness = capture_master_readiness(db, certificate)
    if not readiness["ready"]:
        raise HTTPException(status_code=409, detail=readiness["reason"])
    now = datetime.now(timezone.utc)
    certificate.quality_reviewed_at = now
    certificate.quality_reviewed_by_id = user_id
    certificate.quality_rejection_reason = None
    return _set_status(
        db,
        certificate,
        "quality_approved",
        action="certificate.quality_approved",
        user_id=user_id,
        comment=payload.comment if payload else None,
        extra_values={
            "quality_reviewed_at": now.isoformat(),
            "capture_master_file_id": readiness["master"]["id"],
            "capture_master_filename": readiness["master"]["filename"],
        },
    )


def quality_reject(
    db: Session,
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Certificate:
    # Ruta conservada sólo por compatibilidad; ya no existe un flujo de rechazo.
    return return_to_technician(db, certificate_id, payload, user_id=user_id)


def return_to_technician(
    db: Session,
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    if certificate.status not in QUALITY_READY_STATUSES | {"match_validated", "quality_approved"}:
        raise HTTPException(status_code=409, detail="El certificado no puede regresarse a Captura desde este estado")
    reason = (payload.reason or payload.comment) if payload else None
    if not reason or not reason.strip():
        raise HTTPException(status_code=422, detail="El comentario de corrección es obligatorio")
    certificate.quality_rejection_reason = reason.strip()
    certificate.quality_reviewed_at = datetime.now(timezone.utc)
    certificate.quality_reviewed_by_id = user_id
    readiness = capture_master_readiness(db, certificate)
    return _set_status(
        db,
        certificate,
        "correction_requested",
        action="certificate.returned_to_capture",
        user_id=user_id,
        comment=reason.strip(),
        extra_values={
            "reason": reason.strip(),
            "field_sheet_id": certificate.field_sheet_id,
            "capture_master_file_id": readiness["master"]["id"] if readiness["master"] else None,
            "capture_master_filename": readiness["master"]["filename"] if readiness["master"] else None,
        },
    )


def _storage_dir(certificate: Certificate) -> Path:
    key = str(certificate.service_order.work_order_number if certificate.service_order else certificate.service_order_id)
    return Path("certificados") / key


def _save_upload(certificate: Certificate, upload: UploadFile, version_number: int) -> tuple[str, str]:
    original = upload.filename or "certificado.pdf"
    if not original.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Solo se permiten archivos PDF")
    filename = f"{certificate.expected_folio or certificate.folio}_v{version_number}_{safe_filename(original, fallback='certificado.pdf')}"
    stored_file = save_upload(
        upload,
        directory=_storage_dir(certificate),
        filename=filename,
        allowed_extensions={".pdf"},
    )
    return str(stored_file.absolute_path), original


def upload_certificate_pdf(
    db: Session,
    certificate_id: int,
    upload: UploadFile,
    *,
    user_id: int | None = None,
    comment: str | None = None,
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    if certificate.authenticated_pdf_path or certificate.status in AUTHENTICATED_STATUSES | TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail="El PDF original no puede reemplazarse después de autenticar")
    if certificate.status not in CAPTURE_READY_STATUSES | {"capture_in_progress", "pdf_uploaded"}:
        raise HTTPException(status_code=409, detail="El PDF solo puede cargarse durante Captura")
    source_status = certificate.status
    previous_final_pdf_path = certificate.final_pdf_path
    if previous_final_pdf_path and not certificate.pdf_versions:
        db.add(CertificatePdfVersion(
            certificate_id=certificate.id,
            version_number=1,
            file_path=previous_final_pdf_path,
            original_filename=certificate.final_pdf_original_filename,
            uploaded_at=certificate.final_pdf_uploaded_at or certificate.updated_at,
            uploaded_by_id=certificate.final_pdf_uploaded_by_id,
            source_status=source_status,
            change_reason="Versión anterior incorporada al historial",
            is_current=False,
        ))
        next_version = 2
    else:
        next_version = max((item.version_number for item in certificate.pdf_versions), default=0) + 1
    path, original = _save_upload(certificate, upload, next_version)
    now = datetime.now(timezone.utc)
    for version in certificate.pdf_versions:
        version.is_current = False
    db.add(CertificatePdfVersion(
        certificate_id=certificate.id,
        version_number=next_version,
        file_path=path,
        original_filename=original,
        uploaded_at=now,
        uploaded_by_id=user_id,
        source_status=source_status,
        change_reason=comment or certificate.quality_rejection_reason,
        is_current=True,
    ))
    certificate.final_pdf_path = path
    certificate.final_pdf_original_filename = original
    certificate.final_pdf_uploaded_at = now
    certificate.final_pdf_uploaded_by_id = user_id
    certificate.authentication_code = None
    certificate.authentication_hash = None
    certificate.authenticated_pdf_path = None
    certificate.authenticated_pdf_generated_at = None
    certificate.authenticated_by_id = None
    certificate.verification_url = None
    if certificate.status in {
        "expected",
        "field_sheet_ready",
        "capture_pending",
        "capture_in_progress",
        "quality_rejected",
        "returned_to_technician",
        "correction_requested",
    }:
        certificate.status = "pdf_uploaded"
    elif certificate.status in QUALITY_APPROVED_STATUSES:
        certificate.status = "pdf_uploaded"
    precheck = validate_certificate_pdf_match(certificate, original)
    certificate.match_status = "pending"
    certificate.match_details = {
        **precheck,
        "status": "pending",
        "precheck_status": precheck["status"],
        "validated_by_quality": False,
    }
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
            "authenticated_pdf_path": None,
            "version_number": next_version,
            "replaces_pdf_path": previous_final_pdf_path,
        },
        comment=comment or certificate.quality_rejection_reason,
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
    if certificate.status not in QUALITY_READY_STATUSES:
        raise HTTPException(status_code=409, detail="El match solo puede validarse durante Calidad")
    if not certificate.final_pdf_path:
        raise HTTPException(status_code=409, detail="No se puede validar el match sin PDF original")
    result = validate_certificate_pdf_match(certificate)
    result["validated_by_quality"] = True
    result["validated_by_id"] = user_id
    certificate.match_status = result["status"]
    certificate.match_details = result
    previous_status = certificate.status
    certificate.status = "match_validated"
    write_audit_log(
        db,
        action="certificate.pdf_match_validated",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": certificate.status, "match_status": certificate.match_status, "score": result["score"]},
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
    if certificate.status != "match_validated":
        raise HTTPException(status_code=409, detail="Primero debe validarse el match en Calidad")
    if certificate.match_status not in {"mismatch", "warning"}:
        raise HTTPException(status_code=409, detail="La aceptación manual sólo aplica a matches con discrepancias")
    if not certificate.final_pdf_path:
        raise HTTPException(status_code=409, detail="No se puede aceptar el match sin PDF original")
    details = certificate.match_details or {}
    details["manual_acceptance"] = {
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "accepted_by_id": user_id,
        "comment": payload.comment if payload else None,
    }
    certificate.match_status = "manual_accepted"
    certificate.match_details = details
    previous_status = certificate.status
    certificate.status = "match_validated"
    write_audit_log(
        db,
        action="certificate.pdf_match_manual_accepted",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": certificate.status, "match_status": certificate.match_status},
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
    if certificate.status in {"released_to_client", "released"} or certificate.client_visible:
        raise _release_conflict("already_released", "El certificado ya fue liberado al cliente.")
    if certificate.status not in AUTHENTICATED_STATUSES:
        raise _release_conflict(
            "certificate_not_authenticated",
            "El certificado debe estar autenticado antes de liberarse.",
        )
    if not _authenticated_document_exists(certificate):
        raise _release_conflict(
            "authenticated_document_missing",
            "No se encontró el documento autenticado correspondiente.",
        )
    _ensure_payment_allows_release(db, certificate, user_id=user_id)
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
    if not certificates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay certificados esperados para asociar PDFs.",
        )
    pending = [item for item in certificates if item.status != "released_to_client"]
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay certificados pendientes para asociar PDFs.",
        )
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
        precheck = validate_certificate_pdf_match(best, filename)
        # Reset file pointer in case future upload implementations read before saving.
        upload.file.seek(0)
        updated = upload_certificate_pdf(db, best.id, upload, user_id=user_id)
        used.add(best.id)
        results.append(
            CertificatePdfUploadRead(
                certificate_id=updated.id,
                filename=filename,
                match_status=precheck["status"],
                match_details={**precheck, "precheck_only": True},
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


def authenticate_certificates_for_service_order(
    db: Session,
    service_order_id: int,
    *,
    user_id: int | None = None,
) -> CertificateBatchActionRead:
    certificates = list_certificates(db, service_order_id=service_order_id)
    results: list[CertificateBatchActionItemRead] = []
    authenticated = 0
    skipped = 0
    errors = 0
    allowed_statuses = QUALITY_APPROVED_STATUSES | {"quality_approved", "approved"}

    for certificate in certificates:
        folio = certificate.expected_folio or certificate.folio
        if certificate.authenticated_pdf_path and certificate.status in AUTHENTICATED_STATUSES | {"released_to_client", "released"}:
            skipped += 1
            results.append(
                CertificateBatchActionItemRead(
                    certificate_id=certificate.id,
                    folio=folio,
                    status="skipped",
                    authenticated_pdf_path=certificate.authenticated_pdf_path,
                    error="Ya tiene PDF autenticado",
                )
            )
            continue
        if certificate.status not in allowed_statuses:
            skipped += 1
            results.append(
                CertificateBatchActionItemRead(
                    certificate_id=certificate.id,
                    folio=folio,
                    status="skipped",
                    error="No está aprobado por Calidad",
                )
            )
            continue
        try:
            updated = authenticate_certificate_pdf(db, certificate, user_id=user_id)
            db.commit()
            authenticated += 1
            results.append(
                CertificateBatchActionItemRead(
                    certificate_id=updated.id,
                    folio=folio,
                    status="authenticated",
                    authenticated_pdf_path=updated.authenticated_pdf_path,
                )
            )
        except Exception as exc:  # noqa: BLE001 - batch mode must continue per certificate.
            db.rollback()
            errors += 1
            results.append(
                CertificateBatchActionItemRead(
                    certificate_id=certificate.id,
                    folio=folio,
                    status="error",
                    error=str(exc),
                )
            )

    return CertificateBatchActionRead(
        service_order_id=service_order_id,
        authenticated=authenticated,
        skipped=skipped,
        errors=errors,
        results=results,
    )


def release_authenticated_certificates_for_service_order(
    db: Session,
    service_order_id: int,
    *,
    user_id: int | None = None,
) -> CertificateBatchActionRead:
    certificates = list_certificates(db, service_order_id=service_order_id)
    readiness = get_service_order_release_readiness(db, service_order_id)
    if not readiness["release_allowed"]:
        write_audit_log(
            db,
            action="certificate.release_blocked",
            entity="service_orders",
            entity_id=service_order_id,
            user_id=user_id,
            new_values={"payment_status": readiness["payment_status"], "reason": readiness["reason"]},
            comment=readiness["reason"],
        )
        db.commit()
        raise HTTPException(
            status_code=409,
            detail={"code": "payment_pending", "message": readiness["reason"]},
        )
    results: list[CertificateBatchActionItemRead] = []
    released = 0
    skipped = 0
    errors = 0

    for certificate in certificates:
        folio = certificate.expected_folio or certificate.folio
        if certificate.client_visible or certificate.status in {"released_to_client", "released"}:
            skipped += 1
            results.append(
                CertificateBatchActionItemRead(
                    certificate_id=certificate.id,
                    folio=folio,
                    status="skipped",
                    authenticated_pdf_path=certificate.authenticated_pdf_path,
                    error="already_released",
                )
            )
            continue
        if (
            certificate.status not in AUTHENTICATED_STATUSES
            or not _authenticated_document_exists(certificate)
        ):
            skipped += 1
            results.append(
                CertificateBatchActionItemRead(
                    certificate_id=certificate.id,
                    folio=folio,
                    status="skipped",
                    authenticated_pdf_path=certificate.authenticated_pdf_path,
                    error=(
                        "certificate_not_authenticated"
                        if certificate.status not in AUTHENTICATED_STATUSES
                        else "authenticated_document_missing"
                    ),
                )
            )
            continue
        try:
            now = datetime.now(timezone.utc)
            previous_status = certificate.status
            certificate.client_visible = True
            certificate.released_to_client_at = now
            certificate.released_to_client_by_id = user_id
            certificate.released_on = date.today()
            certificate.status = "released_to_client"
            write_audit_log(
                db,
                action="certificate.released_to_client",
                entity="certificates",
                entity_id=certificate.id,
                user_id=user_id,
                previous_values={"status": previous_status, "client_visible": False},
                new_values={"status": "released_to_client", "client_visible": True},
            )
            db.commit()
            released += 1
            results.append(
                CertificateBatchActionItemRead(
                    certificate_id=certificate.id,
                    folio=folio,
                    status="released",
                    authenticated_pdf_path=certificate.authenticated_pdf_path,
                )
            )
        except Exception as exc:  # noqa: BLE001 - batch mode must continue per certificate.
            db.rollback()
            errors += 1
            results.append(
                CertificateBatchActionItemRead(
                    certificate_id=certificate.id,
                    folio=folio,
                    status="error",
                    authenticated_pdf_path=certificate.authenticated_pdf_path,
                    error=str(exc),
                )
            )

    service_order = db.get(ServiceOrder, service_order_id)
    if service_order is not None and certificates:
        refreshed = list_certificates(db, service_order_id=service_order_id)
        if refreshed and all(item.status == "released_to_client" for item in refreshed):
            service_order.status = "released"
            db.commit()

    return CertificateBatchActionRead(
        service_order_id=service_order_id,
        released=released,
        skipped=skipped,
        errors=errors,
        results=results,
    )


def deactivate_certificate(
    db: Session, certificate_id: int, *, user_id: int | None = None
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    if certificate.status in {"released_to_client", "released"}:
        raise HTTPException(status_code=409, detail="No se puede cancelar un certificado liberado")
    previous_final_pdf_path = certificate.final_pdf_path
    previous_final_pdf_filename = certificate.final_pdf_original_filename
    previous_authenticated_pdf_path = certificate.authenticated_pdf_path
    certificate.is_active = False
    certificate.status = "cancelled"
    certificate.client_visible = False
    certificate.deleted_at = datetime.now(timezone.utc)
    certificate.deleted_by = user_id
    certificate.final_pdf_path = None
    certificate.final_pdf_original_filename = None
    certificate.final_pdf_uploaded_at = None
    certificate.final_pdf_uploaded_by_id = None
    certificate.authentication_code = None
    certificate.authentication_hash = None
    certificate.authenticated_pdf_path = None
    certificate.authenticated_pdf_generated_at = None
    certificate.authenticated_by_id = None
    certificate.verification_url = None
    write_audit_log(
        db,
        action="certificate.deactivated",
        entity="certificates",
        entity_id=certificate.id,
        user_id=user_id,
        previous_values={"is_active": True},
        new_values={"is_active": False, "status": "cancelled", "files_cleared": True},
    )
    delete_if_unreferenced(
        db,
        previous_final_pdf_path,
        user_id=user_id,
        module="Certificados",
        entity="certificates",
        entity_id=certificate.id,
        filename=previous_final_pdf_filename,
    )
    delete_if_unreferenced(
        db,
        previous_authenticated_pdf_path,
        user_id=user_id,
        module="Certificados",
        entity="certificates",
        entity_id=certificate.id,
        filename=Path(previous_authenticated_pdf_path).name if previous_authenticated_pdf_path else None,
    )
    db.commit()
    return certificate
