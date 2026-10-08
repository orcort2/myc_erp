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
    # BIOMETRIC-2 adds biometric enroll/exchange/delete under /mobile/v1/auth.
    # DEV-0 adds GET/POST/DELETE /mobile/v1/developer/session.
    # DEV-1A adds GET /mobile/v1/developer/broker/health.
    # ETS/LAB Phase 1 adds six ERP link/history/candidate operations.
    # EMAIL-1 adds seven /email operations (templates, deliveries, transport status).
    # EMAIL-2 adds public forgot-password / reset-password.
    # EMAIL-3 adds five ClientContact operations and three contextual quotation email operations.
    # SG-2 adds GET/POST .../equipment/{equipment_id}/technical-report (mobile lab).
    # SG-4 adds PATCH technical-report, POST/GET/DELETE technical-report evidence.
    # SG-4E adds POST .../technical-report/confirm-capture.
    # SG-4G adds POST ./technical-report/finalize and GET ./technical-report/pdf.
    # SG-4I adds POST ./technical-report/delete-draft and POST ./technical-report/change-type.
    assert len(operations) == 579
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
        ("POST", "/api/auth/forgot-password"),
        ("POST", "/api/auth/reset-password"),
        ("POST", "/api/mobile/v1/auth/login"),
        ("POST", "/api/mobile/v1/auth/refresh"),
        ("POST", "/api/mobile/v1/auth/biometric/exchange"),
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
