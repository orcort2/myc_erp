from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.reference_standard_certificate import (
    ReferenceStandardCertificateCreate,
    ReferenceStandardCertificateRead,
    ReferenceStandardCertificateUncertaintyCreate,
    ReferenceStandardCertificateUncertaintyUpdate,
    ReferenceStandardCertificateUpdate,
)
from app.services.auth import require_permission
from app.services.reference_standard_certificates import (
    activate_certificate,
    add_certificate_uncertainty,
    create_certificate,
    deactivate_certificate_uncertainty,
    get_certificate,
    list_certificates,
    suspend_certificate,
    update_certificate,
    update_certificate_uncertainty,
)


router = APIRouter(tags=["reference-standard-certificates"])


@router.get("/reference-standard-certificates", response_model=list[ReferenceStandardCertificateRead])
def get_reference_standard_certificates(
    reference_standard_id: int | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    is_current: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reference_standard_certificates.read")),
) -> list[ReferenceStandardCertificateRead]:
    return list_certificates(
        db,
        reference_standard_id=reference_standard_id,
        status=status_value,
        is_current=is_current,
    )


@router.get("/reference-standard-certificates/{certificate_id}", response_model=ReferenceStandardCertificateRead)
def get_reference_standard_certificate_by_id(
    certificate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reference_standard_certificates.read")),
) -> ReferenceStandardCertificateRead:
    return get_certificate(db, certificate_id)


@router.post(
    "/reference-standards/{standard_id}/certificates",
    response_model=ReferenceStandardCertificateRead,
    status_code=status.HTTP_201_CREATED,
)
def post_reference_standard_certificate(
    standard_id: int,
    payload: ReferenceStandardCertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reference_standard_certificates.create")),
) -> ReferenceStandardCertificateRead:
    return create_certificate(db, standard_id, payload, user_id=current_user.id)


@router.patch("/reference-standard-certificates/{certificate_id}", response_model=ReferenceStandardCertificateRead)
def patch_reference_standard_certificate(
    certificate_id: int,
    payload: ReferenceStandardCertificateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reference_standard_certificates.update")),
) -> ReferenceStandardCertificateRead:
    return update_certificate(db, certificate_id, payload, user_id=current_user.id)


@router.post("/reference-standard-certificates/{certificate_id}/activate", response_model=ReferenceStandardCertificateRead)
def post_activate_reference_standard_certificate(
    certificate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reference_standard_certificates.approve")),
) -> ReferenceStandardCertificateRead:
    return activate_certificate(db, certificate_id, user_id=current_user.id)


@router.post("/reference-standard-certificates/{certificate_id}/suspend", response_model=ReferenceStandardCertificateRead)
def post_suspend_reference_standard_certificate(
    certificate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reference_standard_certificates.update")),
) -> ReferenceStandardCertificateRead:
    return suspend_certificate(db, certificate_id, user_id=current_user.id)


@router.post(
    "/reference-standard-certificates/{certificate_id}/uncertainties",
    response_model=ReferenceStandardCertificateRead,
    status_code=status.HTTP_201_CREATED,
)
def post_reference_standard_certificate_uncertainty(
    certificate_id: int,
    payload: ReferenceStandardCertificateUncertaintyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reference_standard_certificates.update")),
) -> ReferenceStandardCertificateRead:
    return add_certificate_uncertainty(db, certificate_id, payload, user_id=current_user.id)


@router.patch(
    "/reference-standard-certificates/uncertainties/{uncertainty_id}",
    response_model=ReferenceStandardCertificateRead,
)
def patch_reference_standard_certificate_uncertainty(
    uncertainty_id: int,
    payload: ReferenceStandardCertificateUncertaintyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reference_standard_certificates.update")),
) -> ReferenceStandardCertificateRead:
    return update_certificate_uncertainty(db, uncertainty_id, payload, user_id=current_user.id)


@router.delete(
    "/reference-standard-certificates/uncertainties/{uncertainty_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_reference_standard_certificate_uncertainty(
    uncertainty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reference_standard_certificates.delete")),
) -> Response:
    deactivate_certificate_uncertainty(db, uncertainty_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
