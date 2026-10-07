from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.lab_work_order import LabWorkOrderEquipment
from app.models.technical_report import TechnicalReport, TechnicalReportEvidence
from app.models.user import User
from app.schemas.technical_report import (
    TechnicalReportCaptureUpdate,
    TechnicalReportCreate,
    TechnicalReportEvidenceType,
    TechnicalReportRead,
)
from app.schemas.technical_report_installation import (
    INSTALLATION_SCHEMA_VERSION,
    InstallationCaptureValues,
    check_installation_consistency,
)
from app.services.audit_logs import write_audit_log
from app.services.file_security import validate_upload
from app.services.storage_service import (
    delete_if_unreferenced,
    require_deliverable_file,
    save_validated_content,
)


TECHNICAL_REPORT_SEQUENCE_PREFIXES = {
    "installation": "MYC-IN",
}

ENABLED_TECHNICAL_REPORT_TYPES = {
    "installation",
}

# Un reporte sólo se edita (captura y evidencia) mientras no esté listo para
# firmas: ready_for_signatures/completed son inmutables salvo reapertura formal
# (SG-4J); cancelled nunca.
EDITABLE_TECHNICAL_REPORT_STATUSES = frozenset({"draft", "in_progress"})

# Límites de evidencia (centralizados). El tamaño por archivo vive en
# file_security.TECHNICAL_REPORT_EVIDENCE_MAX_BYTES junto con la política MIME.
MAX_EVIDENCE_PER_REPORT = 20
EVIDENCE_MIME_BY_EXTENSION = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}

CLIENT_CONFORMITY_TEXT_INSTALLATION = (
    "El cliente confirma que el equipo o producto fue instalado, "
    "se verificó su funcionamiento y se recibe de conformidad con "
    "el servicio realizado."
)


def _get_equipment_for_technical_report(
    db: Session,
    work_order_id: int,
    equipment_id: int,
) -> LabWorkOrderEquipment:
    equipment = db.scalar(
        select(LabWorkOrderEquipment)
        .where(
            LabWorkOrderEquipment.id == equipment_id,
            LabWorkOrderEquipment.work_order_id == work_order_id,
            LabWorkOrderEquipment.is_active.is_(True),
        )
        .options(
            selectinload(LabWorkOrderEquipment.work_order),
            selectinload(LabWorkOrderEquipment.technical_reports),
            selectinload(LabWorkOrderEquipment.current_technical_report),
        )
    )

    if equipment is None:
        raise HTTPException(
            status_code=404,
            detail="Equipo de OT no encontrado",
        )

    return equipment


def _technical_report_prefix(report_type: str) -> str:
    prefix = TECHNICAL_REPORT_SEQUENCE_PREFIXES.get(report_type)
    if prefix is None:
        raise HTTPException(
            status_code=422,
            detail="Tipo de reporte sin serie institucional configurada",
        )
    return prefix


def _allocate_technical_report_folio(
    db: Session,
    report_type: str,
    *,
    issued_on: date | None = None,
) -> str:
    """Reserva el siguiente folio institucional del tipo de reporte.

    La secuencia XXXX es anual. MM sólo forma parte del folio visible.

    Ejemplo:
        2026-10 / sequence=1 -> MYC-IN10-26-0001
        2026-11 / sequence=2 -> MYC-IN11-26-0002
    """

    prefix = _technical_report_prefix(report_type)
    today = issued_on or date.today()

    lock_key = f"technical_report:{prefix}:{today.year}"

    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": lock_key},
        )

    counter = db.scalar(
        select(InstitutionalFolioSequence)
        .where(
            InstitutionalFolioSequence.document_type == "technical_report",
            InstitutionalFolioSequence.prefix == prefix,
            InstitutionalFolioSequence.year == today.year,
        )
        .with_for_update()
    )

    if counter is None:
        counter = InstitutionalFolioSequence(
            document_type="technical_report",
            prefix=prefix,
            year=today.year,
            next_value=1,
        )
        db.add(counter)
        db.flush()

    sequence = counter.next_value

    if sequence < 1:
        raise HTTPException(
            status_code=409,
            detail="La secuencia institucional del reporte es inválida",
        )

    if sequence > 9999:
        raise HTTPException(
            status_code=409,
            detail=f"Se agotó la secuencia anual {prefix} {today.year}",
        )

    counter.next_value = sequence + 1
    db.flush()

    return (
        f"{prefix}{today.strftime('%m')}-"
        f"{today.strftime('%y')}-"
        f"{sequence:04d}"
    )


def _installation_document_snapshot(
    equipment: LabWorkOrderEquipment,
) -> dict:
    order = equipment.work_order

    return {
        "work_order": {
            "id": order.id,
            "folio": order.folio,
            "operational_category": order.operational_category,
            "reception_date": (
                order.reception_date.isoformat()
                if order.reception_date
                else None
            ),
            "purchase_order": order.purchase_order,
        },
        "client": {
            "name": order.client_name,
            "address": order.address,
            "contact_name": order.contact_name,
            "contact_phone": order.contact_phone,
            "contact_email": order.contact_email,
            "postal_code": order.postal_code,
            "city": order.city,
            "state_name": order.state_name,
        },
        "equipment": {
            "id": equipment.id,
            "position": equipment.position,
            "instrument": equipment.instrument,
            "brand": equipment.brand,
            "model": equipment.model,
            "identification": equipment.identification,
            "serial_number": equipment.serial_number,
            "report_number": equipment.report_number,
            "observations": equipment.observations,
            "is_good_condition": equipment.is_good_condition,
        },
    }


def _create_technical_report_uncommitted(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: TechnicalReportCreate,
    user: User,
) -> TechnicalReport:
    """Crea una revisión inicial de reporte sin hacer commit.

    El caller controla la transacción. Esta es la autoridad reutilizable para
    endpoint público, pruebas y futuras operaciones atómicas.
    """
    equipment = _get_equipment_for_technical_report(
        db,
        work_order_id,
        equipment_id,
    )

    order = equipment.work_order

    if order.operational_category != "general_service":
        raise HTTPException(
            status_code=409,
            detail="Los reportes técnicos sólo están disponibles para Servicio General",
        )

    # Mismo lifecycle que la captura de FieldSheets: el reporte pertenece a la
    # etapa técnica, es decir, DESPUÉS de firmar la recepción.
    if order.status not in {"received_signed", "in_progress"}:
        raise HTTPException(
            status_code=409,
            detail="La OT no admite captura técnica: firma primero la recepción",
        )

    if payload.report_type not in ENABLED_TECHNICAL_REPORT_TYPES:
        raise HTTPException(
            status_code=409,
            detail="Este tipo de reporte todavía no está habilitado",
        )

    current = equipment.current_technical_report
    if current is not None:
        raise HTTPException(
            status_code=409,
            detail="El equipo ya tiene un reporte técnico vigente",
        )

    # Servicio General y calibración son verticales distintas. Un equipo que
    # ya recibió modalidad/folio metrológico no puede convertirse
    # silenciosamente en reporte técnico.
    if equipment.service_type is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "El equipo de Servicio General no debe tener modalidad "
                "metrológica asignada"
            ),
        )

    if (
        equipment.certificate_folio is not None
        or equipment.automatic_certificate_folio is not None
        or equipment.folio_status != "unassigned"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "El equipo de Servicio General tiene estado de folio "
                "metrológico incompatible"
            ),
        )

    folio = _allocate_technical_report_folio(
        db,
        payload.report_type,
    )

    conformity_text = (
        CLIENT_CONFORMITY_TEXT_INSTALLATION
        if payload.report_type == "installation"
        else None
    )

    report = TechnicalReport(
        lab_equipment_id=equipment.id,
        report_type=payload.report_type,
        folio=folio,
        status="draft",
        capture_values={},
        document_snapshot=_installation_document_snapshot(equipment),
        report_schema_version=1,
        revision_number=1,
        is_current=True,
        client_conformity_text_snapshot=conformity_text,
    )

    db.add(report)
    db.flush()

    # Primera mutación técnica real: received_signed -> in_progress, igual que
    # la primera FieldSheet de calibración (backend-authoritative).
    if order.status == "received_signed":
        order.status = "in_progress"
        write_audit_log(
            db,
            action="lab_work_order.capture_started",
            entity="lab_work_orders",
            entity_id=order.id,
            user_id=user.id,
            previous_values={"status": "received_signed"},
            new_values={"status": "in_progress", "technical_report_id": report.id},
        )

    write_audit_log(
        db,
        action="technical_report.created",
        entity="technical_reports",
        entity_id=report.id,
        user_id=user.id,
        new_values={
            "work_order_id": order.id,
            "work_order_folio": order.folio,
            "lab_equipment_id": equipment.id,
            "report_type": report.report_type,
            "folio": report.folio,
            "revision_number": report.revision_number,
        },
    )

    return report


def _read_technical_report_by_id(
    db: Session,
    report_id: int,
) -> TechnicalReportRead:
    report = db.scalar(
        select(TechnicalReport)
        .where(TechnicalReport.id == report_id)
        .options(
            selectinload(TechnicalReport.evidence),
        )
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Reporte técnico no encontrado",
        )

    return TechnicalReportRead.model_validate(report)


def create_technical_report(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: TechnicalReportCreate,
    user: User,
) -> TechnicalReportRead:
    try:
        report = _create_technical_report_uncommitted(
            db,
            work_order_id,
            equipment_id,
            payload,
            user,
        )
        report_id = report.id
        db.commit()
        return _read_technical_report_by_id(db, report_id)
    except Exception:
        db.rollback()
        raise

def read_technical_report(
    db: Session,
    work_order_id: int,
    equipment_id: int,
) -> TechnicalReportRead:
    equipment = _get_equipment_for_technical_report(
        db,
        work_order_id,
        equipment_id,
    )

    report = equipment.current_technical_report

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="El equipo no tiene reporte técnico vigente",
        )

    report = db.scalar(
        select(TechnicalReport)
        .where(TechnicalReport.id == report.id)
        .options(
            selectinload(TechnicalReport.evidence),
        )
    )

    assert report is not None

    return TechnicalReportRead.model_validate(report)


# ---------------------------------------------------------------------------
# SG-4A/B: captura (capture_values)
# ---------------------------------------------------------------------------

def _lock_current_report(
    db: Session,
    work_order_id: int,
    equipment_id: int,
) -> TechnicalReport:
    """Reporte vigente de la ruta, bloqueado para escritura.

    La pertenencia se resuelve desde la ruta (OT -> equipo -> vigente): un
    reporte de otro equipo u OT nunca es alcanzable."""
    equipment = _get_equipment_for_technical_report(db, work_order_id, equipment_id)
    current = equipment.current_technical_report
    if current is None:
        raise HTTPException(status_code=404, detail="El equipo no tiene reporte técnico vigente")
    report = db.scalar(
        select(TechnicalReport)
        .where(TechnicalReport.id == current.id, TechnicalReport.is_current.is_(True))
        .options(selectinload(TechnicalReport.evidence))
        .with_for_update()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="El equipo no tiene reporte técnico vigente")
    return report


def _ensure_editable(report: TechnicalReport) -> None:
    if report.status not in EDITABLE_TECHNICAL_REPORT_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="El reporte ya no es editable",
        )


def _promote_to_in_progress(report: TechnicalReport) -> None:
    """Primera captura real (valores o evidencia): draft -> in_progress."""
    if report.status == "draft":
        report.status = "in_progress"


def update_technical_report_capture(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: TechnicalReportCaptureUpdate,
    user: User,
) -> TechnicalReportRead:
    """Autosave del borrador: sólo toca `capture_values` (más el estado
    draft -> in_progress en la primera captura). Folio, tipo, revisión, firma,
    PDF y responsable jamás se modifican aquí."""
    try:
        report = _lock_current_report(db, work_order_id, equipment_id)
        _ensure_editable(report)
        if report.report_type != "installation" or report.report_schema_version != INSTALLATION_SCHEMA_VERSION:
            raise HTTPException(
                status_code=409,
                detail="Este tipo de reporte todavía no admite captura",
            )
        current = InstallationCaptureValues.model_validate(report.capture_values or {})
        changes = payload.capture_values.model_dump(exclude_unset=True)
        try:
            merged = InstallationCaptureValues.model_validate({**current.model_dump(), **changes})
            check_installation_consistency(merged)
        except (ValidationError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        stored = merged.model_dump(mode="json", exclude_none=True)
        if stored != (report.capture_values or {}):
            report.capture_values = stored
        if stored:
            _promote_to_in_progress(report)
        report_id = report.id
        db.commit()
        return _read_technical_report_by_id(db, report_id)
    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# SG-4C: evidencia fotográfica
# ---------------------------------------------------------------------------

def _recompact_evidence_positions(db: Session, report: TechnicalReport) -> None:
    """Deja las posiciones en 1..N. Se actualiza en orden ascendente con flush
    por fila: la restricción única (reporte, posición) no es diferible."""
    ordered = sorted(report.evidence, key=lambda item: item.position)
    for index, item in enumerate(ordered, start=1):
        if item.position != index:
            item.position = index
            db.flush()


def add_technical_report_evidence(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    *,
    evidence_type: TechnicalReportEvidenceType,
    caption: str | None,
    upload: UploadFile,
    user: User,
) -> TechnicalReportEvidence:
    # Contenido validado antes de tocar la base: extensión, MIME declarado,
    # firma binaria, decodificación real con Pillow, tamaño y no vacío.
    validated = validate_upload(upload, "technical_report_evidence")
    stored_relative_path: str | None = None
    try:
        report = _lock_current_report(db, work_order_id, equipment_id)
        _ensure_editable(report)
        if len(report.evidence) >= MAX_EVIDENCE_PER_REPORT:
            raise HTTPException(
                status_code=409,
                detail=f"El reporte ya tiene el máximo de {MAX_EVIDENCE_PER_REPORT} fotografías",
            )
        position = max((item.position for item in report.evidence), default=0) + 1
        stored = save_validated_content(
            directory=Path("technical-reports") / str(report.id) / "evidence",
            filename=f"{uuid4().hex}{validated.extension}",
            content=validated.content,
            original_filename=validated.original_filename,
        )
        stored_relative_path = stored.relative_path
        evidence = TechnicalReportEvidence(
            technical_report_id=report.id,
            evidence_type=evidence_type,
            storage_path=stored.relative_path,
            mime_type=EVIDENCE_MIME_BY_EXTENSION[validated.extension],
            sha256=validated.checksum_sha256,
            size_bytes=len(validated.content),
            position=position,
            caption=(caption or "").strip()[:255] or None,
            created_by_user_id=user.id,
        )
        db.add(evidence)
        db.flush()
        _promote_to_in_progress(report)
        write_audit_log(
            db,
            action="technical_report.evidence_added",
            entity="technical_report_evidence",
            entity_id=evidence.id,
            user_id=user.id,
            new_values={
                "technical_report_id": report.id,
                "evidence_type": evidence_type,
                "position": position,
                "sha256": evidence.sha256,
                "size_bytes": evidence.size_bytes,
            },
        )
        db.commit()
        db.refresh(evidence)
        return evidence
    except Exception:
        db.rollback()
        if stored_relative_path is not None:
            delete_if_unreferenced(
                db,
                stored_relative_path,
                user_id=user.id,
                module="technical_reports",
                entity="technical_report_evidence",
                entity_id=None,
                reason="Evidencia descartada: la operación no se confirmó.",
            )
            db.commit()
        raise


def delete_technical_report_evidence(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    evidence_id: int,
    user: User,
) -> TechnicalReportRead:
    try:
        report = _lock_current_report(db, work_order_id, equipment_id)
        _ensure_editable(report)
        evidence = next((item for item in report.evidence if item.id == evidence_id), None)
        if evidence is None:
            raise HTTPException(status_code=404, detail="Evidencia no encontrada")
        removed_path = evidence.storage_path
        removed_position = evidence.position
        report.evidence.remove(evidence)
        db.flush()
        _recompact_evidence_positions(db, report)
        write_audit_log(
            db,
            action="technical_report.evidence_deleted",
            entity="technical_report_evidence",
            entity_id=evidence_id,
            user_id=user.id,
            previous_values={
                "technical_report_id": report.id,
                "position": removed_position,
            },
        )
        report_id = report.id
        db.commit()
    except Exception:
        db.rollback()
        raise
    # El archivo se retira sólo después de confirmar la baja en base de datos.
    delete_if_unreferenced(
        db,
        removed_path,
        user_id=user.id,
        module="technical_reports",
        entity="technical_report_evidence",
        entity_id=evidence_id,
        reason="Evidencia eliminada por el técnico mientras el reporte era editable.",
    )
    db.commit()
    return _read_technical_report_by_id(db, report_id)


def resolve_technical_report_evidence_file(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    evidence_id: int,
) -> tuple[Path, str]:
    equipment = _get_equipment_for_technical_report(db, work_order_id, equipment_id)
    report = equipment.current_technical_report
    if report is None:
        raise HTTPException(status_code=404, detail="El equipo no tiene reporte técnico vigente")
    evidence = db.scalar(
        select(TechnicalReportEvidence).where(
            TechnicalReportEvidence.id == evidence_id,
            TechnicalReportEvidence.technical_report_id == report.id,
        )
    )
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada")
    return require_deliverable_file(evidence.storage_path), evidence.mime_type
