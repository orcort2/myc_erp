from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.mobile.scope import ensure_lab_work_order_scope
from app.core.mobile.security import (
    MobileSecurityContext,
    require_internal_mobile_permission,
    require_mobile_permission,
)
from app.schemas.operational_ticket import (
    CertificateFolioBlockCreate,
    FieldSheetTemplateRequestCreate,
    FolioTicketCreate,
    PartialCloseTicketCreate,
    ReopenTicketCreate,
    TicketRead,
    TicketReject,
    TicketReview,
    TicketResolve,
)
from app.services.operational_tickets import (
    approve_reopen_ticket,
    create_certificate_block_ticket,
    create_field_sheet_template_request_ticket,
    create_folio_ticket,
    create_partial_close_ticket,
    create_reopen_ticket,
    get_ticket,
    list_tickets,
    reject_ticket,
    resolve_operational_ticket,
)


router = APIRouter(
    prefix="/mobile/v1/technician/tickets",
    tags=["mobile-operational-tickets"],
)


@router.post("", response_model=TicketRead, status_code=201)
def create_ticket(
    payload: ReopenTicketCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("mobile_tickets.create", "tickets.create")
    ),
) -> TicketRead:
    ensure_lab_work_order_scope(db, payload.work_order_id, context)
    return create_reopen_ticket(db, payload, context.user)


@router.post("/folio", response_model=TicketRead, status_code=201)
def create_folio_request(
    payload: FolioTicketCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("mobile_tickets.create", "tickets.create")
    ),
) -> TicketRead:
    ensure_lab_work_order_scope(db, payload.work_order_id, context)
    return create_folio_ticket(
        db, payload, context.user, operator_client_id=context.client_id
    )


@router.post("/partial-close", response_model=TicketRead, status_code=201)
def create_partial_close_request(
    payload: PartialCloseTicketCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("mobile_tickets.create", "tickets.create")
    ),
) -> TicketRead:
    ensure_lab_work_order_scope(db, payload.work_order_id, context)
    return create_partial_close_ticket(
        db, payload, context.user, operator_client_id=context.client_id
    )


@router.post("/field-sheet-template", response_model=TicketRead, status_code=201)
def create_field_sheet_template_request(
    payload: FieldSheetTemplateRequestCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("mobile_tickets.create", "tickets.create")
    ),
) -> TicketRead:
    ensure_lab_work_order_scope(db, payload.work_order_id, context)
    return create_field_sheet_template_request_ticket(
        db, payload, context.user, operator_client_id=context.client_id
    )


@router.post("/certificate-block", response_model=TicketRead, status_code=201)
def create_certificate_block_request(
    payload: CertificateFolioBlockCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("mobile_tickets.create", "tickets.create")
    ),
) -> TicketRead:
    return create_certificate_block_ticket(
        db, payload, context.user, operator_client_id=context.client_id
    )


@router.get("", response_model=list[TicketRead])
def get_tickets(
    status: Literal[
        "pending", "approved", "rejected", "in_progress", "resolved", "cancelled"
    ] | None = None,
    search: str | None = Query(default=None, max_length=255),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("mobile_tickets.read", "tickets.view_own")
    ),
) -> list[TicketRead]:
    return list_tickets(
        db,
        context.user,
        ticket_status=status,
        search=search,
        offset=offset,
        limit=limit,
        client_id=context.client_id,
    )


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket_detail(
    ticket_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("mobile_tickets.read", "tickets.view_own")
    ),
) -> TicketRead:
    ticket = get_ticket(db, ticket_id, context.user, client_id=context.client_id)
    return ticket


@router.post("/{ticket_id}/approve", response_model=TicketRead)
def approve_ticket(
    ticket_id: int,
    payload: TicketReview,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(require_internal_mobile_permission("tickets.review")),
) -> TicketRead:
    return approve_reopen_ticket(db, ticket_id, payload, context.user)


@router.post("/{ticket_id}/resolve", response_model=TicketRead)
def resolve_ticket(
    ticket_id: int,
    payload: TicketResolve,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_internal_mobile_permission("lab_folios.resolve")
    ),
) -> TicketRead:
    return resolve_operational_ticket(db, ticket_id, payload, context.user)


@router.post("/{ticket_id}/reject", response_model=TicketRead)
def reject_ticket_endpoint(
    ticket_id: int,
    payload: TicketReject,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(require_internal_mobile_permission("tickets.review")),
) -> TicketRead:
    return reject_ticket(db, ticket_id, payload, context.user)
