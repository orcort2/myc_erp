from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.reference_standard import (
    ReferenceStandardCreate,
    ReferenceStandardRead,
    ReferenceStandardUncertaintyCreate,
    ReferenceStandardUncertaintyUpdate,
    ReferenceStandardUpdate,
)
from app.services.auth import require_permission
from app.services.reference_standards import (
    create_reference_standard,
    create_reference_standard_uncertainty,
    deactivate_reference_standard,
    deactivate_reference_standard_uncertainty,
    get_reference_standard,
    list_reference_standards,
    update_reference_standard,
    update_reference_standard_uncertainty,
)


router = APIRouter(prefix="/reference-standards", tags=["reference-standards"])


@router.get("", response_model=list[ReferenceStandardRead])
def get_reference_standards(
    include_inactive: bool = Query(default=False),
    owner_company: str | None = Query(default=None),
    magnitude: str | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("standards.read")),
) -> list[ReferenceStandardRead]:
    return list_reference_standards(
        db,
        include_inactive=include_inactive,
        owner_company=owner_company,
        magnitude=magnitude,
        status_value=status_value,
        search=search,
    )


@router.post("", response_model=ReferenceStandardRead, status_code=status.HTTP_201_CREATED)
def post_reference_standard(
    payload: ReferenceStandardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("standards.create")),
) -> ReferenceStandardRead:
    return create_reference_standard(db, payload, user_id=current_user.id)


@router.get("/{standard_id}", response_model=ReferenceStandardRead)
def get_reference_standard_by_id(
    standard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("standards.read")),
) -> ReferenceStandardRead:
    return get_reference_standard(db, standard_id)


@router.patch("/{standard_id}", response_model=ReferenceStandardRead)
def patch_reference_standard(
    standard_id: int,
    payload: ReferenceStandardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("standards.update")),
) -> ReferenceStandardRead:
    return update_reference_standard(db, standard_id, payload, user_id=current_user.id)


@router.delete("/{standard_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference_standard(
    standard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("standards.delete")),
) -> Response:
    deactivate_reference_standard(db, standard_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{standard_id}/uncertainties",
    response_model=ReferenceStandardRead,
    status_code=status.HTTP_201_CREATED,
)
def post_reference_standard_uncertainty(
    standard_id: int,
    payload: ReferenceStandardUncertaintyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("standards.update")),
) -> ReferenceStandardRead:
    return create_reference_standard_uncertainty(db, standard_id, payload, user_id=current_user.id)


@router.patch(
    "/{standard_id}/uncertainties/{uncertainty_id}",
    response_model=ReferenceStandardRead,
)
def patch_reference_standard_uncertainty(
    standard_id: int,
    uncertainty_id: int,
    payload: ReferenceStandardUncertaintyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("standards.update")),
) -> ReferenceStandardRead:
    return update_reference_standard_uncertainty(
        db, standard_id, uncertainty_id, payload, user_id=current_user.id
    )


@router.delete(
    "/{standard_id}/uncertainties/{uncertainty_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_reference_standard_uncertainty(
    standard_id: int,
    uncertainty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("standards.delete")),
) -> Response:
    deactivate_reference_standard_uncertainty(
        db, standard_id, uncertainty_id, user_id=current_user.id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
