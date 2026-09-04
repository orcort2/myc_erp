"""Notificación a Captura cuando una OT LAB llega a cierre TÉCNICO.

Regla de producto: se notifica en cuanto _finish_complete_members corre --
nunca depende de que exista o no una entrega física (Delivery) -- y sólo a
usuarios internos activos con el rol activo 'Captura'. La idempotencia usa
event_key = work_order.id + revision_number + recipient.id, respaldada por
el UNIQUE real de Notification.event_key en la base de datos."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.lab_work_order import LabWorkOrder
from app.models.notification import Notification
from app.models.user import Role, User
from app.services.lab_work_orders import _notify_capture_work_order_completed


@pytest.fixture()
def capture_notify_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    user_ids: dict[str, int] = {}
    with factory() as db:
        technician_role = Role(name="Tecnico")
        admin_role = Role(name="Administrador")
        captura_role = Role(name="Captura")
        db.add_all([technician_role, admin_role, captura_role])
        db.flush()

        def _user(key: str, role: Role, *, is_active: bool = True, status: str = "active") -> User:
            user = User(
                username=f"notif-{key}",
                email=f"notif-{key}@example.test",
                full_name=f"NOTIF {key}",
                hashed_password="unused",
                account_type="internal",
                status=status,
                is_active=is_active,
                role_id=role.id,
                roles=[role],
            )
            db.add(user)
            return user

        tech = _user("tech", technician_role)
        admin = _user("admin", admin_role)
        captura_one = _user("captura-1", captura_role)
        captura_two = _user("captura-2", captura_role)
        captura_inactive = _user("captura-inactive", captura_role, is_active=False, status="disabled")
        db.flush()
        for key, user in (
            ("tech", tech), ("admin", admin),
            ("captura_one", captura_one), ("captura_two", captura_two), ("captura_inactive", captura_inactive),
        ):
            user_ids[key] = user.id
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    tokens = {
        "tech": create_access_token(str(user_ids["tech"]), extra_claims={"roles": ["Tecnico"], "auth_context": "internal"}),
        "admin": create_access_token(str(user_ids["admin"]), extra_claims={"roles": ["Administrador"], "auth_context": "internal"}),
    }
    try:
        yield client, factory, tokens, user_ids
    finally:
        app.dependency_overrides.clear()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_payload(client_name: str = "Cliente Notificación") -> dict:
    return {
        "reception_date": "2026-08-13",
        "client_name": client_name,
        "address": "Av. Prueba 123",
        "contact_name": "Persona Cliente",
        "contact_phone": "3312345678",
        "contact_email": "cliente@example.com",
        "postal_code": "45601",
        "city": "Tlaquepaque",
        "state_name": "Jalisco",
        "purchase_order": "OC-123",
        "notes": "Recepción LAB",
    }


def equipment_payload(index: int, **extra) -> dict:
    return {
        "instrument": f"Instrumento {index}",
        "brand": "MYC Test",
        "identification": f"ID-{index}",
        "serial_number": f"SER-{index}",
        "report_number": None,
        "is_good_condition": True,
        **extra,
    }


def configure_default_services(client: TestClient, headers: dict[str, str], work_order_id: int) -> None:
    detail = client.get(f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}", headers=headers).json()
    for item in detail["equipment"]:
        if item["service_type"] is not None:
            continue
        response = client.put(
            f"/api/mobile/v1/technician/lab-work-orders/{work_order_id}/equipment/{item['id']}/service",
            json={"service_type": "traceable", "linked_company_id": None},
            headers=headers,
        )
        assert response.status_code == 200, response.text


def signatures_payload() -> dict:
    from datetime import datetime, timezone
    signed_at = datetime.now(timezone.utc).isoformat()
    png = "data:image/png;base64," + "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    return {
        "technician": {"signer_name": "Técnico LAB", "signed_at": signed_at, "version": 1, "signature_data_url": png},
        "client": {"signer_name": "Cliente LAB", "signed_at": signed_at, "version": 1, "signature_data_url": png},
    }


def _complete_single(client: TestClient, token: str, client_name: str) -> dict:
    headers = auth(token)
    created = client.post("/api/mobile/v1/technician/lab-work-orders", json=create_payload(client_name), headers=headers).json()
    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{created['id']}/equipment",
        json=equipment_payload(1), headers=headers,
    )
    assert response.status_code == 201, response.text
    configure_default_services(client, headers, created["id"])
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{created['id']}/signatures",
        json=signatures_payload(), headers=headers,
    )
    assert signed.status_code == 200, signed.text
    completed = client.post(f"/api/mobile/v1/technician/lab-work-orders/{created['id']}/complete", headers=headers)
    assert completed.status_code == 200, completed.text
    return completed.json()


def test_transition_to_completed_notifies_one_per_active_captura_user_and_not_others(capture_notify_context):
    client, factory, tokens, user_ids = capture_notify_context
    work_order = _complete_single(client, tokens["tech"], "Cliente Captura A")

    with factory() as db:
        notifications = list(
            db.scalars(
                select(Notification).where(
                    Notification.notification_type == "work_order.completed",
                    Notification.entity_id == work_order["id"],
                )
            )
        )
        recipients = {item.recipient_user_id for item in notifications}
        assert recipients == {user_ids["captura_one"], user_ids["captura_two"]}
        assert user_ids["captura_inactive"] not in recipients
        assert user_ids["tech"] not in recipients
        assert user_ids["admin"] not in recipients

        one = next(item for item in notifications if item.recipient_user_id == user_ids["captura_one"])
        assert one.metadata_json["work_order_id"] == work_order["id"]
        assert one.metadata_json["work_order_folio"] == work_order["folio"]
        assert one.metadata_json["client_name"] == "Cliente Captura A"


def test_retry_over_the_same_revision_does_not_duplicate(capture_notify_context):
    client, factory, tokens, user_ids = capture_notify_context
    work_order = _complete_single(client, tokens["tech"], "Cliente Captura Retry")

    with factory() as db:
        count_before = db.scalar(
            select(Notification).where(
                Notification.notification_type == "work_order.completed",
                Notification.entity_id == work_order["id"],
            )
        )
        wo = db.get(LabWorkOrder, work_order["id"])
        admin = db.get(User, user_ids["admin"])
        # Retry directo de la misma revisión -- simula un reintento de la
        # petición de cierre (misma revision_number).
        _notify_capture_work_order_completed(db, wo, admin)
        db.commit()

        notifications_after = list(
            db.scalars(
                select(Notification).where(
                    Notification.notification_type == "work_order.completed",
                    Notification.entity_id == work_order["id"],
                )
            )
        )
        assert len(notifications_after) == 2, "no debe duplicar por reintento sobre la misma revisión"


def test_reopen_and_new_close_bumps_revision_and_generates_a_new_notification(capture_notify_context):
    client, factory, tokens, user_ids = capture_notify_context
    work_order = _complete_single(client, tokens["tech"], "Cliente Captura Reapertura")
    admin_headers = auth(tokens["admin"])

    reopen = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}/reopen",
        json={"requested_signature_policy": "preserve", "reason": "Corregir dato"},
        headers=admin_headers,
    )
    assert reopen.status_code == 200, reopen.text
    assert reopen.json()["revision_number"] == work_order["revision_number"] + 1

    with factory() as db:
        first_revision_notifications = list(
            db.scalars(
                select(Notification).where(
                    Notification.notification_type == "work_order.completed",
                    Notification.entity_id == work_order["id"],
                )
            )
        )
        assert len(first_revision_notifications) == 2

        reopened = db.get(LabWorkOrder, work_order["id"])
        admin = db.get(User, user_ids["admin"])
        # Segundo cierre técnico de la misma OT ya reabierta (revision_number
        # incrementado) -- se ejerce directamente sobre la función real de
        # notificación, sin repetir aquí toda la orquestación de captura/
        # firmas que _finish_complete_members exige para completar de nuevo.
        _notify_capture_work_order_completed(db, reopened, admin)
        db.commit()

        second_revision_notifications = list(
            db.scalars(
                select(Notification).where(
                    Notification.notification_type == "work_order.completed",
                    Notification.entity_id == work_order["id"],
                    Notification.event_key.like(f"%revision:{reopened.revision_number}:%"),
                )
            )
        )
        assert len(second_revision_notifications) == 2
        assert set(item.event_key for item in second_revision_notifications).isdisjoint(
            set(item.event_key for item in first_revision_notifications)
        )

        # Retry del segundo cierre -- tampoco duplica.
        _notify_capture_work_order_completed(db, reopened, admin)
        db.commit()
        all_notifications = list(
            db.scalars(
                select(Notification).where(
                    Notification.notification_type == "work_order.completed",
                    Notification.entity_id == work_order["id"],
                )
            )
        )
        assert len(all_notifications) == 4, "2 de la primera revisión + 2 de la segunda, sin duplicar el retry"


def test_completion_notification_does_not_depend_on_delivery(capture_notify_context):
    """La OT se completa y notifica sin que exista ninguna entrega física --
    nunca se llama ni se espera a /delivery en este flujo."""
    client, factory, tokens, user_ids = capture_notify_context
    work_order = _complete_single(client, tokens["tech"], "Cliente Sin Delivery")

    with factory() as db:
        from app.models.lab_work_order_delivery import LabWorkOrderDelivery
        assert db.scalar(select(LabWorkOrderDelivery.id)) is None, "fixture no debe crear ninguna entrega"

        notifications = list(
            db.scalars(
                select(Notification).where(
                    Notification.notification_type == "work_order.completed",
                    Notification.entity_id == work_order["id"],
                )
            )
        )
        assert len(notifications) == 2


def test_notification_event_key_unique_constraint_backs_concurrent_idempotency(capture_notify_context):
    """Verifica que la garantía de idempotencia no depende sólo del chequeo
    de aplicación (select-then-insert, vulnerable a carrera) -- el UNIQUE
    real de event_key en la base de datos es quien realmente la respalda."""
    _client, factory, _tokens, user_ids = capture_notify_context
    with factory() as db:
        db.add(Notification(
            recipient_user_id=user_ids["captura_one"],
            notification_type="work_order.completed",
            event_key="dup-key-test",
            title="Uno",
        ))
        db.commit()

        db.add(Notification(
            recipient_user_id=user_ids["captura_two"],
            notification_type="work_order.completed",
            event_key="dup-key-test",
            title="Dos",
        ))
        with pytest.raises(IntegrityError):
            db.commit()
