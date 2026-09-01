from __future__ import annotations

import base64
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.notification import Notification, PushDevice
from app.models.operational_ticket import OperationalTicket
from app.models.user import Role, User
from app.services import push_notifications as push_notifications_service
from app.services.push_notifications import deliver_notification_ids, expo_push_service


PNG = "data:image/png;base64," + base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
).decode()


@pytest.fixture()
def notification_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        roles = {
            name: Role(name=name, description=name)
            for name in ("Tecnico", "Administrador")
        }
        db.add_all(roles.values())
        db.flush()
        users = {}
        for key, role_name in (("tech", "Tecnico"), ("admin", "Administrador")):
            role = roles[role_name]
            user = User(
                username=f"notify-{key}",
                email=f"notify-{key}@example.test",
                full_name=f"Notify {key}",
                hashed_password="unused",
                account_type="internal",
                status="active",
                is_active=True,
                role_id=role.id,
                roles=[role],
            )
            db.add(user)
            users[key] = user
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    tokens = {
        key: create_access_token(
            str(user.id),
            extra_claims={"roles": [user.roles[0].name], "auth_context": "internal"},
        )
        for key, user in users.items()
    }
    try:
        yield client, factory, users, tokens
    finally:
        app.dependency_overrides.clear()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def token(index: int) -> str:
    return f"ExponentPushToken[notification-device-{index:02d}]"


def test_push_devices_are_idempotent_multi_device_and_owned(notification_context):
    client, factory, users, tokens = notification_context
    endpoint = "/api/mobile/v1/notifications/devices"
    payload = {"expo_push_token": token(1), "platform": "ios"}
    first = client.post(endpoint, json=payload, headers=auth(tokens["tech"]))
    repeated = client.post(endpoint, json=payload, headers=auth(tokens["tech"]))
    second = client.post(
        endpoint,
        json={"expo_push_token": token(2), "platform": "android"},
        headers=auth(tokens["tech"]),
    )
    assert first.status_code == repeated.status_code == second.status_code == 201
    assert first.json()["id"] == repeated.json()["id"]
    assert second.json()["id"] != first.json()["id"]
    assert client.delete(
        f"{endpoint}/{first.json()['id']}", headers=auth(tokens["admin"])
    ).status_code == 404

    reassigned = client.post(endpoint, json=payload, headers=auth(tokens["admin"]))
    assert reassigned.json()["id"] == first.json()["id"]
    assert client.delete(
        f"{endpoint}/{first.json()['id']}", headers=auth(tokens["tech"])
    ).status_code == 404
    assert client.delete(
        f"{endpoint}/{first.json()['id']}", headers=auth(tokens["admin"])
    ).status_code == 200
    assert client.post(
        endpoint,
        json={"expo_push_token": "invalid", "platform": "ios"},
        headers=auth(tokens["tech"]),
    ).status_code == 422
    with factory() as db:
        assert db.scalar(select(PushDevice).where(PushDevice.user_id == users["tech"].id))


def test_notification_center_enforces_ownership_and_read_state(notification_context):
    client, factory, users, tokens = notification_context
    with factory() as db:
        own = Notification(
            recipient_user_id=users["tech"].id,
            notification_type="ticket.created",
            event_key="test:own",
            title="Propia",
            delivery_status="pending",
        )
        other = Notification(
            recipient_user_id=users["admin"].id,
            notification_type="ticket.created",
            event_key="test:other",
            title="Ajena",
            delivery_status="pending",
        )
        db.add_all([own, other]); db.commit()
        own_id, other_id = own.id, other.id

    listed = client.get("/api/notifications?limit=1&offset=0", headers=auth(tokens["tech"]))
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert [item["id"] for item in listed.json()["items"]] == [own_id]
    assert client.get("/api/notifications/unread-count", headers=auth(tokens["tech"])).json() == {"count": 1}
    assert client.post(f"/api/notifications/{other_id}/read", headers=auth(tokens["tech"])).status_code == 404
    assert client.post(f"/api/notifications/{own_id}/read", headers=auth(tokens["tech"])).status_code == 200
    assert client.post("/api/notifications/read-all", headers=auth(tokens["tech"])).status_code == 200
    assert client.get("/api/notifications?unread_only=true", headers=auth(tokens["tech"])).json()["items"] == []


def test_expo_delivery_handles_success_invalid_device_and_provider_failure(
    notification_context, monkeypatch
):
    _client, factory, users, _tokens = notification_context
    with factory() as db:
        db.add_all([
            PushDevice(user_id=users["tech"].id, expo_push_token=token(1), platform="ios", is_active=True, last_seen_at=datetime.now(timezone.utc)),
            PushDevice(user_id=users["tech"].id, expo_push_token=token(2), platform="android", is_active=True, last_seen_at=datetime.now(timezone.utc)),
        ])
        notification = Notification(recipient_user_id=users["tech"].id, notification_type="ticket.approved", event_key="delivery:1", title="Aprobado", delivery_status="pending")
        db.add(notification); db.commit(); notification_id = notification.id

    monkeypatch.setattr(expo_push_service, "send", lambda _messages: [
        {"status": "ok", "id": "expo-1"},
        {"status": "error", "details": {"error": "DeviceNotRegistered"}},
    ])
    with factory() as db:
        deliver_notification_ids(db, [notification_id])
    with factory() as db:
        delivered = db.get(Notification, notification_id)
        assert delivered.delivery_status == "sent"
        assert delivered.error_code == "partial_failure"
        assert len(list(db.scalars(select(PushDevice).where(PushDevice.is_active.is_(True))))) == 1
        failed = Notification(recipient_user_id=users["tech"].id, notification_type="ticket.rejected", event_key="delivery:2", title="Rechazado", delivery_status="pending")
        db.add(failed); db.commit(); failed_id = failed.id

    def provider_failure(_messages):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(expo_push_service, "send", provider_failure)
    with factory() as db:
        deliver_notification_ids(db, [failed_id])
    with factory() as db:
        assert db.get(Notification, failed_id).delivery_status == "failed"


def _completed_work_order(client: TestClient, access_token: str, name: str) -> dict:
    headers = auth(access_token)
    created = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json={
            "reception_date": "2026-08-14", "departure_date": "2026-08-15",
            "client_name": name, "address": "Domicilio de prueba",
            "contact_name": "Cliente", "contact_phone": None, "contact_email": None,
            "postal_code": None, "city": None, "state_name": None,
            "purchase_order": None, "notes": None,
        },
        headers=headers,
    ).json()
    base = f"/api/mobile/v1/technician/lab-work-orders/{created['id']}"
    added = client.post(base + "/equipment", json={"instrument": "Equipo", "brand": "MYC", "identification": "ID", "serial_number": name, "report_number": None, "is_good_condition": True}, headers=headers)
    equipment_id = added.json()["equipment"][-1]["id"]
    # Fase 3: la recepción sólo se firma con el servicio del equipo ya
    # elegido (ver _ensure_reception_prerequisites); "traceable" reserva un
    # folio MYCT real sin requerir LinkedCompany.
    client.put(
        base + f"/equipment/{equipment_id}/service",
        json={"service_type": "traceable", "linked_company_id": None},
        headers=headers,
    )
    signed_at = datetime.now(timezone.utc).isoformat()
    signature = {"signer_name": "Persona", "signed_at": signed_at, "version": 1, "signature_data_url": PNG}
    signed = client.post(base + "/signatures", json={"technician": signature, "client": signature}, headers=headers)
    assert signed.status_code == 200, signed.text
    response = client.post(base + "/complete", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _create_ticket(client: TestClient, access_token: str, work_order_id: int) -> dict:
    response = client.post(
        "/api/mobile/v1/technician/tickets",
        json={"work_order_id": work_order_id, "reason": "Corrección requerida", "description": "Solicitud operativa para pruebas de notificaciones.", "requested_signature_policy": "preserve"},
        headers=auth(access_token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_ticket_events_persist_and_push_failure_never_rolls_back(
    notification_context, monkeypatch
):
    client, factory, users, tokens = notification_context
    client.post(
        "/api/mobile/v1/notifications/devices",
        json={"expo_push_token": token(9), "platform": "ios"},
        headers=auth(tokens["admin"]),
    )
    monkeypatch.setattr(
        expo_push_service,
        "send",
        lambda _messages: (_ for _ in ()).throw(httpx.ConnectError("offline")),
    )
    preserve_order = _completed_work_order(client, tokens["tech"], "Evento preserve")
    preserve_ticket = _create_ticket(client, tokens["tech"], preserve_order["id"])
    approved = client.post(
        f"/api/mobile/v1/technician/tickets/{preserve_ticket['id']}/approve",
        json={"signature_policy": "preserve"}, headers=auth(tokens["admin"]),
    )
    assert approved.status_code == 200
    assert client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{preserve_order['id']}/complete",
        headers=auth(tokens["tech"]),
    ).status_code == 200

    reject_order = _completed_work_order(client, tokens["tech"], "Evento reject")
    reject_ticket = _create_ticket(client, tokens["tech"], reject_order["id"])
    assert client.post(
        f"/api/mobile/v1/technician/tickets/{reject_ticket['id']}/reject",
        json={"comment": "No procede"}, headers=auth(tokens["admin"]),
    ).status_code == 200

    invalidate_order = _completed_work_order(client, tokens["tech"], "Evento invalidate")
    invalidate_ticket = _create_ticket(client, tokens["tech"], invalidate_order["id"])
    assert client.post(
        f"/api/mobile/v1/technician/tickets/{invalidate_ticket['id']}/approve",
        json={"signature_policy": "invalidate"}, headers=auth(tokens["admin"]),
    ).status_code == 200

    with factory() as db:
        assert db.get(OperationalTicket, preserve_ticket["id"]).status == "resolved"
        types = set(db.scalars(select(Notification.notification_type)))
        assert {"ticket.created", "ticket.approved", "ticket.rejected", "ticket.resolved", "ticket.signature_required"} <= types
        created = db.scalar(select(Notification).where(Notification.notification_type == "ticket.created"))
        assert created.recipient_user_id == users["admin"].id
        assert created.delivery_status == "failed"


def test_ticket_notifications_are_published_on_the_realtime_channel(
    notification_context, monkeypatch
):
    """MOB-004: ticket-lifecycle notifications (reopen requests, approvals,
    rejections, resolutions, signature-required) must reach a foregrounded
    app instance through the realtime channel, not only through OS push.

    Before this fix, app.services.notification_events only ever queued
    these notifications for OS push delivery — nothing published a
    "notification.created" realtime event for them (unlike
    app/routers/communications.py, which already does both). This asserts
    the wiring in commit_and_dispatch_notifications actually calls
    publish_to_users with the right recipient and payload shape for a
    ticket.created notification, independent of whatever the OS push
    channel does.
    """
    client, factory, users, tokens = notification_context
    published: list[tuple[set[int], str, dict]] = []

    async def fake_publish_to_users(user_ids, event, data):
        published.append((set(user_ids), event, data))

    monkeypatch.setattr(push_notifications_service, "publish_to_users", fake_publish_to_users)
    monkeypatch.setattr(
        expo_push_service, "send", lambda messages: [{"status": "ok"}] * len(messages)
    )

    order = _completed_work_order(client, tokens["tech"], "Evento realtime")
    ticket = _create_ticket(client, tokens["tech"], order["id"])

    ticket_created_events = [item for item in published if item[1] == "notification.created"]
    assert ticket_created_events, "se esperaba al menos un evento notification.created publicado"
    recipients, event, data = ticket_created_events[0]
    assert recipients == {users["admin"].id}
    assert event == "notification.created"
    assert data["event_type"] == "ticket.created"
    assert data["entity_type"] == "ticket"
    assert data["ticket_id"] == ticket["id"]
    assert data["work_order_id"] == order["id"]

    published.clear()
    approved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket['id']}/approve",
        json={"signature_policy": "preserve"},
        headers=auth(tokens["admin"]),
    )
    assert approved.status_code == 200

    approved_events = [item for item in published if item[1] == "notification.created"]
    assert approved_events
    recipients, _event, data = approved_events[0]
    assert recipients == {users["tech"].id}
    assert data["event_type"] == "ticket.approved"
