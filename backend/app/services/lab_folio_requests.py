from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.communication import CommunicationConversation
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.operational_ticket import OperationalTicket
from app.models.user import User
from app.services.audit_logs import write_audit_log
from app.services.notification_events import notify_ticket_created, notify_ticket_rejected


def ensure_linked_folio_request(
    db: Session,
    *,
    work_order: LabWorkOrder,
    equipment: LabWorkOrderEquipment,
    user: User,
    operator_client_id: int | None,
) -> OperationalTicket:
    """Materializa una solicitud Vinculado dentro de la transacción caller."""
    existing = db.scalar(
        select(OperationalTicket)
        .where(
            OperationalTicket.equipment_id == equipment.id,
            OperationalTicket.type == "linked_folio",
            OperationalTicket.status.in_(("pending", "in_progress")),
        )
        .with_for_update()
    )
    if existing is not None:
        equipment.folio_ticket_id = existing.id
        equipment.folio_status = "pending"
        return existing

    identity = " · ".join(
        part
        for part in (
            f"Equipo {equipment.position}",
            equipment.instrument,
            equipment.brand,
            equipment.model,
            equipment.identification,
            equipment.serial_number,
        )
        if part
    )
    ticket = OperationalTicket(
        type="linked_folio",
        status="pending",
        work_order_id=work_order.id,
        equipment_id=equipment.id,
        operator_client_id=operator_client_id,
        linked_company_id=None,
        requested_by_user_id=user.id,
        requested_folio=None,
        automatic_folio=None,
        reason="Asignación de folio Vinculado",
        description=identity,
    )
    db.add(ticket)
    db.flush()

    conversation = CommunicationConversation(
        conversation_type="client" if operator_client_id else "internal",
        client_id=operator_client_id,
        ticket_id=ticket.id,
        title=f"Solicitud LAB #{ticket.id} · linked_folio",
        created_by_user_id=user.id,
        participants=[user],
    )
    db.add(conversation)
    db.flush()
    ticket.conversation_id = conversation.id
    equipment.folio_ticket_id = ticket.id
    equipment.folio_status = "pending"

    write_audit_log(
        db,
        action="lab_folio.requested",
        entity="operational_tickets",
        entity_id=ticket.id,
        user_id=user.id,
        new_values={
            "type": ticket.type,
            "work_order_id": work_order.id,
            "equipment_id": equipment.id,
            "automatic_folio": None,
            "requested_folio": None,
            "linked_company_id": None,
        },
    )
    notify_ticket_created(db, ticket, user)
    return ticket


def cancel_linked_folio_request(
    db: Session,
    *,
    equipment: LabWorkOrderEquipment,
    user: User,
    reason: str,
) -> OperationalTicket | None:
    """Cancela la solicitud Vinculado activa de un equipo (Cierre UX 2026-09,
    item C) cuando el equipo abandona service_type='linked' antes de tener
    folio autorizado/reservado -- el caller (_assign_equipment_service_core)
    ya garantiza esa precondición vía el guard de folio_already_secured, que
    corre antes y bloquea con 409 cualquier cambio si hay folio reserved/
    authorized. Idempotente: si no hay solicitud pending/in_progress, no hace
    nada (no falla, no crea nada) -- misma llamada segura de usar siempre que
    el equipo deja de ser Vinculado, sin que el caller tenga que verificar
    primero si existía una solicitud."""
    ticket = db.scalar(
        select(OperationalTicket)
        .where(
            OperationalTicket.equipment_id == equipment.id,
            OperationalTicket.type == "linked_folio",
            OperationalTicket.status.in_(("pending", "in_progress")),
        )
        .with_for_update()
    )
    if ticket is None:
        return None
    previous_status = ticket.status
    ticket.status = "cancelled"
    ticket.reviewed_by_user_id = user.id
    ticket.reviewed_at = datetime.now(timezone.utc)
    ticket.decision_comment = reason
    if equipment.folio_ticket_id == ticket.id:
        equipment.folio_ticket_id = None
    write_audit_log(
        db,
        action="lab_folio.cancelled_service_change",
        entity="operational_tickets",
        entity_id=ticket.id,
        user_id=user.id,
        previous_values={"status": previous_status},
        new_values={"status": "cancelled", "reason": reason, "equipment_id": equipment.id},
    )
    notify_ticket_rejected(db, ticket, user)
    return ticket
