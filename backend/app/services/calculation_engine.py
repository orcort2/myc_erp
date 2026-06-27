from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.operational_engine import (
    CalculationPointInput,
    CalculationPointResult,
    CalculationResult,
    EngineMessage,
)
from app.services.audit_logs import write_audit_log
from app.services.metrology_engine import (
    absolute_error,
    average,
    combined_uncertainty,
    expanded_uncertainty,
    repeatability_uncertainty,
    resolution_uncertainty,
)
from app.services.metrology_profiles import get_metrology_profile


def _message(severity: str, code: str, message: str) -> EngineMessage:
    return EngineMessage(severity=severity, code=code, message=message)


def calculate_structured_results(
    db: Session,
    *,
    profile_key: str,
    points: list[CalculationPointInput],
    user_id: int | None = None,
) -> CalculationResult:
    profile = get_metrology_profile(profile_key)
    results: list[CalculationPointResult] = []
    messages: list[EngineMessage] = []

    for point in points:
        mean = average(point.indications)
        error = absolute_error(mean, point.reference_value)
        repeatability = repeatability_uncertainty(point.indications)
        resolution = resolution_uncertainty(point.resolution)
        components = [repeatability, resolution]
        if point.pattern_uncertainty is not None:
            components.append(float(point.pattern_uncertainty))
        combined = combined_uncertainty(components)
        expanded = expanded_uncertainty(combined, point.k)
        accepted = None
        if point.tolerance is not None:
            accepted = abs(error) + expanded <= point.tolerance
        results.append(
            CalculationPointResult(
                reference_value=round(point.reference_value, 6),
                average=round(mean, 6),
                error=round(error, 6),
                repeatability_uncertainty=round(repeatability, 6),
                resolution_uncertainty=round(resolution, 6),
                combined_uncertainty=round(combined, 6),
                expanded_uncertainty=round(expanded, 6),
                tolerance=point.tolerance,
                accepted=accepted,
            )
        )

    decisions = [result.accepted for result in results if result.accepted is not None]
    final_result = "informative"
    if decisions:
        final_result = "accepted" if all(decisions) else "rejected"
    else:
        messages.append(
            _message(
                "ADVERTENCIA",
                "tolerance_missing",
                "No se indicaron tolerancias; el resultado final es informativo.",
            )
        )

    certificate_tables = [
        {
            "profile_key": profile["profile_key"],
            "magnitude": profile["magnitude"],
            "rows": [result.model_dump() for result in results],
        }
    ]
    result = CalculationResult(
        profile_key=profile_key,
        final_result=final_result,
        points=results,
        certificate_tables=certificate_tables,
        messages=messages,
    )
    write_audit_log(
        db,
        action="engine.calculation_executed",
        entity="metrology",
        entity_id=None,
        user_id=user_id,
        new_values=result.model_dump(),
    )
    db.commit()
    return result
