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

Authority is the explicit Developer policy (``app.core.developer_policy``):
internal actor AND an exact Developer capability (the exact capability string,
e.g. ``developer.access``). ``"*"`` alone never opens Developer.

Invariants:
- A Developer token is only usable from the exact MobileAuthSession
  generation that opened it (same user, same trusted device, same
  ``mobile_session_id``). A Mobile refresh rotation or logout ends it.
- At most ONE non-revoked DeveloperSession per trusted device (therefore
  also per MobileAuthSession). Opening a new one supersedes the previous one
  (``revocation_reason = "superseded"``) under the same device row lock
  BIOMETRIC-1/2 already take, backed by the partial unique index
  ``uq_developer_sessions_active_device``.
- Every use re-validates live authority (mobile session, trusted device, user
  account, explicit Developer capability, internal actor) instead of trusting
  the claims captured when the session was opened; a newly-detected expiry or
  authority loss is lazily converted into a revocation so no separate sweeper
  job is needed.
- Future DEV-1+ operations must go through ``authorize_developer_operation`` /
  ``require_developer_session``: a live DeveloperSession AND the specific
  granular capability, never the client's ``isDeveloperUnlocked`` boolean.

See docs/architecture/MOBILE_DEVELOPER_AUTHORITY.md for the full threat
model, the DeveloperSession/MobileAuthSession/future-ShellSession
distinction and the LocalSystem/PowerShell invariant this authority exists
to eventually gate (NOT implemented in DEV-0).
"""

from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.developer_policy import (
    DEVELOPER_ACCESS,
    actor_has_developer_capability,
    user_has_developer_capability,
)
from app.core.login_policy import as_utc, utc_now
from app.core.mobile.biometric import resolve_biometric_credential
from app.core.mobile.developer_credentials import generate_developer_token, hash_developer_token
from app.core.mobile.security import MobileSecurityContext, _lock_device, get_mobile_context
from app.models.developer_session import DeveloperSession
from app.models.mobile_auth_session import MobileAuthSession
from app.models.mobile_trusted_device import MobileTrustedDevice
from app.models.user import User
from app.services.audit_logs import write_audit_log


# Canonical revocation reasons -- never free text from a caller.
REASON_EXPIRED = "expired"
REASON_USER_LOCK = "user_lock"
REASON_AUTHORITY_REVOKED = "authority_revoked"
REASON_SUPERSEDED = "superseded"

DEVELOPER_TOKEN_HEADER = "X-MYC-Developer-Token"


def _unauthorized(detail: str = "Sesión Developer inválida") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(
    detail: str = "Developer es exclusivo de staff MYC con capacidad Developer explícita",
) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _current_mobile_session(db: Session, context: MobileSecurityContext) -> MobileAuthSession:
    if context.mobile_session_id is None:
        raise _unauthorized("Se requiere una sesión Mobile vigente")
    session = db.get(MobileAuthSession, context.mobile_session_id)
    if session is None or session.user_id != context.user.id:
        raise _unauthorized("Se requiere una sesión Mobile vigente")
    return session


def _audit(db: Session, action: str, record: DeveloperSession, **extra: object) -> None:
    # Never the token, never the token_hash, never any credential.
    write_audit_log(
        db,
        action=action,
        entity="developer_session",
        entity_id=record.id,
        user_id=record.user_id,
        new_values={
            "device_id": record.device_id,
            "mobile_session_id": record.mobile_session_id,
            **extra,
        },
    )


def _audit_revocation(db: Session, record: DeveloperSession, **extra: object) -> None:
    reason = record.revocation_reason
    action = "developer_session.expired" if reason == REASON_EXPIRED else "developer_session.revoked"
    _audit(db, action, record, revocation_reason=reason, **extra)


def _mark_revoked(db: Session, record: DeveloperSession, reason: str, now: datetime) -> bool:
    """Conditional revocation: only the transaction that actually flips
    ``revoked_at`` from NULL wins. A concurrent supersede, lock or lazy
    expiry never double-revokes, double-audits or overwrites the winning
    reason."""
    result = db.execute(
        update(DeveloperSession)
        .where(DeveloperSession.id == record.id, DeveloperSession.revoked_at.is_(None))
        .values(revoked_at=now, revocation_reason=reason)
        .execution_options(synchronize_session=False)
    )
    db.refresh(record)
    return result.rowcount == 1


def _revoke(db: Session, record: DeveloperSession, reason: str, now: datetime) -> None:
    if _mark_revoked(db, record, reason, now):
        _audit_revocation(db, record)


def require_mobile_developer_capability(capability: str = DEVELOPER_ACCESS):
    """Route guard for Developer entry points that do not carry a
    DeveloperSession yet (i.e. opening one). Explicit policy, never ``"*"``."""

    def dependency(
        context: MobileSecurityContext = Depends(get_mobile_context),
    ) -> MobileSecurityContext:
        if not actor_has_developer_capability(context.actor_type, context.user, capability):
            raise _forbidden()
        return context

    return dependency


def _supersede_active(db: Session, device_id: int, now: datetime) -> list[DeveloperSession]:
    """Revokes every still-open DeveloperSession of this trusted device.
    The caller MUST already hold the device row lock (serializes concurrent
    opens). Audit is deferred to the caller, once the successor id exists."""
    rows = db.scalars(
        select(DeveloperSession)
        .where(DeveloperSession.device_id == device_id, DeveloperSession.revoked_at.is_(None))
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    return [
        row for row in rows
        if _mark_revoked(
            db, row, REASON_EXPIRED if as_utc(row.expires_at) <= now else REASON_SUPERSEDED, now
        )
    ]


def open_developer_session(
    db: Session, context: MobileSecurityContext, biometric_credential: str
) -> dict:
    """Unlock Developer for the current Mobile actor. Every check below must
    pass or no DeveloperSession is created -- see module docstring."""
    if not actor_has_developer_capability(context.actor_type, context.user):
        raise _forbidden()

    mobile_session = _current_mobile_session(db, context)
    # Lock order is the one BIOMETRIC-1/2 already use: trusted device FIRST
    # (then, inside resolve_biometric_credential, the biometric credential).
    # Held until commit, it serializes concurrent opens for this device and
    # also serializes against logout, which takes the same lock before
    # revoking the Mobile family.
    device = _lock_device(db, mobile_session.device_id)
    mobile_session = db.scalar(
        select(MobileAuthSession)
        .where(MobileAuthSession.id == mobile_session.id)
        .execution_options(populate_existing=True)
    )
    now = utc_now()
    if (
        device is None
        or device.user_id != context.user.id
        or not device.is_active
        or device.revoked_at is not None
        or mobile_session is None
        or mobile_session.revoked_at is not None
        or as_utc(mobile_session.expires_at) <= now
    ):
        raise _unauthorized("Se requiere una sesión Mobile vigente")

    resolved = resolve_biometric_credential(db, biometric_credential)

    # The identity/device this unlock authenticated as (the Mobile Bearer
    # context) must be the SAME one the biometric credential is bound to --
    # both are server-derived, never client-supplied, but they still must
    # agree with each other.
    if resolved.user.id != context.user.id or resolved.device.id != device.id:
        raise _unauthorized("Credencial biométrica inválida")

    now = utc_now()
    superseded = _supersede_active(db, device.id, now)

    token = generate_developer_token()
    expires_at = now + timedelta(minutes=settings.developer_session_expire_minutes)
    record = DeveloperSession(
        user_id=context.user.id,
        device_id=device.id,
        mobile_session_id=mobile_session.id,
        token_hash=hash_developer_token(token),
        last_used_at=now,
        expires_at=expires_at,
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError as exc:
        # Backstop only: uq_developer_sessions_active_device rejected a second
        # active row that escaped the device lock. Never leave two live.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Otra apertura Developer está en curso; inténtalo de nuevo",
        ) from exc

    for previous in superseded:
        _audit_revocation(db, previous, superseded_by_session_id=record.id)
    _audit(
        db,
        "developer_session.opened",
        record,
        superseded_session_ids=[item.id for item in superseded],
    )
    db.commit()
    return {"developer_token": token, "expires_at": expires_at, "session_id": record.id}


def _live_authority(db: Session, record: DeveloperSession) -> bool:
    """Re-derives the DeveloperSession's authority from current state --
    never from claims captured when it was issued."""
    now = utc_now()
    mobile_session = db.get(MobileAuthSession, record.mobile_session_id, populate_existing=True)
    if (
        mobile_session is None
        or mobile_session.user_id != record.user_id
        or mobile_session.device_id != record.device_id
        or mobile_session.actor_type != "internal"
        or mobile_session.revoked_at is not None
        or as_utc(mobile_session.expires_at) <= now
    ):
        return False
    device = db.get(MobileTrustedDevice, record.device_id, populate_existing=True)
    if device is None or not device.is_active or device.revoked_at is not None:
        return False
    return user_has_developer_capability(db.get(User, record.user_id, populate_existing=True))


def _check_live(db: Session, record: DeveloperSession) -> bool:
    """True while `record` is a live Developer authority. As a side effect,
    a newly-detected expiry or authority loss is lazily revoked (once) and
    audited, so callers never need a separate sweeper job."""
    if record.revoked_at is not None:
        return False
    now = utc_now()
    if as_utc(record.expires_at) <= now:
        _revoke(db, record, REASON_EXPIRED, now)
        db.commit()
        return False
    if not _live_authority(db, record):
        _revoke(db, record, REASON_AUTHORITY_REVOKED, now)
        db.commit()
        return False
    return True


def _bound_record(
    db: Session, context: MobileSecurityContext, developer_token: str
) -> DeveloperSession | None:
    """The DeveloperSession behind `developer_token`, ONLY if it belongs to
    the exact Mobile authority presenting it: same user, same trusted device
    AND same MobileAuthSession generation. A token replayed from another
    MobileAuthSession (even of the same user/device), another device or
    another identity resolves to None."""
    token_hash = hash_developer_token(developer_token)
    record = db.scalar(select(DeveloperSession).where(DeveloperSession.token_hash == token_hash))
    if record is None:
        return None
    mobile_session = _current_mobile_session(db, context)
    if (
        record.user_id != context.user.id
        or record.mobile_session_id != mobile_session.id
        or record.device_id != mobile_session.device_id
    ):
        return None
    return record


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
    forced logout) that belongs to the Mobile session, not to Developer.

    This leniency is exclusive to this status probe: privileged operations
    go through ``authorize_developer_operation`` and are REJECTED instead."""
    record = _bound_record(db, context, developer_token)
    if record is None or not _check_live(db, record):
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
    record = _bound_record(db, context, developer_token)
    if record is None or record.revoked_at is not None:
        return
    _revoke(db, record, REASON_USER_LOCK, utc_now())
    db.commit()


def authorize_developer_operation(
    db: Session, context: MobileSecurityContext, developer_token: str, capability: str
) -> DeveloperSession:
    """Canonical guard for every future privileged Developer operation
    (DEV-1+: database, shell, logs, services, git). Requires BOTH a live
    DeveloperSession bound to this exact Mobile authority AND the specific
    granular capability -- developer.access alone is not enough, and the
    client's isDeveloperUnlocked flag is never trusted. Unlike the status
    probe, an invalid/expired/foreign token is REJECTED (401)."""
    record = _bound_record(db, context, developer_token)
    if record is None or not _check_live(db, record):
        raise _unauthorized()
    if not actor_has_developer_capability(context.actor_type, context.user, capability):
        raise _forbidden("Capacidad Developer insuficiente")
    record.last_used_at = utc_now()
    db.flush()
    return record


def developer_token_header(
    x_myc_developer_token: str = Header(..., alias=DEVELOPER_TOKEN_HEADER),
) -> str:
    return x_myc_developer_token


def require_developer_session(capability: str):
    """FastAPI dependency form of ``authorize_developer_operation`` for
    DEV-1+ routes. Deliberately not mounted on any route in DEV-0."""

    def dependency(
        developer_token: str = Depends(developer_token_header),
        context: MobileSecurityContext = Depends(get_mobile_context),
        db: Session = Depends(get_db),
    ) -> DeveloperSession:
        return authorize_developer_operation(db, context, developer_token, capability)

    return dependency
