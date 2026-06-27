from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.folios import FolioRequest, generate_folio
from app.models.certificate import Certificate
from app.schemas.operational_engine import EngineMessage, FolioSuggestionResult
from app.services.audit_logs import write_audit_log


def _message(severity: str, code: str, message: str) -> EngineMessage:
    return EngineMessage(severity=severity, code=code, message=message)


def _next_sequence(db: Session, *, certificate_type: str, issued_on: date) -> int:
    prefix = "MYCA" if certificate_type == "acreditado" else "MYCT"
    prefix = f"{prefix}-{issued_on:%m}-{issued_on:%Y}-"
    last_folio = db.scalar(
        select(Certificate.folio)
        .where(Certificate.folio.like(f"{prefix}%"))
        .order_by(Certificate.folio.desc())
        .limit(1)
    )
    return 1 if not last_folio else int(last_folio.rsplit("-", 1)[-1]) + 1


def suggest_certificate_folio(
    db: Session,
    *,
    certificate_type: str,
    issued_on: date | None = None,
    sequence: int | None = None,
    manual_folio: str | None = None,
    reason: str | None = None,
    user_id: int | None = None,
) -> FolioSuggestionResult:
    folio_date = issued_on or date.today()
    service_type = "acreditado" if certificate_type == "acreditado" else "trazable"
    messages: list[EngineMessage] = []

    if manual_folio:
        exists = db.scalar(select(Certificate.id).where(Certificate.folio == manual_folio))
        if exists is not None:
            messages.append(
                _message("ERROR", "folio_already_used", "El folio manual ya existe en certificados.")
            )
        if not reason:
            messages.append(
                _message("ADVERTENCIA", "manual_reason_missing", "La captura manual debe documentar motivo.")
            )
        result = FolioSuggestionResult(
            suggested_folio=manual_folio,
            mode="manual",
            issued_on=folio_date,
            messages=messages,
        )
    else:
        resolved_sequence = sequence or _next_sequence(
            db,
            certificate_type=certificate_type,
            issued_on=folio_date,
        )
        suggested = generate_folio(
            FolioRequest(
                document_type="certificado",
                service_type=service_type,
                issued_on=folio_date,
                sequence=resolved_sequence,
            )
        )
        result = FolioSuggestionResult(
            suggested_folio=suggested,
            mode="automatic",
            issued_on=folio_date,
            messages=messages,
        )

    write_audit_log(
        db,
        action="engine.folio_suggested",
        entity="certificates",
        entity_id=None,
        user_id=user_id,
        new_values={
            **result.model_dump(),
            "reason": reason,
            "sequence": sequence,
        },
    )
    db.commit()
    return result
