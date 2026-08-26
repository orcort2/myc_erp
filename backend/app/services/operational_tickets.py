from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.lab_work_order import LabWorkOrder
from app.models.lab_work_order_revision import LabWorkOrderRevision
from app.models.operational_ticket import OperationalTicket
from app.models.user import User
from app.schemas.operational_ticket import (
    LabRevisionRead,
    ReopenTicketCreate,
    TicketRead,
    TicketReject,
    TicketReview,
)
from app.services.audit_logs import write_audit_log
from app.services.auth import user_has_permission
from app.services.lab_work_orders import _get, _group, _root_id
from app.services.notification_events import (
    notify_ticket_approved,
    notify_ticket_created,
    notify_ticket_rejected,
)
from app.services.push_notifications import commit_and_dispatch_notifications


def _ticket_query():
    return select(OperationalTicket).options(
        joinedload(OperationalTicket.work_order),
        joinedload(OperationalTicket.requested_by),
    )


def _read(ticket: OperationalTicket) -> TicketRead:
    return TicketRead(
        id=ticket.id,
        type=ticket.type,
        status=ticket.status,
        work_order_id=ticket.work_order_id,
        work_order_folio=ticket.work_order.folio,
        client_name=ticket.work_order.client_name,
        requested_by_user_id=ticket.requested_by_user_id,
        requested_by_name=ticket.requested_by.full_name,
        reviewed_by_user_id=ticket.reviewed_by_user_id,
        reason=ticket.reason,
        description=ticket.description,
        requested_signature_policy=ticket.requested_signature_policy,
        final_signature_policy=ticket.final_signature_policy,
        decision_comment=ticket.decision_comment,
        created_at=ticket.created_at,
        reviewed_at=ticket.reviewed_at,
        resolved_at=ticket.resolved_at,
    )


def _get_ticket(db: Session, ticket_id: int, *, lock: bool = False) -> OperationalTicket:
    if lock:
        locked_ticket_id = db.scalar(
            select(OperationalTicket.id)
            .where(OperationalTicket.id == ticket_id)
            .with_for_update()
        )
        if locked_ticket_id is None:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
    ticket = db.scalar(_ticket_query().where(OperationalTicket.id == ticket_id))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


def _can_view_all(user: User) -> bool:
    return user_has_permission(user, "tickets.view_all") or user_has_permission(
        user, "tickets.review"
    )


def create_reopen_ticket(
    db: Session, payload: ReopenTicketCreate, user: User
) -> TicketRead:
    work_order = _get(db, payload.work_order_id, lock=True)
    if work_order.status != "completed":
        raise HTTPException(status_code=409, detail="OT_NOT_CLOSED")
    existing = db.scalar(
        select(OperationalTicket.id).where(
            OperationalTicket.work_order_id == work_order.id,
            OperationalTicket.type == "reopen_work_order",
            OperationalTicket.status.in_(("pending", "approved", "in_progress")),
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ya existe una solicitud activa para esta OT")
    ticket = OperationalTicket(
        type="reopen_work_order",
        status="pending",
        work_order_id=work_order.id,
        requested_by_user_id=user.id,
        reason=payload.reason.strip(),
        description=payload.description.strip(),
        requested_signature_policy=payload.requested_signature_policy,
    )
    db.add(ticket)
    db.flush()
    write_audit_log(
        db,
        action="ticket.created",
        entity="operational_tickets",
        entity_id=ticket.id,
        user_id=user.id,
        new_values={"type": ticket.type, "work_order_id": work_order.id},
    )
    notify_ticket_created(db, ticket, user)
    commit_and_dispatch_notifications(db)
    return _read(_get_ticket(db, ticket.id))


def list_tickets(
    db: Session,
    user: User,
    *,
    ticket_status: str | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 25,
    client_id: int | None = None,
) -> list[TicketRead]:
    query = _ticket_query()
    if client_id is not None:
        query = query.join(OperationalTicket.work_order).where(
            LabWorkOrder.client_id == client_id
        )
    elif not _can_view_all(user):
        query = query.where(OperationalTicket.requested_by_user_id == user.id)
    if ticket_status:
        query = query.where(OperationalTicket.status == ticket_status)
    if search and search.strip():
        value = f"%{search.strip()}%"
        if client_id is None:
            query = query.join(OperationalTicket.work_order)
        query = query.where(
            LabWorkOrder.client_name.ilike(value)
            | OperationalTicket.reason.ilike(value)
        )
    tickets = db.scalars(
        query.order_by(OperationalTicket.created_at.desc(), OperationalTicket.id.desc())
        .offset(offset)
        .limit(limit)
    ).unique().all()
    return [_read(ticket) for ticket in tickets]


def get_ticket(
    db: Session,
    ticket_id: int,
    user: User,
    *,
    client_id: int | None = None,
) -> TicketRead:
    ticket = _get_ticket(db, ticket_id)
    if client_id is not None and ticket.work_order.client_id != client_id:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if client_id is not None:
        return _read(ticket)
    if ticket.requested_by_user_id != user.id and not _can_view_all(user):
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return _read(ticket)


def _snapshot(item: LabWorkOrder) -> dict:
    return {
        "folio": item.folio,
        "status": item.status,
        "revision_number": item.revision_number,
        "client_name": item.client_name,
        "reception_date": item.reception_date.isoformat(),
        "departure_date": item.departure_date.isoformat(),
        "address": item.address,
        "contact_name": item.contact_name,
        "contact_phone": item.contact_phone,
        "contact_email": item.contact_email,
        "postal_code": item.postal_code,
        "city": item.city,
        "state_name": item.state_name,
        "purchase_order": item.purchase_order,
        "notes": item.notes,
        "equipment": [
            {
                "position": equipment.position,
                "instrument": equipment.instrument,
                "brand": equipment.brand,
                "identification": equipment.identification,
                "serial_number": equipment.serial_number,
                "report_number": equipment.report_number,
                "is_good_condition": equipment.is_good_condition,
            }
            for equipment in item.equipment
        ],
    }


def approve_reopen_ticket(
    db: Session, ticket_id: int, payload: TicketReview, user: User
) -> TicketRead:
    ticket = _get_ticket(db, ticket_id, lock=True)
    if ticket.status != "pending":
        raise HTTPException(status_code=409, detail="TICKET_ALREADY_RESOLVED")
    required_permission = (
        "work_orders.reopen_preserve_signatures"
        if payload.signature_policy == "preserve"
        else "work_orders.reopen_invalidate_signatures"
    )
    if not user_has_permission(user, "work_orders.reopen") or not user_has_permission(
        user, required_permission
    ):
        raise HTTPException(status_code=403, detail="REOPEN_NOT_AUTHORIZED")

    work_order = _get(db, ticket.work_order_id, lock=True)
    group = _group(db, work_order, lock=True)
    if any(item.status != "completed" for item in group):
        raise HTTPException(status_code=409, detail="OT_NOT_CLOSED")
    now = datetime.now(timezone.utc)
    preserve = payload.signature_policy == "preserve"
    for item in group:
        db.add(
            LabWorkOrderRevision(
                work_order_id=item.id,
                revision_number=item.revision_number,
                reopen_ticket_id=ticket.id,
                snapshot=_snapshot(item),
                signature_session_id=item.signature_session_id,
                signature_preserved=preserve,
                final_pdf=item.final_pdf,
                final_pdf_sha256=item.final_pdf_sha256,
                final_pdf_generated_at=item.final_pdf_generated_at,
            )
        )
        item.revision_number += 1
        item.edit_version += 1
        item.reopened_at = now
        item.reopened_by_user_id = user.id
        item.reopen_ticket_id = ticket.id
        item.signature_preserved = preserve
        item.signature_required = not preserve
        if not preserve:
            item.signature_session_id = None
        item.status = "draft"
        item.completed_at = None
        item.final_pdf = None
        item.final_pdf_sha256 = None
        item.final_pdf_generated_at = None

    ticket.status = "in_progress"
    ticket.reviewed_by_user_id = user.id
    ticket.reviewed_at = now
    ticket.final_signature_policy = payload.signature_policy
    ticket.decision_comment = payload.comment
    write_audit_log(
        db,
        action="ticket.reopen_approved",
        entity="operational_tickets",
        entity_id=ticket.id,
        user_id=user.id,
        previous_values={"status": "pending"},
        new_values={
            "status": "in_progress",
            "signature_policy": payload.signature_policy,
            "work_order_ids": [item.id for item in group],
            "revision": work_order.revision_number,
        },
    )
    notify_ticket_approved(db, ticket, user, signature_required=not preserve)
    commit_and_dispatch_notifications(db)
    return _read(_get_ticket(db, ticket.id))


def reject_ticket(
    db: Session, ticket_id: int, payload: TicketReject, user: User
) -> TicketRead:
    ticket = _get_ticket(db, ticket_id, lock=True)
    if ticket.status != "pending":
        raise HTTPException(status_code=409, detail="TICKET_ALREADY_RESOLVED")
    ticket.status = "rejected"
    ticket.reviewed_by_user_id = user.id
    ticket.reviewed_at = datetime.now(timezone.utc)
    ticket.decision_comment = payload.comment.strip()
    write_audit_log(
        db,
        action="ticket.rejected",
        entity="operational_tickets",
        entity_id=ticket.id,
        user_id=user.id,
        previous_values={"status": "pending"},
        new_values={"status": "rejected"},
    )
    notify_ticket_rejected(db, ticket, user)
    commit_and_dispatch_notifications(db)
    return _read(_get_ticket(db, ticket.id))


def list_revisions(db: Session, work_order_id: int) -> list[LabRevisionRead]:
    work_order = _get(db, work_order_id)
    historical = list(
        db.scalars(
            select(LabWorkOrderRevision)
            .where(LabWorkOrderRevision.work_order_id == work_order.id)
            .order_by(LabWorkOrderRevision.revision_number)
        )
    )
    result = [
        LabRevisionRead(
            id=item.id,
            revision_number=item.revision_number,
            status="completed",
            reopen_ticket_id=item.reopen_ticket_id,
            signature_session_id=item.signature_session_id,
            signature_preserved=item.signature_preserved,
            final_pdf_sha256=item.final_pdf_sha256,
            final_pdf_generated_at=item.final_pdf_generated_at,
            created_at=item.created_at,
        )
        for item in historical
    ]
    result.append(
        LabRevisionRead(
            revision_number=work_order.revision_number,
            status=work_order.status,
            reopen_ticket_id=work_order.reopen_ticket_id,
            signature_session_id=work_order.signature_session_id,
            signature_preserved=work_order.signature_preserved,
            final_pdf_sha256=work_order.final_pdf_sha256,
            final_pdf_generated_at=work_order.final_pdf_generated_at,
            created_at=work_order.updated_at,
        )
    )
    return result


def get_revision_pdf(
    db: Session, work_order_id: int, revision_number: int
) -> tuple[bytes, str]:
    work_order = _get(db, work_order_id)
    if revision_number == work_order.revision_number:
        if not work_order.final_pdf:
            raise HTTPException(status_code=409, detail="La revisión aún no tiene PDF")
        return work_order.final_pdf, f"OT-{work_order.folio}-r{revision_number}.pdf"
    revision = db.scalar(
        select(LabWorkOrderRevision).where(
            LabWorkOrderRevision.work_order_id == work_order.id,
            LabWorkOrderRevision.revision_number == revision_number,
        )
    )
    if revision is None or not revision.final_pdf:
        raise HTTPException(status_code=404, detail="Revisión documental no encontrada")
    return revision.final_pdf, f"OT-{work_order.folio}-r{revision_number}.pdf"
