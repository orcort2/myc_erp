from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_template import DocumentTemplate
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.schemas.operational_engine import DocumentSelectionResult, EngineMessage


def _message(severity: str, code: str, message: str) -> EngineMessage:
    return EngineMessage(severity=severity, code=code, message=message)


def _tokens(*values: str | None) -> set[str]:
    raw = " ".join(value or "" for value in values).lower()
    return {token for token in re.split(r"[^a-z0-9]+", raw) if token}


def _best_template(
    templates: list[DocumentTemplate],
    *,
    target_tokens: set[str],
    default_key: str,
) -> str:
    if not templates:
        return default_key
    scored = []
    for template in templates:
        template_tokens = _tokens(template.template_key, template.name, template.document_title)
        scored.append((len(template_tokens & target_tokens), template.template_key))
    score, key = sorted(scored, key=lambda item: (-item[0], item[1]))[0]
    return key if score > 0 else default_key


def select_document_templates(db: Session, field_sheet_id: int) -> DocumentSelectionResult:
    field_sheet = db.get(FieldSheet, field_sheet_id)
    messages: list[EngineMessage] = []
    if field_sheet is None or not field_sheet.is_active:
        return DocumentSelectionResult(
            field_sheet_template="general",
            certificate_template="certificate_general",
            label_template="label_general",
            criteria={},
            messages=[_message("ERROR", "field_sheet_missing", "No se encontro la hoja de campo.")],
        )

    equipment = db.get(Equipment, field_sheet.equipment_id)
    procedure = field_sheet.calibration_procedure
    criteria = {
        "procedure_id": field_sheet.calibration_procedure_id,
        "procedure_code": procedure.code if procedure else None,
        "magnitude": procedure.magnitude if procedure else None,
        "instrument_type": equipment.name if equipment else None,
        "service_type": procedure.certificate_type if procedure else None,
        "scope": equipment.range_or_capacity if equipment else None,
        "certificate_type": procedure.certificate_type if procedure else "trazable",
    }
    target_tokens = _tokens(*[str(value) if value is not None else None for value in criteria.values()])
    templates = list(
        db.scalars(
            select(DocumentTemplate).where(DocumentTemplate.is_active.is_(True))
        ).all()
    )

    selected_field_sheet = field_sheet.template_key or "general"
    certificate_template = _best_template(
        templates,
        target_tokens=target_tokens | {"certificado", "certificate"},
        default_key=f"certificate_{selected_field_sheet}",
    )
    label_template = _best_template(
        templates,
        target_tokens=target_tokens | {"etiqueta", "label"},
        default_key=f"label_{selected_field_sheet}",
    )

    if not templates:
        messages.append(
            _message(
                "ADVERTENCIA",
                "templates_registry_empty",
                "No hay plantillas documentales activas; se usaron claves convencionales.",
            )
        )
    if procedure is None:
        messages.append(
            _message("ADVERTENCIA", "procedure_missing", "La hoja no tiene procedimiento asignado.")
        )

    return DocumentSelectionResult(
        field_sheet_template=selected_field_sheet,
        certificate_template=certificate_template,
        label_template=label_template,
        criteria=criteria,
        messages=messages,
    )
