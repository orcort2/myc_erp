from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.calibration_procedure import (
    CalibrationProcedureCreate,
    CalibrationProcedureRead,
    CalibrationProcedureUpdate,
)
from app.services.auth import require_permission
from app.services.calibration_procedures import (
    create_calibration_procedure,
    deactivate_calibration_procedure,
    get_calibration_procedure,
    list_calibration_procedures,
    update_calibration_procedure,
)


router = APIRouter(prefix="/calibration-procedures", tags=["calibration-procedures"])


@router.get("", response_model=list[CalibrationProcedureRead])
def get_calibration_procedures(
    include_inactive: bool = Query(default=False),
    magnitude: str | None = Query(default=None),
    profile_key: str | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("procedures.read")),
) -> list[CalibrationProcedureRead]:
    return list_calibration_procedures(
        db,
        include_inactive=include_inactive,
        magnitude=magnitude,
        profile_key=profile_key,
        status_value=status_value,
        search=search,
    )


@router.post("", response_model=CalibrationProcedureRead, status_code=status.HTTP_201_CREATED)
def post_calibration_procedure(
    payload: CalibrationProcedureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("procedures.create")),
) -> CalibrationProcedureRead:
    return create_calibration_procedure(db, payload, user_id=current_user.id)


@router.get("/{procedure_id}", response_model=CalibrationProcedureRead)
def get_calibration_procedure_by_id(
    procedure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("procedures.read")),
) -> CalibrationProcedureRead:
    return get_calibration_procedure(db, procedure_id)


@router.patch("/{procedure_id}", response_model=CalibrationProcedureRead)
def patch_calibration_procedure(
    procedure_id: int,
    payload: CalibrationProcedureUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("procedures.update")),
) -> CalibrationProcedureRead:
    return update_calibration_procedure(db, procedure_id, payload, user_id=current_user.id)


@router.delete("/{procedure_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calibration_procedure(
    procedure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("procedures.delete")),
) -> Response:
    deactivate_calibration_procedure(db, procedure_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
