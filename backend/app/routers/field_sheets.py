from io import BytesIO

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.field_sheet import (
    FieldSheetCreate,
    FieldSheetRead,
    FieldSheetStatusChange,
    FieldSheetUpdate,
)
from app.services.field_sheets import (
    complete_field_sheet,
    create_field_sheet,
    deactivate_field_sheet,
    get_field_sheet,
    list_field_sheets,
    review_field_sheet,
    update_field_sheet,
)
from app.services.field_sheet_pdfs import generate_field_sheet_pdf


router = APIRouter(prefix="/field-sheets", tags=["field-sheets"])


@router.get("", response_model=list[FieldSheetRead])
def get_field_sheets(
    equipment_id: int | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[FieldSheetRead]:
    return list_field_sheets(
        db,
        equipment_id=equipment_id,
        include_inactive=include_inactive,
    )


@router.post("", response_model=FieldSheetRead, status_code=status.HTTP_201_CREATED)
def post_field_sheet(
    payload: FieldSheetCreate,
    db: Session = Depends(get_db),
) -> FieldSheetRead:
    return create_field_sheet(db, payload)


@router.get("/{field_sheet_id}", response_model=FieldSheetRead)
def get_field_sheet_by_id(
    field_sheet_id: int, db: Session = Depends(get_db)
) -> FieldSheetRead:
    return get_field_sheet(db, field_sheet_id)


@router.get("/{field_sheet_id}/pdf")
def get_field_sheet_pdf(
    field_sheet_id: int,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    pdf_bytes, filename = generate_field_sheet_pdf(db, field_sheet_id)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.patch("/{field_sheet_id}", response_model=FieldSheetRead)
def patch_field_sheet(
    field_sheet_id: int,
    payload: FieldSheetUpdate,
    db: Session = Depends(get_db),
) -> FieldSheetRead:
    return update_field_sheet(db, field_sheet_id, payload)


@router.post("/{field_sheet_id}/complete", response_model=FieldSheetRead)
def complete_field_sheet_route(
    field_sheet_id: int,
    payload: FieldSheetStatusChange | None = None,
    db: Session = Depends(get_db),
) -> FieldSheetRead:
    return complete_field_sheet(db, field_sheet_id, payload)


@router.post("/{field_sheet_id}/review", response_model=FieldSheetRead)
def review_field_sheet_route(
    field_sheet_id: int,
    payload: FieldSheetStatusChange | None = None,
    db: Session = Depends(get_db),
) -> FieldSheetRead:
    return review_field_sheet(db, field_sheet_id, payload)


@router.delete("/{field_sheet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field_sheet(
    field_sheet_id: int, db: Session = Depends(get_db)
) -> Response:
    deactivate_field_sheet(db, field_sheet_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
