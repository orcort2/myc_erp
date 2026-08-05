from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.portal.invitation import PortalInvitationAccept, PortalInvitationAccepted, PortalInvitationCreate, PortalInvitationRead, PortalInvitationValidate
from app.services.auth import require_permission
from app.services.portal.invitation_service import accept_invitation, cancel_invitation, create_invitation, list_invitations, resend_invitation, validate_invitation

admin_router = APIRouter(prefix="/client-portal/invitations", tags=["client-portal-invitations"])
public_router = APIRouter(prefix="/portal/invitations", tags=["portal-invitations-public"])


@admin_router.post("", response_model=PortalInvitationRead, status_code=201)
def post_invitation(payload: PortalInvitationCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return create_invitation(db, client_id=payload.client_id, email=str(payload.email), full_name=payload.full_name, role_codes=payload.role_codes, notes=payload.notes, actor_id=actor.id)


@admin_router.get("", response_model=list[PortalInvitationRead])
def get_invitations(client_id: int | None = None, db: Session = Depends(get_db), _actor: User = Depends(require_permission("users.manage"))):
    return list_invitations(db, client_id)


@admin_router.post("/{invitation_id}/cancel", response_model=PortalInvitationRead)
def post_cancel(invitation_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return cancel_invitation(db, invitation_id, actor.id)


@admin_router.post("/{invitation_id}/revoke", response_model=PortalInvitationRead)
def post_revoke(invitation_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return cancel_invitation(db, invitation_id, actor.id, revoke=True)


@admin_router.post("/{invitation_id}/resend", response_model=PortalInvitationRead)
def post_resend(invitation_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return resend_invitation(db, invitation_id, actor.id)


@public_router.get("/{token}", response_model=PortalInvitationValidate)
def get_invitation(token: str, db: Session = Depends(get_db)):
    item = validate_invitation(db, token)
    return PortalInvitationValidate(email=item.email, full_name=item.full_name, client_name=item.client.commercial_name or item.client.legal_name, role_names=[link.role.name for link in item.invitation_roles], expires_at=item.expires_at)


@public_router.post("/{token}/accept", response_model=PortalInvitationAccepted, status_code=status.HTTP_201_CREATED)
def post_accept(token: str, payload: PortalInvitationAccept, db: Session = Depends(get_db)):
    membership = accept_invitation(db, token, username=payload.username, full_name=payload.full_name, password=payload.password)
    return PortalInvitationAccepted(user_id=membership.user_id, membership_id=membership.id, client_id=membership.client_id, message="Invitación aceptada. Ya puedes iniciar sesión en el portal.")
