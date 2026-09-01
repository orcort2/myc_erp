from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.security import decode_token, hash_password
from app.main import app
from app.models.client import Client
from app.models.client_portal_membership import ClientPortalMembership
from app.models.client_portal_membership_role import ClientPortalMembershipRole
from app.models.client_portal_role import ClientPortalRole
from app.models.communication import CommunicationConversation
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderGroupRequest
from app.models.linked_company import LinkedCompany
from app.models.notification import PushDevice
from app.models.user import Role, User
from app.schemas.lab_work_order import LabWorkOrderCreate
from app.services.lab_work_orders import create_work_order
from app.realtime.authentication import RealtimeIdentity
from app.routers.client_portal import _ensure_portal_managed_roles
from app.routers.realtime import _can_access_conversation
from app.services.portal.membership_service import create_membership
from app.services.portal.permission_service import ensure_portal_catalog
from app.services.portal.role_service import list_roles


PASSWORD = "MobilePass123"


def _user(email: str, *, account_type: str, role: Role | None = None) -> User:
    user = User(
        username=email,
        email=email,
        full_name=email.split("@", 1)[0].replace(".", " ").title(),
        hashed_password=hash_password(PASSWORD),
        account_type=account_type,
        status="active",
        email_verified_at=datetime.now(timezone.utc),
    )
    if role is not None:
        user.roles = [role]
        user.role_id = role.id
    return user


@pytest.fixture()
def mobile_security_api():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        technician = Role(name="Tecnico", description="Técnico MYC")
        administrator = Role(name="Administrador", description="Administrador MYC")
        advisor = Role(name="Asesor", description="Sin acceso Mobile")
        db.add_all([technician, administrator, advisor])
        db.flush()
        staff = _user("staff@myc.example.com", account_type="internal", role=technician)
        admin = _user("admin@myc.example.com", account_type="internal", role=administrator)
        staff_without_mobile = _user(
            "advisor@myc.example.com", account_type="internal", role=advisor
        )
        client_a = Client(legal_name="Cliente A", commercial_name="Cliente A")
        client_b = Client(legal_name="Cliente B", commercial_name="Cliente B")
        db.add_all([staff, admin, staff_without_mobile, client_a, client_b])
        db.commit()
        ensure_portal_catalog(db)

        users: dict[str, User] = {}
        for key, role_code, client in (
            ("viewer", "external_viewer", client_a),
            ("jr", "external_operator_jr", client_a),
            ("sr", "external_operator_sr", client_a),
            ("other", "external_operator_jr", client_b),
            ("other_sr", "external_operator_sr", client_b),
            ("portal_only", "viewer", client_a),
        ):
            user = _user(f"{key}@client.example.com", account_type="client_portal")
            db.add(user)
            db.flush()
            role = db.scalar(select(ClientPortalRole).where(ClientPortalRole.code == role_code))
            membership = ClientPortalMembership(
                client_id=client.id,
                user_id=user.id,
                status="active",
            )
            db.add(membership)
            db.flush()
            db.add(
                ClientPortalMembershipRole(
                    membership_id=membership.id,
                    role_id=role.id,
                )
            )
            users[key] = user
        db.commit()

        app.dependency_overrides[get_db] = lambda: db
        api = TestClient(app)
        yield api, db, {
            "staff": staff,
            "admin": admin,
            "staff_without_mobile": staff_without_mobile,
            "client_a": client_a,
            "client_b": client_b,
            **users,
        }
        api.close()
        app.dependency_overrides.clear()
    engine.dispose()


def _login(api: TestClient, email: str):
    return api.post(
        "/api/mobile/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )


def _headers(response) -> dict[str, str]:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _work_order_payload(client_name: str) -> dict:
    today = date.today()
    return {
        "reception_date": today.isoformat(),
        "departure_date": (today + timedelta(days=1)).isoformat(),
        "client_name": client_name,
        "address": "Domicilio de prueba",
    }


def test_internal_mobile_access_is_explicit_and_keeps_internal_scope(mobile_security_api):
    api, db, data = mobile_security_api
    accepted = _login(api, data["staff"].email)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["user"]["actor_type"] == "internal"
    assert accepted.json()["user"]["client_id"] is None
    assert "mobile.access" in accepted.json()["user"]["permissions"]

    rejected = _login(api, data["staff_without_mobile"].email)
    assert rejected.status_code == 403
    assert rejected.json()["detail"] == "La cuenta no tiene acceso a MYC Mobile"


@pytest.mark.parametrize("profile", ["viewer", "jr", "sr"])
def test_external_mobile_profiles_authenticate_with_client_context(
    mobile_security_api, profile
):
    api, db, data = mobile_security_api
    response = _login(api, data[profile].email)
    assert response.status_code == 200, response.text
    body = response.json()
    membership = db.scalar(
        select(ClientPortalMembership).where(
            ClientPortalMembership.user_id == data[profile].id
        )
    )
    assert body["user"]["actor_type"] == "client"
    assert body["user"]["client_id"] == data["client_a"].id
    assert body["user"]["membership_id"] == membership.id
    assert "mobile.access" in body["user"]["permissions"]


def test_external_profiles_are_persisted_outside_internal_rbac_and_admin_scoped(
    mobile_security_api,
):
    _, db, data = mobile_security_api
    mobile_roles = {
        "external_viewer",
        "external_operator_jr",
        "external_operator_sr",
    }
    assert mobile_roles.issubset(
        {role["code"] for role in list_roles(db, data["client_a"].id)}
    )
    assert mobile_roles.isdisjoint(
        {
            role["code"]
            for role in list_roles(
                db,
                data["client_a"].id,
                include_mobile=False,
            )
        }
    )
    assert mobile_roles.isdisjoint(set(db.scalars(select(Role.name)).all()))
    with pytest.raises(HTTPException) as exc_info:
        _ensure_portal_managed_roles(
            db,
            data["client_a"].id,
            ["external_operator_sr"],
        )
    assert "sólo pueden ser asignados por staff MYC" in str(exc_info.value)


def test_portal_access_and_mobile_access_are_independent(mobile_security_api):
    api, _, data = mobile_security_api
    portal_only = _login(api, data["portal_only"].email)
    assert portal_only.status_code == 403

    mobile_only = _login(api, data["viewer"].email)
    portal_response = api.get(
        "/api/client-portal/profile",
        headers=_headers(mobile_only),
    )
    assert portal_response.status_code == 401


def test_mobile_refresh_preserves_client_actor_and_scope(mobile_security_api):
    api, _, data = mobile_security_api
    login = _login(api, data["jr"].email)
    refreshed = api.post(
        "/api/mobile/v1/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["user"]["actor_type"] == "client"
    assert refreshed.json()["user"]["client_id"] == data["client_a"].id
    assert decode_token(refreshed.json()["access_token"])["auth_context"] == "mobile_client"


def test_client_mobile_token_is_not_accepted_as_internal_token(mobile_security_api):
    api, _, data = mobile_security_api
    login = _login(api, data["jr"].email)
    response = api.get("/api/auth/me", headers=_headers(login))
    assert response.status_code == 401


def test_membership_and_client_state_are_revalidated_on_every_request(mobile_security_api):
    api, db, data = mobile_security_api
    login = _login(api, data["viewer"].email)
    membership = db.scalar(
        select(ClientPortalMembership).where(
            ClientPortalMembership.user_id == data["viewer"].id
        )
    )
    membership.status = "suspended"
    db.commit()
    assert api.get("/api/mobile/v1/auth/me", headers=_headers(login)).status_code == 403

    membership.status = "revoked"
    db.commit()
    assert api.get("/api/mobile/v1/auth/me", headers=_headers(login)).status_code == 403

    membership.status = "active"
    data["client_a"].is_active = False
    db.commit()
    assert _login(api, data["viewer"].email).status_code == 403


def test_second_active_membership_is_rejected_but_historical_one_is_allowed(
    mobile_security_api,
):
    _, db, data = mobile_security_api
    viewer_role = db.scalar(
        select(ClientPortalRole).where(ClientPortalRole.code == "external_viewer")
    )
    with pytest.raises(HTTPException) as exc_info:
        create_membership(
            db,
            client_id=data["client_b"].id,
            user_id=data["viewer"].id,
            role_codes=[viewer_role.code],
            primary=False,
            actor_id=data["staff"].id,
        )
    assert "Este usuario ya pertenece a otra organización activa" in str(exc_info.value)
    db.rollback()

    active = db.scalar(
        select(ClientPortalMembership).where(
            ClientPortalMembership.user_id == data["viewer"].id
        )
    )
    active.status = "suspended"
    db.commit()
    created = create_membership(
        db,
        client_id=data["client_b"].id,
        user_id=data["viewer"].id,
        role_codes=[viewer_role.code],
        primary=False,
        actor_id=data["staff"].id,
    )
    assert created["client_id"] == data["client_b"].id


def test_viewer_has_no_implicit_operational_permissions(mobile_security_api):
    api, _, data = mobile_security_api
    viewer = _login(api, data["viewer"].email)
    denied = api.post(
        "/api/mobile/v1/technician/lab-work-orders",
        headers=_headers(viewer),
        json=_work_order_payload("Cliente enviado por frontend"),
    )
    assert denied.status_code == 403


def test_external_operators_cannot_create_direct_lab_work_orders(mobile_security_api):
    api, _, data = mobile_security_api
    for key in ("jr", "sr"):
        token = _login(api, data[key].email)
        response = api.post(
            "/api/mobile/v1/technician/lab-work-orders",
            headers=_headers(token),
            json=_work_order_payload("Cliente final"),
        )
        assert response.status_code == 403


def test_lab_clients_are_strictly_tenant_scoped_for_external_operators(mobile_security_api):
    api, _, data = mobile_security_api
    headers_a = _headers(_login(api, data["jr"].email))
    headers_b = _headers(_login(api, data["other"].email))
    headers_staff = _headers(_login(api, data["staff"].email))
    payload_a = {"company": "Cliente tenant A", "address": "Calle A", "attention": "Contacto A"}
    payload_b = {"company": "Cliente tenant B", "address": "Calle B", "attention": "Contacto B"}
    assert api.post("/api/mobile/v1/technician/lab-clients", json=payload_a, headers=headers_a).status_code == 201
    assert api.post("/api/mobile/v1/technician/lab-clients", json=payload_b, headers=headers_b).status_code == 201

    names_a = {item["company"] for item in api.get("/api/mobile/v1/technician/lab-clients", headers=headers_a).json()}
    names_b = {item["company"] for item in api.get("/api/mobile/v1/technician/lab-clients", headers=headers_b).json()}
    names_staff = {item["company"] for item in api.get("/api/mobile/v1/technician/lab-clients", headers=headers_staff).json()}
    assert names_a == {"Cliente tenant A"}
    assert names_b == {"Cliente tenant B"}
    assert names_staff == set()


def test_external_linked_sheet_can_start_pending_and_does_not_block_closure(mobile_security_api):
    api, db, data = mobile_security_api
    sr_headers = _headers(_login(api, data["sr"].email))
    admin_headers = _headers(_login(api, data["admin"].email))
    lab_client = api.post(
        "/api/mobile/v1/technician/lab-clients",
        json={"company": "Cliente externo", "address": "Calle externa", "attention": "Responsable externo"},
        headers=sr_headers,
    ).json()
    request_payload = {
        **_work_order_payload("Snapshot enviado no autoritativo"),
        "lab_client_id": lab_client["id"],
        "quantity": 1,
    }
    group_request = api.post(
        "/api/mobile/v1/technician/lab-work-orders/group-requests",
        json=request_payload,
        headers=sr_headers,
    )
    assert group_request.status_code == 201, group_request.text
    request_id = group_request.json()["id"]
    assert api.post(
        f"/api/mobile/v1/technician/lab-work-orders/group-requests/{request_id}/claim",
        headers=admin_headers,
    ).status_code == 200
    approved = api.post(
        f"/api/mobile/v1/technician/lab-work-orders/group-requests/{request_id}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    order_id = approved.json()["root_work_order_id"]
    added = api.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json={
            "instrument": "Instrumento externo",
            "brand": "Marca",
            "identification": "EXT-1",
            "serial_number": "SER-EXT",
            "report_number": None,
            "is_good_condition": True,
        },
        headers=sr_headers,
    )
    assert added.status_code == 201, added.text
    equipment_id = added.json()["equipment"][0]["id"]
    linked = LinkedCompany(
        name="Vinculado externo",
        abbreviation="VEXT",
        default_certificate_prefix="VEXT",
        is_enabled=True,
    )
    db.add(linked)
    db.commit()
    service = api.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "linked", "linked_company_id": linked.id},
        headers=sr_headers,
    )
    assert service.status_code == 200, service.text
    assert service.json()["equipment"][0]["folio_status"] == "pending"
    assert service.json()["equipment"][0]["certificate_folio"] is None
    assert api.get(
        "/api/mobile/v1/technician/lab-work-orders/field-sheet-templates",
        headers=sr_headers,
    ).status_code == 200
    sheet = api.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "general"},
        headers=sr_headers,
    )
    assert sheet.status_code == 201, sheet.text
    assert sheet.json()["status"] == "draft"

    signed_at = datetime.now(timezone.utc).isoformat()
    signatures = {
        "technician": {"signer_name": "Operador", "signed_at": signed_at, "version": 1, "signature_data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="},
        "client": {"signer_name": "Cliente", "signed_at": signed_at, "version": 1, "signature_data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="},
    }
    signed = api.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures",
        json=signatures,
        headers=sr_headers,
    )
    assert signed.status_code == 200, signed.text
    completed = api.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete",
        headers=sr_headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"


def test_external_certificate_block_limit_and_admin_resolution(mobile_security_api):
    api, _, data = mobile_security_api
    external_headers = _headers(_login(api, data["jr"].email))
    admin_headers = _headers(_login(api, data["admin"].email))
    valid = api.post(
        "/api/mobile/v1/technician/tickets/certificate-block",
        json={
            "accredited_quantity": 70,
            "traceable_quantity": 30,
            "reason": "Bloque semanal",
            "description": "Reserva para calibraciones externas",
        },
        headers=external_headers,
    )
    assert valid.status_code == 201, valid.text
    invalid = api.post(
        "/api/mobile/v1/technician/tickets/certificate-block",
        json={
            "accredited_quantity": 100,
            "traceable_quantity": 100,
            "reason": "Demasiados folios",
            "description": "Debe rechazarse por exceder el máximo combinado",
        },
        headers=external_headers,
    )
    assert invalid.status_code == 422
    resolved = api.post(
        f"/api/mobile/v1/technician/tickets/{valid.json()['id']}/resolve",
        json={"authorized_folio": None, "comment": "Bloque autorizado"},
        headers=admin_headers,
    )
    assert resolved.status_code == 200, resolved.text
    folios = resolved.json()["resolution_snapshot"]["folios"]
    assert len(folios["MYCA"]) == 70
    assert len(folios["MYCT"]) == 30
    assert folios["MYCA"][0].endswith("-4700")
    assert folios["MYCT"][0].endswith("-1640")


def test_internal_authorized_actor_keeps_direct_lab_creation(mobile_security_api):
    api, _, data = mobile_security_api
    token = _login(api, data["staff"].email)
    response = api.post(
        "/api/mobile/v1/technician/lab-work-orders",
        headers=_headers(token),
        json=_work_order_payload("Cliente staff"),
    )
    assert response.status_code == 201, response.text


def test_only_sr_creates_group_request_and_other_tenant_cannot_list_it(mobile_security_api):
    api, _, data = mobile_security_api
    payload = {**_work_order_payload("Cliente final solicitado"), "quantity": 3}
    for key in ("viewer", "jr"):
        denied = api.post(
            "/api/mobile/v1/technician/lab-work-orders/group-requests",
            headers=_headers(_login(api, data[key].email)),
            json=payload,
        )
        assert denied.status_code == 403
    sr = _login(api, data["sr"].email)
    created = api.post(
        "/api/mobile/v1/technician/lab-work-orders/group-requests",
        headers=_headers(sr),
        json=payload,
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "pending"
    assert created.json()["folios"] == []
    assert created.json()["conversation_id"] is None
    admin = _login(api, data["admin"].email)
    claimed = api.post(
        f"/api/mobile/v1/technician/lab-work-orders/group-requests/{created.json()['id']}/claim",
        headers=_headers(admin),
    )
    assert claimed.status_code == 200, claimed.text
    conversation_id = claimed.json()["conversation_id"]
    assert conversation_id is not None
    assert api.get(
        f"/api/communications/conversations/{conversation_id}", headers=_headers(sr)
    ).status_code == 200
    assert api.get(
        f"/api/communications/conversations/{conversation_id}", headers=_headers(admin)
    ).status_code == 200
    own = api.get(
        "/api/mobile/v1/technician/lab-work-orders/group-requests",
        headers=_headers(sr),
    )
    assert [item["id"] for item in own.json()] == [created.json()["id"]]
    other = _login(api, data["other"].email)
    assert api.get(
        "/api/mobile/v1/technician/lab-work-orders/group-requests",
        headers=_headers(other),
    ).status_code == 403
    other_sr = _login(api, data["other_sr"].email)
    assert api.get(
        "/api/mobile/v1/technician/lab-work-orders/group-requests",
        headers=_headers(other_sr),
    ).json() == []
    assert api.get(
        f"/api/communications/conversations/{conversation_id}", headers=_headers(other_sr)
    ).status_code in {403, 404}


def test_internal_cannot_use_external_request_but_can_create_direct_group(mobile_security_api):
    api, db, data = mobile_security_api
    staff_login = _login(api, data["staff"].email)
    assert staff_login.status_code == 200, staff_login.text
    staff_user = staff_login.json()["user"]
    assert staff_user["actor_type"] == "internal"
    assert "lab_work_order_groups.create" in staff_user["permissions"]
    assert not {
        "lab_work_order_groups.requests.read",
        "lab_work_order_groups.requests.claim",
        "lab_work_order_groups.requests.decide",
    }.intersection(staff_user["permissions"])
    staff_headers = _headers(staff_login)
    payload = {**_work_order_payload("Cliente directo Técnico"), "quantity": 3}

    external_route = api.post(
        "/api/mobile/v1/technician/lab-work-orders/group-requests",
        headers=staff_headers,
        json=payload,
    )
    assert external_route.status_code == 403

    direct = api.post(
        "/api/mobile/v1/technician/lab-work-orders/groups",
        headers=staff_headers,
        json=payload,
    )
    assert direct.status_code == 201, direct.text
    direct_body = direct.json()
    assert [item["folio"] for item in direct_body["related_work_orders"]] == [
        6400,
        6401,
        6402,
    ]
    assert set(db.scalars(select(LabWorkOrder.root_work_order_id)).all()) == {
        direct_body["id"]
    }
    assert db.scalar(select(func.count(LabWorkOrder.id))) == 3
    assert db.scalar(select(func.count(LabWorkOrderGroupRequest.id))) == 0

    client_headers = _headers(_login(api, data["sr"].email))
    requested = api.post(
        "/api/mobile/v1/technician/lab-work-orders/group-requests",
        headers=client_headers,
        json={**_work_order_payload("Cliente externo autorizado"), "quantity": 2},
    )
    assert requested.status_code == 201, requested.text
    request_id = requested.json()["id"]
    assert requested.json()["status"] == "pending"
    assert requested.json()["folios"] == []

    client_direct = api.post(
        "/api/mobile/v1/technician/lab-work-orders/groups",
        headers=client_headers,
        json={**_work_order_payload("Directo externo prohibido"), "quantity": 2},
    )
    assert client_direct.status_code == 403

    assert api.get(
        "/api/mobile/v1/technician/lab-work-orders/group-requests/review",
        headers=staff_headers,
    ).status_code == 403
    assert api.post(
        f"/api/mobile/v1/technician/lab-work-orders/group-requests/{request_id}/claim",
        headers=staff_headers,
    ).status_code == 403
    assert api.post(
        f"/api/mobile/v1/technician/lab-work-orders/group-requests/{request_id}/approve",
        headers=staff_headers,
    ).status_code == 403
    assert api.post(
        f"/api/mobile/v1/technician/lab-work-orders/group-requests/{request_id}/reject",
        headers=staff_headers,
        json={"reason": "No debe poder decidir"},
    ).status_code == 403
    assert db.scalar(
        select(LabWorkOrderGroupRequest.status).where(
            LabWorkOrderGroupRequest.id == request_id
        )
    ) == "pending"

    admin_headers = _headers(_login(api, data["admin"].email))
    claimed = api.post(
        f"/api/mobile/v1/technician/lab-work-orders/group-requests/{request_id}/claim",
        headers=admin_headers,
    )
    assert claimed.status_code == 200, claimed.text


def test_client_cannot_create_direct_group(mobile_security_api):
    api, _, data = mobile_security_api
    sr_headers = _headers(_login(api, data["sr"].email))
    response = api.post(
        "/api/mobile/v1/technician/lab-work-orders/groups",
        headers=sr_headers,
        json={**_work_order_payload("Cliente directo denegado"), "quantity": 2},
    )
    assert response.status_code == 403
    forged_tenant = api.post(
        "/api/mobile/v1/technician/lab-work-orders/group-requests",
        headers=sr_headers,
        json={
            **_work_order_payload("Tenant forjado"),
            "quantity": 2,
            "operator_client_id": data["client_b"].id,
        },
    )
    assert forged_tenant.status_code == 422


def test_client_scope_blocks_cross_tenant_list_read_write_and_subresources(
    mobile_security_api,
):
    api, db, data = mobile_security_api
    created = create_work_order(
        db,
        LabWorkOrderCreate(**_work_order_payload("Nombre documental")),
        data["jr"],
        operator_client_id=data["client_a"].id,
    )
    work_order_id = created.id

    jr = _login(api, data["jr"].email)
    other = _login(api, data["other"].email)
    listed = api.get(
        "/api/mobile/v1/technician/lab-work-orders", headers=_headers(other)
    )
    assert listed.status_code == 200
    assert listed.json() == []
    base = f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}"
    assert api.post(f"{base}/additional", headers=_headers(jr)).status_code == 403
    assert api.get(base, headers=_headers(other)).status_code == 404
    assert (
        api.patch(base, headers=_headers(other), json={"notes": "IDOR"}).status_code
        == 404
    )
    assert (
        api.post(
            f"{base}/equipment",
            headers=_headers(other),
            json={
                "instrument": "Balanza",
                "brand": "MYC",
                "identification": "EQ-1",
                "serial_number": "SN-1",
                "is_good_condition": True,
            },
        ).status_code
        == 404
    )
    signed_at = datetime.now(timezone.utc).isoformat()
    signature = {
        "signer_name": "Prueba de scope",
        "signed_at": signed_at,
        "version": 1,
        "signature_data_url": "data:image/png;base64," + "A" * 32,
    }
    assert (
        api.post(
            f"{base}/signatures",
            headers=_headers(other),
            json={"technician": signature, "client": signature},
        ).status_code
        == 404
    )
    assert (
        api.post(
            f"{base}/signatures/individual",
            headers=_headers(other),
            json={"technician": signature, "client": signature},
        ).status_code
        == 404
    )
    assert api.post(
        f"{base}/complete/individual", headers=_headers(other)
    ).status_code == 404
    assert api.get(f"{base}/pdf", headers=_headers(other)).status_code == 404
    assert api.get(f"{base}/revisions", headers=_headers(other)).status_code == 404
    assert (
        api.get(f"{base}/revisions/1/pdf", headers=_headers(other)).status_code
        == 404
    )


def test_same_client_users_share_organization_read_scope(mobile_security_api):
    api, db, data = mobile_security_api
    created = create_work_order(
        db,
        LabWorkOrderCreate(**_work_order_payload("Cliente compartido")),
        data["jr"],
        operator_client_id=data["client_a"].id,
    )
    viewer = _login(api, data["viewer"].email)
    listed = api.get(
        "/api/mobile/v1/technician/lab-work-orders", headers=_headers(viewer)
    )
    assert [item["id"] for item in listed.json()] == [created.id]


def test_external_actor_is_denied_from_unreviewed_product_mobile_routes(
    mobile_security_api,
):
    api, _, data = mobile_security_api
    jr = _login(api, data["jr"].email)
    headers = _headers(jr)
    assert api.get("/api/mobile/v1/technician/service-orders", headers=headers).status_code == 403
    assert api.get("/api/mobile/v1/technician/equipment/1", headers=headers).status_code == 403
    assert api.get("/api/mobile/v1/technician/field-sheets/1", headers=headers).status_code == 403


def test_external_push_device_registration_keeps_user_ownership(mobile_security_api):
    api, db, data = mobile_security_api
    viewer = _login(api, data["viewer"].email)
    other = _login(api, data["other"].email)
    endpoint = "/api/mobile/v1/notifications/devices"
    created = api.post(
        endpoint,
        headers=_headers(viewer),
        json={
            "expo_push_token": "ExponentPushToken[external-mobile-a]",
            "platform": "ios",
        },
    )
    assert created.status_code == 201, created.text
    assert api.delete(
        f"{endpoint}/{created.json()['id']}", headers=_headers(other)
    ).status_code == 404
    assert db.get(PushDevice, created.json()["id"]).user_id == data["viewer"].id


def test_realtime_client_conversation_scope_is_permission_and_tenant_bound(
    mobile_security_api,
):
    _, db, data = mobile_security_api
    own = CommunicationConversation(
        conversation_type="client",
        client_id=data["client_a"].id,
        created_by_user_id=data["viewer"].id,
        participants=[data["viewer"]],
    )
    foreign = CommunicationConversation(
        conversation_type="client",
        client_id=data["client_b"].id,
        created_by_user_id=data["viewer"].id,
        participants=[data["viewer"]],
    )
    internal = CommunicationConversation(
        conversation_type="internal",
        created_by_user_id=data["viewer"].id,
        participants=[data["viewer"]],
    )
    db.add_all([own, foreign, internal])
    db.commit()
    denied_without_permission = RealtimeIdentity(
        user_id=data["viewer"].id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        actor_type="client",
        client_id=data["client_a"].id,
        permissions=frozenset({"mobile.access"}),
    )
    assert not _can_access_conversation(
        db, conversation_id=own.id, identity=denied_without_permission
    )
    authorized = RealtimeIdentity(
        user_id=data["viewer"].id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        actor_type="client",
        client_id=data["client_a"].id,
        permissions=frozenset({"mobile.access", "communications.view"}),
    )
    assert _can_access_conversation(db, conversation_id=own.id, identity=authorized)
    assert not _can_access_conversation(
        db, conversation_id=foreign.id, identity=authorized
    )
    assert not _can_access_conversation(
        db, conversation_id=internal.id, identity=authorized
    )
