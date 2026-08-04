from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.portal.constants import ClientPortalMembershipStatus
from app.models.user import User
from app.schemas.portal.user import PortalLinkRequestCreate, PortalLinkRequestRead, PortalLinkRequestResolve, PortalMembershipCreate, PortalMembershipRead, PortalMembershipReason, PortalMembershipRolesUpdate
from app.schemas.portal.registration import PortalRegistrationRead
from app.services.auth import require_permission
from app.services.portal.membership_service import create_link_request, create_membership, list_link_requests, list_memberships, list_registrations, replace_roles, resolve_link_request, set_primary, update_status

router = APIRouter(prefix="/client-portal/memberships", tags=["client-portal-memberships"])
review_router = APIRouter(prefix="/client-portal", tags=["client-portal-registration-review"])


@router.get("", response_model=list[PortalMembershipRead])
def get_memberships(client_id: int | None = None, db: Session = Depends(get_db), _actor: User = Depends(require_permission("users.manage"))):
    return list_memberships(db, client_id)


@router.post("", response_model=PortalMembershipRead, status_code=201)
def post_membership(payload: PortalMembershipCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return create_membership(db, client_id=payload.client_id, user_id=payload.user_id, role_codes=payload.role_codes, primary=payload.is_primary_contact, actor_id=actor.id)


@router.patch("/{membership_id}/roles", response_model=PortalMembershipRead)
def patch_roles(membership_id: int, payload: PortalMembershipRolesUpdate, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return replace_roles(db, membership_id, payload.role_codes, actor.id)


@router.post("/{membership_id}/suspend", response_model=PortalMembershipRead)
def suspend(membership_id: int, payload: PortalMembershipReason, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return update_status(db, membership_id, ClientPortalMembershipStatus.SUSPENDED.value, actor.id, payload.reason)


@router.post("/{membership_id}/reactivate", response_model=PortalMembershipRead)
def reactivate(membership_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return update_status(db, membership_id, ClientPortalMembershipStatus.ACTIVE.value, actor.id, "Reactivación administrativa")


@router.post("/{membership_id}/revoke", response_model=PortalMembershipRead)
def revoke(membership_id: int, payload: PortalMembershipReason, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return update_status(db, membership_id, ClientPortalMembershipStatus.REVOKED.value, actor.id, payload.reason)


@router.post("/{membership_id}/primary", response_model=PortalMembershipRead)
def primary(membership_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return set_primary(db, membership_id, actor.id)


@review_router.get("/registrations", response_model=list[PortalRegistrationRead])
def get_registrations(db: Session = Depends(get_db), _actor: User = Depends(require_permission("users.manage"))):
    return list_registrations(db)


@review_router.get("/link-requests", response_model=list[PortalLinkRequestRead])
def get_link_requests(db: Session = Depends(get_db), _actor: User = Depends(require_permission("users.manage"))):
    return list_link_requests(db)


@review_router.post("/link-requests", response_model=PortalLinkRequestRead, status_code=201)
def post_link_request(payload: PortalLinkRequestCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return create_link_request(db, payload.registration_id, payload.client_id, payload.reason, actor.id)


@review_router.post("/link-requests/{request_id}/approve", response_model=PortalLinkRequestRead)
def approve_link_request(request_id: int, payload: PortalLinkRequestResolve, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return resolve_link_request(db, request_id, approve=True, reason=payload.reason, role_codes=payload.role_codes, actor_id=actor.id)


@review_router.post("/link-requests/{request_id}/reject", response_model=PortalLinkRequestRead)
def reject_link_request(request_id: int, payload: PortalLinkRequestResolve, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return resolve_link_request(db, request_id, approve=False, reason=payload.reason, role_codes=payload.role_codes, actor_id=actor.id)
