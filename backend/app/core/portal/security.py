"""Autenticación y autorización independientes del Portal del Cliente."""

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.portal.constants import ClientPortalMembershipStatus, PortalAccountType, UserAccountStatus
from app.core.login_policy import is_temporarily_locked, register_failed_login, register_successful_login
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models.client import Client
from app.models.client_portal import ClientPortal
from app.models.client_portal_membership import ClientPortalMembership
from app.models.client_portal_membership_role import ClientPortalMembershipRole
from app.models.client_portal_permission import ClientPortalPermission
from app.models.client_portal_role import ClientPortalRole
from app.models.client_portal_role_permission import ClientPortalRolePermission
from app.models.user import User

portal_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/portal/auth/login")


@dataclass(frozen=True, slots=True)
class PortalSecurityContext:
    user: User
    membership: ClientPortalMembership
    client: Client
    permissions: frozenset[str]


def _unauthorized(detail: str = "Credenciales inválidas") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def resolve_active_membership(db: Session, user_id: int, membership_id: int | None = None) -> ClientPortalMembership:
    query = select(ClientPortalMembership).where(
        ClientPortalMembership.user_id == user_id,
        ClientPortalMembership.status == ClientPortalMembershipStatus.ACTIVE.value,
    ).options(selectinload(ClientPortalMembership.client))
    if membership_id is not None:
        query = query.where(ClientPortalMembership.id == membership_id)
    memberships = list(db.scalars(query).all())
    if len(memberships) != 1:
        raise HTTPException(status_code=403, detail="La cuenta no tiene una membresía activa única")
    if not memberships[0].client.is_active:
        raise HTTPException(status_code=403, detail="El cliente vinculado no está activo")
    configuration = db.scalar(select(ClientPortal).where(ClientPortal.client_id == memberships[0].client_id, ClientPortal.is_active.is_(True)))
    if configuration is not None and not configuration.is_enabled:
        raise HTTPException(status_code=403, detail="El portal del cliente está deshabilitado")
    return memberships[0]


def resolve_permissions(db: Session, membership_id: int) -> frozenset[str]:
    values = db.scalars(
        select(ClientPortalPermission.code)
        .join(ClientPortalRolePermission, ClientPortalRolePermission.permission_id == ClientPortalPermission.id)
        .join(ClientPortalRole, ClientPortalRole.id == ClientPortalRolePermission.role_id)
        .join(ClientPortalMembershipRole, ClientPortalMembershipRole.role_id == ClientPortalRole.id)
        .where(
            ClientPortalMembershipRole.membership_id == membership_id,
            ClientPortalRole.is_active.is_(True),
            ClientPortalPermission.is_active.is_(True),
        )
    ).all()
    return frozenset(values)


def build_portal_tokens(user: User, membership: ClientPortalMembership, permissions: frozenset[str]) -> dict:
    claims = {"auth_context": "client_portal", "membership_id": membership.id, "client_id": membership.client_id}
    return {
        "access_token": create_access_token(str(user.id), extra_claims=claims),
        "refresh_token": create_refresh_token(str(user.id), extra_claims=claims),
        "token_type": "bearer",
        "expires_in": 60 * 60 * 8,
        "permissions": sorted(permissions),
    }


def authenticate_portal_user(db: Session, identifier: str, password: str) -> dict:
    normalized = identifier.strip().lower()
    user = db.scalar(select(User).where(or_(User.username == normalized, User.email == normalized)))
    now = datetime.now(timezone.utc)
    invalid = (
        user is None
        or user.account_type != PortalAccountType.CLIENT_PORTAL.value
        or user.status != UserAccountStatus.ACTIVE.value
        or not user.is_active
        or user.email_verified_at is None
        or (user is not None and is_temporarily_locked(user, now=now))
        or not verify_password(password, user.hashed_password)
    )
    if invalid:
        if user is not None and user.account_type == PortalAccountType.CLIENT_PORTAL.value:
            register_failed_login(db, user, auth_context="client_portal")
        raise _unauthorized()
    membership = resolve_active_membership(db, user.id)
    permissions = resolve_permissions(db, membership.id)
    if "portal.view" not in permissions:
        raise HTTPException(status_code=403, detail="La membresía no autoriza acceso al portal")
    register_successful_login(db, user, auth_context="client_portal")
    return build_portal_tokens(user, membership, permissions)


def resolve_portal_token(db: Session, token: str, *, token_type: str = "access") -> PortalSecurityContext:
    try:
        payload = decode_token(token)
        if payload.get("token_type") != token_type or payload.get("auth_context") != "client_portal":
            raise ValueError
        user_id = int(payload["sub"])
        membership_id = int(payload["membership_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _unauthorized("Token del portal inválido") from exc
    user = db.get(User, user_id)
    if user is None or user.account_type != PortalAccountType.CLIENT_PORTAL.value or user.status != UserAccountStatus.ACTIVE.value or not user.is_active:
        raise _unauthorized("Cuenta del portal no disponible")
    membership = resolve_active_membership(db, user_id, membership_id)
    return PortalSecurityContext(user, membership, membership.client, resolve_permissions(db, membership.id))


def get_portal_context(token: str = Depends(portal_oauth2_scheme), db: Session = Depends(get_db)) -> PortalSecurityContext:
    return resolve_portal_token(db, token)


def require_portal_permission(permission: str):
    def dependency(context: PortalSecurityContext = Depends(get_portal_context)) -> PortalSecurityContext:
        if permission not in context.permissions:
            raise HTTPException(status_code=403, detail="Permiso del portal insuficiente")
        return context
    return dependency


def refresh_portal_tokens(db: Session, token: str) -> dict:
    context = resolve_portal_token(db, token, token_type="refresh")
    return build_portal_tokens(context.user, context.membership, context.permissions)
