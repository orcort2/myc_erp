from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.technical_intervention import TechnicalIntervention, TechnicalInterventionDelivery
from app.models.technical_report import TechnicalReport, TechnicalReportEvidence
from app.models.user import User
from app.schemas.technical_report import (
    TechnicalReportCaptureUpdate,
    TechnicalReportCreate,
    TechnicalReportDraftDeleted,
    TechnicalReportEvidenceType,
    TechnicalReportRead,
    TechnicalReportRetype,
)
from app.schemas.technical_report_installation import (
    INSTALLATION_FIELD_LABELS,
    INSTALLATION_SCHEMA_VERSION,
    InstallationCaptureValues,
    check_installation_consistency,
    installation_missing_fields,
)
from app.services.audit_logs import write_audit_log
from app.services.lab_work_order_deliveries import resolve_current_delivery_for_intervention
from app.services.lab_work_orders import sync_general_service_readiness
from app.services.technical_interventions import (
    InterventionRef,
    current_deliveries_for_equipment,
)
from app.services.technical_report_pdfs import (
    INSTALLATION_REPORT_RENDERER_VERSION,
    build_installation_final_snapshot,
    installation_report_filename,
    load_evidence_images,
    render_installation_report_pdf,
    validate_signature_data_url,
)
from app.services.file_security import validate_upload
from app.services.storage_service import (
    delete_if_unreferenced,
    require_deliverable_file,
    resolve_storage_path,
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
    # Serializa la creación por equipo: dos solicitudes simultáneas no pueden
    # crear dos intervenciones/reportes vigentes (la segunda ve el vigente y
    # responde 409 en lugar de chocar con el índice único).
    db.scalar(
        select(LabWorkOrderEquipment.id)
        .where(LabWorkOrderEquipment.id == equipment_id)
        .with_for_update()
    )
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

    # SG-4J-A1: la intervención es la identidad estable del trabajo técnico.
    # Hoy se crea exactamente una por reporte, de forma transparente; el folio
    # institucional pertenece a la intervención y el reporte conserva su copia.
    intervention = TechnicalIntervention(
        lab_equipment_id=equipment.id,
        intervention_type=payload.report_type,
        folio=folio,
        status="open",
        created_by_user_id=user.id,
    )
    db.add(intervention)
    db.flush()

    report = TechnicalReport(
        intervention_id=intervention.id,
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


# ---------------------------------------------------------------------------
# SG-4D/E: confirmar captura
# ---------------------------------------------------------------------------

def _installation_confirmation_problems(report: TechnicalReport) -> tuple[list[str], list[str]]:
    """Validación COMPLETA de Installation v1 (sólo al confirmar).

    Devuelve (campos faltantes, otros problemas). El autosave jamás pasa por
    aquí: acepta borradores incompletos."""
    values = InstallationCaptureValues.model_validate(report.capture_values or {})
    missing = installation_missing_fields(values)
    problems: list[str] = []
    try:
        check_installation_consistency(values)
    except ValueError as exc:
        problems.append(str(exc))
    has_incident_evidence = any(item.evidence_type == "incident" for item in report.evidence)
    if values.has_incidents is False and has_incident_evidence:
        problems.append(
            "Indicaste que no hubo incidencias, pero el reporte tiene evidencias de incidencia: "
            "elimínalas o indica que sí hubo incidencias"
        )
    return missing, problems


def confirm_technical_report_capture(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    user: User,
) -> TechnicalReportRead:
    """Confirma la captura: valida completo, fija al técnico responsable y
    pasa `in_progress -> ready_for_signatures`.

    Es una transición explícita y separada del autosave. Desde `draft` no es
    coherente confirmar: un reporte pasa a `in_progress` con su primera
    captura (valores o foto), y sin captura la validación completa no puede
    cumplirse; se rechaza con un mensaje claro en lugar de abrir una
    transición arbitraria. Una segunda confirmación no vuelve a mutar nada."""
    try:
        report = _lock_current_report(db, work_order_id, equipment_id)
        if report.status == "draft":
            raise HTTPException(
                status_code=409,
                detail="Aún no hay captura: llena el reporte antes de confirmarlo",
            )
        _ensure_editable(report)  # ready_for_signatures / completed / cancelled -> 409
        if report.report_type != "installation" or report.report_schema_version != INSTALLATION_SCHEMA_VERSION:
            raise HTTPException(
                status_code=409,
                detail="Este tipo de reporte todavía no admite confirmación",
            )
        missing, problems = _installation_confirmation_problems(report)
        if missing or problems:
            labels = [INSTALLATION_FIELD_LABELS.get(field, field) for field in missing]
            parts = []
            if labels:
                parts.append("Faltan: " + ", ".join(labels))
            parts.extend(problems)
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "TECHNICAL_REPORT_INCOMPLETE",
                    "message": ". ".join(parts) + ".",
                    "missing_fields": missing,
                },
            )
        report.performed_by_user_id = user.id
        report.performed_by_name_snapshot = (user.full_name or user.username or "").strip() or None
        report.performed_at = datetime.now(timezone.utc)
        report.status = "ready_for_signatures"
        write_audit_log(
            db,
            action="technical_report.capture_confirmed",
            entity="technical_reports",
            entity_id=report.id,
            user_id=user.id,
            previous_values={"status": "in_progress"},
            new_values={
                "status": "ready_for_signatures",
                "performed_by_user_id": user.id,
                "folio": report.folio,
                "revision_number": report.revision_number,
            },
        )
        report_id = report.id
        db.commit()
        return _read_technical_report_by_id(db, report_id)
    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# SG-4G: PDF institucional y cierre documental del reporte
# ---------------------------------------------------------------------------

def _link_report_to_delivery(db: Session, report: TechnicalReport, delivery, item) -> None:
    """SG-4J-A1: deja constancia exacta de la entrega que usó el PDF final de
    esta revisión (además del snapshot). No cambia ningún comportamiento."""
    intervention = report.intervention
    if intervention is None:
        return
    intervention.status = "completed"
    link = db.scalar(
        select(TechnicalInterventionDelivery).where(
            TechnicalInterventionDelivery.intervention_id == intervention.id,
            TechnicalInterventionDelivery.delivery_id == delivery.id,
        )
    )
    if link is None:
        link = TechnicalInterventionDelivery(
            intervention_id=intervention.id, delivery_id=delivery.id,
            delivery_item_id=item.id if item is not None else None,
        )
        db.add(link)
    link.technical_report_id = report.id
    db.flush()


def finalize_technical_report(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    user: User,
) -> TechnicalReportRead:
    """`ready_for_signatures` + entrega válida -> PDF final + `completed`.

    Todo ocurre en una sola unidad: se valida, se congela el snapshot, se
    renderiza, se escribe el archivo y SÓLO entonces se confirma la base. Si
    cualquier paso falla (incluido el commit) la base hace rollback y el
    archivo recién escrito se elimina: el reporte sigue en
    `ready_for_signatures` sin ningún `final_pdf_*`. Una segunda llamada sobre
    un reporte ya completado devuelve el documento existente sin regenerarlo
    (regenerar = revisión formal, SG-4J)."""
    written_path: str | None = None
    try:
        report = _lock_current_report(db, work_order_id, equipment_id)
        if report.status == "completed":
            if not report.final_pdf_path:
                raise HTTPException(status_code=409, detail="El reporte está completado pero no tiene PDF final")
            return _read_technical_report_by_id(db, report.id)
        if report.status != "ready_for_signatures" or report.final_pdf_path:
            raise HTTPException(
                status_code=409,
                detail="El reporte debe tener la captura finalizada antes de generar el documento final",
            )
        if report.report_type != "installation" or report.report_schema_version != INSTALLATION_SCHEMA_VERSION:
            raise HTTPException(status_code=409, detail="Este tipo de reporte todavía no genera documento final")
        if not (report.performed_by_user_id and report.performed_by_name_snapshot and report.performed_at):
            raise HTTPException(status_code=409, detail="El reporte no tiene técnico responsable confirmado")
        if not report.client_conformity_text_snapshot:
            raise HTTPException(status_code=409, detail="El reporte no tiene texto de conformidad congelado")
        missing, problems = _installation_confirmation_problems(report)
        if missing or problems:
            raise HTTPException(status_code=409, detail="La captura del reporte no es válida para el documento final")

        delivery, item = resolve_current_delivery_for_intervention(
            db, report.lab_equipment, InterventionRef(report.intervention, report),
        )
        if not delivery.recipient_name.strip() or delivery.delivered_at is None:
            raise HTTPException(status_code=409, detail="La entrega no tiene receptor o fecha")
        signatures = {
            "delivered_by": validate_signature_data_url(delivery.delivered_by_signature_data_url, "firma de quien entrega"),
            "recipient": validate_signature_data_url(delivery.recipient_signature_data_url, "firma de quien recibe"),
        }
        del signatures  # sólo valida; el render usa las data URLs originales
        now = datetime.now(timezone.utc)
        snapshot = build_installation_final_snapshot(
            report, delivery, delivery_item_id=item.id, generated_at=now,
        )
        images = load_evidence_images(snapshot)
        pdf = render_installation_report_pdf(
            snapshot,
            images,
            {
                "delivered_by": delivery.delivered_by_signature_data_url,
                "recipient": delivery.recipient_signature_data_url,
            },
        )
        digest = hashlib.sha256(pdf).hexdigest()
        stored = save_validated_content(
            directory=Path("technical-reports") / str(report.id) / "final",
            filename=f"installation-r{report.revision_number}-{digest[:16]}.pdf",
            content=pdf,
            original_filename=installation_report_filename(snapshot),
        )
        written_path = stored.relative_path
        report.document_snapshot = snapshot
        report.pdf_renderer_version = INSTALLATION_REPORT_RENDERER_VERSION
        report.final_pdf_path = stored.relative_path
        report.final_pdf_sha256 = digest
        report.final_pdf_generated_at = now
        report.completed_at = now
        report.status = "completed"
        _link_report_to_delivery(db, report, delivery, item)
        write_audit_log(
            db,
            action="technical_report.finalized",
            entity="technical_reports",
            entity_id=report.id,
            user_id=user.id,
            previous_values={"status": "ready_for_signatures"},
            new_values={
                "status": "completed",
                "folio": report.folio,
                "revision_number": report.revision_number,
                "delivery_id": delivery.id,
                "final_pdf_sha256": digest,
                "pdf_renderer_version": INSTALLATION_REPORT_RENDERER_VERSION,
            },
        )
        report_id = report.id
        # SG-4H: el último reporte completado puede dejar la OT lista para cerrar.
        # La fila de la OT se bloquea como lo hace /complete (serializa ambos).
        order = db.scalar(
            select(LabWorkOrder)
            .join(LabWorkOrderEquipment, LabWorkOrderEquipment.work_order_id == LabWorkOrder.id)
            .where(LabWorkOrderEquipment.id == report.lab_equipment_id)
            .with_for_update()
        )
        db.flush()
        if order is not None:
            sync_general_service_readiness(db, order, user)
        db.commit()
        return _read_technical_report_by_id(db, report_id)
    except BaseException:
        db.rollback()
        if written_path:
            resolved = resolve_storage_path(written_path)
            if resolved is not None and resolved.is_file():
                resolved.unlink(missing_ok=True)
        raise


def read_technical_report_pdf(
    db: Session,
    work_order_id: int,
    equipment_id: int,
) -> tuple[bytes, str]:
    """PDF final congelado del reporte vigente; nunca se re-renderiza."""
    equipment = _get_equipment_for_technical_report(db, work_order_id, equipment_id)
    report = equipment.current_technical_report
    if report is None:
        raise HTTPException(status_code=404, detail="El equipo no tiene reporte técnico vigente")
    if report.status != "completed" or not report.final_pdf_path:
        raise HTTPException(status_code=404, detail="El reporte aún no tiene documento final")
    stored = require_deliverable_file(report.final_pdf_path, not_found_detail="El PDF final no está disponible")
    content = stored.read_bytes()
    if not report.final_pdf_sha256 or hashlib.sha256(content).hexdigest() != report.final_pdf_sha256:
        raise HTTPException(status_code=409, detail="El PDF final no coincide con su SHA-256")
    return content, installation_report_filename(report.document_snapshot or {"document": {"folio": report.folio, "revision_number": report.revision_number}})


# ---------------------------------------------------------------------------
# SG-4I-A: administración del borrador (eliminar / cambiar tipo)
# ---------------------------------------------------------------------------

def _ensure_draft_administrable(db: Session, report: TechnicalReport) -> None:
    """Sólo un borrador realmente editable y sin consecuencias documentales:
    draft/in_progress, sin PDF final, sin completar y sin entrega vigente."""
    _ensure_editable(report)
    if report.final_pdf_path or report.completed_at or report.final_pdf_sha256:
        raise HTTPException(status_code=409, detail="El reporte ya tiene documento final")
    if current_deliveries_for_equipment(db, report.lab_equipment_id):
        raise HTTPException(status_code=409, detail="El equipo ya tiene una entrega registrada")


def _discard_evidence_files(db: Session, paths: list[str], user: User, reason: str) -> None:
    for path in paths:
        delete_if_unreferenced(
            db, path, user_id=user.id, module="technical_reports",
            entity="technical_report_evidence", entity_id=None, reason=reason,
        )
    db.commit()


def _delete_orphan_intervention(db: Session, intervention_id: int | None) -> None:
    """Una intervención sin ningún reporte (borrador eliminado) deja de existir.
    Su folio ya emitido sigue consumido: la secuencia nunca retrocede."""
    if intervention_id is None:
        return
    remaining = db.scalar(select(TechnicalReport.id).where(TechnicalReport.intervention_id == intervention_id).limit(1))
    if remaining is not None:
        return
    for link in db.scalars(select(TechnicalInterventionDelivery).where(TechnicalInterventionDelivery.intervention_id == intervention_id)):
        db.delete(link)
    intervention = db.get(TechnicalIntervention, intervention_id)
    if intervention is not None:
        db.delete(intervention)
        db.flush()


def delete_technical_report_draft(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    user: User,
) -> TechnicalReportDraftDeleted:
    """Elimina un borrador (captura + evidencias + archivos). El folio
    institucional YA emitido queda consumido: la secuencia anual
    (`InstitutionalFolioSequence`) sólo avanza, así que nunca se reasigna; la
    trazabilidad queda en la auditoría con el folio, tipo y revisión."""
    removed_paths: list[str] = []
    try:
        report = _lock_current_report(db, work_order_id, equipment_id)
        _ensure_draft_administrable(db, report)
        removed_paths = [item.storage_path for item in report.evidence]
        result = TechnicalReportDraftDeleted(
            technical_report_id=report.id, folio=report.folio, report_type=report.report_type,
        )
        write_audit_log(
            db,
            action="technical_report.draft_deleted",
            entity="technical_reports",
            entity_id=report.id,
            user_id=user.id,
            previous_values={
                "folio": report.folio,
                "report_type": report.report_type,
                "revision_number": report.revision_number,
                "status": report.status,
                "lab_equipment_id": report.lab_equipment_id,
                "evidence_count": len(report.evidence),
            },
        )
        intervention_id = report.intervention_id
        db.delete(report)
        db.flush()
        _delete_orphan_intervention(db, intervention_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    # Los archivos se retiran sólo después de confirmar la baja en base de datos.
    _discard_evidence_files(db, removed_paths, user, "Borrador de reporte eliminado.")
    return result


def change_technical_report_type(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: TechnicalReportRetype,
    user: User,
) -> TechnicalReportRead:
    """Cambia el tipo de un reporte editable. Sólo hacia tipos con perfil
    completo (`ENABLED_TECHNICAL_REPORT_TYPES`; hoy ninguno distinto de
    Installation). Un cambio real NO reinterpreta `capture_values`: resetea la
    captura y la versión de esquema al perfil destino, emite el folio de la
    serie del nuevo tipo (el anterior queda consumido) y, si había evidencias,
    exige confirmación explícita antes de descartarlas."""
    removed_paths: list[str] = []
    try:
        report = _lock_current_report(db, work_order_id, equipment_id)
        _ensure_draft_administrable(db, report)
        if payload.report_type == report.report_type:
            raise HTTPException(status_code=409, detail="El reporte ya es de ese tipo")
        if payload.report_type not in ENABLED_TECHNICAL_REPORT_TYPES:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "TECHNICAL_REPORT_TYPE_NOT_AVAILABLE",
                    "message": "Ese tipo de reporte aún no está disponible.",
                },
            )
        if report.evidence and not payload.confirm_discard_evidence:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "TECHNICAL_REPORT_RETYPE_REQUIRES_CONFIRMATION",
                    "message": "El reporte tiene evidencias que se descartarán al cambiar de tipo.",
                    "evidence_count": len(report.evidence),
                },
            )
        previous = {
            "folio": report.folio, "report_type": report.report_type,
            "schema_version": report.report_schema_version, "evidence_count": len(report.evidence),
        }
        removed_paths = [item.storage_path for item in report.evidence]
        for item in list(report.evidence):
            report.evidence.remove(item)
        report.report_type = payload.report_type
        report.report_schema_version = 1
        report.capture_values = {}
        report.folio = _allocate_technical_report_folio(db, payload.report_type)
        report.status = "draft"
        if report.intervention is not None:
            report.intervention.intervention_type = payload.report_type
            report.intervention.folio = report.folio
            report.intervention.status = "open"
        write_audit_log(
            db,
            action="technical_report.type_changed",
            entity="technical_reports",
            entity_id=report.id,
            user_id=user.id,
            previous_values=previous,
            new_values={"folio": report.folio, "report_type": report.report_type},
        )
        report_id = report.id
        db.commit()
    except Exception:
        db.rollback()
        raise
    _discard_evidence_files(db, removed_paths, user, "Evidencias descartadas por cambio de tipo de reporte.")
    return _read_technical_report_by_id(db, report_id)
