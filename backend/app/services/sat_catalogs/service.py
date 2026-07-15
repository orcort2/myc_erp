from datetime import date
import re

from sqlalchemy import and_, exists, func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.models.sat_catalog import SatCatalog, SatCatalogAlias, SatCatalogFavorite, SatCatalogRecord, SatCatalogVersion
from app.services.sat_catalogs.definitions import DEFINITIONS_BY_CODE
from app.services.sat_catalogs.normalizers import normalize_search


def list_catalogs(db: Session) -> list[SatCatalog]:
    catalogs = list(db.scalars(select(SatCatalog).order_by(SatCatalog.name)).all())
    for catalog in catalogs:
        catalog.installed_version = latest_version(db, catalog)
    return catalogs


def get_catalog(db: Session, catalog_code: str) -> SatCatalog:
    if catalog_code not in DEFINITIONS_BY_CODE:
        raise KeyError(catalog_code)
    catalog = db.scalar(select(SatCatalog).where(SatCatalog.code == catalog_code))
    if catalog is None:
        raise KeyError(catalog_code)
    return catalog


def latest_version(db: Session, catalog: SatCatalog) -> SatCatalogVersion | None:
    return db.scalar(
        select(SatCatalogVersion)
        .where(SatCatalogVersion.catalog_id == catalog.id, SatCatalogVersion.status == "imported")
        .order_by(SatCatalogVersion.imported_at.desc(), SatCatalogVersion.id.desc())
        .limit(1)
    )


def activate_catalog_version(db: Session, *, catalog_code: str, version: str) -> SatCatalogVersion:
    catalog = get_catalog(db, catalog_code)
    target = db.scalar(select(SatCatalogVersion).where(SatCatalogVersion.catalog_id == catalog.id, SatCatalogVersion.version == version, SatCatalogVersion.status == "staged"))
    if target is None:
        raise KeyError(f"No existe una versión staged para {catalog_code} / {version}.")
    db.execute(update(SatCatalogVersion).where(SatCatalogVersion.catalog_id == catalog.id, SatCatalogVersion.status == "imported").values(status="archived"))
    target.status = "imported"
    db.flush()
    return target


def is_record_current(record: SatCatalogRecord, today: date | None = None) -> bool:
    today = today or date.today()
    return bool(record.is_active and (record.valid_from is None or record.valid_from <= today) and (record.valid_until is None or record.valid_until >= today))


def search_records(db: Session, catalog_code: str, *, search: str | None, active_only: bool, favorites_only: bool = False, version_id: int | None = None, offset: int = 0, limit: int = 50, user_id: int | None = None):
    catalog = get_catalog(db, catalog_code)
    version = db.get(SatCatalogVersion, version_id) if version_id else latest_version(db, catalog)
    if version is not None and version.catalog_id != catalog.id:
        raise KeyError(catalog_code)
    if version is None:
        return None, 0, []
    today = date.today()
    favorite_join = and_(SatCatalogFavorite.catalog_record_id == SatCatalogRecord.id, SatCatalogFavorite.created_by_id == user_id)
    record_filters = [SatCatalogRecord.catalog_version_id == version.id]
    query = (
        select(SatCatalogRecord, SatCatalogFavorite.id.label("favorite_id"))
        .outerjoin(SatCatalogFavorite, favorite_join)
        .where(*record_filters)
    )
    if active_only:
        record_filters.extend([SatCatalogRecord.is_active.is_(True), or_(SatCatalogRecord.valid_from.is_(None), SatCatalogRecord.valid_from <= today), or_(SatCatalogRecord.valid_until.is_(None), SatCatalogRecord.valid_until >= today)])
        query = query.where(*record_filters[1:])
    if favorites_only:
        query = query.where(SatCatalogFavorite.id.is_not(None))
    normalized = normalize_search(search) if search else ""
    if normalized:
        terms = [term for term in normalized.split() if term]
        is_code_search = bool(re.fullmatch(r"[a-z0-9.-]+", normalized)) and any(character.isdigit() for character in normalized)
        if is_code_search:
            query = query.where(SatCatalogRecord.normalized_code.like(f"{normalized}%"))
        else:
            pattern = f"%{normalized}%"
            alias_match = exists(select(1).where(SatCatalogAlias.catalog_record_id == SatCatalogRecord.id, SatCatalogAlias.is_active.is_(True), SatCatalogAlias.normalized_alias.like(pattern)))
            textual_match = or_(SatCatalogRecord.normalized_name.like(pattern), SatCatalogRecord.search_text.like(pattern))
            if db.bind and db.bind.dialect.name == "postgresql" and terms:
                textual_match = func.to_tsvector("simple", SatCatalogRecord.search_text).op("@@")(func.plainto_tsquery("simple", " ".join(terms)))
            text_ids = select(SatCatalogRecord.id).where(*record_filters, textual_match)
            alias_ids = select(SatCatalogRecord.id).where(*record_filters, alias_match)
            match_ids = text_ids.union(alias_ids).subquery()
            query = query.where(SatCatalogRecord.id.in_(select(match_ids.c.id)))
    total = db.scalar(select(func.count()).select_from(query.with_only_columns(SatCatalogRecord.id).subquery())) or 0
    rows = db.execute(query.options(selectinload(SatCatalogRecord.aliases)).order_by(SatCatalogFavorite.id.desc().nulls_last(), SatCatalogRecord.code).offset(offset).limit(limit)).all()
    records = []
    for record, favorite_id in rows:
        aliases = [alias for alias in record.aliases if alias.is_active]
        matched_on = []
        if normalized:
            if record.normalized_code == normalized or record.normalized_code.startswith(normalized):
                matched_on.append("code")
            if normalized in record.normalized_name or normalized in record.search_text:
                matched_on.append("description")
            if any(normalized in alias.normalized_alias for alias in aliases):
                matched_on.append("alias")
        record.is_favorite = favorite_id is not None
        record.is_current = is_record_current(record, today)
        record.matched_on = matched_on
        records.append(record)
    return version, total, records


def get_record(db: Session, record_id: int) -> SatCatalogRecord | None:
    return db.scalar(select(SatCatalogRecord).where(SatCatalogRecord.id == record_id))


def list_aliases(db: Session, record_id: int) -> list[SatCatalogAlias]:
    return list(db.scalars(select(SatCatalogAlias).where(SatCatalogAlias.catalog_record_id == record_id).order_by(SatCatalogAlias.alias)).all())


def add_alias(db: Session, record: SatCatalogRecord, *, alias: str, user_id: int) -> SatCatalogAlias:
    normalized_alias = normalize_search(alias)
    if not normalized_alias:
        raise ValueError("El alias no puede estar vacío.")
    existing = db.scalar(select(SatCatalogAlias).where(SatCatalogAlias.catalog_record_id == record.id, SatCatalogAlias.normalized_alias == normalized_alias))
    if existing:
        raise ValueError("Ya existe un alias equivalente para este registro.")
    item = SatCatalogAlias(catalog_record_id=record.id, alias=alias.strip(), normalized_alias=normalized_alias, created_by_id=user_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_alias(db: Session, alias: SatCatalogAlias) -> None:
    db.delete(alias)
    db.commit()


def add_favorite(db: Session, record: SatCatalogRecord, *, user_id: int, notes: str | None = None) -> SatCatalogFavorite:
    favorite = db.scalar(select(SatCatalogFavorite).where(SatCatalogFavorite.catalog_record_id == record.id, SatCatalogFavorite.created_by_id == user_id))
    if favorite:
        return favorite
    favorite = SatCatalogFavorite(catalog_record_id=record.id, created_by_id=user_id, notes=notes)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


def remove_favorite(db: Session, record: SatCatalogRecord, *, user_id: int) -> bool:
    favorite = db.scalar(select(SatCatalogFavorite).where(SatCatalogFavorite.catalog_record_id == record.id, SatCatalogFavorite.created_by_id == user_id))
    if favorite is None:
        return False
    db.delete(favorite)
    db.commit()
    return True
