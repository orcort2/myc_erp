from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.metrology import (
    MetrologyPreviewInput,
    MetrologyPreviewResult,
    MetrologyProfileRead,
)
from app.services.audit_logs import write_audit_log
from app.services.auth import require_permission
from app.services.metrology_engine import (
    absolute_error,
    average,
    combined_uncertainty,
    expanded_uncertainty,
    repeatability_uncertainty,
    resolution_uncertainty,
)
from app.services.metrology_profiles import get_metrology_profile, list_metrology_profiles


router = APIRouter(prefix="/metrology", tags=["metrology"])


@router.get("/profiles", response_model=list[MetrologyProfileRead])
def get_profiles(
    current_user: User = Depends(require_permission("procedures.read")),
) -> list[MetrologyProfileRead]:
    return list_metrology_profiles()


@router.post("/calculate-preview", response_model=MetrologyPreviewResult)
def post_calculate_preview(
    payload: MetrologyPreviewInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("metrology.execute")),
) -> MetrologyPreviewResult:
    try:
        get_metrology_profile(payload.profile_key)
        mean = average(payload.indications)
        error = absolute_error(mean, payload.reference_value)
        repeatability = repeatability_uncertainty(payload.indications)
        resolution = resolution_uncertainty(payload.resolution)
        components = [repeatability, resolution]
        if payload.pattern_uncertainty is not None:
            components.append(float(payload.pattern_uncertainty))
        combined = combined_uncertainty(components)
        expanded = expanded_uncertainty(combined, payload.k)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = MetrologyPreviewResult(
        average=round(mean, 6),
        error=round(error, 6),
        repeatability_uncertainty=round(repeatability, 6),
        resolution_uncertainty=round(resolution, 6),
        combined_uncertainty=round(combined, 6),
        expanded_uncertainty=round(expanded, 6),
    )
    write_audit_log(
        db,
        action="metrology.preview_calculated",
        entity="metrology",
        entity_id=None,
        user_id=current_user.id,
        new_values={
            "profile_key": payload.profile_key,
            "reference_value": payload.reference_value,
            "indications_count": len(payload.indications),
            "result": result.model_dump(),
        },
    )
    db.commit()
    return result
