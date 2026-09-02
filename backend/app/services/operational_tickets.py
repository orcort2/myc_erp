from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.lab_work_order import LabWorkOrder
from app.models.lab_work_order import LabWorkOrderEquipment
from app.models.communication import CommunicationConversation
from app.models.lab_work_order_revision import LabWorkOrderRevision
from app.models.operational_ticket import OperationalTicket
from app.models.user import User
from app.schemas.operational_ticket import (
    LabRevisionRead,
    CertificateFolioBlockCreate,
    FieldSheetReopenTicketCreate,
    FieldSheetTemplateRequestCreate,
    FolioTicketCreate,
    PartialCloseTicketCreate,
    ReopenTicketCreate,
    TicketRead,
    TicketReject,
    TicketReview,
    TicketResolve,
)
from app.services.audit_logs import write_audit_log
from app.services.auth import user_has_permission
from app.services.lab_work_orders import (
    _get,
    _group,
    _lock_historical_group,
    _notify_work_order_owner,
    _open_group_members,
    _signature_cohort,
    _allocate_lab_certificate_folio,
    _missing_completed_sheets,
    _retire_current_field_sheet_revision,
)
from app.services.lab_work_orders import _read as _read_work_order
from app.services.notification_events import (
    notify_ticket_approved,
    notify_ticket_created,
    notify_ticket_rejected,
    notify_ticket_resolved,
)
from app.services.push_notifications import commit_and_dispatch_notifications


def _ticket_query():
    return select(OperationalTicket).options(
        joinedload(OperationalTicket.work_order),
        joinedload(OperationalTicket.equipment),
        joinedload(OperationalTicket.requested_by),
    )


def _read(ticket: OperationalTicket) -> TicketRead:
    return TicketRead(
        id=ticket.id,
        type=ticket.type,
        status=ticket.status,
        work_order_id=ticket.work_order_id,
        equipment_id=ticket.equipment_id,
        equipment_position=ticket.equipment.position if ticket.equipment else None,
        equipment_instrument=ticket.equipment.instrument if ticket.equipment else None,
        equipment_brand=ticket.equipment.brand if ticket.equipment else None,
        equipment_model=ticket.equipment.model if ticket.equipment else None,
        equipment_identification=ticket.equipment.identification if ticket.equipment else None,
        equipment_serial_number=ticket.equipment.serial_number if ticket.equipment else None,
        equipment_service_type=ticket.equipment.service_type if ticket.equipment else None,
        equipment_folio_status=ticket.equipment.folio_status if ticket.equipment else None,
        operator_client_id=ticket.operator_client_id,
        work_order_folio=ticket.work_order.folio if ticket.work_order else None,
        client_name=ticket.work_order.client_name if ticket.work_order else None,
        requested_by_user_id=ticket.requested_by_user_id,
        requested_by_name=ticket.requested_by.full_name,
        reviewed_by_user_id=ticket.reviewed_by_user_id,
        reason=ticket.reason,
        description=ticket.description,
        requested_signature_policy=ticket.requested_signature_policy,
        final_signature_policy=ticket.final_signature_policy,
        linked_company_id=ticket.linked_company_id,
        conversation_id=ticket.conversation_id,
        automatic_folio=ticket.automatic_folio,
        requested_folio=ticket.requested_folio,
        authorized_folio=ticket.authorized_folio,
        accredited_quantity=ticket.accredited_quantity,
        traceable_quantity=ticket.traceable_quantity,
        resolution_snapshot=ticket.resolution_snapshot,
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
    if work_order.status not in {"completed", "partially_closed"}:
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
    equipment_id = payload.equipment_id
    if equipment_id is not None:
        equipment = db.scalar(
            select(LabWorkOrderEquipment).where(
                LabWorkOrderEquipment.id == equipment_id,
                LabWorkOrderEquipment.work_order_id == work_order.id,
            )
        )
        if equipment is None:
            raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")
    ticket = OperationalTicket(
        type="reopen_work_order",
        status="pending",
        work_order_id=work_order.id,
        equipment_id=equipment_id,
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


def _attach_conversation(db: Session, ticket: OperationalTicket, user: User) -> None:
    conversation = CommunicationConversation(
        conversation_type="client" if ticket.operator_client_id else "internal",
        client_id=ticket.operator_client_id,
        ticket_id=ticket.id,
        title=f"Solicitud LAB #{ticket.id} · {ticket.type}",
        created_by_user_id=user.id,
        participants=[user],
    )
    db.add(conversation)
    db.flush()
    ticket.conversation_id = conversation.id


def create_folio_ticket(
    db: Session,
    payload: FolioTicketCreate,
    user: User,
    *,
    operator_client_id: int | None,
) -> TicketRead:
    work_order = _get(db, payload.work_order_id, lock=True)
    equipment = db.scalar(
        select(LabWorkOrderEquipment).where(
            LabWorkOrderEquipment.id == payload.equipment_id,
            LabWorkOrderEquipment.work_order_id == work_order.id,
        )
    )
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")
    expected_type = "linked_folio" if equipment.service_type == "linked" else "manual_myc_folio"
    if payload.type != expected_type:
        raise HTTPException(status_code=422, detail="El tipo de solicitud no corresponde al servicio")
    if payload.type == "manual_myc_folio" and not (payload.requested_folio or "").strip():
        raise HTTPException(status_code=422, detail="Indica el folio MYC manual solicitado")
    existing = db.scalar(
        select(OperationalTicket.id).where(
            OperationalTicket.equipment_id == equipment.id,
            OperationalTicket.type == payload.type,
            OperationalTicket.status == "pending",
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="El equipo ya tiene una solicitud de folio pendiente")
    ticket = OperationalTicket(
        type=payload.type,
        status="pending",
        work_order_id=work_order.id,
        equipment_id=equipment.id,
        operator_client_id=operator_client_id,
        linked_company_id=equipment.linked_company_id,
        requested_by_user_id=user.id,
        reason=payload.reason.strip(),
        description=payload.description.strip(),
        automatic_folio=equipment.automatic_certificate_folio,
        requested_folio=(payload.requested_folio or "").strip() or None,
    )
    db.add(ticket)
    db.flush()
    _attach_conversation(db, ticket, user)
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
            "automatic_folio": ticket.automatic_folio,
            "requested_folio": ticket.requested_folio,
            "linked_company_id": ticket.linked_company_id,
        },
    )
    notify_ticket_created(db, ticket, user)
    commit_and_dispatch_notifications(db)
    return _read(_get_ticket(db, ticket.id))


def create_field_sheet_template_request_ticket(
    db: Session,
    payload: FieldSheetTemplateRequestCreate,
    user: User,
    *,
    operator_client_id: int | None,
) -> TicketRead:
    """Fase 1F: sólo deja el dominio listo (OperationalTicket como autoridad
    única, sin tabla nueva). El técnico simplemente puede dejar constancia de
    'no encuentro la hoja de campo necesaria'; la atención/resolución de este
    tipo de ticket es una fase posterior y no se implementa aquí."""
    work_order = _get(db, payload.work_order_id, lock=True)
    equipment = db.scalar(
        select(LabWorkOrderEquipment).where(
            LabWorkOrderEquipment.id == payload.equipment_id,
            LabWorkOrderEquipment.work_order_id == work_order.id,
        )
    )
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")
    ticket = OperationalTicket(
        type="field_sheet_template_request",
        status="pending",
        work_order_id=work_order.id,
        equipment_id=equipment.id,
        operator_client_id=operator_client_id,
        requested_by_user_id=user.id,
        reason=payload.reason.strip(),
        description=payload.description.strip(),
    )
    db.add(ticket)
    db.flush()
    _attach_conversation(db, ticket, user)
    write_audit_log(
        db,
        action="field_sheet_template_request.requested",
        entity="operational_tickets",
        entity_id=ticket.id,
        user_id=user.id,
        new_values={"work_order_id": work_order.id, "equipment_id": equipment.id},
    )
    notify_ticket_created(db, ticket, user)
    commit_and_dispatch_notifications(db)
    return _read(_get_ticket(db, ticket.id))


def create_field_sheet_reopen_ticket(
    db: Session,
    payload: FieldSheetReopenTicketCreate,
    user: User,
    *,
    operator_client_id: int | None,
) -> TicketRead:
    """Desbloqueo/reapertura de UNA FieldSheet/equipo completed mientras la
    OT sigue abierta. Distinto de create_reopen_ticket: no requiere que la
    OT ya esté cerrada -- por diseño puede pedirse con otras hojas de la
    misma OT todavía en captura. Cuando la OT SÍ ya está cerrada, ese caso
    usa el ticket reopen_work_order existente (equipment_id opcional ahí),
    que reabre la OT completa con su propia ceremonia de firmas/versión."""
    work_order = _get(db, payload.work_order_id, lock=True)
    if work_order.status not in {"received_signed", "in_progress", "ready_to_close"}:
        raise HTTPException(
            status_code=409,
            detail="La OT ya está cerrada; solicita la reapertura de la OT completa",
        )
    equipment = db.scalar(
        select(LabWorkOrderEquipment)
        .where(
            LabWorkOrderEquipment.id == payload.equipment_id,
            LabWorkOrderEquipment.work_order_id == work_order.id,
        )
        .with_for_update()
    )
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")
    current = equipment.field_sheet
    if current is None or current.status != "completed":
        raise HTTPException(status_code=409, detail="El equipo no tiene una hoja completed para desbloquear")
    existing = db.scalar(
        select(OperationalTicket.id).where(
            OperationalTicket.equipment_id == equipment.id,
            OperationalTicket.type == "field_sheet_reopen",
            OperationalTicket.status.in_(("pending", "approved", "in_progress")),
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ya existe una solicitud activa para esta hoja")
    ticket = OperationalTicket(
        type="field_sheet_reopen",
        status="pending",
        work_order_id=work_order.id,
        equipment_id=equipment.id,
        operator_client_id=operator_client_id,
        requested_by_user_id=user.id,
        reason=payload.reason.strip(),
        description=payload.description.strip(),
        resolution_snapshot={
            "field_sheet_id": current.id,
            "revision_number": current.revision_number,
        },
    )
    db.add(ticket)
    db.flush()
    _attach_conversation(db, ticket, user)
    write_audit_log(
        db,
        action="field_sheet_reopen.requested",
        entity="operational_tickets",
        entity_id=ticket.id,
        user_id=user.id,
        new_values={
            "work_order_id": work_order.id,
            "equipment_id": equipment.id,
            "field_sheet_id": current.id,
            "revision_number": current.revision_number,
        },
    )
    notify_ticket_created(db, ticket, user)
    commit_and_dispatch_notifications(db)
    return _read(_get_ticket(db, ticket.id))


def create_partial_close_ticket(
    db: Session,
    payload: PartialCloseTicketCreate,
    user: User,
    *,
    operator_client_id: int | None,
) -> TicketRead:
    if operator_client_id is not None:
        raise HTTPException(status_code=403, detail="La excepción de cierre parcial es exclusiva de staff MYC")
    work_order = _get(db, payload.work_order_id, lock=True)
    # Fase 3: el cierre parcial excusa hojas pendientes de una OT que sigue en
    # trabajo técnico activo (recepción ya firmada) -- ya no "draft", que
    # ahora es sólo el estado previo a la recepción. No genera ni requiere
    # una nueva firma de recepción (ver sección 17: son conceptos distintos).
    if work_order.status not in {"received_signed", "in_progress"}:
        raise HTTPException(status_code=409, detail="La OT no admite una excepción de cierre")
    group = _group(db, work_order, lock=True)
    if len(_open_group_members(group)) <= 1:
        raise HTTPException(
            status_code=409,
            detail="La excepción de cierre parcial requiere un grupo con más de una OT relevante",
        )
    missing = _missing_completed_sheets([work_order])
    if not missing:
        raise HTTPException(status_code=409, detail="La OT no tiene hojas pendientes")
    ticket = OperationalTicket(
        type="partial_close",
        status="pending",
        work_order_id=work_order.id,
        operator_client_id=None,
        requested_by_user_id=user.id,
        reason=payload.reason.strip(),
        description=payload.description.strip(),
        resolution_snapshot={"pending_items": missing},
    )
    db.add(ticket)
    db.flush()
    _attach_conversation(db, ticket, user)
    write_audit_log(
        db,
        action="lab_partial_close.requested",
        entity="operational_tickets",
        entity_id=ticket.id,
        user_id=user.id,
        new_values={"work_order_id": work_order.id, "pending_items": missing},
    )
    notify_ticket_created(db, ticket, user)
    commit_and_dispatch_notifications(db)
    return _read(_get_ticket(db, ticket.id))


def create_certificate_block_ticket(
    db: Session,
    payload: CertificateFolioBlockCreate,
    user: User,
    *,
    operator_client_id: int | None,
) -> TicketRead:
    if operator_client_id is None:
        raise HTTPException(status_code=403, detail="Los bloques temporales son para operadores externos")
    total = payload.accredited_quantity + payload.traceable_quantity
    if total < 1 or total > 100:
        raise HTTPException(status_code=422, detail="La solicitud admite máximo 100 folios combinados")
    ticket = OperationalTicket(
        type="certificate_folio_block",
        status="pending",
        work_order_id=None,
        operator_client_id=operator_client_id,
        requested_by_user_id=user.id,
        reason=payload.reason.strip(),
        description=payload.description.strip(),
        accredited_quantity=payload.accredited_quantity,
        traceable_quantity=payload.traceable_quantity,
    )
    db.add(ticket)
    db.flush()
    _attach_conversation(db, ticket, user)
    write_audit_log(
        db,
        action="lab_certificate_block.requested",
        entity="operational_tickets",
        entity_id=ticket.id,
        user_id=user.id,
        new_values={"MYCA": payload.accredited_quantity, "MYCT": payload.traceable_quantity, "total": total},
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
        query = query.where(OperationalTicket.operator_client_id == client_id)
    elif not _can_view_all(user):
        query = query.where(OperationalTicket.requested_by_user_id == user.id)
    if ticket_status:
        query = query.where(OperationalTicket.status == ticket_status)
    if search and search.strip():
        value = f"%{search.strip()}%"
        query = query.outerjoin(OperationalTicket.work_order).where(
            LabWorkOrder.client_name.ilike(value) | OperationalTicket.reason.ilike(value)
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
    if client_id is not None and ticket.operator_client_id != client_id:
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


def _reopen_closed_cohort(
    db: Session,
    work_order_id: int,
    user: User,
    *,
    signature_policy: str,
    equipment_id: int | None,
    reopen_ticket_id: int | None,
) -> tuple[LabWorkOrder, list[LabWorkOrder], dict | None]:
    """Núcleo compartido de reapertura: valida que la cohorte de cierre esté
    realmente cerrada, congela un LabWorkOrderRevision por miembro (snapshot
    inmutable -- histórico nunca se pierde) y regresa cada uno a draft con la
    política preserve/invalidate. Retira la revisión vigente de la
    FieldSheet del equipo si se indica. No hace commit ni toca el ticket --
    approve_reopen_ticket (mediado por ticket) y reopen_work_order_directly
    (Admin con autoridad directa, sin ticket artificial) terminan cada uno
    con su propia bitácora."""
    work_order, historical_group = _lock_historical_group(db, work_order_id)
    if work_order.status not in {"completed", "partially_closed"}:
        raise HTTPException(status_code=409, detail="OT_NOT_CLOSED")
    cohort = _signature_cohort(
        historical_group, work_order, include_completed=True
    )
    if not cohort or any(item.status not in {"completed", "partially_closed"} for item in cohort):
        raise HTTPException(status_code=409, detail="CLOSURE_COHORT_NOT_CLOSED")
    now = datetime.now(timezone.utc)
    preserve = signature_policy == "preserve"
    for item in cohort:
        db.add(
            LabWorkOrderRevision(
                work_order_id=item.id,
                revision_number=item.revision_number,
                reopen_ticket_id=reopen_ticket_id,
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
        item.reopen_ticket_id = reopen_ticket_id
        item.signature_preserved = preserve
        item.signature_required = not preserve
        if not preserve:
            item.signature_session_id = None
        # Fase 3: sin cambios aquí -- la distinción preserve/invalidate ya
        # gobierna correctamente qué ediciones invalidan la firma de
        # recepción (ver CRITICAL_GENERAL_FIELDS/CRITICAL_EQUIPMENT_FIELDS y
        # _member_signatures_preserved en lab_work_orders.py: con preserve,
        # sólo cambios estructurales -- p.ej. agregar equipo -- invalidan;
        # correcciones de datos ya existentes no). "draft" sigue siendo el
        # estado de reapertura para ambas políticas; _closable_status permite
        # completar directamente desde draft cuando la reapertura fue
        # preserve, igual que antes de esta fase.
        item.status = "draft"
        item.completed_at = None
        item.final_pdf = None
        item.final_pdf_sha256 = None
        item.final_pdf_generated_at = None

    retired_snapshot = None
    if equipment_id is not None:
        equipment = db.scalar(
            select(LabWorkOrderEquipment)
            .where(LabWorkOrderEquipment.id == equipment_id)
            .with_for_update()
        )
        if equipment is not None:
            retired = equipment.field_sheet
            _retire_current_field_sheet_revision(equipment)
            if retired is not None and retired.status == "completed":
                retired_snapshot = {
                    "retired_field_sheet_id": retired.id,
                    "retired_revision_number": retired.revision_number,
                }
    return work_order, cohort, retired_snapshot


def reopen_work_order_directly(
    db: Session, work_order_id: int, user: User, *, signature_policy: str, reason: str,
) -> LabWorkOrderRead:
    """Reapertura administrativa directa: el actor YA posee
    work_orders.reopen + la política correspondiente, así que ejecuta la
    reapertura en una sola llamada -- no crea ni pasa por un ticket
    artificial (misma autoridad, mismo núcleo _reopen_closed_cohort que ya
    usa el ticket mediado, sólo sin ticket ni segunda aprobación)."""
    required_permission = (
        "work_orders.reopen_preserve_signatures"
        if signature_policy == "preserve"
        else "work_orders.reopen_invalidate_signatures"
    )
    if not user_has_permission(user, "work_orders.reopen") or not user_has_permission(
        user, required_permission
    ):
        raise HTTPException(status_code=403, detail="REOPEN_NOT_AUTHORIZED")
    work_order, _cohort, _retired = _reopen_closed_cohort(
        db, work_order_id, user,
        signature_policy=signature_policy, equipment_id=None, reopen_ticket_id=None,
    )
    write_audit_log(
        db,
        action="lab_work_order.reopened_directly",
        entity="lab_work_orders",
        entity_id=work_order.id,
        user_id=user.id,
        previous_values={"status": "completed_or_partially_closed"},
        new_values={
            "status": "draft",
            "signature_policy": signature_policy,
            "reason": reason.strip(),
        },
    )
    _notify_work_order_owner(
        db, work_order, user,
        event="work_order.reopened",
        title="OT reabierta",
        body=f"OT {work_order.folio} fue reabierta. Motivo: {reason.strip()}",
    )
    commit_and_dispatch_notifications(db)
    return _read_work_order(db, _get(db, work_order.id))


def approve_reopen_ticket(
    db: Session, ticket_id: int, payload: TicketReview, user: User
) -> TicketRead:
    ticket = _get_ticket(db, ticket_id, lock=True)
    if ticket.status != "pending":
        raise HTTPException(status_code=409, detail="TICKET_ALREADY_RESOLVED")
    if ticket.requested_by_user_id == user.id:
        raise HTTPException(status_code=403, detail="TICKET_SELF_APPROVAL_FORBIDDEN")
    required_permission = (
        "work_orders.reopen_preserve_signatures"
        if payload.signature_policy == "preserve"
        else "work_orders.reopen_invalidate_signatures"
    )
    if not user_has_permission(user, "work_orders.reopen") or not user_has_permission(
        user, required_permission
    ):
        raise HTTPException(status_code=403, detail="REOPEN_NOT_AUTHORIZED")

    work_order, cohort, retired_snapshot = _reopen_closed_cohort(
        db, ticket.work_order_id, user,
        signature_policy=payload.signature_policy,
        equipment_id=ticket.equipment_id,
        reopen_ticket_id=ticket.id,
    )
    if retired_snapshot is not None:
        ticket.resolution_snapshot = retired_snapshot
    preserve = payload.signature_policy == "preserve"

    ticket.status = "in_progress"
    ticket.reviewed_by_user_id = user.id
    ticket.reviewed_at = datetime.now(timezone.utc)
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
            "root_work_order_id": work_order.root_work_order_id,
            "signature_session_id": work_order.signature_session_id,
            "work_order_ids": [item.id for item in cohort],
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
    if ticket.requested_by_user_id == user.id:
        raise HTTPException(status_code=403, detail="TICKET_SELF_APPROVAL_FORBIDDEN")
    ticket.status = "rejected"
    ticket.reviewed_by_user_id = user.id
    ticket.reviewed_at = datetime.now(timezone.utc)
    ticket.decision_comment = payload.comment.strip()
    if ticket.type == "manual_myc_folio" and ticket.equipment is not None:
        ticket.equipment.certificate_folio = ticket.equipment.automatic_certificate_folio
        ticket.equipment.folio_status = "reserved"
    write_audit_log(
        db,
        action="ticket.rejected",
        entity="operational_tickets",
        entity_id=ticket.id,
        user_id=user.id,
        previous_values={"status": "pending"},
        new_values={
            "status": "rejected",
            "automatic_folio_restored": (
                ticket.equipment.automatic_certificate_folio
                if ticket.type == "manual_myc_folio" and ticket.equipment is not None
                else None
            ),
        },
    )
    notify_ticket_rejected(db, ticket, user)
    commit_and_dispatch_notifications(db)
    return _read(_get_ticket(db, ticket.id))


def resolve_operational_ticket(
    db: Session, ticket_id: int, payload: TicketResolve, user: User
) -> TicketRead:
    ticket = _get_ticket(db, ticket_id, lock=True)
    if ticket.status != "pending":
        raise HTTPException(status_code=409, detail="TICKET_ALREADY_RESOLVED")
    if ticket.requested_by_user_id == user.id:
        raise HTTPException(status_code=403, detail="TICKET_SELF_APPROVAL_FORBIDDEN")
    now = datetime.now(timezone.utc)
    if ticket.type == "certificate_folio_block":
        myca = [
            _allocate_lab_certificate_folio(db, "MYCA")
            for _ in range(ticket.accredited_quantity or 0)
        ]
        myct = [
            _allocate_lab_certificate_folio(db, "MYCT")
            for _ in range(ticket.traceable_quantity or 0)
        ]
        ticket.resolution_snapshot = {"folios": {"MYCA": myca, "MYCT": myct}, "used": {}}
        action = "lab_certificate_block.approved"
    elif ticket.type in {"manual_myc_folio", "linked_folio"}:
        folio = (payload.authorized_folio or "").strip()
        if not folio:
            raise HTTPException(status_code=422, detail="El folio autorizado es obligatorio")
        duplicate = db.scalar(
            select(LabWorkOrderEquipment.id).where(
                LabWorkOrderEquipment.certificate_folio == folio,
                LabWorkOrderEquipment.id != ticket.equipment_id,
            )
        )
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="El folio ya está asignado a otro equipo LAB")
        equipment = db.scalar(
            select(LabWorkOrderEquipment)
            .where(LabWorkOrderEquipment.id == ticket.equipment_id)
            .with_for_update()
        )
        if equipment is None:
            raise HTTPException(status_code=409, detail="El equipo solicitado ya no está disponible")
        equipment.certificate_folio = folio
        equipment.folio_status = "authorized"
        equipment.folio_ticket_id = ticket.id
        ticket.authorized_folio = folio
        ticket.resolution_snapshot = {
            "automatic_folio_preserved": equipment.automatic_certificate_folio,
            "final_folio": folio,
            "linked_company_id": equipment.linked_company_id,
            "linked_company_name_snapshot": equipment.linked_company_name_snapshot,
        }
        action = "lab_folio.authorized"
    elif ticket.type == "partial_close":
        if ticket.work_order is None:
            raise HTTPException(status_code=409, detail="La OT ya no está disponible")
        work_order = _get(db, ticket.work_order.id, lock=True)
        missing = _missing_completed_sheets([work_order])
        work_order.partial_close_ticket_id = ticket.id
        work_order.partial_close_pending_snapshot = {"items": missing, "approved_at": now.isoformat()}
        ticket.resolution_snapshot = work_order.partial_close_pending_snapshot
        action = "lab_partial_close.approved"
    elif ticket.type == "field_sheet_reopen":
        equipment = db.scalar(
            select(LabWorkOrderEquipment)
            .where(LabWorkOrderEquipment.id == ticket.equipment_id)
            .with_for_update()
        )
        if equipment is None:
            raise HTTPException(status_code=409, detail="El equipo solicitado ya no está disponible")
        current = equipment.field_sheet
        if current is None or current.status != "completed":
            raise HTTPException(status_code=409, detail="La hoja ya no está completed; nada que reabrir")
        _retire_current_field_sheet_revision(equipment)
        # ready_to_close exige que TODO el equipo tenga hoja completed
        # (_missing_completed_sheets); al retirar una revisión ese invariante
        # deja de cumplirse, así que se re-deriva la misma regla que ya
        # produce ready_to_close hacia adelante -- no es un estado nuevo.
        if equipment.work_order.status == "ready_to_close":
            equipment.work_order.status = "in_progress"
        ticket.resolution_snapshot = {
            "retired_field_sheet_id": current.id,
            "retired_revision_number": current.revision_number,
        }
        action = "lab_field_sheet.reopen_approved"
    else:
        raise HTTPException(status_code=409, detail="La solicitud requiere el flujo específico de reapertura")
    ticket.status = "resolved"
    ticket.reviewed_by_user_id = user.id
    ticket.reviewed_at = now
    ticket.resolved_at = now
    ticket.decision_comment = payload.comment
    conversation = db.get(CommunicationConversation, ticket.conversation_id) if ticket.conversation_id else None
    if conversation is not None and all(item.id != user.id for item in conversation.participants):
        conversation.participants.append(user)
    write_audit_log(
        db,
        action=action,
        entity="operational_tickets",
        entity_id=ticket.id,
        user_id=user.id,
        previous_values={"status": "pending"},
        new_values={
            "status": "resolved",
            "authorized_folio": ticket.authorized_folio,
            "resolution_snapshot": ticket.resolution_snapshot,
        },
    )
    # Cierre UX 2026-09: faltaba notificar al solicitante y despachar
    # push/realtime -- este endpoint sólo hacía db.commit() plano, que deja
    # la fila Notification creada por _create() en la sesión sin nunca
    # dispatch-earla (commit_and_dispatch_notifications es la única función
    # que entrega push y publica el evento realtime, ver push_notifications.py).
    notify_ticket_resolved(db, ticket, user)
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
