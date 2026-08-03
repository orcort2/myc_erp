from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import get_db
from app.core.security import create_access_token, create_refresh_token
from app.main import app
from app.models.client import Client, ClientContact
from app.models.user import Role, User, user_roles


@pytest.fixture()
def security_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (Role.__table__, User.__table__, user_roles, Client.__table__, ClientContact.__table__):
        table.create(engine)

    with Session(engine, expire_on_commit=False) as session:
        admin_role = Role(name="Administrador", description="Admin")
        client_role = Role(name="Cliente", description="Portal")
        session.add_all([admin_role, client_role])
        session.flush()

        admin = User(
            email="admin@example.test",
            full_name="Admin",
            hashed_password="not-used",
            role_id=admin_role.id,
        )
        client_a_user = User(
            email="portal-a@example.test",
            full_name="Portal A",
            hashed_password="not-used",
            role_id=client_role.id,
        )
        client_b_user = User(
            email="portal-b@example.test",
            full_name="Portal B",
            hashed_password="not-used",
            role_id=client_role.id,
        )
        disabled = User(
            email="disabled@example.test",
            full_name="Disabled",
            hashed_password="not-used",
            role_id=admin_role.id,
            is_active=False,
        )
        admin.roles = [admin_role]
        client_a_user.roles = [client_role]
        client_b_user.roles = [client_role]
        disabled.roles = [admin_role]
        session.add_all([admin, client_a_user, client_b_user, disabled])

        client_a = Client(
            client_type="persona_moral",
            legal_name="Cliente A",
            email=client_a_user.email,
        )
        client_b = Client(
            client_type="persona_moral",
            legal_name="Cliente B",
            email=client_b_user.email,
        )
        session.add_all([client_a, client_b])
        session.commit()

        yield SimpleNamespace(
            db=session,
            admin=admin,
            client_a_user=client_a_user,
            client_b_user=client_b_user,
            disabled=disabled,
            client_a=client_a,
            client_b=client_b,
        )

    engine.dispose()


@pytest.fixture()
def api_client(security_session):
    app.dependency_overrides[get_db] = lambda: security_session.db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def bearer(user: User, *, refresh: bool = False) -> dict[str, str]:
    token = create_refresh_token(str(user.id)) if refresh else create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


def test_public_health_and_internal_401_permission_403_and_admin_success(
    api_client,
    security_session,
):
    assert api_client.get("/api/health").status_code == 200
    assert api_client.get("/api/clients").status_code == 401
    assert api_client.get(
        "/api/clients",
        headers=bearer(security_session.client_a_user),
    ).status_code == 403

    with patch("app.routers.clients.list_clients", return_value=[]):
        response = api_client.get(
            "/api/clients",
            headers=bearer(security_session.admin),
        )
    assert response.status_code == 200
    assert response.json() == []


def test_refresh_cannot_cross_access_boundary_and_disabled_user_is_rejected(
    api_client,
    security_session,
):
    assert api_client.get(
        "/api/clients",
        headers=bearer(security_session.admin, refresh=True),
    ).status_code == 401
    assert api_client.get(
        "/api/clients",
        headers=bearer(security_session.disabled),
    ).status_code == 401


def test_administrative_endpoint_rejects_normal_authenticated_user(
    api_client,
    security_session,
):
    response = api_client.get(
        "/api/users",
        headers=bearer(security_session.client_a_user),
    )

    assert response.status_code == 403


def test_portal_is_anonymous_safe_and_enforces_two_client_certificate_ownership(
    api_client,
    security_session,
    tmp_path: Path,
):
    own_a = tmp_path / "a.pdf"
    own_b = tmp_path / "b.pdf"
    own_a.write_bytes(b"%PDF-1.4 client-a")
    own_b.write_bytes(b"%PDF-1.4 client-b")

    certificates = {
        101: SimpleNamespace(
            id=101,
            folio="CERT-A",
            authentication_code="AUTH-A",
            client_visible=True,
            authenticated_pdf_path=str(own_a),
            service_order=SimpleNamespace(client_id=security_session.client_a.id),
        ),
        202: SimpleNamespace(
            id=202,
            folio="CERT-B",
            authentication_code="AUTH-B",
            client_visible=True,
            authenticated_pdf_path=str(own_b),
            service_order=SimpleNamespace(client_id=security_session.client_b.id),
        ),
    }

    assert api_client.get("/api/client-portal/certificates/101/pdf").status_code == 401

    with (
        patch("app.routers.client_portal.get_certificate", side_effect=lambda _db, item_id: certificates[item_id]),
        patch("app.routers.client_portal.resolve_storage_path", side_effect=lambda value: Path(value)),
        patch("app.routers.client_portal.write_audit_log") as audit,
    ):
        client_a_headers = bearer(security_session.client_a_user)
        client_b_headers = bearer(security_session.client_b_user)

        assert api_client.get(
            "/api/client-portal/certificates/101/pdf",
            headers=client_a_headers,
        ).status_code == 200
        assert api_client.get(
            "/api/client-portal/certificates/202/pdf",
            headers=client_a_headers,
        ).status_code == 404
        assert api_client.get(
            "/api/client-portal/certificates/202/pdf",
            headers=client_b_headers,
        ).status_code == 200
        assert api_client.get(
            "/api/client-portal/certificates/101/pdf",
            headers=client_b_headers,
        ).status_code == 404

    assert audit.call_count == 2
    assert {call.kwargs["user_id"] for call in audit.call_args_list} == {
        security_session.client_a_user.id,
        security_session.client_b_user.id,
    }


def test_portal_list_queries_receive_only_the_derived_client_scope(
    api_client,
    security_session,
):
    headers = bearer(security_session.client_a_user)
    with (
        patch("app.routers.client_portal.list_quotations", return_value=[]) as quotations,
        patch("app.routers.client_portal.list_service_orders", return_value=[]) as service_orders,
        patch("app.routers.client_portal.list_certificates", return_value=[]) as certificates,
    ):
        assert api_client.get("/api/client-portal/quotations", headers=headers).status_code == 200
        assert api_client.get("/api/client-portal/service-orders", headers=headers).status_code == 200
        assert api_client.get("/api/client-portal/certificates", headers=headers).status_code == 200

    expected_client_id = security_session.client_a.id
    quotations.assert_called_once_with(security_session.db, client_id=expected_client_id)
    service_orders.assert_called_once_with(security_session.db, client_id=expected_client_id)
    certificates.assert_called_once_with(
        security_session.db,
        client_id=expected_client_id,
        client_visible=True,
    )
