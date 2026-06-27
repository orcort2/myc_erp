from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from app.models.field_sheet import FieldSheet
from app.schemas.operational_engine import EngineMessage, TechnicalCaptureResult
from app.services.document_selection_engine import select_document_templates
from app.services.standards_validation_engine import validate_reference_standards


def _message(severity: str, code: str, message: str) -> EngineMessage:
    return EngineMessage(severity=severity, code=code, message=message)


def build_technical_capture_checklist(
    db: Session,
    field_sheet_id: int,
) -> TechnicalCaptureResult:
    field_sheet = db.get(FieldSheet, field_sheet_id)
    if field_sheet is None or not field_sheet.is_active:
        return TechnicalCaptureResult(
            field_sheet_id=field_sheet_id,
            procedure_confirmed=False,
            template_confirmed=False,
            standards_confirmed=False,
            folio_confirmed=False,
            ready_for_calculation=False,
            messages=[_message("ERROR", "field_sheet_missing", "No se encontro la hoja de campo.")],
        )

    document_selection = select_document_templates(db, field_sheet_id)
    standards_validation = validate_reference_standards(db, field_sheet_id, audit=False)
    certificate = db.scalar(
        select(Certificate).where(
            Certificate.field_sheet_id == field_sheet.id,
            Certificate.is_active.is_(True),
        )
    )
    procedure_confirmed = field_sheet.calibration_procedure_id is not None
    template_confirmed = bool(document_selection.field_sheet_template)
    standards_confirmed = standards_validation.status != "ERROR"
    folio_confirmed = certificate is not None and bool(certificate.folio)
    messages: list[EngineMessage] = []

    if not procedure_confirmed:
        messages.append(_message("ERROR", "procedure_missing", "Falta confirmar procedimiento."))
    if not template_confirmed:
        messages.append(_message("ERROR", "template_missing", "Falta confirmar plantilla."))
    if not standards_confirmed:
        messages.extend(standards_validation.messages)
    if not folio_confirmed:
        messages.append(_message("ADVERTENCIA", "folio_missing", "Aun no existe folio de certificado."))

    return TechnicalCaptureResult(
        field_sheet_id=field_sheet.id,
        procedure_confirmed=procedure_confirmed,
        template_confirmed=template_confirmed,
        standards_confirmed=standards_confirmed,
        folio_confirmed=folio_confirmed,
        ready_for_calculation=all(
            [procedure_confirmed, template_confirmed, standards_confirmed, folio_confirmed]
        ),
        messages=messages,
    )
