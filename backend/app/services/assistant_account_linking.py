"""MYC-ASSISTANT-1A: secure, revocable linking of a private Telegram identity
to an internal MYC user. Domain core only -- no Telegram, push, UI or AI.

Authority model:
- A link request is created by a trusted server-side caller (the future bot
  adapter). Creating it grants nothing.
- Approval is the ONLY way to create an ``AssistantAccountLink``. It requires
  the authenticated Mobile context (Bearer, server-derived) AND a real
  biometric credential re-proven through ``resolve_biometric_credential``
  (the same authority BIOMETRIC-2 / DEV-0 use). The approving user and the
  device are derived server-side and must agree; nothing the client says about
  "biometrics passed" is ever accepted.
- ``comparison_code`` is shown on both sides for a human to compare. It is
  never an input of any authorizing function.
- Everything not explicitly allowed is denied; callers see a uniform
  ``not_found`` for requests/links that are not theirs.

Transactions: every public write function OWNS its transaction (call it with a
clean session). A successful operation commits its domain change and audit row
atomically. A denial NEVER commits and NEVER audits: it only rolls the
transaction back (releasing locks). Any unexpected exception (deadlock, lock
timeout, integrity or audit failure) also rolls back and propagates. Reads
never write, commit or audit. Denials are recorded by the adapter (HTTP/bot,
not yet built) through ``record_link_denial``, in its own session from the
official factory -- never on the domain session.

Lock order (identical in every writer, to rule out deadlocks; each operation
takes only the locks it needs, always in this order):
trusted device -> biometric credential -> MYC user that owns/would own the link
-> link requests (ascending id) -> link rows (ascending id).
Waits are bounded by ``LOCK_TIMEOUT_MS`` (PostgreSQL ``SET LOCAL lock_timeout``).
Existence checks are not the safety net against two racing inserts: the
partial unique indexes plus IntegrityError handling are.

Comparison code: stored only while a request is pending (DB check), nulled on
every terminal transition, and exposed only through the identity-checked
``LinkRequestView`` readers.

Future password-based approval (dependency of MYC-ASSISTANT-1B, NOT implemented
here) must provide: real re-authentication of the account; the current user and
Mobile session; a short lifetime; single use; binding to the concrete request;
and invalidation on logout, password change or session revocation. It must be
a server-issued proof -- never a client boolean, the comparison code, an access
JWT or a Developer token.
"""

import functools
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.login_policy import as_utc, utc_now
from app.core.mobile.biometric import resolve_biometric_credential
from app.core.mobile.security import MobileSecurityContext, _lock_device
from app.core.portal.constants import PortalAccountType, UserAccountStatus
from app.models.assistant_account_link import AssistantAccountLink
from app.models.assistant_link_request import AssistantLinkRequest
from app.models.mobile_auth_session import MobileAuthSession
from app.models.user import User
from app.services.audit_logs import write_audit_log
from app.services.auth import user_has_permission

LINK_REQUEST_TTL = timedelta(minutes=5)
MAX_PENDING_PER_CANDIDATE = 3
ADMIN_REVOKE_PERMISSION = "users.manage"
LOCK_TIMEOUT_MS = 5000

logger = logging.getLogger(__name__)

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_EXPIRED = "expired"
STATUS_SUPERSEDED = "superseded"

LINK_ACTIVE = "active"
LINK_REVOKED = "revoked"

# Canonical revocation reasons -- never free text from a caller.
REVOKE_BY_USER = "user"
REVOKE_BY_ADMIN = "admin"

REQUEST_ENTITY = "assistant_link_request"
LINK_ENTITY = "assistant_account_link"


class AssistantLinkError(Exception):
    """Domain failure with a stable machine-readable ``code``."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class LinkRequestView:
    """Read model returned to the authorized adapters. ``comparison_code`` is
    present only while the request is effectively pending."""

    id: int
    public_id: str
    status: str
    comparison_code: str | None
    expires_at: datetime
    telegram_user_id: int
    telegram_chat_id: int
    candidate_user_id: int


def effective_status(request: AssistantLinkRequest, now: datetime | None = None) -> str:
    """Logical status: a pending request past ``expires_at`` is expired even
    if no write has settled the row yet."""
    if request.status == STATUS_PENDING and as_utc(request.expires_at) <= (now or utc_now()):
        return STATUS_EXPIRED
    return request.status


def _view(request: AssistantLinkRequest) -> LinkRequestView:
    status = effective_status(request)
    return LinkRequestView(
        id=request.id,
        public_id=request.public_id,
        status=status,
        comparison_code=request.comparison_code if status == STATUS_PENDING else None,
        expires_at=request.expires_at,
        telegram_user_id=request.telegram_user_id,
        telegram_chat_id=request.telegram_chat_id,
        candidate_user_id=request.candidate_user_id,
    )


def _as_int_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssistantLinkError("invalid_identity")
    return value


def _audit(db: Session, action: str, entity: str, entity_id: int | None, user_id: int | None, **values: object) -> None:
    # Never the comparison code, never a credential or token.
    write_audit_log(db, action=action, entity=entity, entity_id=entity_id, user_id=user_id, new_values=values or None)


def _deny(db: Session, code: str) -> AssistantLinkError:
    """Ends a denied operation: rolls the transaction back (never commits it,
    releases its locks). Auditing the denial is the adapter's job."""
    db.rollback()
    return AssistantLinkError(code)


def record_link_denial(
    *, action: str, code: str, entity: str = REQUEST_ENTITY, entity_id: int | None = None,
    user_id: int | None = None, session_factory=SessionLocal,
) -> bool:
    """For adapters: persists a denial audit in its own session/transaction.
    Never receives or touches the domain session, so it cannot confirm its
    pending changes. Best effort by design: an audit-store failure is logged
    (without data) and reported as False, never allowed to mask the denial."""
    try:
        with session_factory() as audit_db:
            _audit(audit_db, action, entity, entity_id, user_id, reason=code)
            audit_db.commit()
        return True
    except SQLAlchemyError:
        logger.warning("assistant link denial audit could not be persisted")
        return False


def _owns_transaction(function):
    """Writers own their transaction: roll back on every failed exit,
    including domain errors raised before ``_deny`` is reached.
    A rollback after an explicitly committed expiry does not undo it."""

    @functools.wraps(function)
    def wrapper(db, *args, **kwargs):
        try:
            return function(db, *args, **kwargs)
        except BaseException:
            db.rollback()
            raise

    return wrapper


def _bound_lock_wait(db: Session) -> None:
    """No writer may wait indefinitely on another transaction's locks."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text(f"SET LOCAL lock_timeout = {int(LOCK_TIMEOUT_MS)}"))


def _is_linkable(user: User | None) -> bool:
    return (
        user is not None
        and user.is_active
        and user.status == UserAccountStatus.ACTIVE.value
        and user.account_type == PortalAccountType.INTERNAL.value
    )


def _close(request: AssistantLinkRequest, status: str, now: datetime) -> None:
    """Terminal transition; the comparison code is sanitized with it."""
    request.status = status
    request.decided_at = now
    request.comparison_code = None


def _expire_if_due(db: Session, request: AssistantLinkRequest, now: datetime) -> bool:
    """Write-path only: the caller MUST hold the request's row lock."""
    if request.status == STATUS_PENDING and as_utc(request.expires_at) <= now:
        _close(request, STATUS_EXPIRED, now)
        _audit(db, "assistant_link.request_expired", REQUEST_ENTITY, request.id, None,
               candidate_user_id=request.candidate_user_id)
        return True
    return False


def _lock_user_row(db: Session, user_id: int) -> User | None:
    return db.scalar(
        select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
    )


def _lock_request(db: Session, request_id: int) -> AssistantLinkRequest | None:
    return db.scalar(
        select(AssistantLinkRequest).where(AssistantLinkRequest.id == request_id)
        .with_for_update().execution_options(populate_existing=True)
    )


def _lock_link(db: Session, link_id: int) -> AssistantAccountLink | None:
    return db.scalar(
        select(AssistantAccountLink).where(AssistantAccountLink.id == link_id)
        .with_for_update().execution_options(populate_existing=True)
    )


def _active_link_exists(db: Session, *, user_id: int, telegram_user_id: int, telegram_chat_id: int) -> bool:
    """Locks any matching active links (ascending id) while checking them; the
    partial unique indexes remain the final guard against a racing insert."""
    return db.scalars(
        select(AssistantAccountLink.id).where(
            AssistantAccountLink.status == LINK_ACTIVE,
            (AssistantAccountLink.user_id == user_id)
            | (AssistantAccountLink.telegram_user_id == telegram_user_id)
            | (AssistantAccountLink.telegram_chat_id == telegram_chat_id),
        ).order_by(AssistantAccountLink.id.asc()).with_for_update()
    ).first() is not None


@_owns_transaction
def create_link_request(
    db: Session, *, telegram_user_id: int, telegram_chat_id: int, candidate_user_id: int
) -> LinkRequestView:
    """Opens a 5-minute request. Telegram private chats have chat_id == user_id
    (both positive); anything else (groups, channels) is rejected."""
    telegram_user_id = _as_int_id(telegram_user_id)
    telegram_chat_id = _as_int_id(telegram_chat_id)
    candidate_user_id = _as_int_id(candidate_user_id)
    if telegram_chat_id != telegram_user_id:
        raise AssistantLinkError("invalid_identity")

    _bound_lock_wait(db)
    candidate = _lock_user_row(db, candidate_user_id)
    if not _is_linkable(candidate):
        raise _deny(db, "invalid_account")

    now = utc_now()
    open_requests = db.scalars(
        select(AssistantLinkRequest).where(
            AssistantLinkRequest.status == STATUS_PENDING,
            (AssistantLinkRequest.telegram_user_id == telegram_user_id)
            | (AssistantLinkRequest.candidate_user_id == candidate.id),
        ).order_by(AssistantLinkRequest.id.asc()).with_for_update().execution_options(populate_existing=True)
    ).all()
    # Same order as approve: user -> requests -> links.
    if _active_link_exists(db, user_id=candidate.id, telegram_user_id=telegram_user_id,
                           telegram_chat_id=telegram_chat_id):
        raise _deny(db, "already_linked")
    live_for_candidate = 0
    for item in open_requests:
        if _expire_if_due(db, item, now):
            continue
        if item.telegram_user_id == telegram_user_id:
            _close(item, STATUS_SUPERSEDED, now)
            _audit(db, "assistant_link.request_superseded", REQUEST_ENTITY, item.id, None,
                   candidate_user_id=item.candidate_user_id)
        elif item.candidate_user_id == candidate.id:
            live_for_candidate += 1
    if live_for_candidate >= MAX_PENDING_PER_CANDIDATE:
        raise _deny(db, "too_many_pending")
    db.flush()  # free the partial unique slot before inserting the successor

    request = AssistantLinkRequest(
        public_id=secrets.token_urlsafe(32),
        telegram_user_id=telegram_user_id,
        telegram_chat_id=telegram_chat_id,
        candidate_user_id=candidate.id,
        status=STATUS_PENDING,
        comparison_code=f"{secrets.randbelow(1_000_000):06d}",
        expires_at=now + LINK_REQUEST_TTL,
    )
    db.add(request)
    try:
        db.flush()
    except IntegrityError as exc:
        raise _deny(db, "conflict") from exc
    _audit(db, "assistant_link.request_created", REQUEST_ENTITY, request.id, None,
           candidate_user_id=candidate.id, telegram_user_id=telegram_user_id,
           expires_at=request.expires_at.isoformat())
    db.commit()
    return _view(request)


def _get_request(db: Session, public_id: str) -> AssistantLinkRequest | None:
    if not isinstance(public_id, str) or not public_id:
        return None
    return db.scalar(
        select(AssistantLinkRequest).where(AssistantLinkRequest.public_id == public_id)
        .execution_options(populate_existing=True)
    )


def get_request_for_candidate(db: Session, *, public_id: str, user: User) -> LinkRequestView:
    """Pure read. Only the candidate MYC user may see a request (and its code)."""
    request = _get_request(db, public_id)
    if request is None or request.candidate_user_id != user.id:
        raise AssistantLinkError("not_found")
    return _view(request)


def get_request_for_telegram(
    db: Session, *, public_id: str, telegram_user_id: int, telegram_chat_id: int
) -> LinkRequestView:
    """Pure read. Only the originating private Telegram identity may see its request."""
    request = _get_request(db, public_id)
    if (request is None or request.telegram_user_id != telegram_user_id
            or request.telegram_chat_id != telegram_chat_id):
        raise AssistantLinkError("not_found")
    return _view(request)


def _live_mobile_device_id(db: Session, context: MobileSecurityContext) -> int:
    """Device of the caller's current Mobile session, derived server-side."""
    if context.actor_type != "internal" or context.mobile_session_id is None:
        raise AssistantLinkError("forbidden")
    session = db.get(MobileAuthSession, context.mobile_session_id, populate_existing=True)
    if (session is None or session.user_id != context.user.id or session.revoked_at is not None
            or as_utc(session.expires_at) <= utc_now()):
        raise AssistantLinkError("forbidden")
    return session.device_id


@_owns_transaction
def approve_link_request(
    db: Session, *, public_id: str, context: MobileSecurityContext, biometric_credential: str
) -> AssistantAccountLink:
    """Approves a request and creates the active link.

    Reinforced authentication is mandatory: ``biometric_credential`` is the
    opaque credential issued by BIOMETRIC-2, validated server-side. There is
    deliberately no flag, code or boolean parameter that could stand in for it.
    """
    if not isinstance(biometric_credential, str) or not biometric_credential:
        raise AssistantLinkError("strong_auth_required")
    device_id = _live_mobile_device_id(db, context)
    actor_id = context.user.id

    request = _get_request(db, public_id)  # unlocked: only to locate the row
    if request is None or request.candidate_user_id != actor_id:
        raise _deny(db, "not_found")
    request_id = request.id

    def deny(code: str) -> AssistantLinkError:
        return _deny(db, code)

    _bound_lock_wait(db)
    # 1. trusted device
    device = _lock_device(db, device_id)
    if device is None or device.user_id != actor_id or not device.is_active or device.revoked_at is not None:
        raise deny("forbidden")
    try:
        live_device_id = _live_mobile_device_id(db, context)  # re-check under the device lock
    except AssistantLinkError:
        live_device_id = None
    if live_device_id != device.id:
        raise deny("forbidden")
    # 2. biometric credential
    try:
        resolved = resolve_biometric_credential(db, biometric_credential)
    except HTTPException:
        raise deny("strong_auth_failed") from None
    if resolved.user.id != actor_id or resolved.device.id != device.id:
        raise deny("strong_auth_failed")
    # 3. candidate user
    candidate = _lock_user_row(db, actor_id)
    if not _is_linkable(candidate):
        raise deny("invalid_account")
    # 4. the request, re-verified under its lock
    request = _lock_request(db, request_id)
    if request is None or request.candidate_user_id != actor_id:
        raise deny("not_found")
    now = utc_now()
    if _expire_if_due(db, request, now):
        db.commit()  # persists only the expiry transition and its audit
        raise AssistantLinkError("expired")
    if request.status != STATUS_PENDING:
        raise deny("not_pending")
    # 5. active links
    if _active_link_exists(db, user_id=candidate.id, telegram_user_id=request.telegram_user_id,
                           telegram_chat_id=request.telegram_chat_id):
        raise deny("already_linked")

    telegram_user_id = request.telegram_user_id
    _close(request, STATUS_APPROVED, now)
    request.approved_by_user_id = actor_id
    request.approved_device_id = device.id
    link = AssistantAccountLink(
        user_id=candidate.id,
        telegram_user_id=telegram_user_id,
        telegram_chat_id=request.telegram_chat_id,
        link_request_id=request.id,
        status=LINK_ACTIVE,
        linked_at=now,
    )
    db.add(link)
    try:
        db.flush()
    except IntegrityError:
        raise deny("already_linked") from None
    _audit(db, "assistant_link.approved", REQUEST_ENTITY, request.id, actor_id,
           link_id=link.id, device_id=device.id, telegram_user_id=telegram_user_id)
    _audit(db, "assistant_link.created", LINK_ENTITY, link.id, actor_id,
           request_id=request.id, telegram_user_id=telegram_user_id)
    db.commit()
    return link


@_owns_transaction
def reject_link_request(db: Session, *, public_id: str, context: MobileSecurityContext) -> LinkRequestView:
    """Rejection only ever reduces access, so it needs the authenticated
    candidate but not a biometric re-proof."""
    if context.actor_type != "internal":
        raise AssistantLinkError("forbidden")
    actor_id = context.user.id
    request = _get_request(db, public_id)  # unlocked: only to locate the row
    if request is None or request.candidate_user_id != actor_id:
        raise _deny(db, "not_found")
    request_id = request.id
    _bound_lock_wait(db)
    if _lock_user_row(db, actor_id) is None:  # user before request, as everywhere
        raise _deny(db, "not_found")
    request = _lock_request(db, request_id)
    if request is None or request.candidate_user_id != actor_id:
        raise _deny(db, "not_found")
    now = utc_now()
    if _expire_if_due(db, request, now):
        db.commit()
        raise AssistantLinkError("expired")
    if request.status != STATUS_PENDING:
        raise _deny(db, "not_pending")
    _close(request, STATUS_REJECTED, now)
    _audit(db, "assistant_link.rejected", REQUEST_ENTITY, request.id, actor_id,
           telegram_user_id=request.telegram_user_id)
    db.commit()
    return _view(request)


@_owns_transaction
def revoke_link(db: Session, *, link_id: int, actor: User) -> AssistantAccountLink:
    """The link owner, or an actor holding ``users.manage`` (existing
    permission system, unchanged), may revoke -- in both cases only from an
    active internal account. Anyone else sees ``not_found``. ``actor`` must be
    the authenticated principal supplied by the (future) adapter, never an
    identifier taken from the request body.

    Lock order: owner user -> link, then everything is re-verified under lock."""
    if not _is_linkable(actor):
        raise AssistantLinkError("not_found")
    actor_id = actor.id
    peek = db.scalar(select(AssistantAccountLink.user_id).where(AssistantAccountLink.id == link_id))
    if peek is None:  # unlocked read, only to learn whose user row to lock first
        raise _deny(db, "not_found")
    _bound_lock_wait(db)
    _lock_user_row(db, peek)
    link = _lock_link(db, link_id)
    if link is None or link.user_id != peek:
        raise _deny(db, "not_found")
    actor = db.get(User, actor_id, populate_existing=True)
    if not _is_linkable(actor):
        raise _deny(db, "not_found")
    is_owner = actor_id == link.user_id
    is_admin = user_has_permission(actor, ADMIN_REVOKE_PERMISSION)
    if not (is_owner or is_admin):
        raise _deny(db, "not_found")
    if link.status != LINK_ACTIVE:
        raise _deny(db, "not_active")
    link.status = LINK_REVOKED
    link.revoked_at = utc_now()
    link.revoked_by_user_id = actor_id
    link.revocation_reason = REVOKE_BY_USER if is_owner else REVOKE_BY_ADMIN
    _audit(db, "assistant_link.revoked", LINK_ENTITY, link.id, actor_id,
           link_user_id=link.user_id, telegram_user_id=link.telegram_user_id,
           revocation_reason=link.revocation_reason)
    db.commit()
    return link


def get_active_link_for_user(db: Session, *, user: User) -> AssistantAccountLink | None:
    return db.scalar(select(AssistantAccountLink).where(
        AssistantAccountLink.user_id == user.id, AssistantAccountLink.status == LINK_ACTIVE))


def resolve_active_link(db: Session, *, telegram_user_id: int, telegram_chat_id: int) -> AssistantAccountLink | None:
    """Deny-by-default lookup for the future bot: an active link counts only
    while the MYC account is still active and internal."""
    link = db.scalar(select(AssistantAccountLink).where(
        AssistantAccountLink.telegram_user_id == telegram_user_id,
        AssistantAccountLink.telegram_chat_id == telegram_chat_id,
        AssistantAccountLink.status == LINK_ACTIVE,
    ))
    if link is None or not _is_linkable(db.get(User, link.user_id)):
        return None
    return link
