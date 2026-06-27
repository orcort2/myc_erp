from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.field_sheet import FieldSheet
from app.models.reference_standard import FieldSheetReferenceStandard, ReferenceStandard
from app.models.reference_standard_certificate import ReferenceStandardCertificate
from app.models.controlled_document import TechnicalProfile
from app.schemas.pattern_selection import (
    PatternCandidate,
    PatternSelectionRequest,
    PatternSelectionResult,
)
from app.services.audit_logs import write_audit_log
from app.services.reference_standard_certificates import get_applicable_uncertainty


def _as_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _numeric_values(values: list[str | None]) -> list[float]:
    result = []
    for value in values:
        converted = _as_float(value)
        if converted is not None:
            result.append(converted)
    return result


def _covers_range(
    *,
    pattern_min: float | None,
    pattern_max: float | None,
    target_min: float | None,
    target_max: float | None,
) -> bool:
    if target_min is not None and pattern_min is not None and target_min < pattern_min:
        return False
    if target_max is not None and pattern_max is not None and target_max > pattern_max:
        return False
    return True


def _target_range(request: PatternSelectionRequest) -> tuple[float | None, float | None]:
    return (
        request.measured_range_min if request.measured_range_min is not None else request.ibc_range_min,
        request.measured_range_max if request.measured_range_max is not None else request.ibc_range_max,
    )


def _profile_allowed_ids(db: Session, technical_profile_id: int | None) -> tuple[set[int], set[int]]:
    if technical_profile_id is None:
        return set(), set()
    profile = db.scalar(
        select(TechnicalProfile)
        .where(TechnicalProfile.id == technical_profile_id)
        .options(selectinload(TechnicalProfile.allowed_patterns))
    )
    if profile is None:
        return set(), set()
    allowed = {item.pattern_id for item in profile.allowed_patterns if item.pattern_id is not None}
    preferred = {
        item.pattern_id
        for item in profile.allowed_patterns
        if item.pattern_id is not None and item.is_preferred
    }
    return allowed, preferred


def generate_pattern_candidates(
    db: Session,
    request: PatternSelectionRequest,
    *,
    user_id: int | None = None,
    audit: bool = True,
) -> PatternSelectionResult:
    service_date = request.service_date or date.today()
    target_min, target_max = _target_range(request)
    profile_allowed, profile_preferred = _profile_allowed_ids(db, request.technical_profile_id)
    allowed_ids = set(request.allowed_pattern_ids or []) | profile_allowed
    selected_ids = set(request.selected_pattern_ids or [])
    query = (
        select(ReferenceStandard)
        .where(ReferenceStandard.is_active.is_(True))
        .options(
            selectinload(ReferenceStandard.certificates).selectinload(
                ReferenceStandardCertificate.uncertainties
            )
        )
    )
    if request.magnitude:
        query = query.where(ReferenceStandard.magnitude == request.magnitude)
    standards = list(db.scalars(query).all())
    candidates: list[PatternCandidate] = []
    warnings: list[str] = []
    errors: list[str] = []

    for standard in standards:
        messages: list[str] = []
        status = "valid"
        score = 100.0
        pattern_min = _as_float(standard.range_min)
        pattern_max = _as_float(standard.range_max)
        certificate = standard.current_certificate
        uncertainty = None

        if standard.status != "active":
            status = "error"
            messages.append("Patron no activo.")
        if allowed_ids and standard.id not in allowed_ids:
            score -= 20
            messages.append("No esta listado como patron permitido del perfil/contexto.")
        if standard.id in profile_preferred:
            score += 10
        if certificate is None:
            status = "error"
            messages.append("Sin certificado vigente activo.")
        elif certificate.expiration_date and certificate.expiration_date < service_date:
            status = "error"
            messages.append("Certificado vigente vencido para la fecha de servicio.")
        else:
            uncertainty = get_applicable_uncertainty(
                certificate,
                range_min=target_min,
                range_max=target_max,
                unit=request.unit,
            )
            if uncertainty is None:
                status = "error"
                messages.append("Sin incertidumbre aplicable para el rango medido.")

        if not _covers_range(
            pattern_min=pattern_min,
            pattern_max=pattern_max,
            target_min=target_min,
            target_max=target_max,
        ):
            status = "error"
            messages.append("El patron no cubre el rango real requerido.")

        if pattern_max is not None and target_max is not None:
            score -= max(pattern_max - target_max, 0) * 0.05
        if uncertainty is not None:
            score -= float(uncertainty.uncertainty_value)
        if status == "error":
            score = min(score, 0)
        elif messages:
            status = "warning"

        candidate = PatternCandidate(
            pattern_id=standard.id,
            pattern_name=standard.name,
            pattern_code=standard.internal_code,
            magnitude=standard.magnitude,
            range_min=pattern_min,
            range_max=pattern_max,
            unit=standard.unit,
            status=standard.status,
            current_certificate_id=certificate.id if certificate else None,
            current_certificate_number=certificate.certificate_number if certificate else None,
            current_certificate_expiration_date=certificate.expiration_date if certificate else None,
            applicable_uncertainty=float(uncertainty.uncertainty_value) if uncertainty else None,
            uncertainty_unit=uncertainty.uncertainty_unit if uncertainty else None,
            k_factor=float(uncertainty.k_factor) if uncertainty and uncertainty.k_factor is not None else None,
            score=round(score, 4),
            validation_status=status,
            validation_messages=messages,
        )
        candidates.append(candidate)

    candidates.sort(key=lambda item: (item.validation_status != "valid", -item.score))
    valid_candidates = [item for item in candidates if item.validation_status == "valid"]
    recommendations = valid_candidates[:3]
    if not recommendations:
        errors.append("No hay patrones validos para el contexto indicado.")
    elif len(valid_candidates) > 1:
        warnings.append("Hay mas de un patron valido; se priorizo menor alcance suficiente e incertidumbre.")
    selected_invalid = [
        item for item in candidates if item.pattern_id in selected_ids and item.validation_status == "error"
    ]
    for item in selected_invalid:
        errors.append(f"Patron seleccionado {item.pattern_code} no cumple: {'; '.join(item.validation_messages)}")

    result = PatternSelectionResult(
        candidates=candidates,
        selected_recommendations=recommendations,
        warnings=warnings,
        errors=errors,
        explanation=(
            "Seleccion basada en magnitud, estado activo, certificado vigente, rango requerido, "
            "perfil tecnico e incertidumbre aplicable."
        ),
    )
    if audit:
        write_audit_log(
            db,
            action="pattern_selection.candidates_generated",
            entity="pattern_selection",
            entity_id=None,
            user_id=user_id,
            new_values={
                "technical_profile_id": request.technical_profile_id,
                "magnitude": request.magnitude,
                "range_min": target_min,
                "range_max": target_max,
                "candidates": len(candidates),
                "recommendations": [item.pattern_id for item in recommendations],
            },
        )
        db.commit()
    return result


def suggest_patterns_for_field_sheet(
    db: Session,
    field_sheet_id: int,
    *,
    user_id: int | None = None,
) -> PatternSelectionResult:
    field_sheet = db.scalar(
        select(FieldSheet)
        .where(FieldSheet.id == field_sheet_id)
        .options(selectinload(FieldSheet.equipment), selectinload(FieldSheet.results_rows))
    )
    if field_sheet is None or not field_sheet.is_active:
        return PatternSelectionResult(
            explanation="No se encontro la hoja de campo.",
            errors=["No se encontro la hoja de campo."],
        )
    values = _numeric_values([row.pattern_value for row in field_sheet.results_rows])
    range_parts = (
        field_sheet.equipment.range_or_capacity.split("-")
        if field_sheet.equipment.range_or_capacity and "-" in field_sheet.equipment.range_or_capacity
        else []
    )
    request = PatternSelectionRequest(
        magnitude=field_sheet.calibration_procedure.magnitude if field_sheet.calibration_procedure else "unknown",
        equipment_type=field_sheet.equipment.name,
        calibration_scope=(
            "accredited"
            if field_sheet.calibration_procedure and field_sheet.calibration_procedure.certificate_type == "acreditado"
            else "traceable"
        ),
        ibc_range_min=_as_float(range_parts[0].strip()) if range_parts else None,
        ibc_range_max=_as_float(range_parts[1].strip()) if len(range_parts) > 1 else None,
        measured_range_min=min(values) if values else None,
        measured_range_max=max(values) if values else None,
        unit=field_sheet.units,
    )
    return generate_pattern_candidates(db, request, user_id=user_id)


def validate_selected_patterns_for_field_sheet(
    db: Session,
    field_sheet_id: int,
    *,
    user_id: int | None = None,
) -> PatternSelectionResult:
    field_sheet = db.scalar(
        select(FieldSheet)
        .where(FieldSheet.id == field_sheet_id)
        .options(
            selectinload(FieldSheet.reference_standard_links).selectinload(
                FieldSheetReferenceStandard.reference_standard
            ),
            selectinload(FieldSheet.results_rows),
            selectinload(FieldSheet.equipment),
            selectinload(FieldSheet.calibration_procedure),
        )
    )
    if field_sheet is None or not field_sheet.is_active:
        return PatternSelectionResult(
            explanation="No se encontro la hoja de campo.",
            errors=["No se encontro la hoja de campo."],
        )
    selected_ids = [link.reference_standard_id for link in field_sheet.reference_standard_links]
    values = _numeric_values([row.pattern_value for row in field_sheet.results_rows])
    request = PatternSelectionRequest(
        magnitude=field_sheet.calibration_procedure.magnitude if field_sheet.calibration_procedure else "unknown",
        equipment_type=field_sheet.equipment.name,
        calibration_scope=(
            "accredited"
            if field_sheet.calibration_procedure and field_sheet.calibration_procedure.certificate_type == "acreditado"
            else "traceable"
        ),
        measured_range_min=min(values) if values else None,
        measured_range_max=max(values) if values else None,
        unit=field_sheet.units,
        selected_pattern_ids=selected_ids,
    )
    result = generate_pattern_candidates(db, request, user_id=user_id, audit=False)
    write_audit_log(
        db,
        action="field_sheet.patterns_validated",
        entity="field_sheets",
        entity_id=field_sheet.id,
        user_id=user_id,
        new_values={
            "selected_pattern_ids": selected_ids,
            "errors": result.errors,
            "warnings": result.warnings,
        },
    )
    db.commit()
    return result
