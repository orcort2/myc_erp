from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.certificate import (
    CertificateCreate,
    CertificatePdfUploadRead,
    CertificateRead,
    CertificateStatusChange,
    CertificateUpdate,
)
from app.services.certificates import (
    manual_accept_match,
    change_status,
    create_certificate,
    deactivate_certificate,
    get_certificate,
    list_certificates,
    quality_approve,
    quality_reject,
    release_to_client,
    request_correction,
    send_to_quality,
    start_capture,
    update_certificate,
    upload_certificate_pdf,
    validate_pdf_match,
)


router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get("", response_model=list[CertificateRead])
def get_certificates(
    service_order_id: int | None = Query(default=None),
    equipment_id: int | None = Query(default=None),
    client_visible: bool | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[CertificateRead]:
    return list_certificates(
        db,
        service_order_id=service_order_id,
        equipment_id=equipment_id,
        client_visible=client_visible,
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
    return change_status(db, certificate_id, "capture_in_progress", payload)


@router.post("/{certificate_id}/quality", response_model=CertificateRead)
def quality_certificate(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return change_status(db, certificate_id, "quality_review", payload)


@router.post("/{certificate_id}/start-capture", response_model=CertificateRead)
def start_certificate_capture(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return start_capture(db, certificate_id, payload)


@router.post("/{certificate_id}/send-to-quality", response_model=CertificateRead)
def send_certificate_to_quality(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return send_to_quality(db, certificate_id, payload)


@router.post("/{certificate_id}/quality-approve", response_model=CertificateRead)
def quality_approve_certificate(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return quality_approve(db, certificate_id, payload)


@router.post("/{certificate_id}/quality-reject", response_model=CertificateRead)
def quality_reject_certificate(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return quality_reject(db, certificate_id, payload)


@router.post("/{certificate_id}/upload-pdf", response_model=CertificateRead)
def upload_certificate_final_pdf(
    certificate_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> CertificateRead:
    return upload_certificate_pdf(db, certificate_id, file)


@router.post("/{certificate_id}/validate-pdf-match", response_model=CertificateRead)
def validate_certificate_pdf_match_route(
    certificate_id: int,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return validate_pdf_match(db, certificate_id)


@router.post("/{certificate_id}/release-to-client", response_model=CertificateRead)
def release_certificate_to_client(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return release_to_client(db, certificate_id, payload)


@router.post("/{certificate_id}/manual-accept-match", response_model=CertificateRead)
def manual_accept_certificate_match(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return manual_accept_match(db, certificate_id, payload)

@router.post("/{certificate_id}/request-correction", response_model=CertificateRead)
def request_certificate_correction(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return request_correction(db, certificate_id, payload)


@router.post("/{certificate_id}/draft", response_model=CertificateRead)
def return_certificate_to_draft(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return change_status(db, certificate_id, "draft", payload)

@router.post("/{certificate_id}/approve", response_model=CertificateRead)
def approve_certificate(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return quality_approve(db, certificate_id, payload)


@router.post("/{certificate_id}/release", response_model=CertificateRead)
def release_certificate(
    certificate_id: int,
    payload: CertificateStatusChange | None = None,
    db: Session = Depends(get_db),
) -> CertificateRead:
    return release_to_client(db, certificate_id, payload)


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
