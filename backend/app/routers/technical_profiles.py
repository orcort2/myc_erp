from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.controlled_document import (
    TechnicalProfileCreate,
    TechnicalProfileRead,
    TechnicalProfileUpdate,
)
from app.services.auth import require_permission
from app.services.technical_profiles import (
    approve_technical_profile,
    create_technical_profile,
    create_technical_profile_new_version,
    get_technical_profile,
    list_technical_profiles,
    resolve_technical_profiles,
    update_technical_profile,
)


router = APIRouter(prefix="/technical-profiles", tags=["technical-profiles"])


@router.get("/resolve", response_model=list[TechnicalProfileRead])
def get_resolved_technical_profile(
    magnitude: str = Query(),
    equipment_type: str = Query(),
    service_type: str = Query(default="calibration"),
    calibration_scope: str = Query(),
    range_min: float | None = Query(default=None),
    range_max: float | None = Query(default=None),
    unit: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("technical_profiles.read")),
) -> list[TechnicalProfileRead]:
    return resolve_technical_profiles(
        db,
        magnitude=magnitude,
        equipment_type=equipment_type,
        service_type=service_type,
        calibration_scope=calibration_scope,
        range_min=range_min,
        range_max=range_max,
        unit=unit,
    )


@router.get("", response_model=list[TechnicalProfileRead])
def get_technical_profiles(
    magnitude: str | None = Query(default=None),
    equipment_type: str | None = Query(default=None),
    service_type: str | None = Query(default=None),
    calibration_scope: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("technical_profiles.read")),
) -> list[TechnicalProfileRead]:
    return list_technical_profiles(
        db,
        magnitude=magnitude,
        equipment_type=equipment_type,
        service_type=service_type,
        calibration_scope=calibration_scope,
        status=status,
    )


@router.post("", response_model=TechnicalProfileRead)
def post_technical_profile(
    payload: TechnicalProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("technical_profiles.create")),
) -> TechnicalProfileRead:
    return create_technical_profile(db, payload, user_id=current_user.id)


@router.get("/{profile_id}", response_model=TechnicalProfileRead)
def get_technical_profile_by_id(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("technical_profiles.read")),
) -> TechnicalProfileRead:
    return get_technical_profile(db, profile_id)


@router.patch("/{profile_id}", response_model=TechnicalProfileRead)
def patch_technical_profile(
    profile_id: int,
    payload: TechnicalProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("technical_profiles.update")),
) -> TechnicalProfileRead:
    return update_technical_profile(db, profile_id, payload, user_id=current_user.id)


@router.post("/{profile_id}/approve", response_model=TechnicalProfileRead)
def post_approve_technical_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("technical_profiles.approve")),
) -> TechnicalProfileRead:
    return approve_technical_profile(db, profile_id, user_id=current_user.id)


@router.post("/{profile_id}/new-version", response_model=TechnicalProfileRead)
def post_technical_profile_new_version(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("technical_profiles.create")),
) -> TechnicalProfileRead:
    return create_technical_profile_new_version(db, profile_id, user_id=current_user.id)
