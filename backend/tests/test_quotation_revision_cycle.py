"""Ciclo de revisión: folio de aceptación, archivo de ETS, evidencia y Comunicaciones."""
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

import app.models  # noqa: F401
from app.models.activity import ActivityMessage
from app.models.client import Client, ClientContact
from app.models.email import EmailDelivery
from app.models.quotation import Quotation
from app.models.quotation_acceptance import QuotationAcceptance
from app.models.service_order import ServiceOrder
from app.models.service_order_archive import ServiceOrderArchive
from app.models.service_order_exception import ServiceOrderExceptionRequest
from app.schemas.communication import CommunicationConversationCreate
from app.schemas.quotation_service_change import QuotationUnlockApply
from app.services.activity import get_activity
from app.services.communications import create_conversation
from app.services.institutional_folios import next_acceptance_confirmation_folio
from app.services.quotation_acceptance_history import get_acceptance_pdf, list_acceptances
from app.services.quotation_service_changes import apply_change
from app.services.service_order_archives import (
    restoration_conflicts,
    restore_service_order,
    serialize_row,
    verify_archive_integrity,
)
from app.services.quotations import update_quotation
from app.schemas.quotation import QuotationUpdate
from app.models.audit_log import AuditLog
from app.services.service_order_rebuilds import can_physically_rebuild_service_order

# Fixtures compartidos con el flujo de desbloqueo existente.
from test_communications_completion import communication_db  # noqa: F401
from test_quotation_service_change_exception import (  # noqa: F401
    _acceptance,
    _request_and_authorize,
    context,
    db,
)


def _apply(db, context, authorized):
    return apply_change(
        db,
        authorized["folio"],
        QuotationUnlockApply(expected_snapshot_number=authorized["base_snapshot_number"]),
        context.requester,
    )


def test_confirmation_folio_is_sequential_unique_and_year_scoped(db):
    first = next_acceptance_confirmation_folio(db, issued_on=date(2026, 10, 1))
    second = next_acceptance_confirmation_folio(db, issued_on=date(2026, 10, 2))
    other_year = next_acceptance_confirmation_folio(db, issued_on=date(2027, 1, 2))
    db.commit()
    assert (first, second, other_year) == (
        "MYC-AC-2026-000001",
        "MYC-AC-2026-000002",
        "MYC-AC-2027-000001",
    )


def test_confirmation_folio_continues_after_historical_acceptances(db, context):
    acceptance = _acceptance(db, context)
    acceptance.confirmation_folio = "MYC-AC-2026-000007"
    db.commit()
    assert (
        next_acceptance_confirmation_folio(db, issued_on=date(2026, 7, 30))
        == "MYC-AC-2026-000008"
    )


def test_confirmation_folio_can_never_be_duplicated(db, context):
    first = _acceptance(db, context)
    first.invalidated_at = datetime.now(timezone.utc)
    db.commit()
    with pytest.raises(IntegrityError):
        _acceptance(db, context)  # mismo folio MYC-AC-2026-000001
    db.rollback()


def test_only_one_current_acceptance_per_quotation(db, context):
    _acceptance(db, context)
    duplicate = QuotationAcceptance(
        confirmation_folio="MYC-AC-2026-000099",
        quotation_id=context.quotation.id,
        snapshot_id=context.base_snapshot.id,
        pdf_sha256="0" * 64,
        pdf_bytes=b"x",
        signer_name="Otro",
        signer_email="otro@example.test",
        consent_text="Acepto",
        evidence={},
        verified_at=datetime.now(timezone.utc),
        accepted_at=datetime.now(timezone.utc),
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_unlock_events_are_visible_in_the_quotation_activity_panel(db, context):
    authorized = _request_and_authorize(db, context)
    _apply(db, context, authorized)
    activity = get_activity(db, "quotation", context.quotation.id, context.administrator)
    codes = [message.event_code for message in activity["messages"]]
    for expected in (
        "quotation.unlock.completed",
        "quotation.service_order_archived",
        "quotation.in_revision",
    ):
        assert expected in codes
    assert all(
        "pdf_bytes" not in (message.metadata_json or {}) for message in activity["messages"]
    )


def test_archive_tampering_is_detected_and_blocks_restoration(db, context):
    _apply(db, context, _request_and_authorize(db, context))
    archive = db.scalar(select(ServiceOrderArchive))
    assert restoration_conflicts(db, archive) == []
    archive.archive_data = {**archive.archive_data, "items": []}
    assert verify_archive_integrity(archive) is False
    assert any("integridad" in item for item in restoration_conflicts(db, archive))


def test_restoration_check_reports_folio_and_status_conflicts(db, context):
    _apply(db, context, _request_and_authorize(db, context))
    archive = db.scalar(select(ServiceOrderArchive))
    quotation = db.get(Quotation, context.quotation.id)
    quotation.status = "sent"
    db.add(
        ServiceOrder(
            folio=archive.service_order_folio,
            client_id=context.client.id,
            quotation_id=quotation.id,
            status="scheduled",
        )
    )
    db.commit()
    conflicts = restoration_conflicts(db, archive)
    assert any("Ya existe una ETS con el folio" in item for item in conflicts)
    assert any("ya no está en revisión" in item for item in conflicts)


def test_failure_after_deleting_ets_rolls_everything_back(db, context, monkeypatch):
    authorized = _request_and_authorize(db, context)
    order_id = context.order.id

    def explode(*_args, **_kwargs):
        raise RuntimeError("fallo tras eliminar la ETS")

    monkeypatch.setattr(
        "app.services.quotation_service_changes.invalidate_document_links", explode
    )
    with pytest.raises(RuntimeError):
        _apply(db, context, authorized)
    db.rollback()
    assert db.get(ServiceOrder, order_id) is not None
    assert db.get(Quotation, context.quotation.id).status == "accepted"
    assert db.scalar(select(func.count(ServiceOrderArchive.id))) == 0


def test_operational_exception_request_blocks_physical_deletion(db, context):
    db.add(
        ServiceOrderExceptionRequest(
            service_order_id=context.order.id,
            requested_by_id=context.requester.id,
            status="requested",
            source_stage="a",
            target_stage="b",
            service_order_status_at_request="scheduled",
            reason="Intervención previa",
        )
    )
    db.commit()
    validation = can_physically_rebuild_service_order(db, context.order)
    assert validation.allowed is False
    assert "exception_requests" in {item.code for item in validation.dependencies}


def test_historical_acceptance_without_folio_stays_consultable(db, context):
    acceptance = _acceptance(db, context)
    acceptance.confirmation_folio = None
    db.commit()
    rows = list_acceptances(db, context.quotation.id)
    assert rows[0]["confirmation_folio"] is None
    assert rows[0]["is_current"] is True
    content, filename = get_acceptance_pdf(db, context.quotation.id, acceptance.id)
    assert content.startswith(b"%PDF") and filename.endswith(".pdf")
    with pytest.raises(HTTPException) as missing:
        get_acceptance_pdf(db, context.quotation.id + 99, acceptance.id)
    assert missing.value.status_code == 404


def test_acceptance_history_survives_unlock(db, context):
    _acceptance(db, context)
    _apply(db, context, _request_and_authorize(db, context))
    rows = list_acceptances(db, context.quotation.id)
    assert len(rows) == 1
    assert rows[0]["is_current"] is False
    assert rows[0]["confirmation_folio"] == "MYC-AC-2026-000001"
    assert rows[0]["invalidation_reason"].startswith("controlled_unlock:")


def test_quotation_exposes_only_the_associated_contact(db, context):
    assert context.quotation.contact_phone is None
    contact = ClientContact(
        client_id=context.client.id,
        name="Luis Pérez",
        email="luis.perez@xyz.com",
        phone="3312345678",
        position="Mantenimiento",
    )
    other = ClientContact(client_id=context.client.id, name="Primero", phone="000")
    db.add_all([other, contact])
    db.flush()
    context.quotation.contact_id = contact.id
    db.commit()
    db.refresh(context.quotation)
    assert (context.quotation.contact_name, context.quotation.contact_phone) == (
        "Luis Pérez",
        "3312345678",
    )


def test_client_conversation_is_internal_reused_and_never_sent_externally(communication_db):
    db, users = communication_db
    client = Client(legal_name="Cliente visible", commercial_name="Visible")
    db.add(client)
    db.commit()
    payload = CommunicationConversationCreate(
        conversation_type="client", client_id=client.id
    )
    first, _message, _notifications = create_conversation(db, users["sender"], payload)
    second, _message, _notifications = create_conversation(db, users["sender"], payload)
    assert first.id == second.id
    assert first.conversation_type == "client"
    assert {participant.account_type for participant in first.participants} == {"internal"}
    assert db.scalar(select(func.count(EmailDelivery.id))) == 0


def _unlock(db, context):
    acceptance = _acceptance(db, context)
    authorized = _request_and_authorize(db, context)
    before = serialize_row(context.order)
    before_items = [serialize_row(i) for i in context.order.items]
    _apply(db, context, authorized)
    return acceptance, before, before_items


def test_admin_restore_rebuilds_identical_ets_and_reinstates_acceptance(db, context):
    acceptance, before, before_items = _unlock(db, context)
    archive = db.scalar(select(ServiceOrderArchive))
    result = restore_service_order(db, archive.id, context.administrator, "Se canceló la revisión")
    assert result["restored_at"] is not None and result["restored_by_id"] == context.administrator.id
    restored = db.get(ServiceOrder, before["id"])
    assert serialize_row(restored) == before
    assert [serialize_row(i) for i in restored.items] == before_items
    assert len(restored.work_orders) == 1
    assert db.get(Quotation, context.quotation.id).status == "accepted"
    db.refresh(acceptance)
    assert acceptance.invalidated_at is None and acceptance.confirmation_folio == "MYC-AC-2026-000001"
    assert db.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.action == "quotation.service_order_restored")
    ) == 1
    codes = set(db.scalars(select(ActivityMessage.event_code)).all())
    assert "quotation.service_order_restored" in codes


def test_restore_is_single_use_and_refuses_after_new_version(db, context):
    _unlock(db, context)
    archive = db.scalar(select(ServiceOrderArchive))
    update_quotation(
        db, context.quotation.id, QuotationUpdate(notes="Nueva versión"), user_id=context.requester.id
    )
    with pytest.raises(HTTPException) as stale:
        restore_service_order(db, archive.id, context.administrator, "Intento tardío")
    assert stale.value.status_code == 409
    assert any("posteriores" in c for c in stale.value.detail["conflicts"])
    assert db.scalar(select(func.count(ServiceOrder.id))) == 0
    assert db.get(Quotation, context.quotation.id).status == "in_revision"


def test_restore_second_time_is_rejected(db, context):
    _unlock(db, context)
    archive = db.scalar(select(ServiceOrderArchive))
    restore_service_order(db, archive.id, context.administrator, "Primera")
    with pytest.raises(HTTPException) as again:
        restore_service_order(db, archive.id, context.administrator, "Segunda")
    assert again.value.status_code == 409
    assert db.scalar(select(func.count(ServiceOrder.id))) == 1


def test_restore_requires_permission_and_reason(db, context):
    _unlock(db, context)
    archive = db.scalar(select(ServiceOrderArchive))
    with pytest.raises(HTTPException) as denied:
        restore_service_order(db, archive.id, _plain_user(db), "Motivo válido")
    assert denied.value.status_code == 403
    with pytest.raises(HTTPException) as no_reason:
        restore_service_order(db, archive.id, context.administrator, " ")
    assert no_reason.value.status_code == 422


def _plain_user(db):
    from app.models.user import Role, User

    role = Role(name="Tecnico", description="t")
    db.add(role)
    db.flush()
    user = User(email="plain@example.test", full_name="Plain", hashed_password="x", role_id=role.id, roles=[role])
    db.add(user)
    db.commit()
    return user


def test_restore_rolls_back_when_a_row_cannot_be_inserted(db, context, monkeypatch):
    _unlock(db, context)
    archive = db.scalar(select(ServiceOrderArchive))
    tampered = dict(archive.archive_data)
    # Dato inválido pero con hash recalculado: debe fallar al insertar y revertir todo.
    from app.services.service_order_archives import canonical_hash

    tampered["items"] = [{**tampered["items"][0], "service_name": None}]
    archive.archive_data = tampered
    archive.integrity_hash = canonical_hash(tampered)
    db.commit()
    with pytest.raises(HTTPException) as failure:
        restore_service_order(db, archive.id, context.administrator, "Debe revertirse")
    assert failure.value.status_code == 409
    db.rollback()
    assert db.scalar(select(func.count(ServiceOrder.id))) == 0
    assert db.get(Quotation, context.quotation.id).status == "in_revision"
    assert db.get(ServiceOrderArchive, archive.id).restored_at is None


def _snapshot_state(db, context):
    acceptance = db.scalar(select(QuotationAcceptance))
    return (
        db.scalar(select(func.count(ServiceOrder.id))),
        db.get(Quotation, context.quotation.id).status,
        None if acceptance is None else (acceptance.invalidated_at, acceptance.invalidation_reason),
        db.scalar(select(ServiceOrderArchive.restored_at)),
    )


def _assert_refused_without_changes(db, context, archive_id, fragment):
    before = _snapshot_state(db, context)
    with pytest.raises(HTTPException) as refused:
        restore_service_order(db, archive_id, context.administrator, "Debe rechazarse")
    assert refused.value.status_code == 409
    assert any(fragment in c for c in refused.value.detail["conflicts"])
    db.rollback()
    assert _snapshot_state(db, context) == before


def test_restore_refuses_when_declared_acceptance_does_not_exist(db, context):
    _unlock(db, context)
    archive = db.scalar(select(ServiceOrderArchive))
    archive.acceptance_id = 999999  # SQLite no impone la FK; en PostgreSQL RESTRICT lo impide
    db.commit()
    _assert_refused_without_changes(db, context, archive.id, "no existe")


def test_restore_refuses_acceptance_of_another_quotation(db, context):
    _unlock(db, context)
    archive = db.scalar(select(ServiceOrderArchive))
    acceptance = db.scalar(select(QuotationAcceptance))
    other_client = Client(legal_name="Otro")
    db.add(other_client)
    db.flush()
    other = Quotation(folio="MYC-OTRA", client_id=other_client.id, status="sent")
    db.add(other)
    db.flush()
    acceptance.quotation_id = other.id
    db.commit()
    _assert_refused_without_changes(db, context, archive.id, "otra cotización")


def test_restore_refuses_acceptance_with_wrong_snapshot(db, context):
    from app.services.quotations import _write_snapshot

    _unlock(db, context)
    archive = db.scalar(select(ServiceOrderArchive))
    acceptance = db.scalar(select(QuotationAcceptance))
    other_snapshot = _write_snapshot(db, db.get(Quotation, context.quotation.id), reason="x", user_id=None)
    acceptance.snapshot_id = other_snapshot.id
    db.commit()
    _assert_refused_without_changes(db, context, archive.id, "snapshot archivado")


def test_restore_refuses_acceptance_invalidated_by_someone_else(db, context):
    _unlock(db, context)
    archive = db.scalar(select(ServiceOrderArchive))
    acceptance = db.scalar(select(QuotationAcceptance))
    acceptance.invalidation_reason = "controlled_unlock:EXV-2099-00001"
    db.commit()
    _assert_refused_without_changes(db, context, archive.id, "no fue invalidada por el desbloqueo")


def test_restore_refuses_when_another_user_invalidated_the_acceptance(db, context):
    _unlock(db, context)
    archive = db.scalar(select(ServiceOrderArchive))
    acceptance = db.scalar(select(QuotationAcceptance))
    acceptance.invalidated_by_id = context.administrator.id
    assert archive.deleted_by_id == context.requester.id
    db.commit()
    _assert_refused_without_changes(db, context, archive.id, "otro usuario")


def test_archive_without_acceptance_restores_without_fabricating_one(db, context):
    # Cotización aceptada manualmente (sin evidencia electrónica): no hay aceptación que reactivar.
    authorized = _request_and_authorize(db, context)
    _apply(db, context, authorized)
    archive = db.scalar(select(ServiceOrderArchive))
    assert archive.acceptance_id is None
    restore_service_order(db, archive.id, context.administrator, "Sin evidencia electrónica")
    assert db.get(Quotation, context.quotation.id).status == "accepted"
    assert db.scalar(select(func.count(QuotationAcceptance.id))) == 0


def test_archive_without_acceptance_refuses_if_unlock_invalidated_one(db, context):
    _unlock(db, context)
    archive = db.scalar(select(ServiceOrderArchive))
    archive.acceptance_id = None
    db.commit()
    _assert_refused_without_changes(db, context, archive.id, "inconsistentes")
