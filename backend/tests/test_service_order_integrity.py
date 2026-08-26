import ast
import inspect
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.activity import ActivityMessage
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.service_order import ServiceOrder
from app.models.user import Role, User
from app.schemas.service_order import (
    ServiceOrderCreate,
    ServiceOrderExceptionCreate,
    ServiceOrderUpdate,
)
from app.services.service_orders import (
    authorize_service_order_exception,
    change_status,
    create_service_order,
    deactivate_service_order,
    execute_service_order_exception,
    request_service_order_exception,
    update_service_order,
)
from app.services import (
    capture_packages,
    certificate_authentication,
    certificates,
    service_orders,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()


@pytest.fixture()
def ets_context(db: Session):
    administrator = Role(name="Administrador")
    db.add(administrator)
    db.flush()
    user = User(
        username="ets-actor",
        email="ets-actor@example.test",
        full_name="Actor ETS",
        hashed_password="unused",
        role_id=administrator.id,
        roles=[administrator],
    )
    client = Client(legal_name="Cliente ETS")
    db.add_all([user, client])
    db.flush()
    order = ServiceOrder(
        folio="OSMYC-26-08-9999",
        work_order_number=9999,
        client_id=client.id,
        status="capture",
        total_equipment=1,
        completed_equipment=0,
        requires_payment=True,
    )
    db.add(order)
    db.commit()
    return user, order


def test_status_change_characterizes_audit_event_and_actor(db: Session, ets_context):
    user, order = ets_context

    updated = change_status(db, order.id, "quality_review", user_id=user.id)

    assert updated.status == "quality_review"
    audit = db.scalar(
        select(AuditLog).where(AuditLog.action == "service_order.quality_review")
    )
    assert audit.user_id == user.id
    assert audit.previous_values == {"status": "capture"}
    assert audit.new_values == {"status": "quality_review"}
    event = db.scalar(
        select(ActivityMessage).where(
            ActivityMessage.event_code == "service_order.status_changed"
        )
    )
    assert event.author_id == user.id
    assert event.metadata_json == {
        "previous_status": "capture",
        "status": "quality_review",
    }


def test_create_update_and_deactivate_characterize_actor_audit(db: Session):
    user = User(
        username="mutation-actor",
        email="mutation-actor@example.test",
        full_name="Mutation Actor",
        hashed_password="unused",
    )
    client = Client(legal_name="Cliente mutaciones")
    db.add_all([user, client])
    db.commit()

    order = create_service_order(
        db,
        ServiceOrderCreate(client_id=client.id, notes="Inicial"),
        user_id=user.id,
    )
    update_service_order(
        db,
        order.id,
        ServiceOrderUpdate(notes="Actualizada"),
        user_id=user.id,
    )
    with pytest.raises(HTTPException) as raised:
        deactivate_service_order(db, order.id, user_id=user.id)
    assert raised.value.detail["code"] == "administrative_resolution_required"
    audits = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.entity_id == order.id)
            .where(
                AuditLog.action.in_(
                    {
                        "service_order.created",
                        "service_order.updated",
                    }
                )
            )
            .order_by(AuditLog.id)
        )
    )
    assert [item.action for item in audits] == [
        "service_order.created",
        "service_order.updated",
    ]
    assert all(item.user_id == user.id for item in audits)
    assert audits[1].previous_values == {"notes": "Inicial"}
    assert audits[1].new_values == {"notes": "Actualizada"}


def test_requested_and_authorized_do_not_mutate_ets_or_invoice(
    db: Session, ets_context, monkeypatch
):
    user, order = ets_context
    resync = Mock()
    monkeypatch.setattr(
        "app.services.invoices.resync_invoices_for_service_exception", resync
    )
    invoice = Invoice(
        internal_uuid="ets-integrity-invoice",
        folio="F-ETS-INTEGRITY",
        client_id=order.client_id,
        service_order_id=order.id,
        status="pending",
        review_required=False,
        source_snapshot={"stable": True},
    )
    db.add(invoice)
    db.commit()

    request = request_service_order_exception(
        db,
        order.id,
        ServiceOrderExceptionCreate(
            source_stage="Captura",
            target_stage="Calidad",
            reason="Corrección controlada",
        ),
        user_id=user.id,
    )

    assert request.status == "requested"
    assert db.get(ServiceOrder, order.id).status == "capture"
    persisted_invoice = db.get(Invoice, invoice.id)
    assert persisted_invoice.status == "pending"
    assert persisted_invoice.review_required is False
    assert persisted_invoice.source_snapshot == {"stable": True}
    resync.assert_not_called()

    authorized = authorize_service_order_exception(
        db,
        order.id,
        request.id,
        user_id=user.id,
        comment="Autorizada para ejecución posterior",
    )
    assert authorized.status == "authorized"
    assert db.get(ServiceOrder, order.id).status == "capture"
    persisted_invoice = db.get(Invoice, invoice.id)
    assert persisted_invoice.status == "pending"
    assert persisted_invoice.review_required is False
    assert persisted_invoice.source_snapshot == {"stable": True}
    resync.assert_not_called()

    audit_rows = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.entity == "service_order_exceptions")
            .order_by(AuditLog.id)
        )
    )
    assert [row.action for row in audit_rows] == [
        "service_order.exception_requested",
        "service_order.exception_authorized",
    ]
    assert all(row.user_id == user.id for row in audit_rows)
    assert [row.new_values["status"] for row in audit_rows] == [
        "requested",
        "authorized",
    ]


def test_administrator_can_request_authorize_and_execute_same_exception(
    db: Session, ets_context, monkeypatch
):
    user, order = ets_context
    resync = Mock(return_value=[])
    monkeypatch.setattr(
        "app.services.invoices.resync_invoices_for_service_exception", resync
    )
    request = request_service_order_exception(
        db,
        order.id,
        ServiceOrderExceptionCreate(
            source_stage="Captura",
            target_stage="Calidad",
            reason="Requiere salto autorizado",
        ),
        user_id=user.id,
    )
    with pytest.raises(HTTPException) as exc_info:
        execute_service_order_exception(
            db, order.id, request.id, user_id=user.id
        )
    assert exc_info.value.status_code == 409
    assert db.get(ServiceOrder, order.id).status == "capture"
    resync.assert_not_called()

    authorized = authorize_service_order_exception(
        db,
        order.id,
        request.id,
        user_id=user.id,
        comment="Autorización administrativa trazable",
    )
    assert authorized.status == "authorized"
    executed = execute_service_order_exception(
        db, order.id, request.id, user_id=user.id
    )

    assert executed.status == "executed"
    assert executed.requested_by_id == user.id
    assert executed.authorized_by_id == user.id
    assert executed.executed_by_id == user.id
    assert executed.created_at is not None
    assert executed.authorized_at is not None
    assert executed.executed_at is not None
    assert executed.reason == "Requiere salto autorizado"
    assert executed.authorization_comment == "Autorización administrativa trazable"
    assert executed.service_order_status_at_request == "capture"
    assert db.get(ServiceOrder, order.id).status == "quality_review"
    resync.assert_called_once_with(
        db,
        order.id,
        comment="Requiere salto autorizado",
        user_id=user.id,
    )
    audits = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.entity == "service_order_exceptions")
            .order_by(AuditLog.id)
        )
    )
    assert [audit.action for audit in audits] == [
        "service_order.exception_requested",
        "service_order.exception_authorized",
        "service_order.exception_executed",
    ]
    assert all(audit.user_id == user.id for audit in audits)
    assert audits[-1].previous_values["service_order_status"] == "capture"
    assert audits[-1].new_values["service_order_status"] == "quality_review"
    events = list(
        db.scalars(
            select(ActivityMessage)
            .where(ActivityMessage.event_code.like("service_order.exception_%"))
            .order_by(ActivityMessage.id)
        )
    )
    assert [event.event_code for event in events] == [
        "service_order.exception_requested",
        "service_order.exception_authorized",
        "service_order.exception_executed",
    ]
    assert all(event.author_id == user.id for event in events)
    assert events[-1].metadata_json["previous_status"] == "capture"
    assert events[-1].metadata_json["service_order_status"] == "quality_review"


def test_execution_revalidates_service_order_status(
    db: Session, ets_context, monkeypatch
):
    user, order = ets_context
    resync = Mock()
    monkeypatch.setattr(
        "app.services.invoices.resync_invoices_for_service_exception", resync
    )
    request = request_service_order_exception(
        db,
        order.id,
        ServiceOrderExceptionCreate(
            source_stage="Captura",
            target_stage="Calidad",
            reason="Solicitud con snapshot",
        ),
        user_id=user.id,
    )
    authorize_service_order_exception(db, order.id, request.id, user_id=user.id)
    order.status = "pending_payment"
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        execute_service_order_exception(db, order.id, request.id, user_id=user.id)

    assert exc_info.value.status_code == 409
    assert db.get(ServiceOrder, order.id).status == "pending_payment"
    resync.assert_not_called()


def test_router_contains_no_service_order_business_implementation():
    router_path = Path(__file__).parents[1] / "app" / "routers" / "service_orders.py"
    tree = ast.parse(router_path.read_text(encoding="utf-8"))
    function_names = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    assert not {
        "list_service_orders",
        "get_service_order",
        "create_service_order",
        "update_service_order",
        "change_status",
        "close_service_order",
        "register_service_order_exception",
        "deactivate_service_order",
        "_build_work_orders_for_service_order",
    } & function_names


def test_every_ets_mutation_route_receives_authenticated_actor():
    from app.routers import service_orders as router

    mutation_routes = [
        router.post_capture_files,
        router.upload_service_order_certificate_pdfs,
        router.release_service_order_certificates,
        router.post_service_order,
        router.patch_service_order,
        router.confirm_service_order_signatures,
        router.confirm_service_order,
        router.call_service_order,
        router.start_service_order,
        router.capture_service_order,
        router.quality_service_order,
        router.create_service_order_exception,
        router.authorize_service_order_exception_route,
        router.execute_service_order_exception_route,
        router.pending_payment_service_order,
        router.release_service_order,
        router.close_service_order_route,
        router.delete_service_order,
    ]
    for route in mutation_routes:
        assert "current_user" in inspect.signature(route).parameters, route.__name__


def test_router_delegates_actor_to_canonical_create(monkeypatch):
    from app.routers import service_orders as router

    service = Mock(return_value=object())
    monkeypatch.setattr(router, "create_service_order", service)
    actor = SimpleNamespace(id=73)
    payload = Mock()
    db = Mock()

    router.post_service_order(payload, db, actor)

    service.assert_called_once_with(db, payload, user_id=73)


def test_critical_ets_service_contracts_require_actor_argument():
    critical_mutations = [
        service_orders.create_service_order,
        service_orders.update_service_order,
        service_orders.confirm_signature_cycle,
        service_orders.change_status,
        service_orders.close_service_order,
        service_orders.deactivate_service_order,
        service_orders.request_service_order_exception,
        service_orders.authorize_service_order_exception,
        service_orders.execute_service_order_exception,
        capture_packages.upload_capture_files,
        certificate_authentication.authenticate_certificate,
        certificates.upload_certificate_pdf,
        certificates.update_certificate,
        certificates.change_status,
        certificates.start_capture,
        certificates.send_to_quality,
        certificates.quality_approve,
        certificates.quality_reject,
        certificates.return_to_technician,
        certificates.validate_pdf_match,
        certificates.manual_accept_match,
        certificates.request_correction,
        certificates.deactivate_certificate,
        certificates.release_to_client,
        certificates.bulk_upload_certificate_pdfs,
        certificates.release_authenticated_certificates_for_service_order,
    ]

    for mutation in critical_mutations:
        actor = inspect.signature(mutation).parameters["user_id"]
        assert actor.default is inspect.Parameter.empty, mutation.__name__
        assert actor.kind is inspect.Parameter.KEYWORD_ONLY, mutation.__name__


def test_critical_ets_service_contract_rejects_explicit_null_actor(db: Session):
    with pytest.raises(ValueError, match="requieren un actor"):
        service_orders.create_service_order(
            db,
            ServiceOrderCreate(client_id=1),
            user_id=None,
        )
    with pytest.raises(ValueError, match="certificados requieren un actor"):
        certificates.update_certificate(
            db,
            1,
            Mock(),
            user_id=None,
        )
