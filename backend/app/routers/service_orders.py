from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.service_order import (
    ServiceOrderCreate,
    ServiceOrderRead,
    ServiceOrderStatusChange,
    ServiceOrderUpdate,
)
from app.schemas.certificate import CertificateBatchActionRead, CertificateBulkUploadRead
from app.services.certificates import (
    authenticate_certificates_for_service_order,
    bulk_upload_certificate_pdfs,
    release_authenticated_certificates_for_service_order,
)
from app.services.service_orders import (
    change_status,
    close_service_order,
    create_service_order,
    deactivate_service_order,
    get_service_order,
    list_service_orders,
    update_service_order,
)
from app.services.work_order_pdfs import (
    generate_service_work_order_pdf,
    generate_work_order_pdf,
)

from io import BytesIO


router = APIRouter(prefix="/service-orders", tags=["service-orders"])


@router.get("", response_model=list[ServiceOrderRead])
def get_service_orders(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[ServiceOrderRead]:
    return list_service_orders(db, include_inactive=include_inactive)


@router.post("", response_model=ServiceOrderRead, status_code=status.HTTP_201_CREATED)
def post_service_order(
    payload: ServiceOrderCreate,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return create_service_order(db, payload)


@router.get("/{service_order_id}", response_model=ServiceOrderRead)
def get_service_order_by_id(
    service_order_id: int, db: Session = Depends(get_db)
) -> ServiceOrderRead:
    return get_service_order(db, service_order_id)


@router.get("/{service_order_id}/work-order-pdf")
def get_service_order_work_order_pdf(
    service_order_id: int,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    pdf_bytes, filename = generate_work_order_pdf(db, service_order_id)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
@router.get("/work-orders/{work_order_id}/pdf")
def get_service_work_order_pdf(
    work_order_id: int,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    pdf_bytes, filename = generate_service_work_order_pdf(db, work_order_id)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/{service_order_id}/certificate-pdfs", response_model=CertificateBulkUploadRead)
def upload_service_order_certificate_pdfs(
    service_order_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> CertificateBulkUploadRead:
    return bulk_upload_certificate_pdfs(db, service_order_id, files)


@router.post("/{service_order_id}/certificates/authenticate-approved", response_model=CertificateBatchActionRead)
def authenticate_service_order_certificates(
    service_order_id: int,
    db: Session = Depends(get_db),
) -> CertificateBatchActionRead:
    return authenticate_certificates_for_service_order(db, service_order_id)


@router.post("/{service_order_id}/certificates/release-authenticated", response_model=CertificateBatchActionRead)
def release_service_order_certificates(
    service_order_id: int,
    db: Session = Depends(get_db),
) -> CertificateBatchActionRead:
    return release_authenticated_certificates_for_service_order(db, service_order_id)


@router.patch("/{service_order_id}", response_model=ServiceOrderRead)
def patch_service_order(
    service_order_id: int,
    payload: ServiceOrderUpdate,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return update_service_order(db, service_order_id, payload)


@router.post("/{service_order_id}/confirm", response_model=ServiceOrderRead)
def confirm_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "confirmed", payload)


@router.post("/{service_order_id}/call", response_model=ServiceOrderRead)
def call_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "called", payload)


@router.post("/{service_order_id}/start", response_model=ServiceOrderRead)
def start_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "in_progress", payload)


@router.post("/{service_order_id}/capture", response_model=ServiceOrderRead)
def capture_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "capture", payload)


@router.post("/{service_order_id}/quality", response_model=ServiceOrderRead)
def quality_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "quality_review", payload)


@router.post("/{service_order_id}/pending-payment", response_model=ServiceOrderRead)
def pending_payment_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "pending_payment", payload)


@router.post("/{service_order_id}/release", response_model=ServiceOrderRead)
def release_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "released", payload)


@router.post("/{service_order_id}/close", response_model=ServiceOrderRead)
def close_service_order_route(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return close_service_order(db, service_order_id, payload)


@router.delete("/{service_order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_order(
    service_order_id: int, db: Session = Depends(get_db)
) -> Response:
    deactivate_service_order(db, service_order_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
