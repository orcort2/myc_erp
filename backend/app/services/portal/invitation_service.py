import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.portal.constants import ClientPortalMembershipStatus, PortalInvitationStatus, UserAccountStatus
from app.core.security import verify_password
from app.models.client import Client
from app.models.client_portal import ClientPortal
from app.models.client_portal_membership import ClientPortalMembership
from app.models.client_portal_membership_role import ClientPortalMembershipRole
from app.models.client_portal_role import ClientPortalRole
from app.models.portal_invitation import PortalInvitation
from app.models.portal_invitation_role import PortalInvitationRole
from app.services.audit_logs import write_audit_log
from app.services.portal.account_service import create_portal_account, get_user_by_email
from app.services.portal.mail_service import send_invitation_email


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _get_by_token(db: Session, token: str) -> PortalInvitation:
    invitation = db.scalar(select(PortalInvitation).where(PortalInvitation.token_hash == _hash(token)).options(selectinload(PortalInvitation.client), selectinload(PortalInvitation.invitation_roles).selectinload(PortalInvitationRole.role)))
    now = datetime.now(timezone.utc)
    if invitation is None or invitation.status != PortalInvitationStatus.PENDING.value or not invitation.is_active:
        raise HTTPException(status_code=404, detail="Invitación no disponible")
    if _as_utc(invitation.expires_at) <= now:
        invitation.status = PortalInvitationStatus.EXPIRED.value
        db.commit()
        raise HTTPException(status_code=410, detail="La invitación expiró")
    return invitation


def serialize_invitation(invitation: PortalInvitation, token: str | None = None) -> dict:
    return {"id": invitation.id, "client_id": invitation.client_id, "email": invitation.email, "full_name": invitation.full_name, "status": invitation.status, "expires_at": invitation.expires_at, "role_codes": [item.role.code for item in invitation.invitation_roles], "invitation_url": f"/portal/invitacion/{token}" if token and settings.environment.lower() not in {"production", "prod"} else None, "notes": invitation.notes, "invited_by": invitation.invited_by, "invited_by_name": invitation.invited_by_user.full_name, "created_at": invitation.created_at, "accepted_at": invitation.accepted_at}


def create_invitation(db: Session, *, client_id: int, email: str, full_name: str | None, role_codes: list[str], notes: str | None, actor_id: int) -> dict:
    client = db.get(Client, client_id)
    if client is None or not client.is_active:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    configuration = db.scalar(select(ClientPortal).where(ClientPortal.client_id == client_id, ClientPortal.is_active.is_(True)))
    if configuration is not None and (not configuration.is_enabled or not configuration.allow_invitations):
        raise HTTPException(status_code=409, detail="Las invitaciones están deshabilitadas para este cliente")
    roles = list(db.scalars(select(ClientPortalRole).where(ClientPortalRole.code.in_(role_codes), ClientPortalRole.is_active.is_(True), (ClientPortalRole.client_id.is_(None)) | (ClientPortalRole.client_id == client_id))).all())
    if {r.code for r in roles} != set(role_codes):
        raise HTTPException(status_code=422, detail="Uno o más roles no son asignables al cliente")
    token = secrets.token_urlsafe(48)
    invitation = PortalInvitation(client_id=client_id, email=email.strip().lower(), full_name=full_name, invited_by=actor_id, status=PortalInvitationStatus.PENDING.value, token_hash=_hash(token), expires_at=datetime.now(timezone.utc) + timedelta(hours=72), notes=notes)
    db.add(invitation)
    db.flush()
    for role in roles:
        db.add(PortalInvitationRole(invitation_id=invitation.id, role_id=role.id))
    write_audit_log(db, action="portal.invitation.created", entity="portal_invitations", entity_id=invitation.id, user_id=actor_id, new_values={"client_id": client_id, "email": invitation.email, "role_codes": role_codes})
    db.commit()
    send_invitation_email(email=invitation.email, token=token)
    return serialize_invitation(_get_invitation(db, invitation.id), token)


def _get_invitation(db: Session, invitation_id: int) -> PortalInvitation:
    invitation = db.scalar(select(PortalInvitation).where(PortalInvitation.id == invitation_id).options(selectinload(PortalInvitation.invitation_roles).selectinload(PortalInvitationRole.role), selectinload(PortalInvitation.invited_by_user)))
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    return invitation


def list_invitations(db: Session, client_id: int | None = None) -> list[dict]:
    query = select(PortalInvitation).options(selectinload(PortalInvitation.invitation_roles).selectinload(PortalInvitationRole.role), selectinload(PortalInvitation.invited_by_user)).order_by(PortalInvitation.created_at.desc())
    if client_id is not None:
        query = query.where(PortalInvitation.client_id == client_id)
    return [serialize_invitation(item) for item in db.scalars(query).all()]


def cancel_invitation(db: Session, invitation_id: int, actor_id: int, *, revoke: bool = False) -> dict:
    invitation = _get_invitation(db, invitation_id)
    if invitation.status != PortalInvitationStatus.PENDING.value:
        raise HTTPException(status_code=409, detail="La invitación ya no está pendiente")
    now = datetime.now(timezone.utc)
    invitation.status = PortalInvitationStatus.REVOKED.value if revoke else PortalInvitationStatus.CANCELLED.value
    if revoke:
        invitation.revoked_at, invitation.revoked_by = now, actor_id
    else:
        invitation.cancelled_at, invitation.cancelled_by = now, actor_id
    write_audit_log(db, action="portal.invitation.revoked" if revoke else "portal.invitation.cancelled", entity="portal_invitations", entity_id=invitation.id, user_id=actor_id)
    db.commit()
    return serialize_invitation(_get_invitation(db, invitation.id))


def resend_invitation(db: Session, invitation_id: int, actor_id: int) -> dict:
    invitation = _get_invitation(db, invitation_id)
    if invitation.status != PortalInvitationStatus.PENDING.value:
        raise HTTPException(status_code=409, detail="Sólo se pueden reenviar invitaciones pendientes")
    token = secrets.token_urlsafe(48)
    invitation.token_hash = _hash(token)
    invitation.expires_at = datetime.now(timezone.utc) + timedelta(hours=72)
    write_audit_log(db, action="portal.invitation.resent", entity="portal_invitations", entity_id=invitation.id, user_id=actor_id, new_values={"expires_at": invitation.expires_at.isoformat()})
    db.commit()
    send_invitation_email(email=invitation.email, token=token)
    return serialize_invitation(_get_invitation(db, invitation.id), token)


def validate_invitation(db: Session, token: str) -> PortalInvitation:
    return _get_by_token(db, token)


def accept_invitation(db: Session, token: str, *, username: str, full_name: str, password: str) -> ClientPortalMembership:
    invitation = _get_by_token(db, token)
    user = get_user_by_email(db, invitation.email)
    if user is None:
        user = create_portal_account(db, username=username, email=invitation.email, full_name=full_name, password=password, initial_status=UserAccountStatus.ACTIVE, email_verified_at=datetime.now(timezone.utc), audit_comment="Cuenta creada al aceptar invitación del portal.")
    elif user.account_type != "client_portal" or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=409, detail="El correo ya pertenece a otra cuenta o la contraseña no coincide")
    existing = db.scalar(select(ClientPortalMembership).where(ClientPortalMembership.client_id == invitation.client_id, ClientPortalMembership.user_id == user.id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="La cuenta ya está vinculada con este cliente")
    membership = ClientPortalMembership(client_id=invitation.client_id, user_id=user.id, status=ClientPortalMembershipStatus.ACTIVE.value, approved_by=invitation.invited_by, approved_at=datetime.now(timezone.utc))
    db.add(membership)
    db.flush()
    for item in invitation.invitation_roles:
        db.add(ClientPortalMembershipRole(membership_id=membership.id, role_id=item.role_id))
    invitation.status = PortalInvitationStatus.ACCEPTED.value
    invitation.accepted_at = datetime.now(timezone.utc)
    invitation.accepted_user_id = user.id
    invitation.resulting_membership_id = membership.id
    write_audit_log(db, action="portal.invitation.accepted", entity="portal_invitations", entity_id=invitation.id, user_id=user.id, new_values={"membership_id": membership.id, "client_id": membership.client_id})
    db.commit()
    return membership
