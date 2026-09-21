from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.db import get_db
from app.core.login_policy import as_utc, utc_now
from app.core.mobile.refresh_credentials import (
    LEGACY_REFRESH_DEADLINE, generate_refresh_credential, hash_refresh_credential,
    is_legacy_refresh_format, has_canonical_legacy_signature,
)
from app.models.mobile_auth_session import MobileAuthSession
from app.models.mobile_trusted_device import MobileTrustedDevice
from app.schemas.mobile_auth import MobileSecurityDeviceInput
from app.core.login_policy import (
    is_temporarily_locked,
    register_failed_login,
    register_successful_login,
)
from app.core.portal.constants import PortalAccountType, UserAccountStatus
from app.core.portal.security import resolve_active_membership, resolve_permissions
from app.core.security import (
    create_access_token,
    decode_token,
    verify_password,
)
from app.models.user import User
from app.services.auth import effective_user_permissions, user_can_resolve_own_lab_folios
from app.services.auth import resolve_access_token_user


mobile_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/mobile/v1/auth/login")


@dataclass(frozen=True, slots=True)
class MobileSecurityContext:
    user: User
    actor_type: Literal["internal", "client"]
    permissions: frozenset[str]
    client_id: int | None = None
    membership_id: int | None = None
    mobile_session_id: int | None = None


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


def _token_response(context: MobileSecurityContext, session: MobileAuthSession, credential: str) -> dict:
    auth_context = (
        "mobile_internal" if context.actor_type == "internal" else "mobile_client"
    )
    claims: dict[str, object] = {
        "auth_context": auth_context,
        "actor_type": context.actor_type,
        "mobile_session_id": session.id,
    }
    if context.actor_type == "client":
        claims.update(
            membership_id=context.membership_id,
            client_id=context.client_id,
        )
    return {
        "access_token": create_access_token(str(context.user.id), extra_claims=claims),
        "refresh_token": credential,
        "token_type": "bearer",
        "user": {
            "id": context.user.id,
            "email": context.user.email,
            "full_name": context.user.full_name,
            "is_active": context.user.is_active,
            "permissions": sorted(context.permissions),
            "can_resolve_own_lab_folios": context.actor_type == "internal" and user_can_resolve_own_lab_folios(context.user),
            "actor_type": context.actor_type,
            "client_id": context.client_id,
            "membership_id": context.membership_id,
        },
    }


def authenticate_mobile_user(
    db: Session, identifier: str, password: str, device: MobileSecurityDeviceInput,
) -> dict:
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
    _lock_user(db, user.id)
    trusted_device = _resolve_device(db, user.id, device)
    session, credential = _new_session(db, context, trusted_device)
    response = _token_response(context, session, credential)
    db.commit()
    return response


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

    context = _ensure_mobile_access(context)
    if "mobile_session_id" in payload:
        session_id = payload["mobile_session_id"]
        if type(session_id) is not int or auth_context not in {"mobile_internal", "mobile_client"}:
            raise _unauthorized()
        session = db.get(MobileAuthSession, session_id, populate_existing=True)
        if session is None or session.user_id != user.id:
            raise _unauthorized()
        device = db.get(MobileTrustedDevice, session.device_id, populate_existing=True)
        _validate_session(session, device)
        if (
            payload.get("actor_type") != session.actor_type
            or context.actor_type != session.actor_type
            or context.client_id != session.client_id
            or context.membership_id != session.membership_id
        ):
            raise _unauthorized()
        context = replace(context, mobile_session_id=session.id)
    return context


def get_mobile_context(
    token: str = Depends(mobile_oauth2_scheme),
    db: Session = Depends(get_db),
) -> MobileSecurityContext:
    return resolve_mobile_token(db, token)


def _lock_user(db: Session, user_id: int) -> None:
    # Serializes first-time device registration and legacy redemption across workers.
    # FOR NO KEY UPDATE remains compatible with the FK key-share lock acquired
    # when another transaction inserts a successor while holding the device lock.
    if db.scalar(select(User.id).where(User.id == user_id).with_for_update(key_share=True)) is None:
        raise _unauthorized()


def _lock_device(db: Session, device_id: int) -> MobileTrustedDevice | None:
    # Always device BEFORE generation: also serializes reuse against successor refresh
    # and logout, preventing a new generation from escaping family revocation.
    return db.scalar(select(MobileTrustedDevice).where(MobileTrustedDevice.id == device_id)
                     .with_for_update().execution_options(populate_existing=True))


def _resolve_device(db: Session, user_id: int, metadata: MobileSecurityDeviceInput) -> MobileTrustedDevice:
    device = db.scalar(select(MobileTrustedDevice).where(
        MobileTrustedDevice.user_id == user_id,
        MobileTrustedDevice.device_uuid == metadata.device_uuid,
    ).with_for_update().execution_options(populate_existing=True))
    now = utc_now()
    if device is None:
        device = MobileTrustedDevice(user_id=user_id, **metadata.model_dump(),
                                     trusted_at=now, last_seen_at=now)
        db.add(device)
        db.flush()
    elif not device.is_active or device.revoked_at is not None or device.platform != metadata.platform:
        raise _unauthorized()
    else:
        device.device_name = metadata.device_name
        device.app_version = metadata.app_version
        device.last_seen_at = now
    return device


def _new_session(
    db: Session, context: MobileSecurityContext, device: MobileTrustedDevice, *,
    predecessor: MobileAuthSession | None = None,
    legacy_hash: str | None = None, expires_at: datetime | None = None,
) -> tuple[MobileAuthSession, str]:
    credential = generate_refresh_credential()
    now = utc_now()
    session = MobileAuthSession(
        user_id=context.user.id, device_id=device.id,
        family_id=predecessor.family_id if predecessor else str(uuid4()),
        refresh_token_hash=hash_refresh_credential(credential),
        legacy_refresh_token_hash=legacy_hash,
        actor_type=context.actor_type, client_id=context.client_id,
        membership_id=context.membership_id, last_used_at=now,
        expires_at=(predecessor.expires_at if predecessor else expires_at)
        or now + timedelta(minutes=settings.refresh_token_expire_minutes),
    )
    db.add(session)
    db.flush()
    return session, credential


def _validate_session(session: MobileAuthSession, device: MobileTrustedDevice | None) -> None:
    if (session.revoked_at is not None or as_utc(session.expires_at) <= utc_now()
            or device is None or device.user_id != session.user_id
            or not device.is_active or device.revoked_at is not None):
        raise _unauthorized()


def _session_context(db: Session, session: MobileAuthSession) -> MobileSecurityContext:
    user = db.scalar(select(User).where(User.id == session.user_id).options(selectinload(User.roles)))
    if user is None or not user.is_active or user.status != UserAccountStatus.ACTIVE.value:
        raise _unauthorized()
    if session.actor_type == "internal" and user.account_type == PortalAccountType.INTERNAL.value:
        context = _internal_context(user)
    elif (session.actor_type == "client" and user.account_type == PortalAccountType.CLIENT_PORTAL.value
          and user.email_verified_at is not None):
        context = _client_context(db, user, session.membership_id)
    else:
        raise _unauthorized()
    if context.client_id != session.client_id or context.membership_id != session.membership_id:
        raise _unauthorized()
    return _ensure_mobile_access(context)


def _revoke_family(db: Session, session: MobileAuthSession, *, reuse: bool = False) -> None:
    now = utc_now()
    if reuse:
        session.reuse_detected_at = now
    db.execute(update(MobileAuthSession).where(
        MobileAuthSession.family_id == session.family_id,
        MobileAuthSession.revoked_at.is_(None),
    ).values(revoked_at=now))
    # Persist security effects even though the caller will return HTTP 401.
    db.commit()


def _migrate_legacy_refresh(db: Session, token: str, device: MobileSecurityDeviceInput) -> dict:
    # TEMPORARY: possession of a valid legacy JWT + UUID presented by this installation.
    # Historical JWTs cannot prove which installation originally obtained them.
    if utc_now() >= LEGACY_REFRESH_DEADLINE or not has_canonical_legacy_signature(token):
        raise _unauthorized()
    context = resolve_mobile_token(db, token, token_type="refresh")
    payload = decode_token(token)
    if "mobile_session_id" in payload or float(payload["exp"]) > LEGACY_REFRESH_DEADLINE.timestamp():
        raise _unauthorized()
    _lock_user(db, context.user.id)
    legacy_hash = hash_refresh_credential(token)
    consumed = db.scalar(select(MobileAuthSession).where(
        MobileAuthSession.legacy_refresh_token_hash == legacy_hash))
    if consumed is not None:
        _lock_device(db, consumed.device_id)
        _revoke_family(db, consumed, reuse=True)
        raise _unauthorized()
    trusted_device = _resolve_device(db, context.user.id, device)
    session, credential = _new_session(
        db, context, trusted_device, legacy_hash=legacy_hash,
        expires_at=datetime.fromtimestamp(float(payload["exp"]), tz=timezone.utc),
    )
    response = _token_response(context, session, credential)
    db.commit()
    return response


def refresh_mobile_tokens(
    db: Session, token: str, device: MobileSecurityDeviceInput | None = None,
) -> dict:
    legacy = is_legacy_refresh_format(token)
    if legacy != (device is not None):
        raise HTTPException(status_code=422, detail="device es obligatorio sólo para migración legacy")
    try:
        if legacy:
            return _migrate_legacy_refresh(db, token, device)
        token_hash = hash_refresh_credential(token)
        session = db.scalar(select(MobileAuthSession).where(MobileAuthSession.refresh_token_hash == token_hash))
        if session is None:
            raise _unauthorized()
        trusted_device = _lock_device(db, session.device_id)
        session = db.scalar(select(MobileAuthSession).where(MobileAuthSession.id == session.id)
                            .with_for_update().execution_options(populate_existing=True))
        if session is None:
            raise _unauthorized()
        if session.replaced_by_id is not None:
            _revoke_family(db, session, reuse=True)
            raise _unauthorized()
        _validate_session(session, trusted_device)
        context = _session_context(db, session)
        successor, credential = _new_session(db, context, trusted_device, predecessor=session)
        now = utc_now()
        session.revoked_at = now
        session.last_used_at = now
        session.replaced_by_id = successor.id
        trusted_device.last_seen_at = now
        response = _token_response(context, successor, credential)
        db.commit()
        return response
    except HTTPException as exc:
        db.rollback()
        raise _unauthorized() from exc


def logout_mobile_session(db: Session, context: MobileSecurityContext) -> None:
    if context.mobile_session_id is None:
        # Legacy clients must migrate first; never guess a session from a user id.
        raise _unauthorized()
    session = db.get(MobileAuthSession, context.mobile_session_id)
    if session is None or session.user_id != context.user.id:
        raise _unauthorized()
    _lock_device(db, session.device_id)
    _revoke_family(db, session)


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
