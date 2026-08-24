from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.institutional_folios import build_certificate_folio
from app.schemas.service_type import normalize_service_type
from app.models.certificate import Certificate
from app.schemas.operational_engine import EngineMessage, FolioSuggestionResult
from app.services.audit_logs import write_audit_log


def _message(severity: str, code: str, message: str) -> EngineMessage:
    return EngineMessage(severity=severity, code=code, message=message)


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
    service_type = (
        "verification"
        if certificate_type == "verification"
        else "acreditado" if certificate_type == "acreditado" else "trazable"
    )
    messages: list[EngineMessage] = []

    if manual_folio:
        if certificate_type == "verification":
            raise HTTPException(
                status_code=422,
                detail="El folio de Verificación se asigna exclusivamente por la secuencia institucional",
            )
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
        if sequence is not None:
            if certificate_type == "verification":
                suggested = f"MYCV-{folio_date:%m}-{folio_date:%y}-{sequence:04d}"
            else:
                normalized = normalize_service_type(service_type)
                prefix = "MYCA" if normalized and normalized.value == "accredited" else "MYCT"
                suggested = f"{prefix}{folio_date:%y%m}{sequence:04d}"
        else:
            suggested = build_certificate_folio(
                db,
                service_type=service_type,
                issued_on=folio_date,
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
            **result.model_dump(mode="json"),
            "reason": reason,
            "sequence": sequence,
        },
    )
    db.commit()
    return result
