from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.client import Client
from app.models.client_portal_permission import ClientPortalPermission
from app.models.client_portal_role import ClientPortalRole
from app.models.client_portal_role_permission import ClientPortalRolePermission
from app.models.portal_registration import PortalRegistration
from app.models.user import Role, User
from app.services.portal.mail_service import development_outbox
from app.services.portal.permission_service import ensure_portal_catalog


@pytest.fixture()
def portal_api():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        admin_role = Role(name="Administrador", description="Administración")
        db.add(admin_role); db.flush()
        admin = User(username="admin", email="admin@myc.test", full_name="Admin MYC", hashed_password=hash_password("AdminPass123"), account_type="internal", status="active", email_verified_at=datetime.now(timezone.utc), roles=[admin_role], role_id=admin_role.id)
        client = Client(client_type="persona_moral", legal_name="Cliente Portal SA", commercial_name="Cliente Portal")
        db.add_all([admin, client]); db.commit()
        ensure_portal_catalog(db)
        development_outbox.clear()
        app.dependency_overrides[get_db] = lambda: db
        api = TestClient(app)
        yield api, db, admin, client
        api.close(); app.dependency_overrides.clear(); development_outbox.clear()
    engine.dispose()


def _admin_headers(admin: User) -> dict[str, str]:
    token = create_access_token(str(admin.id), extra_claims={"auth_context": "internal", "roles": ["Administrador"]})
    return {"Authorization": f"Bearer {token}"}


def test_registration_review_membership_login_and_scope(portal_api):
    api, db, admin, client = portal_api
    password = "ClientePass123"
    created = api.post("/api/portal/registration", json={"username": "cliente.portal", "email": "cliente@example.com", "full_name": "Persona Cliente", "password": password, "password_confirmation": password, "declared_company_name": "Cliente Portal SA", "declared_company_rfc": "ABC010101ABC", "contact_phone": None, "job_title": "Calidad"})
    assert created.status_code == 201, created.text
    assert created.json()["portal_access_enabled"] is False
    registration = db.scalar(select(PortalRegistration))
    assert registration.verification_token_hash
    assert development_outbox[-1].kind == "verification"
    assert development_outbox[-1].token != registration.verification_token_hash

    verified = api.post("/api/portal/registration/verify-email", json={"token": development_outbox[-1].token})
    assert verified.status_code == 200
    assert verified.json()["portal_access_enabled"] is False

    headers = _admin_headers(admin)
    request = api.post("/api/client-portal/link-requests", headers=headers, json={"registration_id": registration.id, "client_id": client.id, "reason": "Identidad comercial comprobada"})
    assert request.status_code == 201
    approved = api.post(f"/api/client-portal/link-requests/{request.json()['id']}/approve", headers=headers, json={"reason": "Vínculo aprobado por MYC", "role_codes": ["viewer"]})
    assert approved.status_code == 200
    assert approved.json()["resulting_membership_id"]

    login = api.post("/api/portal/auth/login", json={"identifier": "cliente.portal", "password": password})
    assert login.status_code == 200
    assert "portal.read" in login.json()["permissions"]
    assert "portal.view" not in login.json()["permissions"]
    portal_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    profile = api.get("/api/client-portal/profile", headers=portal_headers)
    assert profile.status_code == 200
    assert profile.json()["client_id"] == client.id

    assert api.post("/api/auth/login", json={"email": "cliente@example.com", "password": password}).status_code == 401


def test_registration_status_is_not_public(portal_api):
    api, *_ = portal_api
    assert api.get("/api/portal/registration/1/status").status_code == 401


def test_portal_catalog_migrates_legacy_view_assignments(portal_api):
    _, db, *_ = portal_api
    viewer = db.scalar(select(ClientPortalRole).where(ClientPortalRole.code == "viewer"))
    canonical = db.scalar(
        select(ClientPortalPermission).where(ClientPortalPermission.code == "portal.read")
    )
    legacy = ClientPortalPermission(
        code="portal.view",
        name="Portal View",
        description="Legacy",
        module="portal",
    )
    db.add(legacy)
    db.flush()
    db.add(ClientPortalRolePermission(role_id=viewer.id, permission_id=legacy.id))
    db.commit()

    ensure_portal_catalog(db)
    db.refresh(legacy)

    assert legacy.is_active is False
    assert not db.scalars(
        select(ClientPortalRolePermission).where(
            ClientPortalRolePermission.permission_id == legacy.id
        )
    ).all()
    assert db.scalar(
        select(ClientPortalRolePermission).where(
            ClientPortalRolePermission.role_id == viewer.id,
            ClientPortalRolePermission.permission_id == canonical.id,
        )
    ) is not None
