from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.login_policy import (
    is_temporarily_locked,
    register_failed_login,
    register_successful_login,
)
from app.core.portal.constants import PortalAccountType, UserAccountStatus
from app.core.portal.security import resolve_active_membership, resolve_permissions
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User
from app.services.auth import effective_user_permissions
from app.services.auth import resolve_access_token_user


mobile_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/mobile/v1/auth/login")


@dataclass(frozen=True, slots=True)
class MobileSecurityContext:
    user: User
    actor_type: Literal["internal", "client"]
    permissions: frozenset[str]
    client_id: int | None = None
    membership_id: int | None = None


def _unauthorized(detail: str = "Credenciales Mobile inválidas") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _active_user_by_identifier(db: Session, identifier: str) -> User | None:
    normalized = identifier.strip().lower()
    return db.scalar(
        select(User)
        .where(or_(User.username == normalized, User.email == normalized))
        .options(selectinload(User.roles))
    )


def _internal_context(user: User) -> MobileSecurityContext:
    return MobileSecurityContext(
        user=user,
        actor_type="internal",
        permissions=frozenset(effective_user_permissions(user)),
    )


def _client_context(db: Session, user: User, membership_id: int | None = None) -> MobileSecurityContext:
    membership = resolve_active_membership(
        db,
        user.id,
        membership_id,
        require_portal_enabled=False,
    )
    permissions = resolve_permissions(db, membership.id)
    return MobileSecurityContext(
        user=user,
        actor_type="client",
        permissions=permissions,
        client_id=membership.client_id,
        membership_id=membership.id,
    )


def _ensure_mobile_access(context: MobileSecurityContext) -> MobileSecurityContext:
    if "*" not in context.permissions and "mobile.access" not in context.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta no tiene acceso a MYC Mobile",
        )
    return context


def _token_response(context: MobileSecurityContext) -> dict:
    auth_context = (
        "mobile_internal" if context.actor_type == "internal" else "mobile_client"
    )
    claims: dict[str, object] = {
        "auth_context": auth_context,
        "actor_type": context.actor_type,
    }
    if context.actor_type == "client":
        claims.update(
            membership_id=context.membership_id,
            client_id=context.client_id,
        )
    return {
        "access_token": create_access_token(str(context.user.id), extra_claims=claims),
        "refresh_token": create_refresh_token(str(context.user.id), extra_claims=claims),
        "token_type": "bearer",
        "user": {
            "id": context.user.id,
            "email": context.user.email,
            "full_name": context.user.full_name,
            "is_active": context.user.is_active,
            "permissions": sorted(context.permissions),
            "actor_type": context.actor_type,
            "client_id": context.client_id,
            "membership_id": context.membership_id,
        },
    }


def authenticate_mobile_user(db: Session, identifier: str, password: str) -> dict:
    user = _active_user_by_identifier(db, identifier)
    if (
        user is None
        or not user.is_active
        or user.status != UserAccountStatus.ACTIVE.value
        or is_temporarily_locked(user)
        or not verify_password(password, user.hashed_password)
    ):
        if user is not None:
            register_failed_login(db, user, auth_context="mobile")
        raise _unauthorized()

    if user.account_type == PortalAccountType.INTERNAL.value:
        context = _internal_context(user)
    elif user.account_type == PortalAccountType.CLIENT_PORTAL.value:
        if user.email_verified_at is None:
            raise _unauthorized()
        context = _client_context(db, user)
    else:
        raise _unauthorized()

    context = _ensure_mobile_access(context)
    register_successful_login(
        db,
        user,
        auth_context=(
            "mobile_internal" if context.actor_type == "internal" else "mobile_client"
        ),
    )
    return _token_response(context)


def resolve_mobile_token(
    db: Session,
    token: str,
    *,
    token_type: str = "access",
) -> MobileSecurityContext:
    try:
        payload = decode_token(token)
        if payload.get("token_type") != token_type:
            raise ValueError
        auth_context = payload.get("auth_context")
        # Temporary compatibility for already-issued internal ERP sessions used
        # by previous MYC Mobile builds. Client actors always require the
        # dedicated mobile_client context and can never enter through this path.
        if auth_context not in {"internal", "mobile_internal", "mobile_client"}:
            raise ValueError
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _unauthorized("Token Mobile inválido") from exc

    user = db.scalar(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )
    if (
        user is None
        or not user.is_active
        or user.status != UserAccountStatus.ACTIVE.value
    ):
        raise _unauthorized("Cuenta Mobile no disponible")

    if auth_context in {"internal", "mobile_internal"}:
        if user.account_type != PortalAccountType.INTERNAL.value:
            raise _unauthorized("El token no corresponde a un actor interno")
        context = _internal_context(user)
    else:
        if user.account_type != PortalAccountType.CLIENT_PORTAL.value:
            raise _unauthorized("El token no corresponde a un actor cliente")
        try:
            membership_id = int(payload["membership_id"])
            claimed_client_id = int(payload["client_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise _unauthorized("Token Mobile client incompleto") from exc
        context = _client_context(db, user, membership_id)
        if context.client_id != claimed_client_id:
            raise _unauthorized("El scope organizacional del token ya no es válido")

    return _ensure_mobile_access(context)


def get_mobile_context(
    token: str = Depends(mobile_oauth2_scheme),
    db: Session = Depends(get_db),
) -> MobileSecurityContext:
    return resolve_mobile_token(db, token)


def refresh_mobile_tokens(db: Session, token: str) -> dict:
    return _token_response(resolve_mobile_token(db, token, token_type="refresh"))


def require_mobile_permission(permission: str, *internal_compatibility: str):
    accepted = {permission, *internal_compatibility}

    def dependency(
        context: MobileSecurityContext = Depends(get_mobile_context),
    ) -> MobileSecurityContext:
        if "*" in context.permissions or accepted.intersection(context.permissions):
            return context
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permiso Mobile insuficiente",
        )

    return dependency


def require_internal_mobile_permission(permission: str):
    def dependency(
        context: MobileSecurityContext = Depends(get_mobile_context),
    ) -> MobileSecurityContext:
        if context.actor_type != "internal":
            raise HTTPException(status_code=403, detail="Esta capacidad es exclusiva de staff MYC")
        if "*" in context.permissions or permission in context.permissions:
            return context
        prefix = permission.split(".", 1)[0]
        if f"{prefix}.*" in context.permissions:
            return context
        raise HTTPException(status_code=403, detail="Permiso Mobile insuficiente")

    return dependency


def get_communications_user(
    token: str = Depends(mobile_oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        auth_context = payload.get("auth_context", "internal")
    except (TypeError, ValueError) as exc:
        raise _unauthorized("Token de Comunicaciones inválido") from exc
    if auth_context == "internal":
        return resolve_access_token_user(db, token)
    context = resolve_mobile_token(db, token)
    if context.actor_type == "client" and not {
        "communications.view",
        "communications.create",
    }.intersection(context.permissions):
        raise HTTPException(status_code=403, detail="Comunicaciones no autorizadas")
    return context.user
