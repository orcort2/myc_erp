import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.activity import ActivityMessage
from app.models.audit_log import AuditLog
from app.models.certificate import Certificate
from app.models.client import Client
from app.models.equipment import Equipment
from app.models.service_order import ServiceOrder
from app.models.user import User
from app.routers import certificates as certificate_router
from app.routers import service_orders as service_order_router
from app.services import certificate_authentication
from app.services.audit_logs import write_audit_log


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()


def approved_certificate(**overrides):
    values = {
        "id": 41,
        "service_order_id": 7,
        "status": "quality_approved",
        "expected_folio": "MYCA-26-000041",
        "folio": "MYCA-26-000041",
        "authentication_code": None,
        "authenticated_pdf_path": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def permission_code(route) -> str:
    dependency = inspect.signature(route).parameters["current_user"].default.dependency
    return dependency.__closure__[0].cell_contents


def authenticate_in_memory(db, certificate, *, user_id=12):
    certificate.status = "authenticated"
    certificate.authentication_code = "MYC-AUTH-2026-000041"
    certificate.authenticated_pdf_path = "certificates/authenticated.pdf"
    certificate.authenticated_by_id = user_id
    return certificate


def test_quality_endpoint_is_a_thin_adapter_to_canonical_authority():
    db = MagicMock()
    actor = SimpleNamespace(id=12)
    certificate = approved_certificate(status="authenticated")
    with patch.object(
        certificate_router,
        "authenticate_certificate_service",
        return_value=certificate,
    ) as authenticate:
        result = certificate_router.authenticate_certificate(certificate.id, db, actor)

    assert result is certificate
    authenticate.assert_called_once_with(
        db,
        certificate.id,
        user_id=actor.id,
        origin="quality",
    )
    db.commit.assert_not_called()


def test_ets_exposes_no_authentication_mutation_adapter():
    paths = {route.path for route in service_order_router.router.routes}
    assert (
        "/service-orders/{service_order_id}/certificates/authenticate-approved"
        not in paths
    )


def test_authentication_uses_existing_quality_approval_permission():
    assert permission_code(certificate_router.authenticate_certificate) == (
        "certificates.approve"
    )


def test_canonical_authentication_locks_row_and_emits_one_event():
    db = MagicMock()
    certificate = approved_certificate()
    db.scalar.return_value = certificate
    with (
        patch.object(
            certificate_authentication,
            "_authenticate_certificate_pdf",
            side_effect=lambda _db, item, *, user_id, origin: authenticate_in_memory(
                _db,
                item,
                user_id=user_id,
            ),
        ) as generate,
        patch.object(certificate_authentication, "publish_event") as event,
    ):
        result = certificate_authentication.authenticate_certificate(
            db,
            certificate.id,
            user_id=12,
            origin="quality",
        )

    statement = db.scalar.call_args.args[0]
    assert statement._for_update_arg is not None
    assert result.status == "authenticated"
    assert result.authenticated_by_id == 12
    generate.assert_called_once_with(
        db,
        certificate,
        user_id=12,
        origin="quality",
    )
    event.assert_called_once()
    assert event.call_args.kwargs["event_code"] == "certificate.authenticated"
    assert event.call_args.kwargs["actor_id"] == 12
    assert event.call_args.kwargs["metadata"] == {
        "previous_status": "quality_approved",
        "status": "authenticated",
        "origin": "quality",
        "authentication_code": "MYC-AUTH-2026-000041",
        "service_order_id": 7,
    }
    db.commit.assert_called_once_with()


def test_double_authentication_has_no_duplicate_mutation_audit_or_event():
    db = MagicMock()
    certificate = approved_certificate()
    db.scalar.return_value = certificate
    with (
        patch.object(
            certificate_authentication,
            "_authenticate_certificate_pdf",
            side_effect=lambda _db, item, *, user_id, origin: authenticate_in_memory(
                _db,
                item,
                user_id=user_id,
            ),
        ) as generate,
        patch.object(certificate_authentication, "publish_event") as event,
    ):
        certificate_authentication.authenticate_certificate(
            db,
            certificate.id,
            user_id=12,
            origin="quality",
        )
        with pytest.raises(HTTPException) as exc_info:
            certificate_authentication.authenticate_certificate(
                db,
                certificate.id,
                user_id=13,
                origin="quality",
            )

    assert exc_info.value.status_code == 409
    generate.assert_called_once()
    event.assert_called_once()
    db.commit.assert_called_once()


def test_authentication_rejects_null_actor_and_non_quality_origin():
    with pytest.raises(ValueError, match="requiere un actor"):
        certificate_authentication.authenticate_certificate(
            MagicMock(),
            41,
            user_id=None,
            origin="quality",
        )
    with pytest.raises(ValueError, match="debe ser Calidad"):
        certificate_authentication.authenticate_certificate(
            MagicMock(),
            41,
            user_id=12,
            origin="ets",
        )


def test_canonical_authentication_persists_actor_audit_and_event(db: Session):
    actor = User(
        username="quality-authenticator",
        email="quality-authenticator@example.test",
        full_name="Quality Authenticator",
        hashed_password="unused",
    )
    client = Client(legal_name="Cliente autenticación")
    db.add_all([actor, client])
    db.flush()
    order = ServiceOrder(
        folio="OSMYC-26-08-8801",
        work_order_number=8801,
        client_id=client.id,
        status="quality_review",
    )
    db.add(order)
    db.flush()
    equipment = Equipment(
        service_order_id=order.id,
        name="Equipo autenticación",
    )
    db.add(equipment)
    db.flush()
    certificate = Certificate(
        folio="MYCA26080001",
        expected_folio="MYCA26080001",
        service_order_id=order.id,
        equipment_id=equipment.id,
        certificate_type="acreditado",
        status="quality_approved",
        match_status="pending",
        client_visible=False,
    )
    db.add(certificate)
    db.commit()

    def authenticate(_db, item, *, user_id, origin):
        previous_status = item.status
        item.status = "authenticated"
        item.authentication_code = "MYC-AUTH-2026-008801"
        item.authentication_hash = "a" * 64
        item.authenticated_pdf_path = "certificates/MYCA26080001.pdf"
        item.authenticated_by_id = user_id
        write_audit_log(
            _db,
            action="certificate.pdf_authenticated",
            entity="certificates",
            entity_id=item.id,
            user_id=user_id,
            previous_values={"status": previous_status},
            new_values={"status": item.status, "origin": origin},
        )
        return item

    with patch.object(
        certificate_authentication,
        "_authenticate_certificate_pdf",
        side_effect=authenticate,
    ):
        updated = certificate_authentication.authenticate_certificate(
            db,
            certificate.id,
            user_id=actor.id,
            origin="quality",
        )

    audit = db.scalar(
        select(AuditLog).where(AuditLog.action == "certificate.pdf_authenticated")
    )
    event = db.scalar(
        select(ActivityMessage).where(
            ActivityMessage.event_code == "certificate.authenticated"
        )
    )
    assert updated.status == "authenticated"
    assert updated.authenticated_by_id == actor.id
    assert audit.user_id == actor.id
    assert audit.previous_values == {"status": "quality_approved"}
    assert audit.new_values == {"status": "authenticated", "origin": "quality"}
    assert event.author_id == actor.id
    assert event.metadata_json["previous_status"] == "quality_approved"
    assert event.metadata_json["status"] == "authenticated"
    assert event.metadata_json["origin"] == "quality"
