from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sat_catalog import SatCatalogRecord, SatCatalogVersion
from app.services.sat_catalogs.parsers import parse_file
from app.services.sat_catalogs.reports import SatCatalogImportReport
from app.services.sat_catalogs.service import get_catalog
from app.services.sat_catalogs.normalizers import parse_date
from app.services.sat_catalogs.validators import canonical_record, validate_rows


class SatCatalogImportError(ValueError):
    pass


def file_checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_catalog_records(db: Session, *, catalog_code: str, rows: list[dict[str, object]], source_filename: str, checksum: str, version: str, publication_date=None, imported_by_id: int | None = None, status: str = "imported", report_metadata: dict | None = None, commit: bool = True) -> SatCatalogImportReport:
    if not version.strip():
        raise SatCatalogImportError("La versión es obligatoria.")
    rows = validate_rows(rows)
    catalog = get_catalog(db, catalog_code)
    existing_checksum = db.scalar(select(SatCatalogVersion).where(SatCatalogVersion.catalog_id == catalog.id, SatCatalogVersion.checksum == checksum))
    if existing_checksum:
        return SatCatalogImportReport(catalog_code, existing_checksum.version, source_filename, checksum, "skipped", existing_checksum.record_count, "La fuente ya fue importada.")
    existing_version = db.scalar(select(SatCatalogVersion).where(SatCatalogVersion.catalog_id == catalog.id, SatCatalogVersion.version == version))
    if existing_version:
        raise SatCatalogImportError("Ya existe esa versión para el catálogo con un checksum distinto.")
    report = SatCatalogImportReport(catalog_code, version, source_filename, checksum, "imported", len(rows), "Importación completada.")
    try:
        with db.begin_nested():
            catalog_version = SatCatalogVersion(
                catalog_id=catalog.id,
                version=version.strip(),
                publication_date=publication_date,
                imported_at=datetime.now(timezone.utc),
                checksum=checksum,
                source_filename=source_filename,
                imported_by_id=imported_by_id,
                record_count=len(rows),
                status=status,
                report={**report.as_dict(), **(report_metadata or {})},
            )
            db.add(catalog_version)
            db.flush()
            for row in rows:
                record = canonical_record(row)
                db.add(SatCatalogRecord(
                    catalog_version_id=catalog_version.id,
                    code=str(record["code"]),
                    name=record["name"],
                    normalized_code=record["normalized_code"],
                    normalized_name=record["normalized_name"],
                    search_text=record["search_text"],
                    valid_from=parse_date(record["valid_from"]),
                    valid_until=parse_date(record["valid_until"]),
                    is_active=True,
                    data=record["data"],
                ))
        if commit:
            db.commit()
    except Exception:
        if commit:
            db.rollback()
        raise
    return report


def import_catalog_file(db: Session, *, catalog_code: str, path: str | Path, version: str, publication_date=None, imported_by_id: int | None = None) -> SatCatalogImportReport:
    source = Path(path).expanduser()
    if not source.is_file():
        raise SatCatalogImportError(f"Archivo no encontrado: {source}")
    return import_catalog_records(
        db,
        catalog_code=catalog_code,
        rows=parse_file(source),
        source_filename=source.name,
        checksum=file_checksum(source),
        version=version,
        publication_date=publication_date,
        imported_by_id=imported_by_id,
    )
