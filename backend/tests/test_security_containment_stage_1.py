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
from app.models.client import Client
from app.models.client_portal_membership import ClientPortalMembership
from app.models.client_portal import ClientPortal
from app.models.client_portal_membership_role import ClientPortalMembershipRole
from app.models.client_portal_permission import ClientPortalPermission
from app.models.client_portal_role import ClientPortalRole
from app.models.client_portal_role_permission import ClientPortalRolePermission
from app.models.user import Role, User, user_roles


@pytest.fixture()
def security_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    tables = [Role.__table__, User.__table__, user_roles, Client.__table__, ClientPortal.__table__, ClientPortalPermission.__table__, ClientPortalRole.__table__, ClientPortalRolePermission.__table__, ClientPortalMembership.__table__, ClientPortalMembershipRole.__table__]
    for table in tables: table.create(engine)
    with Session(engine, expire_on_commit=False) as db:
        admin_role, normal_role = Role(name="Administrador"), Role(name="Técnico")
        db.add_all([admin_role, normal_role]); db.flush()
        admin = User(username="admin", email="admin@example.test", full_name="Admin", hashed_password="x", account_type="internal", status="active", role_id=admin_role.id, roles=[admin_role])
        normal = User(username="normal", email="normal@example.test", full_name="Normal", hashed_password="x", account_type="internal", status="active", role_id=normal_role.id, roles=[normal_role])
        disabled = User(username="disabled", email="disabled@example.test", full_name="Disabled", hashed_password="x", account_type="internal", status="disabled", is_active=False, role_id=admin_role.id, roles=[admin_role])
        pa = User(username="portal-a", email="portal-a@example.test", full_name="Portal A", hashed_password="x", account_type="client_portal", status="active")
        pb = User(username="portal-b", email="portal-b@example.test", full_name="Portal B", hashed_password="x", account_type="client_portal", status="active")
        ca, cb = Client(client_type="persona_moral", legal_name="Cliente A"), Client(client_type="persona_moral", legal_name="Cliente B")
        db.add_all([admin, normal, disabled, pa, pb, ca, cb]); db.flush()
        permissions = []
        for code in ["portal.view", "quotations.view", "services.view", "certificates.view", "certificates.download"]:
            permission = ClientPortalPermission(code=code, name=code, module=code.split('.')[0]); db.add(permission); permissions.append(permission)
        role = ClientPortalRole(code="portal_administrator", name="Administrador", is_system=True); db.add(role); db.flush()
        for permission in permissions: db.add(ClientPortalRolePermission(role_id=role.id, permission_id=permission.id))
        ma = ClientPortalMembership(client_id=ca.id, user_id=pa.id, status="active")
        mb = ClientPortalMembership(client_id=cb.id, user_id=pb.id, status="active")
        db.add_all([ma, mb]); db.flush(); db.add_all([ClientPortalMembershipRole(membership_id=ma.id, role_id=role.id), ClientPortalMembershipRole(membership_id=mb.id, role_id=role.id)]); db.commit()
        yield SimpleNamespace(db=db, admin=admin, normal=normal, disabled=disabled, pa=pa, pb=pb, ca=ca, cb=cb, ma=ma, mb=mb)
    engine.dispose()


@pytest.fixture()
def api_client(security_session):
    app.dependency_overrides[get_db] = lambda: security_session.db
    try:
        with TestClient(app) as client: yield client
    finally: app.dependency_overrides.clear()


def internal(user, refresh=False):
    maker = create_refresh_token if refresh else create_access_token
    return {"Authorization": f"Bearer {maker(str(user.id), extra_claims={'auth_context': 'internal'})}"}


def portal(user, membership):
    token = create_access_token(str(user.id), extra_claims={"auth_context": "client_portal", "membership_id": membership.id, "client_id": membership.client_id})
    return {"Authorization": f"Bearer {token}"}


def test_internal_boundary(api_client, security_session):
    assert api_client.get('/api/health').status_code == 200
    assert api_client.get('/api/clients').status_code == 401
    assert api_client.get('/api/clients', headers=internal(security_session.normal)).status_code == 403
    with patch('app.routers.clients.list_clients', return_value=[]): assert api_client.get('/api/clients', headers=internal(security_session.admin)).status_code == 200
    assert api_client.get('/api/clients', headers=internal(security_session.admin, refresh=True)).status_code == 401
    assert api_client.get('/api/clients', headers=internal(security_session.disabled)).status_code == 401
    assert api_client.get('/api/clients', headers=portal(security_session.pa, security_session.ma)).status_code == 401


def test_portal_certificate_ownership(api_client, security_session, tmp_path: Path):
    a, b = tmp_path/'a.pdf', tmp_path/'b.pdf'; a.write_bytes(b'%PDF-a'); b.write_bytes(b'%PDF-b')
    certificates = {101: SimpleNamespace(id=101, folio='A', authentication_code='A', client_visible=True, authenticated_pdf_path=str(a), service_order=SimpleNamespace(client_id=security_session.ca.id)), 202: SimpleNamespace(id=202, folio='B', authentication_code='B', client_visible=True, authenticated_pdf_path=str(b), service_order=SimpleNamespace(client_id=security_session.cb.id))}
    assert api_client.get('/api/client-portal/certificates/101/pdf').status_code == 401
    with patch('app.routers.client_portal.get_certificate', side_effect=lambda _db, item_id: certificates[item_id]), patch('app.routers.client_portal.require_deliverable_file', side_effect=lambda value, **_: Path(value)), patch('app.routers.client_portal.write_audit_log'):
        assert api_client.get('/api/client-portal/certificates/101/pdf', headers=portal(security_session.pa, security_session.ma)).status_code == 200
        assert api_client.get('/api/client-portal/certificates/202/pdf', headers=portal(security_session.pa, security_session.ma)).status_code == 404


def test_portal_scope_comes_from_membership(api_client, security_session):
    headers = portal(security_session.pa, security_session.ma)
    with patch('app.routers.client_portal.list_quotations', return_value=[]) as quotations, patch('app.routers.client_portal.list_service_orders', return_value=[]) as services, patch('app.routers.client_portal.list_certificates', return_value=[]) as certificates:
        assert api_client.get('/api/client-portal/quotations', headers=headers).status_code == 200
        assert api_client.get('/api/client-portal/service-orders', headers=headers).status_code == 200
        assert api_client.get('/api/client-portal/certificates', headers=headers).status_code == 200
    quotations.assert_called_once_with(security_session.db, client_id=security_session.ca.id)
    services.assert_called_once_with(security_session.db, client_id=security_session.ca.id)
    certificates.assert_called_once_with(security_session.db, client_id=security_session.ca.id, client_visible=True)
