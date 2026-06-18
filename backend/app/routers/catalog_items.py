from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.catalog_item import CatalogItemCreate, CatalogItemOut, CatalogItemUpdate
from app.services.catalog_items import (
    create_catalog_item,
    delete_catalog_item,
    get_catalog_item,
    list_catalog_items,
    update_catalog_item,
)


router = APIRouter(prefix="/catalog-items", tags=["catalog-items"])


@router.get("", response_model=list[CatalogItemOut])
def get_catalog_items(
    item_type: str | None = Query(default=None),
    commodity: str | None = Query(default=None),
    category: str | None = Query(default=None),
    origin_currency: str | None = Query(default=None),
    tax_object: str | None = Query(default=None),
    is_active: bool | None = Query(default=True),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CatalogItemOut]:
    return list_catalog_items(
        db,
        item_type=item_type,
        commodity=commodity,
        category=category,
        origin_currency=origin_currency,
        tax_object=tax_object,
        is_active=is_active,
        search=search,
    )


@router.post("", response_model=CatalogItemOut, status_code=status.HTTP_201_CREATED)
def post_catalog_item(
    payload: CatalogItemCreate,
    db: Session = Depends(get_db),
) -> CatalogItemOut:
    return create_catalog_item(db, payload)


@router.get("/{catalog_item_id}", response_model=CatalogItemOut)
def get_catalog_item_by_id(
    catalog_item_id: int,
    db: Session = Depends(get_db),
) -> CatalogItemOut:
    return get_catalog_item(db, catalog_item_id)


@router.patch("/{catalog_item_id}", response_model=CatalogItemOut)
def patch_catalog_item(
    catalog_item_id: int,
    payload: CatalogItemUpdate,
    db: Session = Depends(get_db),
) -> CatalogItemOut:
    return update_catalog_item(db, catalog_item_id, payload)


@router.delete("/{catalog_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog_item_by_id(
    catalog_item_id: int,
    db: Session = Depends(get_db),
) -> Response:
    delete_catalog_item(db, catalog_item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
