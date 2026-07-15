from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.sat_catalog import SatCatalogAlias
from app.models.user import User
from app.schemas.sat_catalog import (
    SatCatalogAliasCreate,
    SatCatalogAliasRead,
    SatCatalogFavoriteCreate,
    SatCatalogFavoriteRead,
    SatCatalogRead,
    SatCatalogRecordPage,
    SatCatalogVersionRead,
)
from app.services.auth import require_permission
from app.services.sat_catalogs.service import (
    add_alias,
    add_favorite,
    delete_alias,
    get_catalog,
    get_record,
    latest_version,
    list_aliases,
    list_catalogs,
    remove_favorite,
    search_records,
)


router = APIRouter(prefix="/sat-catalogs", tags=["sat-catalogs"])


@router.get("", response_model=list[SatCatalogRead])
def read_sat_catalogs(db: Session = Depends(get_db), current_user: User = Depends(require_permission("sat_catalogs.read"))):
    return list_catalogs(db)


@router.get("/{catalog_code}/versions", response_model=list[SatCatalogVersionRead])
def read_sat_catalog_versions(catalog_code: str, db: Session = Depends(get_db), current_user: User = Depends(require_permission("sat_catalogs.read"))):
    try:
        catalog = get_catalog(db, catalog_code)
    except KeyError:
        raise HTTPException(status_code=404, detail="Catálogo SAT no encontrado")
    return sorted(catalog.versions, key=lambda item: (item.imported_at, item.id), reverse=True)


@router.get("/{catalog_code}/records", response_model=SatCatalogRecordPage)
def read_sat_catalog_records(
    catalog_code: str,
    search: str | None = Query(default=None, max_length=160),
    active_only: bool = True,
    favorites_only: bool = False,
    version_id: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("sat_catalogs.read")),
):
    try:
        version, total, records = search_records(db, catalog_code, search=search, active_only=active_only, favorites_only=favorites_only, version_id=version_id, offset=offset, limit=limit, user_id=current_user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Catálogo SAT no encontrado")
    if version is None:
        raise HTTPException(status_code=404, detail="No hay una versión instalada para este catálogo")
    return SatCatalogRecordPage(catalog=catalog_code, version=version.version, total=total, items=records)


def _require_record(db: Session, record_id: int):
    record = get_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Registro SAT no encontrado")
    return record


@router.post("/records/{record_id}/favorite", response_model=SatCatalogFavoriteRead, status_code=status.HTTP_201_CREATED)
def create_favorite(record_id: int, payload: SatCatalogFavoriteCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("sat_catalogs.manage_favorites"))):
    return add_favorite(db, _require_record(db, record_id), user_id=current_user.id, notes=payload.notes)


@router.delete("/records/{record_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_permission("sat_catalogs.manage_favorites"))):
    _require_record(db, record_id)
    remove_favorite(db, _require_record(db, record_id), user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/records/{record_id}/aliases", response_model=list[SatCatalogAliasRead])
def read_aliases(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_permission("sat_catalogs.read"))):
    _require_record(db, record_id)
    return list_aliases(db, record_id)


@router.post("/records/{record_id}/aliases", response_model=SatCatalogAliasRead, status_code=status.HTTP_201_CREATED)
def create_alias(record_id: int, payload: SatCatalogAliasCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("sat_catalogs.manage_aliases"))):
    try:
        return add_alias(db, _require_record(db, record_id), alias=payload.alias, user_id=current_user.id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.delete("/aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_alias(alias_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_permission("sat_catalogs.manage_aliases"))):
    alias = db.get(SatCatalogAlias, alias_id)
    if alias is None:
        raise HTTPException(status_code=404, detail="Alias SAT no encontrado")
    delete_alias(db, alias)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
