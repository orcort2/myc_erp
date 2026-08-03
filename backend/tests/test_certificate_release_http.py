from datetime import datetime, timezone
import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app
from app.models.certificate import Certificate
from app.routers.certificates import release_certificate_to_client
from app.security.api_access import enforce_api_access


def test_release_endpoint_accepts_authenticated_certificate_with_pending_match():
    now = datetime(2026, 7, 21, tzinfo=timezone.utc)
    certificate = Certificate(
        id=91,
        folio="MYCA-07-2026-0091",
        expected_folio="MYCA-07-2026-0091",
        service_order_id=1,
        equipment_id=1,
        field_sheet_id=1,
        certificate_type="acreditado",
        status="authenticated",
        external_source="excel",
        match_status="pending",
        authenticated_pdf_path="certificates/MYCA-07-2026-0091-authenticated.pdf",
        is_active=True,
        client_visible=False,
        created_at=now,
        updated_at=now,
    )
    certificate.pdf_versions = []
    db = MagicMock()
    permission_dependency = inspect.signature(release_certificate_to_client).parameters[
        "current_user"
    ].default.dependency
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[enforce_api_access] = lambda: None
    app.dependency_overrides[permission_dependency] = lambda: SimpleNamespace(id=7)

    try:
        with (
            patch("app.routers.certificates.get_certificate", return_value=certificate),
            patch("app.services.certificates.get_certificate", side_effect=[certificate, certificate]),
            patch("app.services.certificates._authenticated_document_exists", return_value=True),
            patch("app.services.certificates._ensure_payment_allows_release"),
            patch("app.services.certificates.write_audit_log") as audit,
            TestClient(app) as client,
        ):
            response = client.post("/api/certificates/91/release-to-client")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "released_to_client"
    assert response.json()["match_status"] == "pending"
    assert response.json()["client_visible"] is True
    assert response.json()["released_to_client_by_id"] == 7
    assert response.json()["released_to_client_at"] is not None
    assert audit.call_args.kwargs["action"] == "certificate.released_to_client"
    assert audit.call_args.kwargs["user_id"] == 7
