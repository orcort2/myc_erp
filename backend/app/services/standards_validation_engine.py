from __future__ import annotations

from datetime import date
from decimal import InvalidOperation

from sqlalchemy.orm import Session

from app.models.field_sheet import FieldSheet
from app.models.reference_standard import ReferenceStandard
from app.schemas.operational_engine import EngineMessage, StandardsValidationResult
from app.services.audit_logs import write_audit_log


def _message(severity: str, code: str, message: str) -> EngineMessage:
    return EngineMessage(severity=severity, code=code, message=message)


def _as_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError, InvalidOperation):
        return None


def _has_uncertainty_for_values(standard: ReferenceStandard, values: list[float]) -> bool:
    if not standard.uncertainties:
        return False
    if not values:
        return True
    for value in values:
        matched = False
        for uncertainty in standard.uncertainties:
            range_min = _as_float(uncertainty.range_min)
            range_max = _as_float(uncertainty.range_max)
            if range_min is not None and value < range_min:
                continue
            if range_max is not None and value > range_max:
                continue
            matched = True
            break
        if not matched:
            return False
    return True


def validate_reference_standards(
    db: Session,
    field_sheet_id: int,
    *,
    user_id: int | None = None,
    audit: bool = True,
) -> StandardsValidationResult:
    field_sheet = db.get(FieldSheet, field_sheet_id)
    if field_sheet is None or not field_sheet.is_active:
        return StandardsValidationResult(
            status="ERROR",
            messages=[_message("ERROR", "field_sheet_missing", "No se encontro la hoja de campo.")],
            blocking_errors=["No se encontro la hoja de campo."],
        )

    procedure = field_sheet.calibration_procedure
    links = field_sheet.reference_standard_links
    values = [
        value
        for row in field_sheet.results_rows
        if (value := _as_float(row.pattern_value)) is not None
    ]
    messages: list[EngineMessage] = []
    errors: list[str] = []
    warnings: list[str] = []

    if not links:
        errors.append("La calibracion requiere al menos un patron.")
        messages.append(_message("ERROR", "no_standards", errors[-1]))

    role_count = len({link.usage_role for link in links})
    if len(links) > 1 and role_count == 1:
        warnings.append("Todos los patrones tienen el mismo rol de uso.")
        messages.append(_message("ADVERTENCIA", "standard_roles_repeated", warnings[-1]))

    for link in links:
        standard = link.reference_standard
        if standard is None:
            errors.append(f"El patron {link.reference_standard_id} no existe.")
            messages.append(_message("ERROR", "standard_missing", errors[-1]))
            continue

        label = f"{standard.internal_code} - {standard.name}"
        if not standard.is_active:
            errors.append(f"El patron {label} esta inactivo.")
            messages.append(_message("ERROR", "standard_inactive", errors[-1]))
        if standard.status != "active":
            errors.append(f"El patron {label} no esta activo operativamente.")
            messages.append(_message("ERROR", "standard_status_invalid", errors[-1]))
        if standard.next_calibration_on and standard.next_calibration_on < date.today():
            errors.append(f"El patron {label} esta vencido.")
            messages.append(_message("ERROR", "standard_expired", errors[-1]))
        if procedure and standard.magnitude.lower() != procedure.magnitude.lower():
            errors.append(
                f"El patron {label} no corresponde a la magnitud {procedure.magnitude}."
            )
            messages.append(_message("ERROR", "standard_magnitude_mismatch", errors[-1]))

        range_min = _as_float(standard.range_min)
        range_max = _as_float(standard.range_max)
        for value in values:
            if range_min is not None and value < range_min:
                errors.append(f"El valor {value} queda debajo del rango del patron {label}.")
                messages.append(_message("ERROR", "standard_range_low", errors[-1]))
            if range_max is not None and value > range_max:
                errors.append(f"El valor {value} queda arriba del rango del patron {label}.")
                messages.append(_message("ERROR", "standard_range_high", errors[-1]))

        if not _has_uncertainty_for_values(standard, values):
            errors.append(f"El patron {label} no tiene incertidumbre aplicable.")
            messages.append(_message("ERROR", "standard_uncertainty_missing", errors[-1]))

    if procedure is None:
        warnings.append("No se puede validar compatibilidad con procedimiento porque no esta asignado.")
        messages.append(_message("ADVERTENCIA", "procedure_missing", warnings[-1]))

    status = "ERROR" if errors else "ADVERTENCIA" if warnings else "VALIDO"
    result = StandardsValidationResult(
        status=status,
        messages=messages,
        blocking_errors=errors,
        warnings=warnings,
    )
    if audit:
        write_audit_log(
            db,
            action="engine.standards_validated",
            entity="field_sheets",
            entity_id=field_sheet.id,
            user_id=user_id,
            new_values=result.model_dump(),
        )
        db.commit()
    return result
