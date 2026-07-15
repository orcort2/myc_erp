"""Comparison helpers for controlled SAT source replacements."""

from __future__ import annotations

from pathlib import Path

from app.services.sat_catalogs.sat_xls_source import CATALOG_SHEETS, extract_catalog_rows
from app.services.sat_catalogs.sqlite_source import SQLITE_TABLE_BY_CATALOG, extract_catalog_rows as extract_sqlite_rows
from app.services.sat_catalogs.validators import canonical_record, validate_rows


def _canonical_by_code(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(record["code"]): record for record in (canonical_record(row) for row in validate_rows(rows))}


def compare_catalog_sources(xls_path: str | Path, sqlite_path: str | Path, catalog_code: str, *, sample_limit: int = 30) -> dict[str, object]:
    xls_rows, sheets = extract_catalog_rows(xls_path, catalog_code)
    xls_records = _canonical_by_code(xls_rows)
    result: dict[str, object] = {
        "catalog": catalog_code,
        "sheets": sheets,
        "excel_records": len(xls_records),
        "sqlite_records": None,
        "matches": 0,
        "missing_in_excel": [],
        "missing_in_sqlite": [],
        "modified": [],
        "duplicates": [],
        "result": "not_compared",
    }
    if catalog_code not in SQLITE_TABLE_BY_CATALOG:
        result["result"] = "sqlite_mapping_unavailable"
        result["missing_in_sqlite"] = sorted(xls_records)[:sample_limit]
        return result
    _, sqlite_rows = extract_sqlite_rows(sqlite_path, catalog_code)
    sqlite_records = _canonical_by_code(sqlite_rows)
    common = sorted(set(xls_records) & set(sqlite_records))
    modified = []
    for code in common:
        left = xls_records[code]
        right = sqlite_records[code]
        fields = [field for field in ("name", "valid_from", "valid_until") if left.get(field) != right.get(field)]
        if fields:
            modified.append({"code": code, "fields": fields, "excel": {field: left.get(field) for field in fields}, "sqlite": {field: right.get(field) for field in fields}})
    result.update({
        "sqlite_records": len(sqlite_records),
        "matches": len(common) - len(modified),
        "missing_in_excel": sorted(set(sqlite_records) - set(xls_records))[:sample_limit],
        "missing_in_sqlite": sorted(set(xls_records) - set(sqlite_records))[:sample_limit],
        "modified": modified[:sample_limit],
        "result": "equal" if not modified and set(xls_records) == set(sqlite_records) else "different",
    })
    return result


def compare_all_catalog_sources(xls_path: str | Path, sqlite_path: str | Path) -> dict[str, object]:
    reports = [compare_catalog_sources(xls_path, sqlite_path, catalog_code) for catalog_code in CATALOG_SHEETS]
    return {"catalogs": reports, "has_differences": any(report["result"] != "equal" for report in reports)}
