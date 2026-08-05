from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.login_policy import as_utc
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.client_portal_membership import ClientPortalMembership
from app.models.notification import Notification
from app.models.user import Role, User
from app.services.portal.permission_service import ensure_portal_catalog


@pytest.fixture()
def admin_api():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        admin_role = Role(name="Administrador", description="Administración")
        commercial_role = Role(name="Comercial", description="Comercial")
        db.add_all([admin_role, commercial_role]); db.flush()
        admin = User(username="admin", email="admin@myc.test", full_name="Admin", hashed_password=hash_password("AdminPass123"), account_type="internal", status="active", roles=[admin_role], role_id=admin_role.id)
        client = Client(client_type="persona_moral", legal_name="Cliente Uno SA", commercial_name="Cliente Uno", rfc="CUO010101AA1")
        db.add_all([admin, client]); db.commit(); ensure_portal_catalog(db)
        token = create_access_token(str(admin.id), extra_claims={"auth_context": "internal", "roles": ["Administrador"]})
        app.dependency_overrides[get_db] = lambda: db
        api = TestClient(app)
        yield api, db, {"Authorization": f"Bearer {token}"}, admin, client
        api.close(); app.dependency_overrides.clear()
    engine.dispose()


def test_internal_username_is_independent_editable_and_roles_are_multiple(admin_api):
    api, db, headers, _admin, _client = admin_api
    created = api.post("/api/users", headers=headers, json={"username": "  usuario.operativo  ", "email": "persona@myc.example.com", "full_name": "Persona MYC", "password": "PersonaPass123", "role_names": ["Administrador", "Comercial"]})
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["username"] == "usuario.operativo"
    assert {role["name"] for role in body["roles"]} == {"Administrador", "Comercial"}
    updated = api.patch(f"/api/users/{body['id']}", headers=headers, json={"username": "persona.operativa", "email": "persona@myc.example.com", "full_name": "Persona MYC", "role_names": ["Administrador", "Comercial"], "is_active": True})
    assert updated.status_code == 200, updated.text
    assert updated.json()["username"] == "persona.operativa"
    assert len(updated.json()["roles"]) == 2
    collision = api.post("/api/users", headers=headers, json={"username": "persona.operativa", "email": "otra@myc.example.com", "full_name": "Otra", "password": "PersonaPass123", "role_names": ["Comercial"]})
    assert collision.status_code == 409


def test_internal_status_is_coherent_and_login_lockout_is_deterministic(admin_api):
    api, db, headers, _admin, _client = admin_api
    created = api.post("/api/users", headers=headers, json={"username": "login.test", "email": "login@myc.example.com", "full_name": "Login Test", "password": "CorrectPass123", "role_names": ["Comercial"]}).json()
    for _ in range(5):
        assert api.post("/api/auth/login", json={"email": "login@myc.example.com", "password": "incorrecta"}).status_code == 401
    user = db.get(User, created["id"]); db.refresh(user)
    assert user.failed_login_attempts == 5
    assert as_utc(user.locked_until) > datetime.now(timezone.utc)
    assert api.post("/api/auth/login", json={"email": "login@myc.example.com", "password": "CorrectPass123"}).status_code == 401
    user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1); db.commit()
    assert api.post("/api/auth/login", json={"email": "login@myc.example.com", "password": "CorrectPass123"}).status_code == 200
    db.refresh(user); assert user.failed_login_attempts == 0 and user.locked_until is None
    disabled = api.patch(f"/api/users/{user.id}/status", headers=headers, json={"is_active": False})
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled" and disabled.json()["is_active"] is False


def _register(api, suffix):
    password = "ClientePass123"
    response = api.post("/api/portal/registration", json={"username": f"cliente.{suffix}", "email": f"cliente.{suffix}@example.com", "full_name": f"Cliente {suffix}", "password": password, "password_confirmation": password, "declared_company_name": "Cliente Uno SA", "declared_company_rfc": "CUO010101AA1", "contact_phone": None, "job_title": "Calidad"})
    assert response.status_code == 201, response.text
    registration = response.json()["registration"]
    user = registration["user"]
    return registration, user


def test_registration_request_approval_multirole_rejection_and_audit(admin_api):
    api, db, headers, _admin, client = admin_api
    registration, _user = _register(api, "uno")
    row = db.get(User, registration["user_id"]); row.email_verified_at = datetime.now(timezone.utc); row.status = "active"; row.portal_registration.email_verified_at = row.email_verified_at; row.portal_registration.status = "pending_review"; db.commit()
    request = api.post("/api/client-portal/link-requests", headers=headers, json={"registration_id": registration["id"], "client_id": client.id, "reason": "RFC, contacto y dominio revisados"})
    assert request.status_code == 201, request.text
    assert api.post(f"/api/client-portal/link-requests/{request.json()['id']}/review", headers=headers).status_code == 200
    approved = api.post(f"/api/client-portal/link-requests/{request.json()['id']}/approve", headers=headers, json={"reason": "Identidad comprobada", "role_codes": ["quality", "viewer"]})
    assert approved.status_code == 200, approved.text
    membership = db.get(ClientPortalMembership, approved.json()["resulting_membership_id"])
    assert {link.role.code for link in membership.membership_roles} == {"quality", "viewer"}
    assert db.scalar(select(AuditLog).where(AuditLog.action == "portal.link_request.approved"))
    notification = db.scalar(
        select(Notification).where(
            Notification.recipient_user_id == registration["user_id"],
            Notification.notification_type == "portal_link_resolved",
        )
    )
    assert notification is not None
    assert notification.metadata_json["membership_id"] == membership.id

    rejected_registration, _ = _register(api, "dos")
    second = db.get(User, rejected_registration["user_id"]); second.email_verified_at = datetime.now(timezone.utc); second.status = "active"; second.portal_registration.email_verified_at = second.email_verified_at; second.portal_registration.status = "pending_review"; db.commit()
    request2 = api.post("/api/client-portal/link-requests", headers=headers, json={"registration_id": rejected_registration["id"], "client_id": client.id, "reason": "Revisión"}).json()
    rejected = api.post(f"/api/client-portal/link-requests/{request2['id']}/reject", headers=headers, json={"reason": "No corresponde al cliente", "role_codes": ["viewer"]})
    assert rejected.status_code == 200
    assert db.scalar(select(ClientPortalMembership).where(ClientPortalMembership.user_id == second.id)) is None


def test_multiple_accounts_can_share_role_and_last_admin_is_protected(admin_api):
    api, db, headers, _admin, client = admin_api
    users = []
    for suffix in ("a", "b"):
        user = User(username=f"portal.{suffix}", email=f"portal.{suffix}@example.com", full_name=f"Portal {suffix}", hashed_password=hash_password("PortalPass123"), account_type="client_portal", status="active", email_verified_at=datetime.now(timezone.utc))
        db.add(user); db.commit(); users.append(user)
        response = api.post("/api/client-portal/memberships", headers=headers, json={"client_id": client.id, "user_id": user.id, "role_codes": ["portal_administrator", "viewer"], "is_primary_contact": suffix == "a"})
        assert response.status_code == 201, response.text
    memberships = api.get(f"/api/client-portal/memberships?client_id={client.id}", headers=headers).json()
    assert len(memberships) == 2 and all("viewer" in item["role_codes"] for item in memberships)
    assert all(item["client_legal_name"] == "Cliente Uno SA" for item in memberships)
    assert all(item["approved_by_name"] == "Admin" for item in memberships)
    assert api.post(f"/api/client-portal/memberships/{memberships[0]['id']}/suspend", headers=headers, json={"reason": "Cambio de responsable"}).status_code == 200
    blocked = api.patch(f"/api/client-portal/memberships/{memberships[1]['id']}/roles", headers=headers, json={"role_codes": ["viewer"]})
    assert blocked.status_code == 409


def test_portal_configuration_validates_and_persists(admin_api):
    api, _db, headers, _admin, client = admin_api
    payload = {"display_name": "Portal Cliente Uno", "logo_path": None, "primary_color": "#0F766E", "language": "es-MX", "timezone": "America/Mexico_City", "default_home_page": "dashboard", "welcome_message": "Bienvenido", "allow_self_registration": True, "allow_invitations": False, "require_mfa": False, "session_timeout_minutes": 240, "password_expiration_days": 90, "email_notifications_enabled": True, "is_enabled": True}
    saved = api.put(f"/api/client-portal/configuration/{client.id}", headers=headers, json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["allow_invitations"] is False
    invalid = api.put(f"/api/client-portal/configuration/{client.id}", headers=headers, json={**payload, "timezone": "Invalid/Zone"})
    assert invalid.status_code == 422


def test_portal_users_navigation_scope_and_last_administrator(admin_api):
    api, db, headers, _admin, client = admin_api
    portal_admin = User(username="company.admin", email="company.admin@example.com", full_name="Company Admin", hashed_password=hash_password("PortalPass123"), account_type="client_portal", status="active", email_verified_at=datetime.now(timezone.utc))
    outsider = User(username="other.user", email="other.user@example.com", full_name="Other User", hashed_password=hash_password("PortalPass123"), account_type="client_portal", status="active", email_verified_at=datetime.now(timezone.utc))
    other_client = Client(client_type="persona_moral", legal_name="Otro Cliente SA", commercial_name="Otro Cliente")
    db.add_all([portal_admin, outsider, other_client]); db.commit()
    own = api.post("/api/client-portal/memberships", headers=headers, json={"client_id": client.id, "user_id": portal_admin.id, "role_codes": ["portal_administrator"], "is_primary_contact": True})
    foreign = api.post("/api/client-portal/memberships", headers=headers, json={"client_id": other_client.id, "user_id": outsider.id, "role_codes": ["viewer"], "is_primary_contact": True})
    assert own.status_code == foreign.status_code == 201
    login = api.post("/api/portal/auth/login", json={"identifier": "company.admin", "password": "PortalPass123"})
    assert login.status_code == 200, login.text
    portal_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    users = api.get("/api/client-portal/users", headers=portal_headers)
    assert users.status_code == 200 and {item["client_id"] for item in users.json()} == {client.id}
    assert api.post(f"/api/client-portal/users/{foreign.json()['id']}/suspend", headers=portal_headers, json={"reason": "No debe cruzar cliente"}).status_code == 404
    assert api.patch(f"/api/client-portal/users/{own.json()['id']}/roles", headers=portal_headers, json={"role_codes": ["viewer"]}).status_code == 409
