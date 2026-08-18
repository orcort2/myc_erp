from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.models.activity import ActivityAttachment, ActivityMessage, ActivityThread
from app.models.audit_log import AuditLog
from app.models.certificate import Certificate, CertificateCaptureFile, CertificatePdfVersion
from app.models.certificate_resolution_operation import CertificateResolutionOperation
from app.models.client import Client
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.models.invoice import Invoice, InvoiceItem
from app.models.notification import Notification
from app.models.service_execution import ServiceTask, ServiceTaskAssignee
from app.models.service_order import (
    ServiceOrder,
    ServiceOrderSignatureCycle,
    ServiceOrderSignatureCycleWorkOrder,
    ServiceWorkOrder,
)
from app.models.user import Role, User
from app.services.mobile_technician import list_assigned_work_orders
from app.services.mobile_technician_scope import get_assigned_work_order
from app.services.service_orders import delete_service_work_order


@pytest.fixture()
def deletion_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        admin_role = Role(name="Administrador")
        technician_role = Role(name="Tecnico")
        db.add_all([admin_role, technician_role])
        db.flush()
        admin = User(
            username="ot-delete-admin",
            email="ot-delete-admin@example.test",
            full_name="Administración OT",
            hashed_password="unused",
            roles=[admin_role],
            role_id=admin_role.id,
        )
        technician = User(
            username="ot-delete-tech",
            email="ot-delete-tech@example.test",
            full_name="Técnico OT",
            hashed_password="unused",
            roles=[technician_role],
            role_id=technician_role.id,
        )
        client = Client(legal_name="Cliente eliminación OT")
        db.add_all([admin, technician, client])
        db.flush()
        ets = ServiceOrder(
            folio="OSMYC-DELETE-0001",
            work_order_number=980001,
            client_id=client.id,
            technician_id=technician.id,
            status="in_progress",
            total_equipment=1,
            completed_equipment=0,
        )
        db.add(ets)
        db.flush()
        target = ServiceWorkOrder(
            service_order_id=ets.id,
            work_order_number=980001,
            sequence=1,
            status="in_progress",
        )
        survivor = ServiceWorkOrder(
            service_order_id=ets.id,
            work_order_number=980002,
            sequence=2,
            status="completed",
        )
        db.add_all([target, survivor])
        db.flush()
        equipment = Equipment(
            service_order_id=ets.id,
            work_order_id=target.id,
            name="Equipo exclusivo",
            status="registered",
        )
        db.add(equipment)
        db.flush()
        field_sheet = FieldSheet(
            equipment_id=equipment.id,
            work_order_id=target.id,
            work_order_number=target.work_order_number,
            template_key="general",
            status="draft",
        )
        db.add(field_sheet)
        db.flush()
        result = FieldSheetResult(
            field_sheet_id=field_sheet.id,
            section_key="general",
            row_number=1,
        )
        certificate = Certificate(
            folio="CERT-DELETE-0001",
            service_order_id=ets.id,
            equipment_id=equipment.id,
            field_sheet_id=field_sheet.id,
            certificate_type="calibration",
            status="draft",
        )
        db.add_all([result, certificate])
        db.flush()
        pdf_version = CertificatePdfVersion(
            certificate_id=certificate.id,
            version_number=1,
            file_path="certificates/nonexistent-delete-test.pdf",
            uploaded_at=datetime.now(timezone.utc),
        )
        capture_file = CertificateCaptureFile(
            certificate_id=certificate.id,
            service_order_id=ets.id,
            original_filename="captura.pdf",
            stored_path="capture/nonexistent-delete-test.pdf",
        )
        invoice = Invoice(
            internal_uuid="invoice-delete-work-order",
            folio="F-DELETE-WO",
            client_id=client.id,
            service_order_id=ets.id,
            status="draft",
        )
        db.add_all([pdf_version, capture_file, invoice])
        db.flush()
        invoice_item = InvoiceItem(
            invoice_id=invoice.id,
            equipment_id=equipment.id,
            certificate_id=certificate.id,
            description="Concepto financiero conservado",
        )
        cycle = ServiceOrderSignatureCycle(
            service_order_id=ets.id,
            cycle_number=1,
            technician_signature_data_url="data:image/png;base64,AA==",
            client_received_signature_data_url="data:image/png;base64,AA==",
            client_acceptance_signature_data_url="data:image/png;base64,AA==",
            technician_signed_name="Técnico",
            client_received_signed_name="Cliente",
            client_acceptance_signed_name="Cliente",
            technician_signed_at=datetime.now(timezone.utc),
            client_received_signed_at=datetime.now(timezone.utc),
            client_acceptance_signed_at=datetime.now(timezone.utc),
            confirmed_at=datetime.now(timezone.utc),
        )
        db.add_all([invoice_item, cycle])
        db.flush()
        target_link = ServiceOrderSignatureCycleWorkOrder(
            signature_cycle_id=cycle.id,
            work_order_id=target.id,
            applied_at=datetime.now(timezone.utc),
        )
        survivor_link = ServiceOrderSignatureCycleWorkOrder(
            signature_cycle_id=cycle.id,
            work_order_id=survivor.id,
            applied_at=datetime.now(timezone.utc),
        )
        db.add_all([target_link, survivor_link])
        thread = ActivityThread(
            entity_type="service_work_order",
            entity_id=target.id,
            created_by_id=admin.id,
        )
        db.add(thread)
        db.flush()
        message = ActivityMessage(
            thread_id=thread.id,
            author_id=admin.id,
            body="Actividad exclusiva de la OT",
        )
        db.add(message)
        db.flush()
        attachment = ActivityAttachment(
            message_id=message.id,
            original_name="evidencia.txt",
            stored_path="activity/nonexistent-evidence.txt",
            size_bytes=1,
        )
        task = ServiceTask(
            source_message_id=message.id,
            created_by_id=admin.id,
            service_order_id=ets.id,
            title="Tarea exclusiva de la OT",
            status="open",
        )
        notification = Notification(
            recipient_user_id=technician.id,
            actor_user_id=admin.id,
            notification_type="activity_mention",
            title="Actividad OT",
            entity_type="service_work_order",
            entity_id=target.id,
            activity_message_id=message.id,
        )
        db.add_all([attachment, task, notification])
        db.flush()
        assignee = ServiceTaskAssignee(task_id=task.id, user_id=technician.id)
        db.add(assignee)
        db.commit()

        app.dependency_overrides[get_db] = lambda: db
        api = TestClient(app)
        try:
            yield {
                "db": db,
                "api": api,
                "admin": admin,
                "technician": technician,
                "ets": ets,
                "target": target,
                "survivor": survivor,
                "equipment_id": equipment.id,
                "field_sheet_id": field_sheet.id,
                "result_id": result.id,
                "certificate_id": certificate.id,
                "pdf_version_id": pdf_version.id,
                "capture_file_id": capture_file.id,
                "invoice_id": invoice.id,
                "invoice_item_id": invoice_item.id,
                "cycle_id": cycle.id,
                "thread_id": thread.id,
                "message_id": message.id,
                "attachment_id": attachment.id,
                "task_id": task.id,
                "assignee_id": assignee.id,
                "notification_id": notification.id,
            }
        finally:
            api.close()
            app.dependency_overrides.clear()
    engine.dispose()


def _headers(user: User) -> dict[str, str]:
    return {
        "Authorization": "Bearer "
        + create_access_token(
            str(user.id),
            extra_claims={
                "auth_context": "internal",
                "roles": [role.name for role in user.roles],
            },
        )
    }


def test_admin_deletes_complete_work_order_and_preserves_shared_resources(
    deletion_context, monkeypatch, tmp_path
):
    context = deletion_context
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    stored_pdf = tmp_path / "certificates" / "delete-me.pdf"
    stored_pdf.parent.mkdir(parents=True)
    stored_pdf.write_bytes(b"exclusive")
    certificate = context["db"].get(Certificate, context["certificate_id"])
    certificate.final_pdf_path = "certificates/delete-me.pdf"
    certificate.final_pdf_original_filename = "delete-me.pdf"
    context["db"].commit()
    response = context["api"].delete(
        f'/api/service-orders/work-orders/{context["target"].id}',
        headers=_headers(context["admin"]),
    )
    assert response.status_code == 204, response.text
    assert not stored_pdf.exists()

    db = context["db"]
    db.expire_all()
    assert db.get(ServiceWorkOrder, context["target"].id) is None
    assert db.get(ServiceWorkOrder, context["survivor"].id) is not None
    assert db.get(Equipment, context["equipment_id"]) is None
    assert db.get(FieldSheet, context["field_sheet_id"]) is None
    assert db.get(FieldSheetResult, context["result_id"]) is None
    assert db.get(Certificate, context["certificate_id"]) is None
    assert db.get(CertificatePdfVersion, context["pdf_version_id"]) is None
    assert db.get(CertificateCaptureFile, context["capture_file_id"]) is None
    assert db.get(ActivityThread, context["thread_id"]) is None
    assert db.get(ActivityMessage, context["message_id"]) is None
    assert db.get(ActivityAttachment, context["attachment_id"]) is None
    assert db.get(ServiceTask, context["task_id"]) is None
    assert db.get(ServiceTaskAssignee, context["assignee_id"]) is None
    notification = db.get(Notification, context["notification_id"])
    assert notification is not None
    assert notification.activity_message_id is None
    assert notification.revoked_at is not None

    invoice = db.get(Invoice, context["invoice_id"])
    invoice_item = db.get(InvoiceItem, context["invoice_item_id"])
    assert invoice is not None
    assert invoice_item is not None
    assert invoice_item.equipment_id is None
    assert invoice_item.certificate_id is None
    assert db.get(ServiceOrderSignatureCycle, context["cycle_id"]) is not None
    remaining_links = db.scalar(
        select(func.count(ServiceOrderSignatureCycleWorkOrder.id)).where(
            ServiceOrderSignatureCycleWorkOrder.signature_cycle_id == context["cycle_id"]
        )
    )
    assert remaining_links == 1
    assert db.get(ServiceOrder, context["ets"].id).work_order_number == context["survivor"].work_order_number
    audit = db.scalar(
        select(AuditLog).where(AuditLog.action == "service_work_order.deleted")
    )
    assert audit.user_id == context["admin"].id
    assert audit.entity_id == context["target"].id

    assert context["target"].id not in {
        item.id for item in list_assigned_work_orders(db, technician=context["technician"])
    }
    with pytest.raises(HTTPException) as exc_info:
        get_assigned_work_order(
            db,
            work_order_id=context["target"].id,
            technician=context["technician"],
        )
    assert exc_info.value.status_code == 404


def test_non_admin_receives_403_and_missing_work_order_returns_404(deletion_context):
    context = deletion_context
    forbidden = context["api"].delete(
        f'/api/service-orders/work-orders/{context["target"].id}',
        headers=_headers(context["technician"]),
    )
    assert forbidden.status_code == 403
    assert context["db"].get(ServiceWorkOrder, context["target"].id) is not None

    missing = context["api"].delete(
        "/api/service-orders/work-orders/99999999",
        headers=_headers(context["admin"]),
    )
    assert missing.status_code == 404


def test_immutable_resolution_evidence_blocks_before_any_mutation(deletion_context):
    context = deletion_context
    operation = CertificateResolutionOperation(
        certificate_id=context["certificate_id"],
        operation_key="certificate.test",
        idempotency_key="work-order-delete-block",
        request_hash="a" * 64,
        actor_id="test-actor",
        correlation_id="test-correlation",
        request_payload={},
        before_snapshot={},
        after_snapshot={},
        result_payload={},
    )
    context["db"].add(operation)
    context["db"].commit()

    response = context["api"].delete(
        f'/api/service-orders/work-orders/{context["target"].id}',
        headers=_headers(context["admin"]),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "WORK_ORDER_DELETE_BLOCKED"
    assert context["db"].get(ServiceWorkOrder, context["target"].id) is not None
    assert context["db"].get(Certificate, context["certificate_id"]) is not None


@pytest.mark.parametrize("work_order_status", ["pending", "in_progress", "completed", "cancelled"])
def test_admin_deletion_has_no_operational_status_restriction(
    deletion_context, work_order_status
):
    context = deletion_context
    context["target"].status = work_order_status
    context["db"].commit()
    delete_service_work_order(
        context["db"], context["target"].id, user_id=context["admin"].id
    )
    assert context["db"].get(ServiceWorkOrder, context["target"].id) is None


def test_commit_failure_rolls_back_every_database_change(
    deletion_context, monkeypatch, tmp_path
):
    context = deletion_context
    db = context["db"]
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    stored_pdf = tmp_path / "certificates" / "rollback.pdf"
    stored_pdf.parent.mkdir(parents=True)
    stored_pdf.write_bytes(b"rollback-safe")
    certificate = db.get(Certificate, context["certificate_id"])
    certificate.final_pdf_path = "certificates/rollback.pdf"
    certificate.final_pdf_original_filename = "rollback.pdf"
    db.commit()
    original_commit = db.commit

    def fail_commit():
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(db, "commit", fail_commit)
    with pytest.raises(HTTPException) as exc_info:
        delete_service_work_order(db, context["target"].id, user_id=context["admin"].id)
    assert exc_info.value.status_code == 409

    monkeypatch.setattr(db, "commit", original_commit)
    db.expire_all()
    assert db.get(ServiceWorkOrder, context["target"].id) is not None
    assert db.get(Equipment, context["equipment_id"]) is not None
    assert db.get(FieldSheet, context["field_sheet_id"]) is not None
    assert db.get(Certificate, context["certificate_id"]) is not None
    assert stored_pdf.read_bytes() == b"rollback-safe"
    invoice_item = db.get(InvoiceItem, context["invoice_item_id"])
    assert invoice_item.equipment_id == context["equipment_id"]
    assert invoice_item.certificate_id == context["certificate_id"]
