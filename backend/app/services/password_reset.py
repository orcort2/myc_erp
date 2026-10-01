"""Password recovery for internal ERP accounts (EMAIL-2).

Design notes
- The reset token is opaque (``secrets.token_urlsafe(48)``); only its SHA-256
  is persisted. The plain token exists in memory just long enough to build the
  email link and is never logged, audited or stored in EmailDelivery.
- Requests are anti-enumeration: callers always answer the same message. A
  persistent per-account cooldown limits spam; anonymous/IP rate limiting is
  NOT implemented here (gateway concern, see TECHNICAL_DEBT).
- The business transaction is committed before any SMTP work, which runs from
  a background task with its own session and can never roll the token back.
- Completing a reset bumps ``users.auth_version`` (kills every web JWT) and
  revokes Mobile sessions and biometric credentials. Trusted devices are kept.
"""

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import SessionLocal
from app.core.login_policy import as_utc, utc_now
from app.core.portal.constants import PortalAccountType, UserAccountStatus
from app.core.security import hash_password
from app.models.mobile_auth_session import MobileAuthSession
from app.models.mobile_biometric_credential import MobileBiometricCredential
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.audit_logs import write_audit_log
from app.services.email import send_email
from app.services.email.urls import resolve_public_base_url

logger = logging.getLogger(__name__)

REQUEST_MESSAGE = "Si existe una cuenta elegible, recibirás un correo con instrucciones."
RESET_DONE_MESSAGE = "Tu contraseña fue actualizada. Inicia sesión nuevamente."
INVALID_LINK_MESSAGE = "El enlace no es válido o expiró. Solicita uno nuevo."


@dataclass(frozen=True)
class PendingResetEmail:
    """In-memory handoff to the email step; the token never leaves the process."""

    user_id: int
    email: str
    full_name: str
    token_id: int
    expires_in_minutes: int
    token: str = field(repr=False)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def is_eligible(user: User | None) -> bool:
    return bool(
        user is not None
        and user.is_active
        and user.account_type == PortalAccountType.INTERNAL.value
        and user.status == UserAccountStatus.ACTIVE.value
    )


def _revoke_usable_tokens(db: Session, user_id: int, now: datetime, *, except_id: int | None = None) -> None:
    statement = update(PasswordResetToken).where(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.revoked_at.is_(None),
    )
    if except_id is not None:
        statement = statement.where(PasswordResetToken.id != except_id)
    db.execute(statement.values(revoked_at=now))


def request_password_reset(db: Session, email: str, settings: Settings | None = None) -> PendingResetEmail | None:
    """Create a fresh token for an eligible account, or return None silently."""
    settings = settings or get_settings()
    normalized = email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == normalized).with_for_update())
    if not is_eligible(user):
        db.rollback()
        return None
    now = utc_now()
    last_request = db.scalar(
        select(func.max(PasswordResetToken.created_at)).where(PasswordResetToken.user_id == user.id)
    )
    if last_request is not None and now - as_utc(last_request) < timedelta(seconds=settings.password_reset_cooldown_seconds):
        db.rollback()
        return None  # cooldown: indistinguishable from any other outcome

    _revoke_usable_tokens(db, user.id, now)
    token = secrets.token_urlsafe(48)
    record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(token),
        expires_at=now + timedelta(minutes=settings.password_reset_expire_minutes),
    )
    db.add(record)
    db.flush()
    write_audit_log(
        db,
        action="auth.password_reset.requested",
        entity="users",
        entity_id=user.id,
        user_id=None,
        new_values={"reset_token_id": record.id, "expires_at": record.expires_at.isoformat()},
    )
    pending = PendingResetEmail(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        token_id=record.id,
        expires_in_minutes=settings.password_reset_expire_minutes,
        token=token,
    )
    db.commit()
    return pending


def send_password_reset_email(pending: PendingResetEmail, settings: Settings | None = None) -> None:
    """Runs after the response (background task) with its own session."""
    settings = settings or get_settings()
    base_url = resolve_public_base_url(settings)
    if base_url is None:
        logger.error("PUBLIC_APP_BASE_URL no está configurado; no se envió el correo password_reset.")
        return
    # Fragment, not query: it never reaches the server, proxies or access logs.
    reset_url = f"{base_url}/reset-password#token={quote(pending.token, safe='')}"
    session = SessionLocal()
    try:
        send_email(
            session,
            template_key="password_reset",
            context={
                "recipient_name": pending.full_name,
                "reset_url": reset_url,
                "expires_in": f"{pending.expires_in_minutes} minutos",
            },
            to=[pending.email],
            related_entity_type="password_reset_token",
            related_entity_id=pending.token_id,
            settings=settings,
        )
    except Exception as exc:  # noqa: BLE001 - never surface SMTP/template errors or the URL
        logger.error("No se pudo enviar el correo password_reset: %s", type(exc).__name__)
    finally:
        session.close()


def _invalid_link() -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_LINK_MESSAGE)


def reset_password(db: Session, token: str, new_password: str) -> None:
    now = utc_now()
    record = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_reset_token(token)).with_for_update()
    )
    if (
        record is None
        or record.used_at is not None
        or record.revoked_at is not None
        or as_utc(record.expires_at) <= now
    ):
        db.rollback()
        raise _invalid_link()
    user = db.scalar(select(User).where(User.id == record.user_id).with_for_update())
    if not is_eligible(user):
        db.rollback()
        raise _invalid_link()

    # Atomic one-shot consumption: only one concurrent request can flip used_at.
    consumed = db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.id == record.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.revoked_at.is_(None),
        )
        .values(used_at=now)
    ).rowcount
    if consumed != 1:
        db.rollback()
        raise _invalid_link()

    user.hashed_password = hash_password(new_password)
    user.password_changed_at = now
    user.auth_version = (user.auth_version or 1) + 1
    user.failed_login_attempts = 0
    user.locked_until = None
    user.must_change_password = False
    _revoke_usable_tokens(db, user.id, now, except_id=record.id)

    mobile_sessions = db.execute(
        update(MobileAuthSession)
        .where(MobileAuthSession.user_id == user.id, MobileAuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    ).rowcount
    biometric = db.execute(
        update(MobileBiometricCredential)
        .where(MobileBiometricCredential.user_id == user.id, MobileBiometricCredential.revoked_at.is_(None))
        .values(revoked_at=now)
    ).rowcount
    write_audit_log(
        db,
        action="auth.password_reset.completed",
        entity="users",
        entity_id=user.id,
        user_id=user.id,
        new_values={"reset_token_id": record.id},
    )
    write_audit_log(
        db,
        action="auth.sessions.revoked",
        entity="users",
        entity_id=user.id,
        user_id=user.id,
        new_values={
            "reason": "password_reset",
            "auth_version": user.auth_version,
            "mobile_sessions_revoked": mobile_sessions,
            "biometric_credentials_revoked": biometric,
            "trusted_devices_revoked": 0,
        },
    )
    db.commit()
