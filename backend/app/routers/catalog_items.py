from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.catalog_item import (
    CatalogItemCreate,
    CatalogItemOut,
    CatalogItemUpdate,
    LinkedCompanyCreate,
    LinkedCompanyOut,
)
from app.services.catalog_items import (
    create_catalog_item,
    create_linked_company,
    delete_catalog_item,
    get_catalog_item,
    list_catalog_items,
    list_linked_companies,
    update_catalog_item,
)
from app.models.user import User
from app.services.auth import get_current_user, user_has_permission


router = APIRouter(prefix="/catalog-items", tags=["catalog-items"])


@router.get("/linked-companies", response_model=list[LinkedCompanyOut])
def get_linked_companies(db: Session = Depends(get_db)) -> list[LinkedCompanyOut]:
    return list_linked_companies(db)


@router.post(
    "/linked-companies",
    response_model=LinkedCompanyOut,
    status_code=status.HTTP_201_CREATED,
)
def post_linked_company(
    payload: LinkedCompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LinkedCompanyOut:
    if not user_has_permission(current_user, "services.manage_linked_company"):
        raise HTTPException(status_code=403, detail="Permiso insuficiente")
    return create_linked_company(db, payload, user_id=current_user.id)


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
