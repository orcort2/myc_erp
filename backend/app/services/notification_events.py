from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.notification import Notification
from app.models.operational_ticket import OperationalTicket
from app.models.user import User
from app.services.auth import user_has_permission
from app.services.push_notifications import queue_notification_for_delivery


TICKET_CREATED = "ticket.created"
TICKET_APPROVED = "ticket.approved"
TICKET_REJECTED = "ticket.rejected"
TICKET_RESOLVED = "ticket.resolved"
TICKET_SIGNATURE_REQUIRED = "ticket.signature_required"


def resolve_notification_recipients(db: Session, event_type: str) -> list[User]:
    if event_type != TICKET_CREATED:
        return []
    users = list(
        db.scalars(
            select(User)
            .where(
                User.account_type == "internal",
                User.status == "active",
                User.is_active.is_(True),
            )
            .options(selectinload(User.roles))
        ).all()
    )
    return [user for user in users if user_has_permission(user, "tickets.review")]


def _create(
    db: Session,
    *,
    recipient_user_id: int,
    actor_user_id: int | None,
    event_type: str,
    event_key: str,
    title: str,
    body: str,
    ticket: OperationalTicket,
) -> Notification:
    existing = db.scalar(select(Notification).where(Notification.event_key == event_key))
    if existing is not None:
        return existing
    notification = Notification(
        recipient_user_id=recipient_user_id,
        actor_user_id=actor_user_id,
        notification_type=event_type,
        event_key=event_key,
        title=title,
        body=body,
        entity_type="ticket",
        entity_id=ticket.id,
        priority="normal",
        metadata_json={
            "event_type": event_type,
            "ticket_id": ticket.id,
            "work_order_id": ticket.work_order_id,
            "work_order_folio": ticket.work_order.folio,
        },
    )
    db.add(notification)
    queue_notification_for_delivery(db, notification)
    return notification


def notify_ticket_created(db: Session, ticket: OperationalTicket, actor: User) -> None:
    for recipient in resolve_notification_recipients(db, TICKET_CREATED):
        if recipient.id == actor.id:
            continue
        _create(
            db,
            recipient_user_id=recipient.id,
            actor_user_id=actor.id,
            event_type=TICKET_CREATED,
            event_key=f"ticket:{ticket.id}:created:user:{recipient.id}",
            title="Nueva solicitud de reapertura",
            body=f"OT {ticket.work_order.folio}",
            ticket=ticket,
        )


def notify_ticket_approved(
    db: Session, ticket: OperationalTicket, actor: User, *, signature_required: bool
) -> None:
    _create(
        db,
        recipient_user_id=ticket.requested_by_user_id,
        actor_user_id=actor.id,
        event_type=TICKET_APPROVED,
        event_key=f"ticket:{ticket.id}:approved",
        title="Solicitud de reapertura aprobada",
        body=f"OT {ticket.work_order.folio} disponible para edición.",
        ticket=ticket,
    )
    if signature_required:
        notify_ticket_signature_required(db, ticket, actor)


def notify_ticket_rejected(db: Session, ticket: OperationalTicket, actor: User) -> None:
    _create(
        db,
        recipient_user_id=ticket.requested_by_user_id,
        actor_user_id=actor.id,
        event_type=TICKET_REJECTED,
        event_key=f"ticket:{ticket.id}:rejected",
        title="Solicitud de reapertura rechazada",
        body=f"OT {ticket.work_order.folio}",
        ticket=ticket,
    )


def notify_ticket_signature_required(
    db: Session, ticket: OperationalTicket, actor: User
) -> None:
    revision = ticket.work_order.revision_number
    _create(
        db,
        recipient_user_id=ticket.requested_by_user_id,
        actor_user_id=actor.id,
        event_type=TICKET_SIGNATURE_REQUIRED,
        event_key=f"ticket:{ticket.id}:signature-required:revision:{revision}",
        title="Nueva firma requerida",
        body=f"OT {ticket.work_order.folio} requiere firmas antes del cierre.",
        ticket=ticket,
    )


def notify_ticket_resolved(db: Session, ticket: OperationalTicket, actor: User) -> None:
    _create(
        db,
        recipient_user_id=ticket.requested_by_user_id,
        actor_user_id=actor.id,
        event_type=TICKET_RESOLVED,
        event_key=f"ticket:{ticket.id}:resolved",
        title="Solicitud resuelta",
        body=f"OT {ticket.work_order.folio} cerrada.",
        ticket=ticket,
    )
