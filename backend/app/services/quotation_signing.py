"""Version-bound quotation email verification.

Internal service only. Public endpoints and electronic acceptance are
intentionally not exposed by this module.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.quotation import Quotation, QuotationSnapshot
from app.models.quotation_signing_challenge import QuotationSigningChallenge
from app.services.quotation_signing_authority import authorize_document_link
from app.services.audit_logs import write_audit_log
from app.services.email import send_email
from app.services.email.errors import EmailError
from app.services.email.transport import normalize_address
from app.services.quotation_signing_otp import (
    code_digest,
    expiry,
    generate_code,
    generate_nonce,
    is_usable,
    verify_code,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Expected timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _enabled(settings: Settings) -> None:
    if not settings.quotation_signing_enabled:
        raise HTTPException(
            status_code=503,
            detail="Mesa de Firmado MYC no habilitada",
        )
    if settings.uses_development_secret:
        raise HTTPException(
            status_code=503,
            detail="Se requiere una clave de firma segura",
        )


def _quotation(db: Session, quotation_id: int) -> Quotation:
    quotation = db.scalar(
        select(Quotation)
        .where(
            Quotation.id == quotation_id,
            Quotation.is_active.is_(True),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if quotation is None:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    if quotation.status not in {"sent", "waiting"}:
        raise HTTPException(
            status_code=409,
            detail="La cotización no está disponible para firmado",
        )
    if quotation.valid_until is not None and quotation.valid_until < _now().date():
        raise HTTPException(
            status_code=409,
            detail="La cotización ha vencido",
        )
    return quotation


def _snapshot(db: Session, quotation_id: int) -> QuotationSnapshot:
    snapshot = db.scalar(
        select(QuotationSnapshot)
        .where(QuotationSnapshot.quotation_id == quotation_id)
        .order_by(
            QuotationSnapshot.snapshot_number.desc(),
            QuotationSnapshot.id.desc(),
        )
        .limit(1)
    )
    if snapshot is None:
        raise HTTPException(
            status_code=409,
            detail="La cotización no tiene una versión registrada",
        )
    return snapshot


def _recipient(quotation: Quotation) -> str:
    contact = quotation.contact
    if (
        contact is None
        or contact.client_id != quotation.client_id
        or not contact.email
    ):
        raise HTTPException(
            status_code=409,
            detail="La cotización requiere un contacto autorizado con correo",
        )
    try:
        return normalize_address(contact.email)
    except EmailError as exc:
        raise HTTPException(
            status_code=409,
            detail="El correo del contacto no es válido",
        ) from exc


def request_signing_code(
    db: Session,
    quotation_id: int,
    *,
    settings: Settings | None = None,
    transport=None,
    signing_token: str | None = None,
) -> dict:
    """Persist challenge before SMTP; return metadata, never the OTP."""
    settings = settings or get_settings()
    _enabled(settings)

    quotation = _quotation(db, quotation_id)
    snapshot = _snapshot(db, quotation.id)
    recipient = _recipient(quotation)
    link_id = None
    if signing_token is not None:
        document, link = authorize_document_link(db, signing_token, settings=settings)
        if (document.quotation_id != quotation.id
            or document.snapshot_id != snapshot.id
            or link.recipient_email.lower() != recipient.lower()):
            raise HTTPException(status_code=404, detail="Enlace de firmado no disponible")
        link_id = link.id
    now = _now()

    previous = list(
        db.scalars(
            select(QuotationSigningChallenge)
            .where(
                QuotationSigningChallenge.quotation_id == quotation.id,
                QuotationSigningChallenge.revoked_at.is_(None),
                QuotationSigningChallenge.consumed_at.is_(None),
            )
            .with_for_update()
        ).all()
    )

    for challenge in previous:
        if (
            challenge.recipient_email.lower() == recipient.lower()
            and challenge.created_at is not None
            and now - _utc(challenge.created_at)
            < timedelta(seconds=settings.quotation_signing_otp_cooldown_seconds)
        ):
            raise HTTPException(
                status_code=429,
                detail="Espera antes de solicitar otro código",
            )

    for challenge in previous:
        challenge.revoked_at = now

    code = generate_code()
    nonce = generate_nonce()

    challenge = QuotationSigningChallenge(
        quotation_id=quotation.id,
        snapshot_id=snapshot.id,
        signing_link_id=link_id,
        recipient_email=recipient,
        code_hash=code_digest(
            code,
            nonce=nonce,
            secret_key=settings.secret_key,
        ),
        nonce=nonce,
        expires_at=expiry(
            settings.quotation_signing_otp_expire_minutes,
            now=now,
        ),
        attempts=0,
    )
    db.add(challenge)
    db.flush()

    write_audit_log(
        db,
        action="quotation.signing_otp.requested",
        entity="quotations",
        entity_id=quotation.id,
        user_id=None,
        new_values={
            "challenge_id": challenge.id,
            "snapshot_id": snapshot.id,
            "recipient_email": recipient,
        },
    )

    challenge_id = challenge.id
    folio = quotation.folio
    db.commit()

    # EmailService manages its own delivery transactions.
    # A transport failure never makes this challenge verified.
    try:
        result = send_email(
            db,
            template_key="quotation_signing_otp",
            context={
                "quotation_folio": folio,
                "otp_code": code,
                "expires_in": settings.quotation_signing_otp_expire_minutes,
            },
            to=[recipient],
            related_entity_type="quotation",
            related_entity_id=quotation_id,
            settings=settings,
            transport=transport,
        )
    except EmailError:
        _revoke(db, challenge_id)
        raise HTTPException(
            status_code=503,
            detail="No fue posible preparar el correo de verificación",
        ) from None

    if not result.sent:
        _revoke(db, challenge_id)
        raise HTTPException(
            status_code=503,
            detail="No fue posible enviar el código de verificación",
        )

    return {
        "challenge_id": challenge_id,
        "snapshot_id": snapshot.id,
        "expires_in_minutes": settings.quotation_signing_otp_expire_minutes,
    }


def _revoke(db: Session, challenge_id: int) -> None:
    challenge = db.scalar(
        select(QuotationSigningChallenge)
        .where(QuotationSigningChallenge.id == challenge_id)
        .with_for_update()
    )
    if challenge is not None and challenge.revoked_at is None:
        challenge.revoked_at = _now()
        db.commit()


def verify_signing_code(
    db: Session,
    quotation_id: int,
    challenge_id: int,
    code: str,
    *,
    settings: Settings | None = None,
    signing_token: str | None = None,
) -> bool:
    """Verify once under a quotation row lock; never consume acceptance."""
    settings = settings or get_settings()
    _enabled(settings)

    quotation = _quotation(db, quotation_id)
    snapshot = _snapshot(db, quotation.id)
    recipient = _recipient(quotation)

    challenge = db.scalar(
        select(QuotationSigningChallenge)
        .where(
            QuotationSigningChallenge.id == challenge_id,
            QuotationSigningChallenge.quotation_id == quotation.id,
        )
        .with_for_update()
    )

    if signing_token is not None:
        document, link = authorize_document_link(db, signing_token, settings=settings)
        if (challenge is None
            or challenge.signing_link_id != link.id
            or document.quotation_id != quotation.id
            or document.snapshot_id != snapshot.id
            or link.recipient_email.lower() != recipient.lower()):
            raise HTTPException(status_code=409, detail="Código no asociado al enlace vigente")

    now = _now()

    if (
        challenge is None
        or challenge.snapshot_id != snapshot.id
        or challenge.recipient_email.lower() != recipient.lower()
    ):
        raise HTTPException(
            status_code=409,
            detail="El desafío no corresponde a la cotización vigente",
        )

    if not is_usable(
        expires_at=_utc(challenge.expires_at),
        attempts=challenge.attempts,
        max_attempts=settings.quotation_signing_otp_max_attempts,
        verified_at=challenge.verified_at,
        consumed_at=challenge.consumed_at,
        revoked_at=challenge.revoked_at,
        now=now,
    ):
        raise HTTPException(
            status_code=409,
            detail="El código ya no está disponible",
        )

    challenge.attempts += 1

    valid = verify_code(
        code,
        expected_digest=challenge.code_hash,
        nonce=challenge.nonce,
        secret_key=settings.secret_key,
    )

    if valid:
        challenge.verified_at = now
        write_audit_log(
            db,
            action="quotation.signing_otp.verified",
            entity="quotations",
            entity_id=quotation.id,
            user_id=None,
            new_values={
                "challenge_id": challenge.id,
                "snapshot_id": snapshot.id,
            },
        )

    db.commit()
    return valid
