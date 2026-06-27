from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.certificate import Certificate
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.models.service_order import ServiceOrder
from app.schemas.operational_engine import EngineMessage, OperationalFlowResult


STAGE_ORDER = [
    "cotizacion_aceptada",
    "orden_servicio",
    "equipo_registrado",
    "orden_trabajo",
    "captura_hoja_campo",
    "hoja_completada",
    "revision_documental",
    "preparacion_certificado",
    "calculo_metrologico",
    "calidad",
    "aprobado",
    "liberado",
    "etiqueta",
    "cierre",
]


def _next_stage(stage: str) -> str | None:
    try:
        return STAGE_ORDER[STAGE_ORDER.index(stage) + 1]
    except (ValueError, IndexError):
        return None


def _message(severity: str, code: str, message: str) -> EngineMessage:
    return EngineMessage(severity=severity, code=code, message=message)


def _latest_active(items):
    active = [item for item in items if getattr(item, "is_active", True)]
    if not active:
        return None
    return sorted(active, key=lambda item: item.created_at, reverse=True)[0]


def evaluate_operational_flow(
    db: Session,
    *,
    service_order_id: int | None = None,
    equipment_id: int | None = None,
    field_sheet_id: int | None = None,
    certificate_id: int | None = None,
) -> OperationalFlowResult:
    service_order = None
    equipment = None
    field_sheet = None
    certificate = None
    messages: list[EngineMessage] = []

    if certificate_id is not None:
        certificate = db.scalar(select(Certificate).where(Certificate.id == certificate_id))
        if certificate is not None:
            service_order_id = certificate.service_order_id
            equipment_id = certificate.equipment_id
            field_sheet_id = certificate.field_sheet_id

    if field_sheet_id is not None:
        field_sheet = db.scalar(
            select(FieldSheet)
            .where(FieldSheet.id == field_sheet_id)
            .options(selectinload(FieldSheet.certificates))
        )
        if field_sheet is not None:
            equipment_id = field_sheet.equipment_id
            certificate = certificate or _latest_active(field_sheet.certificates)

    if equipment_id is not None:
        equipment = db.scalar(
            select(Equipment)
            .where(Equipment.id == equipment_id)
            .options(
                selectinload(Equipment.field_sheets),
                selectinload(Equipment.certificates),
                selectinload(Equipment.service_order),
            )
        )
        if equipment is not None:
            service_order = equipment.service_order
            field_sheet = field_sheet or _latest_active(equipment.field_sheets)
            certificate = certificate or _latest_active(equipment.certificates)

    if service_order_id is not None and service_order is None:
        service_order = db.scalar(
            select(ServiceOrder)
            .where(ServiceOrder.id == service_order_id)
            .options(selectinload(ServiceOrder.equipment), selectinload(ServiceOrder.certificates))
        )

    if service_order is None:
        return OperationalFlowResult(
            current_stage="sin_expediente",
            messages=[_message("ERROR", "service_order_missing", "No se encontro la orden de servicio.")],
            blocked_actions=["advance_stage"],
        )

    stage = "orden_servicio"
    allowed_actions = ["register_equipment"]
    blocked_actions: list[str] = []

    if service_order.quotation_id is not None:
        stage = "cotizacion_aceptada"
    if service_order.status in {"closed", "cancelled"}:
        stage = "cierre"
        allowed_actions = []
        blocked_actions = ["register_equipment", "capture_field_sheet", "prepare_certificate"]
    elif equipment is not None:
        stage = "equipo_registrado"
        allowed_actions = ["generate_work_order", "capture_field_sheet"]
        if equipment.status == "registered":
            stage = "orden_trabajo"
        if field_sheet is not None:
            stage = "captura_hoja_campo"
            allowed_actions = ["complete_field_sheet"]
            if field_sheet.status == "completed":
                stage = "hoja_completada"
                allowed_actions = ["send_to_document_review"]
            elif field_sheet.status == "under_review":
                stage = "revision_documental"
                allowed_actions = ["prepare_certificate"]
            elif field_sheet.status == "approved":
                stage = "preparacion_certificado"
                allowed_actions = ["prepare_certificate"]
        if certificate is not None:
            stage = "preparacion_certificado"
            allowed_actions = ["run_calculation"]
            if certificate.status == "generated":
                stage = "calculo_metrologico"
                allowed_actions = ["send_to_quality"]
            elif certificate.status == "quality_review":
                stage = "calidad"
                allowed_actions = ["approve_certificate", "request_correction"]
            elif certificate.status == "approved":
                stage = "aprobado"
                allowed_actions = ["release_certificate"]
            elif certificate.status == "released":
                stage = "liberado"
                allowed_actions = ["prepare_label", "close_service_order"]
            elif certificate.status == "suspended":
                allowed_actions = ["return_to_draft", "cancel_certificate"]
                messages.append(
                    _message("ADVERTENCIA", "certificate_suspended", "El certificado esta suspendido.")
                )

    if equipment is None:
        blocked_actions.append("capture_field_sheet")
    if field_sheet is None:
        blocked_actions.extend(["complete_field_sheet", "prepare_certificate"])
    if certificate is None:
        blocked_actions.extend(["send_to_quality", "release_certificate", "prepare_label"])

    return OperationalFlowResult(
        current_stage=stage,
        next_stage=_next_stage(stage),
        allowed_actions=sorted(set(allowed_actions)),
        blocked_actions=sorted(set(blocked_actions) - set(allowed_actions)),
        messages=messages,
    )
