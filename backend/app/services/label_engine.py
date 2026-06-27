from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from app.schemas.operational_engine import EngineMessage, LabelPreparationResult


def _message(severity: str, code: str, message: str) -> EngineMessage:
    return EngineMessage(severity=severity, code=code, message=message)


def prepare_label_payload(db: Session, certificate_id: int) -> LabelPreparationResult:
    certificate = db.get(Certificate, certificate_id)
    if certificate is None or not certificate.is_active:
        return LabelPreparationResult(
            folio="",
            equipment_name="",
            certificate_type="",
            status="error",
            messages=[_message("ERROR", "certificate_missing", "No se encontro el certificado.")],
        )
    messages: list[EngineMessage] = []
    if certificate.status not in {"approved", "released"}:
        messages.append(
            _message(
                "ERROR",
                "certificate_not_ready",
                "La etiqueta requiere certificado aprobado o liberado.",
            )
        )

    field_sheet = certificate.field_sheet
    client = certificate.service_order.client if certificate.service_order else None
    return LabelPreparationResult(
        folio=certificate.folio,
        client_name=client.commercial_name if client else None,
        equipment_name=certificate.equipment.name,
        calibration_date=field_sheet.calibration_date if field_sheet else certificate.issued_on,
        next_calibration_date=field_sheet.next_calibration_date if field_sheet else None,
        certificate_type=certificate.certificate_type,
        status=certificate.status,
        messages=messages,
    )
