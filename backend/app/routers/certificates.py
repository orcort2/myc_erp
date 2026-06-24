from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.certificate import (
    CertificateCreate,
    CertificateRead,
    CertificateStatusChange,
    CertificateUpdate,
)
from app.services.certificates import (
    change_status,
    create_certificate,
    deactivate_certificate,
    get_certificate,
    list_certificates,
    request_correction,
    update_certificate,
)


router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get("", response_model=list[CertificateRead])
def get_certificates(
    service_order_id: int | None = Query(default=None),
    equipment_id: int | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[CertificateRead]:
    return list_certificates(
        db,
        service_order_id=service_order_id,
        equipment_id=equipment_id,
        include_inactive=include_inactive,
    )


@router.post("", response_model=CertificateRead, status_code=status.HTTP_201_CREATED)
def post_certificate(
    payload: CertificateCreate,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return create_certificate(db, payload)


@router.get("/{certificate_id}", response_model=CertificateRead)
def get_certificate_by_id(
    certificate_id: int, db: Session = Depends(get_db)
) -> CertificateRead:
    return get_certificate(db, certificate_id)


@router.patch("/{certificate_id}", response_model=CertificateRead)
def patch_certificate(
    certificate_id: int,
    payload: CertificateUpdate,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return update_certificate(db, certificate_id, payload)


@router.post("/{certificate_id}/generate", response_model=CertificateRead)
def generate_certificate(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return change_status(db, certificate_id, "generated", payload)


@router.post("/{certificate_id}/quality", response_model=CertificateRead)
def quality_certificate(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return change_status(db, certificate_id, "quality_review", payload)

@router.post("/{certificate_id}/request-correction", response_model=CertificateRead)
def request_certificate_correction(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return request_correction(db, certificate_id, payload)

@router.post("/{certificate_id}/approve", response_model=CertificateRead)
def approve_certificate(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return change_status(db, certificate_id, "approved", payload)


@router.post("/{certificate_id}/release", response_model=CertificateRead)
def release_certificate(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return change_status(db, certificate_id, "released", payload)


@router.post("/{certificate_id}/suspend", response_model=CertificateRead)
def suspend_certificate(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return change_status(db, certificate_id, "suspended", payload)


@router.delete("/{certificate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_certificate(
    certificate_id: int, db: Session = Depends(get_db)
) -> Response:
    deactivate_certificate(db, certificate_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
