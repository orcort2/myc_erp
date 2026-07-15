#!/usr/bin/env python3
"""Stage and explicitly activate CFDI 4.0 catalogs from an official SAT Excel file."""

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
from app.services.sat_catalogs.sat_xls_source import CATALOG_SHEETS, catalog_checksum, detect_version, extract_catalog_rows, inspect_source, source_metadata  # noqa: E402
from app.services.sat_catalogs.service import activate_catalog_version  # noqa: E402


def resolve_version(source: Path, supplied: str | None) -> str:
    detected = detect_version(source)
    if detected and supplied and detected != supplied:
        raise ValueError(f"La versión indicada ({supplied}) no coincide con el nombre del archivo ({detected}).")
    if detected:
        return detected
    if supplied:
        return supplied
    raise ValueError("No se detectó una versión YYYYMMDD en el nombre del archivo; indica --version explícitamente.")


def write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa catálogos CFDI 4.0 desde el Excel oficial SAT en modo seguro.")
    parser.add_argument("--source", type=Path, default=BACKEND_DIR / "resources/sat/catalogo sat.xlsx")
    parser.add_argument("--catalog", choices=[*CATALOG_SHEETS, "all"], default="all")
    parser.add_argument("--version")
    parser.add_argument("--publication-date", type=date.fromisoformat)
    parser.add_argument("--user-id", type=int)
    parser.add_argument("--report", type=Path, default=BACKEND_DIR / "resources/sat/reports/sat_official_xls_comparison.json")
    parser.add_argument("--activate", action="store_true", help="Activa las versiones staged al finalizar la transacción.")
    args = parser.parse_args()

    source = args.source.expanduser()
    version = resolve_version(source, args.version)
    started = time.perf_counter()
    inspection = inspect_source(source)
    payload = {
        "source": source_metadata(source, version=version, publication_date=args.publication_date),
        "inspection": inspection,
        "activation": "not_requested",
    }
    write_report(args.report, payload)
    targets = list(CATALOG_SHEETS) if args.catalog == "all" else [args.catalog]
    db = SessionLocal()
    try:
        reports = []
        with db.begin():
            for catalog_code in targets:
                rows, sheets = extract_catalog_rows(source, catalog_code)
                report = import_catalog_records(
                    db,
                    catalog_code=catalog_code,
                    rows=rows,
                    source_filename=source.name,
                    checksum=catalog_checksum(source, catalog_code),
                    version=version,
                    publication_date=args.publication_date,
                    imported_by_id=args.user_id,
                    status="staged",
                    report_metadata={**payload["source"], "sheets": sheets},
                    commit=False,
                )
                reports.append(report.as_dict())
            if args.activate:
                for report in reports:
                    if report["status"] == "imported":
                        activate_catalog_version(db, catalog_code=report["catalog"], version=version)
                payload["activation"] = "activated"
            else:
                payload["activation"] = "staged"
        payload["reports"] = reports
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        write_report(args.report, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as error:
        db.rollback()
        payload["error"] = str(error)
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        write_report(args.report, payload)
        print(f"Error de importación oficial SAT: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
