"""DEV-0: DeveloperSession authority.

A DeveloperSession is a short-lived (10 min, ``developer_session_expire_minutes``),
non-renewing privilege that unlocks Developer infrastructure tooling
(Developer Center, DB console, shell broker, logs, services, git -- most of
those still unimplemented, see DEV-1+) for an already-authenticated internal
Mobile actor.

It is issued only after re-proving the SAME real biometric credential
BIOMETRIC-2 already authors, via ``resolve_biometric_credential`` -- never a
boolean "Face ID passed" claim, and never a second biometric authority. A
DeveloperSession is never a substitute for, never extends, and never
survives the logout of, the underlying MobileAuthSession. device_id,
user_id and mobile_session_id are always derived server-side from the
Mobile Bearer token and the stored biometric credential -- never accepted
from the caller.

Every use re-validates live authority (mobile session, trusted device, user
account, developer.access permission, internal actor) instead of trusting
the claims captured when the session was opened; a newly-detected expiry or
authority loss is lazily converted into a revocation so no separate sweeper
job is needed.

See docs/architecture/MOBILE_DEVELOPER_AUTHORITY.md for the full threat
model, the DeveloperSession/MobileAuthSession/future-ShellSession
distinction and the LocalSystem/PowerShell invariant this authority exists
to eventually gate (NOT implemented in DEV-0).
"""

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.login_policy import as_utc, utc_now
from app.core.mobile.biometric import resolve_biometric_credential
from app.core.mobile.developer_credentials import generate_developer_token, hash_developer_token
from app.core.mobile.security import MobileSecurityContext
from app.core.portal.constants import PortalAccountType, UserAccountStatus
from app.models.developer_session import DeveloperSession
from app.models.mobile_auth_session import MobileAuthSession
from app.models.mobile_trusted_device import MobileTrustedDevice
from app.models.user import User
from app.services.audit_logs import write_audit_log
from app.services.auth import effective_user_permissions


def _unauthorized(detail: str = "Sesión Developer inválida") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _current_mobile_session(db: Session, context: MobileSecurityContext) -> MobileAuthSession:
    if context.mobile_session_id is None:
        raise _unauthorized("Se requiere una sesión Mobile vigente")
    session = db.get(MobileAuthSession, context.mobile_session_id)
    if session is None or session.user_id != context.user.id:
        raise _unauthorized("Se requiere una sesión Mobile vigente")
    return session


def _audit(db: Session, action: str, record: DeveloperSession) -> None:
    write_audit_log(
        db,
        action=action,
        entity="developer_session",
        entity_id=record.id,
        user_id=record.user_id,
        new_values={
            "device_id": record.device_id,
            "mobile_session_id": record.mobile_session_id,
        },
    )


def open_developer_session(
    db: Session, context: MobileSecurityContext, biometric_credential: str
) -> dict:
    """Unlock Developer for the current Mobile actor. Every check below must
    pass or no DeveloperSession is created -- see module docstring."""
    if context.actor_type != "internal":
        raise HTTPException(status_code=403, detail="Developer es exclusivo de staff MYC")

    mobile_session = _current_mobile_session(db, context)
    resolved = resolve_biometric_credential(db, biometric_credential)

    # The identity/device this unlock authenticated as (the Mobile Bearer
    # context) must be the SAME one the biometric credential is bound to --
    # both are server-derived, never client-supplied, but they still must
    # agree with each other.
    if resolved.user.id != context.user.id or resolved.device.id != mobile_session.device_id:
        raise _unauthorized("Credencial biométrica inválida")

    now = utc_now()
    token = generate_developer_token()
    expires_at = now + timedelta(minutes=settings.developer_session_expire_minutes)
    record = DeveloperSession(
        user_id=context.user.id,
        device_id=mobile_session.device_id,
        mobile_session_id=mobile_session.id,
        token_hash=hash_developer_token(token),
        last_used_at=now,
        expires_at=expires_at,
    )
    db.add(record)
    db.flush()
    _audit(db, "developer_session.opened", record)
    db.commit()
    return {"developer_token": token, "expires_at": expires_at, "session_id": record.id}


def _live_authority(db: Session, record: DeveloperSession) -> bool:
    """Re-derives the DeveloperSession's authority from current state --
    never from claims captured when it was issued."""
    now = utc_now()
    mobile_session = db.get(MobileAuthSession, record.mobile_session_id)
    if (
        mobile_session is None
        or mobile_session.revoked_at is not None
        or as_utc(mobile_session.expires_at) <= now
    ):
        return False
    device = db.get(MobileTrustedDevice, record.device_id, populate_existing=True)
    if device is None or not device.is_active or device.revoked_at is not None:
        return False
    user = db.scalar(
        select(User).where(User.id == record.user_id).options(selectinload(User.roles))
    )
    if user is None or not user.is_active or user.status != UserAccountStatus.ACTIVE.value:
        return False
    if user.account_type != PortalAccountType.INTERNAL.value:
        return False
    permissions = effective_user_permissions(user)
    return "*" in permissions or "developer.access" in permissions


def _check_live(db: Session, record: DeveloperSession) -> bool:
    """True while `record` is a live Developer authority. As a side effect,
    a newly-detected expiry or authority loss is lazily revoked (once) and
    audited, so callers never need a separate sweeper job."""
    if record.revoked_at is not None:
        return False
    now = utc_now()
    if as_utc(record.expires_at) <= now:
        record.revoked_at = now
        record.revocation_reason = "expired"
        _audit(db, "developer_session.expired", record)
        db.commit()
        return False
    if not _live_authority(db, record):
        record.revoked_at = now
        record.revocation_reason = "authority_revoked"
        _audit(db, "developer_session.revoked", record)
        db.commit()
        return False
    return True


def _resolve_token(db: Session, developer_token: str) -> DeveloperSession | None:
    token_hash = hash_developer_token(developer_token)
    return db.scalar(select(DeveloperSession).where(DeveloperSession.token_hash == token_hash))


_INACTIVE_STATUS = {
    "active": False,
    "expires_at": None,
    "remaining_seconds": None,
    "user_id": None,
    "device_id": None,
}


def developer_session_status(
    db: Session, context: MobileSecurityContext, developer_token: str
) -> dict:
    """Never raises for an invalid/expired/foreign token -- reports
    ``active: false`` instead, so a stale Developer token in a mobile
    client's memory never triggers generic 401 handling (session refresh,
    forced logout) that belongs to the Mobile session, not to Developer."""
    record = _resolve_token(db, developer_token)
    if (
        record is None
        or record.user_id != context.user.id
        or record.device_id != _current_mobile_session(db, context).device_id
        or not _check_live(db, record)
    ):
        return dict(_INACTIVE_STATUS)
    record.last_used_at = utc_now()
    db.commit()
    remaining = int((as_utc(record.expires_at) - utc_now()).total_seconds())
    return {
        "active": True,
        "expires_at": record.expires_at,
        "remaining_seconds": max(remaining, 0),
        "user_id": record.user_id,
        "device_id": record.device_id,
    }


def lock_developer_session(
    db: Session, context: MobileSecurityContext, developer_token: str
) -> None:
    """Revokes the caller's own DeveloperSession. Idempotent: a token that
    is missing, foreign, or already revoked/expired is a no-op, never an
    error -- closing Developer never touches Mobile login or biometry."""
    record = _resolve_token(db, developer_token)
    current_device_id = _current_mobile_session(db, context).device_id
    if record is None or record.user_id != context.user.id or record.device_id != current_device_id:
        return
    if record.revoked_at is None:
        record.revoked_at = utc_now()
        record.revocation_reason = "user_lock"
        _audit(db, "developer_session.revoked", record)
        db.commit()
