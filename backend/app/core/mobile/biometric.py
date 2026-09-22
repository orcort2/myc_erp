"""BIOMETRIC-2: enroll/exchange/revoke logic for device-bound biometric login.

A biometric credential unlocks the same MobileAuthSession machinery BIOMETRIC-1
already authored; it never becomes a second security authority. PushDevice is
never consulted here, and no device_uuid is ever accepted from the exchange
caller -- the trusted device always comes from the stored credential row.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.login_policy import as_utc, utc_now
from app.core.mobile.biometric_credentials import (
    generate_biometric_credential,
    hash_biometric_credential,
)
from app.core.mobile.security import (
    MobileSecurityContext,
    _client_context,
    _ensure_mobile_access,
    _internal_context,
    _lock_device,
    _new_session,
    _token_response,
)
from app.core.portal.constants import PortalAccountType, UserAccountStatus
from app.models.mobile_auth_session import MobileAuthSession
from app.models.mobile_biometric_credential import MobileBiometricCredential
from app.models.mobile_trusted_device import MobileTrustedDevice
from app.models.user import User


def _unauthorized(detail: str = "Credencial biométrica inválida") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _current_session_device_id(db: Session, context: MobileSecurityContext) -> int:
    if context.mobile_session_id is None:
        raise _unauthorized("Se requiere una sesión Mobile vigente")
    session = db.get(MobileAuthSession, context.mobile_session_id)
    if session is None or session.user_id != context.user.id:
        raise _unauthorized("Se requiere una sesión Mobile vigente")
    return session.device_id


def enroll_biometric_credential(db: Session, context: MobileSecurityContext) -> dict:
    device_id = _current_session_device_id(db, context)
    # Same lock BIOMETRIC-1 takes before creating a generation: held until
    # commit, it serializes two concurrent enrolls for this device so the
    # second only sees/revokes the first's row after it actually committed,
    # never racing an INSERT against another INSERT.
    device = _lock_device(db, device_id)
    if (
        device is None
        or device.user_id != context.user.id
        or not device.is_active
        or device.revoked_at is not None
    ):
        raise _unauthorized("Se requiere una sesión Mobile vigente")
    now = utc_now()
    # Replace, never stack: only one active biometric credential per user+device.
    db.execute(
        update(MobileBiometricCredential)
        .where(
            MobileBiometricCredential.user_id == context.user.id,
            MobileBiometricCredential.device_id == device_id,
            MobileBiometricCredential.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    credential = generate_biometric_credential()
    expires_at = now + timedelta(days=settings.mobile_biometric_credential_expire_days)
    record = MobileBiometricCredential(
        user_id=context.user.id,
        device_id=device_id,
        credential_hash=hash_biometric_credential(credential),
        last_used_at=now,
        expires_at=expires_at,
        password_changed_at_snapshot=context.user.password_changed_at,
    )
    db.add(record)
    db.commit()
    return {"biometric_credential": credential, "expires_at": expires_at}


def _password_changed_since_enrollment(user: User, record: MobileBiometricCredential) -> bool:
    if user.password_changed_at is None:
        return False
    if record.password_changed_at_snapshot is None:
        return True
    return as_utc(user.password_changed_at) > as_utc(record.password_changed_at_snapshot)


@dataclass(frozen=True, slots=True)
class ResolvedBiometricCredential:
    """A biometric credential resolved down to its bound device and user,
    fully validated -- but WITHOUT creating a new MobileAuthSession. Shared
    authority for BIOMETRIC-2 exchange and DEV-0 Developer unlock; there is
    still only one biometric authority, this just lets a second caller reuse
    its validation instead of re-deriving it (or worse, trusting client
    input) for a different purpose."""

    record: MobileBiometricCredential
    device: MobileTrustedDevice
    user: User


def resolve_biometric_credential(db: Session, credential: str) -> ResolvedBiometricCredential:
    credential_hash = hash_biometric_credential(credential)
    record = db.scalar(
        select(MobileBiometricCredential)
        .where(MobileBiometricCredential.credential_hash == credential_hash)
        .with_for_update()
    )
    if record is None:
        raise _unauthorized()

    now = utc_now()
    if record.revoked_at is not None or as_utc(record.expires_at) <= now:
        raise _unauthorized()

    device = db.get(MobileTrustedDevice, record.device_id, populate_existing=True)
    if device is None or not device.is_active or device.revoked_at is not None:
        raise _unauthorized()

    user = db.scalar(
        select(User).where(User.id == record.user_id).options(selectinload(User.roles))
    )
    if user is None or not user.is_active or user.status != UserAccountStatus.ACTIVE.value:
        raise _unauthorized("Cuenta Mobile no disponible")

    if _password_changed_since_enrollment(user, record):
        raise _unauthorized("La contraseña cambió; vuelve a activar el acceso biométrico")

    return ResolvedBiometricCredential(record=record, device=device, user=user)


def exchange_biometric_credential(db: Session, credential: str) -> dict:
    resolved = resolve_biometric_credential(db, credential)
    record, device, user = resolved.record, resolved.device, resolved.user

    if user.account_type == PortalAccountType.INTERNAL.value:
        context = _internal_context(user)
    elif user.account_type == PortalAccountType.CLIENT_PORTAL.value:
        if user.email_verified_at is None:
            raise _unauthorized()
        context = _client_context(db, user)
    else:
        raise _unauthorized()
    context = _ensure_mobile_access(context)

    session, session_credential = _new_session(db, context, device)
    record.last_used_at = utc_now()
    response = _token_response(context, session, session_credential)
    db.commit()
    return response


def revoke_biometric_credential(db: Session, context: MobileSecurityContext) -> None:
    device_id = _current_session_device_id(db, context)
    db.execute(
        update(MobileBiometricCredential)
        .where(
            MobileBiometricCredential.user_id == context.user.id,
            MobileBiometricCredential.device_id == device_id,
            MobileBiometricCredential.revoked_at.is_(None),
        )
        .values(revoked_at=utc_now())
    )
    db.commit()
