"""Excepción administrativa acotada de auto-resolución de folios LAB."""
import pytest
from sqlalchemy import select
from app.models.user import User
from test_lab_field_sheets_external import (  # noqa: F401
    lab_context, auth, create_order_with_linked_equipment,
)


@pytest.mark.parametrize("ticket_type", ["linked_folio", "manual_myc_folio"])
@pytest.mark.parametrize("self_review", [True, False])
def test_authorized_admin_resolves_folio_with_full_audit(lab_context, ticket_type, self_review):
    from app.models.audit_log import AuditLog
    from app.models.notification import Notification
    from app.models.operational_ticket import OperationalTicket
    from app.schemas.operational_ticket import FolioTicketCreate, TicketResolve
    from app.services.operational_tickets import create_folio_ticket, resolve_operational_ticket

    client, factory, tokens = lab_context
    requester_key = "admin" if self_review else "tech"
    order_id, equipment_id = create_order_with_linked_equipment(client, auth(tokens[requester_key]), factory)
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        requester = db.scalar(select(User).where(User.username == f"lab-{requester_key}"))
        ticket = db.scalar(select(OperationalTicket).where(OperationalTicket.equipment_id == equipment_id))
        if ticket_type == "manual_myc_folio":
            # Replace the fixture's service before creating a real manual request.
            ticket.status = "cancelled"
            equipment = ticket.equipment
            equipment.service_type = "traceable"
            db.commit()
            created = create_folio_ticket(db, FolioTicketCreate(
                work_order_id=order_id, equipment_id=equipment_id, type=ticket_type,
                requested_folio="MYCT-TEST-1", reason="Ajuste autorizado", description="Solicitud manual de prueba",
            ), requester, operator_client_id=None)
            ticket = db.get(OperationalTicket, created.id)
        assert ticket.requested_by_user_id == requester.id
        resolved = resolve_operational_ticket(db, ticket.id, TicketResolve(
            authorized_folio="MYC-TEST-1", comment="Validado por administrador",
        ), admin)
        db.refresh(ticket)
        assert resolved.status == "resolved"
        assert ticket.reviewed_by_user_id == admin.id
        assert ticket.reviewed_at is not None and ticket.resolved_at is not None
        assert ticket.decision_comment == "Validado por administrador"
        assert ticket.resolution_snapshot["final_folio"] == "MYC-TEST-1"
        assert ticket.equipment.certificate_folio == "MYC-TEST-1"
        notification = db.scalar(select(Notification).where(Notification.event_key == f"ticket:{ticket.id}:resolved"))
        assert notification is not None
        assert notification.recipient_user_id == requester.id
        assert notification.actor_user_id == admin.id
        assert db.scalar(select(AuditLog).where(
            AuditLog.entity == "operational_tickets", AuditLog.entity_id == ticket.id,
            AuditLog.action == "lab_folio.authorized", AuditLog.user_id == admin.id,
        )) is not None


@pytest.mark.parametrize("authority", ["non_admin_with_permission", "admin_without_permission", "inactive_admin", "external_admin"])
def test_folio_self_resolution_requires_all_authority_conditions(lab_context, monkeypatch, authority):
    from fastapi import HTTPException
    from app.core.permissions import ROLE_PERMISSIONS
    from app.models.operational_ticket import OperationalTicket
    from app.schemas.operational_ticket import TicketResolve
    from app.services.operational_tickets import resolve_operational_ticket

    client, factory, tokens = lab_context
    actor = "tech" if authority == "non_admin_with_permission" else "admin"
    _, equipment_id = create_order_with_linked_equipment(client, auth(tokens[actor]), factory)
    with factory() as db:
        user = db.scalar(select(User).where(User.username == f"lab-{actor}"))
        ticket = db.scalar(select(OperationalTicket).where(OperationalTicket.equipment_id == equipment_id))
        if authority == "non_admin_with_permission":
            monkeypatch.setitem(ROLE_PERMISSIONS, "Tecnico", {"lab_folios.resolve"})
        elif authority == "admin_without_permission":
            monkeypatch.setitem(ROLE_PERMISSIONS, "Administrador", {"mobile.access"})
        elif authority == "inactive_admin":
            user.roles[0].is_active = False
        else:
            user.account_type = "client_portal"
        with pytest.raises(HTTPException) as exc:
            resolve_operational_ticket(db, ticket.id, TicketResolve(authorized_folio="DENIED"), user)
        assert exc.value.status_code == 403
        assert exc.value.detail == "TICKET_SELF_APPROVAL_FORBIDDEN"
        assert ticket.status == "pending" and ticket.reviewed_at is None


@pytest.mark.parametrize("ticket_type", ["reopen_work_order", "field_sheet_reopen", "partial_close", "certificate_folio_block", "reception_date_change", "partial_delivery", "field_sheet_template_request"])
def test_admin_self_resolution_stays_forbidden_for_other_tickets(lab_context, ticket_type):
    from fastapi import HTTPException
    from app.models.operational_ticket import OperationalTicket
    from app.schemas.operational_ticket import TicketResolve
    from app.services.operational_tickets import resolve_operational_ticket

    _, factory, _ = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        ticket = OperationalTicket(type=ticket_type, status="pending", requested_by_user_id=admin.id,
                                   reason="Prueba seguridad", description="No autoaprobar")
        db.add(ticket)
        db.commit()
        with pytest.raises(HTTPException) as exc:
            resolve_operational_ticket(db, ticket.id, TicketResolve(), admin)
        assert exc.value.detail == "TICKET_SELF_APPROVAL_FORBIDDEN"
