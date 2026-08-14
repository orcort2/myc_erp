from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.operational_ticket import (
    ReopenTicketCreate,
    TicketRead,
    TicketReject,
    TicketReview,
)
from app.services.auth import require_permission
from app.services.operational_tickets import (
    approve_reopen_ticket,
    create_reopen_ticket,
    get_ticket,
    list_tickets,
    reject_ticket,
)


router = APIRouter(
    prefix="/mobile/v1/technician/tickets",
    tags=["mobile-operational-tickets"],
)


@router.post("", response_model=TicketRead, status_code=201)
def create_ticket(
    payload: ReopenTicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("tickets.create")),
) -> TicketRead:
    return create_reopen_ticket(db, payload, current_user)


@router.get("", response_model=list[TicketRead])
def get_tickets(
    status: Literal[
        "pending", "approved", "rejected", "in_progress", "resolved", "cancelled"
    ] | None = None,
    search: str | None = Query(default=None, max_length=255),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("tickets.view_own")),
) -> list[TicketRead]:
    return list_tickets(
        db,
        current_user,
        ticket_status=status,
        search=search,
        offset=offset,
        limit=limit,
    )


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket_detail(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("tickets.view_own")),
) -> TicketRead:
    return get_ticket(db, ticket_id, current_user)


@router.post("/{ticket_id}/approve", response_model=TicketRead)
def approve_ticket(
    ticket_id: int,
    payload: TicketReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("tickets.review")),
) -> TicketRead:
    return approve_reopen_ticket(db, ticket_id, payload, current_user)


@router.post("/{ticket_id}/reject", response_model=TicketRead)
def reject_ticket_endpoint(
    ticket_id: int,
    payload: TicketReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("tickets.review")),
) -> TicketRead:
    return reject_ticket(db, ticket_id, payload, current_user)
