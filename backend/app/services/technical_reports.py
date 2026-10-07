from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models.folio_sequence import InstitutionalFolioSequence
from app.models.lab_work_order import LabWorkOrderEquipment
from app.models.technical_report import TechnicalReport
from app.models.user import User
from app.schemas.technical_report import (
    TechnicalReportCreate,
    TechnicalReportRead,
)
from app.services.audit_logs import write_audit_log


TECHNICAL_REPORT_SEQUENCE_PREFIXES = {
    "installation": "MYC-IN",
}

ENABLED_TECHNICAL_REPORT_TYPES = {
    "installation",
}

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
