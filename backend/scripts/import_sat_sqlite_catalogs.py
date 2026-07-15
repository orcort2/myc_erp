#!/usr/bin/env python3
"""Controlled import of the bundled, read-only SAT SQLite release."""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import SessionLocal  # noqa: E402
from app.services.sat_catalogs.importer import import_catalog_records  # noqa: E402
from app.services.sat_catalogs.sqlite_source import SQLITE_TABLE_BY_CATALOG, extract_catalog_rows, source_checksum  # noqa: E402


def source_version(source: Path) -> str:
    version_file = source.parent / "VERSION.txt"
    if not version_file.is_file():
        raise ValueError("No se encontró VERSION.txt junto a la fuente SQLite; indica --version.")
    return version_file.read_text(encoding="utf-8").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa los catálogos CFDI 4.0 desde SQLite en modo lectura.")
    parser.add_argument("--source", type=Path, default=BACKEND_DIR / "resources/sat/catalogs.db")
    parser.add_argument("--catalog", choices=[*SQLITE_TABLE_BY_CATALOG, "all"], default="all")
    parser.add_argument("--version")
    parser.add_argument("--publication-date", type=date.fromisoformat)
    parser.add_argument("--user-id", type=int)
    args = parser.parse_args()
    version = args.version or source_version(args.source)
    targets = list(SQLITE_TABLE_BY_CATALOG) if args.catalog == "all" else [args.catalog]
    db = SessionLocal()
    reports = []
    started = time.perf_counter()
    try:
        for catalog_code in targets:
            table, rows = extract_catalog_rows(args.source, catalog_code)
            reports.append(import_catalog_records(db, catalog_code=catalog_code, rows=rows, source_filename=f"{args.source.name}:{table}", checksum=source_checksum(args.source, table), version=version, publication_date=args.publication_date, imported_by_id=args.user_id).as_dict())
        print(json.dumps({"source": str(args.source), "version": version, "elapsed_seconds": round(time.perf_counter() - started, 3), "reports": reports}, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as error:
        db.rollback()
        print(f"Error de importación SQLite: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
