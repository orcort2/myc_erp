from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.quotation import (
    QuotationCreate,
    QuotationItemCreate,
    QuotationItemUpdate,
    QuotationRead,
    QuotationStatusChange,
    QuotationUpdate,
)
from app.services.quotations import (
    add_quotation_item,
    change_quotation_status,
    create_quotation,
    deactivate_quotation,
    deactivate_quotation_item,
    get_quotation,
    list_quotations,
    update_quotation,
    update_quotation_item,
)
from app.services.quotation_pdfs import generate_quotation_pdf


router = APIRouter(prefix="/quotations", tags=["quotations"])


@router.get("", response_model=list[QuotationRead])
def get_quotations(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[QuotationRead]:
    return list_quotations(db, include_inactive=include_inactive)


@router.post("", response_model=QuotationRead, status_code=status.HTTP_201_CREATED)
def post_quotation(
    payload: QuotationCreate,
    db: Session = Depends(get_db),
) -> QuotationRead:
    return create_quotation(db, payload)


@router.get("/{quotation_id}", response_model=QuotationRead)
def get_quotation_by_id(
    quotation_id: int, db: Session = Depends(get_db)
) -> QuotationRead:
    return get_quotation(db, quotation_id)


@router.get("/{quotation_id}/pdf")
def get_quotation_pdf(
    quotation_id: int,
    db: Session = Depends(get_db),
) -> Response:
    pdf_bytes, filename = generate_quotation_pdf(db, quotation_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.patch("/{quotation_id}", response_model=QuotationRead)
def patch_quotation(
    quotation_id: int,
    payload: QuotationUpdate,
    db: Session = Depends(get_db),
) -> QuotationRead:
    return update_quotation(db, quotation_id, payload)


@router.post("/{quotation_id}/items", response_model=QuotationRead)
def post_quotation_item(
    quotation_id: int,
    payload: QuotationItemCreate,
    db: Session = Depends(get_db),
) -> QuotationRead:
    return add_quotation_item(db, quotation_id, payload)


@router.patch("/{quotation_id}/items/{item_id}", response_model=QuotationRead)
def patch_quotation_item(
    quotation_id: int,
    item_id: int,
    payload: QuotationItemUpdate,
    db: Session = Depends(get_db),
) -> QuotationRead:
    return update_quotation_item(db, quotation_id, item_id, payload)


@router.delete("/{quotation_id}/items/{item_id}", response_model=QuotationRead)
def delete_quotation_item(
    quotation_id: int,
    item_id: int,
    db: Session = Depends(get_db),
) -> QuotationRead:
    return deactivate_quotation_item(db, quotation_id, item_id)


@router.post("/{quotation_id}/send", response_model=QuotationRead)
def send_quotation(
    quotation_id: int,
    payload: QuotationStatusChange | None = None,
    db: Session = Depends(get_db),
) -> QuotationRead:
    return change_quotation_status(db, quotation_id, "sent", payload)


@router.post("/{quotation_id}/waiting", response_model=QuotationRead)
def mark_quotation_waiting(
    quotation_id: int,
    payload: QuotationStatusChange | None = None,
    db: Session = Depends(get_db),
) -> QuotationRead:
    return change_quotation_status(db, quotation_id, "waiting", payload)


@router.post("/{quotation_id}/accept", response_model=QuotationRead)
def accept_quotation(
    quotation_id: int,
    payload: QuotationStatusChange | None = None,
    db: Session = Depends(get_db),
) -> QuotationRead:
    return change_quotation_status(db, quotation_id, "accepted", payload)


@router.post("/{quotation_id}/reject", response_model=QuotationRead)
def reject_quotation(
    quotation_id: int,
    payload: QuotationStatusChange | None = None,
    db: Session = Depends(get_db),
) -> QuotationRead:
    return change_quotation_status(db, quotation_id, "rejected", payload)


@router.post("/{quotation_id}/expire", response_model=QuotationRead)
def expire_quotation(
    quotation_id: int,
    payload: QuotationStatusChange | None = None,
    db: Session = Depends(get_db),
) -> QuotationRead:
    return change_quotation_status(db, quotation_id, "expired", payload)


@router.post("/{quotation_id}/cancel", response_model=QuotationRead)
def cancel_quotation(
    quotation_id: int,
    payload: QuotationStatusChange | None = None,
    db: Session = Depends(get_db),
) -> QuotationRead:
    return change_quotation_status(db, quotation_id, "cancelled", payload)


@router.delete("/{quotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quotation(quotation_id: int, db: Session = Depends(get_db)) -> Response:
    deactivate_quotation(db, quotation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
