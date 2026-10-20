"""API por intervención (SG-4J-A4): consulta y administración de intervenciones
técnicas individuales. Las operaciones heredadas por equipo siguen en
`technical_reports.py`; este módulo nunca opera sobre "la" intervención
principal: toda operación nombra la intervención y se valida que pertenezca al
equipo y a la OT de la ruta."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.lab_work_order import LabWorkOrderEquipment
from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.technical_intervention import TechnicalIntervention, TechnicalInterventionDelivery
from app.models.technical_report import TechnicalReport
from app.models.user import User
from app.schemas.technical_intervention import (
    TechnicalInterventionCancel,
    TechnicalInterventionCreate,
    TechnicalInterventionDeliveryRead,
    TechnicalInterventionDetailRead,
    TechnicalInterventionRead,
    TechnicalReportRevisionRead,
)
from app.services.audit_logs import write_audit_log
from app.services.lab_work_orders import sync_general_service_readiness
from app.services.technical_interventions import current_revision, is_mandatory
from app.services.technical_reports import _get_equipment_for_technical_report, _open_intervention


def _intervention_of_route(db: Session, equipment: LabWorkOrderEquipment, intervention_id: int) -> TechnicalIntervention:
    """La intervención debe pertenecer al equipo de la ruta (y éste a la OT de la
    ruta, ya validado por `_get_equipment_for_technical_report`); si no, 404 sin
    revelar su existencia."""
    intervention = db.scalar(
        select(TechnicalIntervention)
        .where(TechnicalIntervention.id == intervention_id, TechnicalIntervention.lab_equipment_id == equipment.id)
        .options(selectinload(TechnicalIntervention.reports))
    )
    if intervention is None:
        raise HTTPException(status_code=404, detail="Intervención técnica no encontrada")
    return intervention


def _delivery_by_report(db: Session, intervention_id: int) -> dict[int, int]:
    return {
        link.technical_report_id: link.delivery_id
        for link in db.scalars(
            select(TechnicalInterventionDelivery).where(
                TechnicalInterventionDelivery.intervention_id == intervention_id,
                TechnicalInterventionDelivery.technical_report_id.is_not(None),
            )
        )
    }


def _revision_read(report: TechnicalReport, delivery_by_report: dict[int, int]) -> TechnicalReportRevisionRead:
    return TechnicalReportRevisionRead(
        id=report.id,
        intervention_id=report.intervention_id,
        revision_number=report.revision_number,
        is_current=report.is_current,
        status=report.status,
        report_type=report.report_type,
        folio=report.folio,
        supersedes_report_id=report.supersedes_report_id,
        performed_by_user_id=report.performed_by_user_id,
        performed_by_name_snapshot=report.performed_by_name_snapshot,
        performed_at=report.performed_at,
        completed_at=report.completed_at,
        pdf_renderer_version=report.pdf_renderer_version,
        final_pdf_generated_at=report.final_pdf_generated_at,
        final_pdf_sha256=report.final_pdf_sha256,
        pdf_available=bool(report.final_pdf_path and report.final_pdf_sha256),
        delivery_id=delivery_by_report.get(report.id)
        or (((report.document_snapshot or {}).get("delivery") or {}).get("delivery_id")),
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def _intervention_read(db: Session, equipment: LabWorkOrderEquipment, intervention: TechnicalIntervention) -> TechnicalInterventionRead:
    delivery_by_report = _delivery_by_report(db, intervention.id)
    current = current_revision(intervention)
    return TechnicalInterventionRead(
        id=intervention.id,
        lab_equipment_id=intervention.lab_equipment_id,
        work_order_id=equipment.work_order_id,
        intervention_type=intervention.intervention_type,
        folio=intervention.folio,
        status=intervention.status,
        mandatory=is_mandatory(intervention),
        created_at=intervention.created_at,
        created_by_user_id=intervention.created_by_user_id,
        revisions_count=len(intervention.reports),
        current_revision=_revision_read(current, delivery_by_report) if current is not None else None,
    )


def list_interventions(
    db: Session, work_order_id: int, equipment_id: int, *, status: str | None = None
) -> list[TechnicalInterventionRead]:
    equipment = _get_equipment_for_technical_report(db, work_order_id, equipment_id)
    interventions = sorted(equipment.technical_interventions, key=lambda item: item.id)
    if status is not None:
        interventions = [item for item in interventions if item.status == status]
    return [_intervention_read(db, equipment, item) for item in interventions]


def get_intervention(db: Session, work_order_id: int, equipment_id: int, intervention_id: int) -> TechnicalInterventionDetailRead:
    equipment = _get_equipment_for_technical_report(db, work_order_id, equipment_id)
    intervention = _intervention_of_route(db, equipment, intervention_id)
    base = _intervention_read(db, equipment, intervention)
    links = db.execute(
        select(TechnicalInterventionDelivery, LabWorkOrderDelivery)
        .join(LabWorkOrderDelivery, LabWorkOrderDelivery.id == TechnicalInterventionDelivery.delivery_id)
        .where(TechnicalInterventionDelivery.intervention_id == intervention.id)
        .order_by(LabWorkOrderDelivery.id)
    ).all()
    return TechnicalInterventionDetailRead(
        **base.model_dump(),
        deliveries=[
            TechnicalInterventionDeliveryRead(
                delivery_id=delivery.id, exhibition_number=delivery.exhibition_number, delivery_status=delivery.status,
                delivered_at=delivery.delivered_at, technical_report_id=link.technical_report_id,
            )
            for link, delivery in links
        ],
    )


def list_revisions(db: Session, work_order_id: int, equipment_id: int, intervention_id: int) -> list[TechnicalReportRevisionRead]:
    equipment = _get_equipment_for_technical_report(db, work_order_id, equipment_id)
    intervention = _intervention_of_route(db, equipment, intervention_id)
    delivery_by_report = _delivery_by_report(db, intervention.id)
    return [
        _revision_read(report, delivery_by_report)
        for report in sorted(intervention.reports, key=lambda item: item.revision_number)
    ]


def create_intervention(
    db: Session, work_order_id: int, equipment_id: int, payload: TechnicalInterventionCreate, user: User
) -> TechnicalInterventionRead:
    """Alta explícita: nueva intervención + R1 en borrador. Serializada por
    equipo (fila bloqueada) y con folio propio; nunca crea R2 ni modifica
    reportes existentes."""
    try:
        db.scalar(select(LabWorkOrderEquipment.id).where(LabWorkOrderEquipment.id == equipment_id).with_for_update())
        equipment = _get_equipment_for_technical_report(db, work_order_id, equipment_id)
        report = _open_intervention(db, equipment, payload.report_type, user, allow_existing=True)
        intervention_id = report.intervention_id
        db.flush()
        db.refresh(equipment)
        # Una intervención obligatoria nueva revoca un `ready_to_close` previo.
        sync_general_service_readiness(db, equipment.work_order, user)
        db.commit()
    except Exception:
        db.rollback()
        raise
    equipment = _get_equipment_for_technical_report(db, work_order_id, equipment_id)
    return _intervention_read(db, equipment, _intervention_of_route(db, equipment, intervention_id))


def cancel_intervention(
    db: Session, work_order_id: int, equipment_id: int, intervention_id: int, payload: TechnicalInterventionCancel, user: User
) -> TechnicalInterventionRead:
    """Cancela una intervención todavía en captura. Conserva el historial (el
    reporte queda `cancelled`, nada se borra) y deja de ser obligatoria para el
    cierre. No se puede cancelar una ya cancelada, finalizada, ni entregada."""
    try:
        equipment = _get_equipment_for_technical_report(db, work_order_id, equipment_id)
        intervention = db.scalar(
            select(TechnicalIntervention)
            .where(TechnicalIntervention.id == intervention_id, TechnicalIntervention.lab_equipment_id == equipment.id)
            .with_for_update()
        )
        if intervention is None:
            raise HTTPException(status_code=404, detail="Intervención técnica no encontrada")
        reports = list(db.scalars(
            select(TechnicalReport).where(TechnicalReport.intervention_id == intervention.id).with_for_update()
        ))
        if intervention.status == "cancelled":
            raise HTTPException(status_code=409, detail="La intervención ya está cancelada")
        report = next((item for item in reports if item.is_current), None)
        delivered = db.scalar(
            select(TechnicalInterventionDelivery.id).where(TechnicalInterventionDelivery.intervention_id == intervention.id).limit(1)
        )
        if intervention.status != "open" or delivered is not None or report is None or report.status not in {"draft", "in_progress"}:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "TECHNICAL_INTERVENTION_NOT_CANCELLABLE",
                    "message": "Sólo puede cancelarse una intervención en captura, sin entrega ni documento final.",
                },
            )
        previous = {"status": intervention.status, "report_status": report.status}
        intervention.status = "cancelled"
        report.status = "cancelled"
        write_audit_log(
            db,
            action="technical_intervention.cancelled",
            entity="technical_interventions",
            entity_id=intervention.id,
            user_id=user.id,
            previous_values=previous,
            new_values={"status": "cancelled", "report_status": "cancelled", "reason": payload.reason.strip()},
            comment=payload.reason.strip()[:500],
        )
        db.flush()
        # Una intervención cancelada deja de bloquear: la OT puede quedar lista.
        sync_general_service_readiness(db, equipment.work_order, user)
        db.commit()
    except Exception:
        db.rollback()
        raise
    equipment = _get_equipment_for_technical_report(db, work_order_id, equipment_id)
    return _intervention_read(db, equipment, _intervention_of_route(db, equipment, intervention_id))
