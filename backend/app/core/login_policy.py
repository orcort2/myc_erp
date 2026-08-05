"""Política reutilizable de bloqueo temporal para identidades autenticables."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.audit_logs import write_audit_log


MAX_FAILED_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def is_temporarily_locked(user: User, *, now: datetime | None = None) -> bool:
    return bool(user.locked_until and as_utc(user.locked_until) > (now or utc_now()))


def register_failed_login(db: Session, user: User, *, auth_context: str) -> None:
    """Registra el fallo y fija un bloqueo determinista al alcanzar el umbral."""
    now = utc_now()
    if is_temporarily_locked(user, now=now):
        write_audit_log(
            db,
            action="auth.login_blocked",
            entity="users",
            entity_id=user.id,
            user_id=user.id,
            new_values={
                "auth_context": auth_context,
                "failed_login_attempts": user.failed_login_attempts,
                "locked_until": user.locked_until.isoformat(),
            },
            comment="Intento rechazado durante un bloqueo temporal vigente.",
        )
        db.commit()
        return
    if user.locked_until and as_utc(user.locked_until) <= now:
        user.failed_login_attempts = 0
        user.locked_until = None

    user.failed_login_attempts += 1
    locked = user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS
    if locked:
        user.locked_until = now + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)

    write_audit_log(
        db,
        action="auth.login_failed",
        entity="users",
        entity_id=user.id,
        user_id=user.id,
        new_values={
            "auth_context": auth_context,
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until.isoformat() if user.locked_until else None,
        },
        comment="Intento de autenticación fallido.",
    )
    db.commit()


def register_successful_login(db: Session, user: User, *, auth_context: str) -> None:
    now = utc_now()
    previous = {
        "failed_login_attempts": user.failed_login_attempts,
        "locked_until": user.locked_until.isoformat() if user.locked_until else None,
    }
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    write_audit_log(
        db,
        action="auth.login_succeeded",
        entity="users",
        entity_id=user.id,
        user_id=user.id,
        previous_values=previous,
        new_values={"auth_context": auth_context, "last_login_at": now.isoformat()},
        comment="Autenticación correcta.",
    )
    db.commit()
