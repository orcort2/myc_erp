#!/usr/bin/env python3
"""Import a manually downloaded SAT catalog into ERP MYC."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import SessionLocal  # noqa: E402
from app.services.sat_catalogs.definitions import CATALOG_DEFINITIONS  # noqa: E402
from app.services.sat_catalogs.importer import import_catalog_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa un catálogo SAT descargado manualmente.")
    parser.add_argument("catalog", choices=[item.code for item in CATALOG_DEFINITIONS])
    parser.add_argument("file", type=Path)
    parser.add_argument("--version", required=True, help="Versión o fecha publicada por el SAT.")
    parser.add_argument("--publication-date", type=date.fromisoformat, help="Fecha de publicación YYYY-MM-DD.")
    parser.add_argument("--user-id", type=int, help="Usuario ERP que ejecuta la importación.")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        report = import_catalog_file(db, catalog_code=args.catalog, path=args.file, version=args.version, publication_date=args.publication_date, imported_by_id=args.user_id)
        print(json.dumps(report.as_dict(), ensure_ascii=False, default=str, indent=2))
        return 0
    except Exception as error:
        db.rollback()
        print(f"Error de importación: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
