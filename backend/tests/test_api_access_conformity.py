import csv
from pathlib import Path

import pytest
from fastapi import FastAPI

from app.main import app
from app.security.api_access import (
    AccessType,
    assert_all_routes_classified,
    build_endpoint_inventory,
    classify_operation,
)


INVENTORY_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs/architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv"
)


def test_every_http_operation_has_an_explicit_access_classification():
    operations = assert_all_routes_classified(app)
    assert len(operations) == 356
    assert all(classify_operation(item.method, item.path, item.tags) for item in operations)


def test_new_unclassified_operation_fails_conformity():
    unsafe_app = FastAPI()

    @unsafe_app.get("/not-classified")
    def not_classified():
        return {"unsafe": True}

    with pytest.raises(RuntimeError, match="sin clasificación"):
        assert_all_routes_classified(unsafe_app)


def test_public_allowlist_is_small_and_intentional():
    rows = build_endpoint_inventory(app)
    public_rows = [row for row in rows if row["access_type"] == AccessType.PUBLIC.value]
    assert {(row["method"], row["path"]) for row in public_rows} == {
        ("GET", "/"),
        ("GET", "/api/health"),
        ("GET", "/api/auth/registration-status"),
        ("POST", "/api/auth/register"),
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/refresh"),
        ("POST", "/api/portal/auth/login"),
        ("POST", "/api/portal/auth/refresh"),
        ("POST", "/api/portal/registration"),
        ("POST", "/api/portal/registration/verify-email"),
        ("POST", "/api/portal/registration/resend-verification"),
    }


def test_committed_inventory_matches_runtime():
    with INVENTORY_PATH.open(newline="", encoding="utf-8") as handle:
        committed = list(csv.DictReader(handle))
    assert committed == build_endpoint_inventory(app)
