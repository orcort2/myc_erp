from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.quotation_service_change import (
    QuotationServiceChangeCreate,
    QuotationServiceChangeRead,
    QuotationServiceChangeReview,
    QuotationUnlockApply,
    QuotationUnlockPreview,
)
from app.services.auth import get_current_user
from app.services.quotation_service_changes import (
    apply_change,
    list_requests,
    preview_change,
    quotation_context,
    request_change,
    review_request,
)


router = APIRouter(prefix="/quotation-service-exceptions", tags=["sales-exceptions"])


@router.get("/quotations/{quotation_folio}/context")
def get_quotation_context(
    quotation_folio: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return quotation_context(db, quotation_folio, current_user)


@router.get("", response_model=list[QuotationServiceChangeRead])
def get_requests(
    quotation_folio: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[QuotationServiceChangeRead]:
    return list_requests(
        db,
        current_user,
        quotation_folio=quotation_folio,
    )


@router.post(
    "/quotations/{quotation_folio}",
    response_model=QuotationServiceChangeRead,
    status_code=status.HTTP_201_CREATED,
)
def post_request(
    quotation_folio: str,
    payload: QuotationServiceChangeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationServiceChangeRead:
    return request_change(db, quotation_folio, payload, current_user)


@router.post(
    "/{exception_folio}/review",
    response_model=QuotationServiceChangeRead,
)
def post_review(
    exception_folio: str,
    payload: QuotationServiceChangeReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationServiceChangeRead:
    return review_request(db, exception_folio, payload, current_user)


@router.post(
    "/{exception_folio}/preview",
)
def post_preview(
    exception_folio: str,
    payload: QuotationUnlockPreview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return preview_change(db, exception_folio, payload, current_user)


@router.post(
    "/{exception_folio}/apply",
    response_model=QuotationServiceChangeRead,
)
def post_apply(
    exception_folio: str,
    payload: QuotationUnlockApply,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationServiceChangeRead:
    return apply_change(db, exception_folio, payload, current_user)
