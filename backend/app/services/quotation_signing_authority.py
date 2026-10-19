"""Persistent authorization for frozen quotation signing documents."""

from datetime import datetime, timezone, timedelta
from app.models.email import EmailDelivery
from hashlib import sha256

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.quotation import Quotation, QuotationSnapshot
from app.models.quotation_signing_document import (
    QuotationSigningDocument,
    QuotationSigningLink,
)
from app.services.quotation_signing_snapshot import snapshot_digest
from app.services.quotation_signing_links import (
    SigningLinkError,
    issue_signing_link,
    verify_signing_link,
)


def _now():
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite naive UTC datetimes and PostgreSQL aware datetimes."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _deny():
    raise HTTPException(
        status_code=404,
        detail="Enlace de firmado no disponible",
    )


def _enabled(settings):
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


def _latest_snapshot(db, quotation_id):
    return db.scalar(
        select(QuotationSnapshot)
        .where(QuotationSnapshot.quotation_id == quotation_id)
        .order_by(
            QuotationSnapshot.snapshot_number.desc(),
            QuotationSnapshot.id.desc(),
        )
        .limit(1)
    )


def freeze_document(
    db: Session,
    *,
    quotation_id: int,
    snapshot_id: int,
    pdf_bytes: bytes,
    filename: str,
    settings: Settings | None = None,
    staged: bool = False,
):
    """Persist the exact PDF bytes, refusing silent replacement."""
    settings = settings or get_settings()
    _enabled(settings)

    quotation = db.scalar(
        select(Quotation)
        .where(
            Quotation.id == quotation_id,
            Quotation.is_active.is_(True),
        )
        .with_for_update()
    )

    if quotation is None or quotation.status not in ({"draft", "in_revision", "sent", "waiting"} if staged else {"sent", "waiting"}):
        _deny()

    latest = _latest_snapshot(db, quotation_id)
    if (latest is None or latest.id != snapshot_id
        or latest.quotation_id != quotation_id):
        _deny()

    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Se requiere un PDF válido")

    if not filename or len(filename) > 255:
        raise ValueError("Nombre de archivo inválido")

    digest = sha256(pdf_bytes).hexdigest()
    commercial_digest = snapshot_digest(latest.snapshot_data)

    existing = db.scalar(
        select(QuotationSigningDocument).where(
            QuotationSigningDocument.quotation_id == quotation_id,
            QuotationSigningDocument.snapshot_id == snapshot_id,
        )
    )

    if existing is not None:
        if (
            existing.pdf_sha256 != digest
            or existing.snapshot_sha256 != commercial_digest
            or existing.pdf_bytes != pdf_bytes
            or existing.invalidated_at is not None
        ):
            raise HTTPException(
                status_code=409,
                detail="La versión ya tiene un documento diferente o invalidado",
            )
        return existing

    document = QuotationSigningDocument(
        quotation_id=quotation_id,
        snapshot_id=snapshot_id,
        snapshot_sha256=commercial_digest,
        pdf_sha256=digest,
        pdf_bytes=bytes(pdf_bytes),
        filename=filename,
    )
    db.add(document)
    db.flush()
    return document


def create_document_link(
    db: Session,
    *,
    document_id: int,
    recipient_email: str,
    settings: Settings | None = None,
    lifetime_seconds: int = 15 * 24 * 60 * 60,
    staged: bool = False,
):
    """Create a revocable link. Caller must be an authorized internal actor."""
    settings = settings or get_settings()
    _enabled(settings)

    document = db.scalar(
        select(QuotationSigningDocument)
        .where(QuotationSigningDocument.id == document_id)
        .with_for_update()
    )
    if document is None or document.invalidated_at is not None:
        _deny()
    snapshot = db.get(QuotationSnapshot, document.snapshot_id)
    if (
        snapshot is None
        or snapshot.quotation_id != document.quotation_id
        or snapshot_digest(snapshot.snapshot_data) != document.snapshot_sha256
        or sha256(document.pdf_bytes).hexdigest() != document.pdf_sha256
    ):
        _deny()

    quotation = db.scalar(
        select(Quotation)
        .where(
            Quotation.id == document.quotation_id,
            Quotation.is_active.is_(True),
        )
        .with_for_update()
    )
    latest = _latest_snapshot(db, document.quotation_id)

    if (
        quotation is None
        or quotation.status not in ({"draft", "in_revision", "sent", "waiting"} if staged else {"sent", "waiting"})
        or latest is None
        or latest.id != document.snapshot_id
        or snapshot_digest(latest.snapshot_data) != document.snapshot_sha256
        or (
            quotation.valid_until is not None
            and quotation.valid_until < _now().date()
        )
    ):
        _deny()


    token = issue_signing_link(
        quotation_id=document.quotation_id,
        snapshot_id=document.snapshot_id,
        pdf_sha256=document.pdf_sha256,
        secret_key=settings.secret_key,
        lifetime_seconds=(30 * 24 * 60 * 60 if staged else lifetime_seconds),
        staged=staged,
    )
    claims = verify_signing_link(token, secret_key=settings.secret_key)

    link = QuotationSigningLink(
        document_id=document.id,
        token_id_hash=sha256(claims.token_id.encode()).hexdigest(),
        recipient_email=recipient_email.strip().lower(),
        expires_at=(
            datetime.fromtimestamp(claims.expires_at, timezone.utc)
            if staged else _now() + timedelta(seconds=lifetime_seconds)
        ),
        activated_at=None if staged else _now(),
    )
    db.add(link)
    db.flush()
    return token, link


def authorize_document_link(
    db: Session,
    token: str,
    *,
    settings: Settings | None = None,
):
    """Require cryptographic and database authorization."""
    settings = settings or get_settings()
    _enabled(settings)

    try:
        claims = verify_signing_link(
            token, secret_key=settings.secret_key
        )
    except (SigningLinkError, ValueError):
        _deny()

    token_hash = sha256(claims.token_id.encode()).hexdigest()

    link = db.scalar(
        select(QuotationSigningLink).where(
            QuotationSigningLink.token_id_hash == token_hash
        )
    )
    if (
        link is None
        or link.revoked_at is not None
        or link.activated_at is None
        or _as_utc(link.expires_at) <= _now()
    ):
        _deny()

    document = db.get(QuotationSigningDocument, link.document_id)
    snapshot = (
        db.get(QuotationSnapshot, document.snapshot_id)
        if document is not None else None
    )
    if (
        document is None
        or document.invalidated_at is not None
        or snapshot is None
        or snapshot.quotation_id != document.quotation_id
        or document.quotation_id != claims.quotation_id
        or document.snapshot_id != claims.snapshot_id
        or document.pdf_sha256 != claims.pdf_sha256
        or document.snapshot_sha256 != snapshot_digest(
            snapshot.snapshot_data
        )
        or sha256(document.pdf_bytes).hexdigest() != claims.pdf_sha256
    ):
        _deny()

    quotation = db.get(Quotation, document.quotation_id)
    latest = _latest_snapshot(db, document.quotation_id)

    if (
        quotation is None
        or not quotation.is_active
        or quotation.status not in {"sent", "waiting"}
        or latest is None
        or latest.id != document.snapshot_id
        or snapshot_digest(latest.snapshot_data) != document.snapshot_sha256
        or (
            quotation.valid_until is not None
            and quotation.valid_until < _now().date()
        )
    ):
        _deny()


    return document, link


def invalidate_document_links(
    db: Session,
    *,
    quotation_id: int,
):
    """Invalidate document versions and associated capabilities.

    Must run in the same transaction as the commercial mutation.
    """
    now = _now()
    documents = list(
        db.scalars(
            select(QuotationSigningDocument)
            .where(
                QuotationSigningDocument.quotation_id == quotation_id,
                QuotationSigningDocument.invalidated_at.is_(None),
            )
            .with_for_update()
        ).all()
    )
    for document in documents:
        document.invalidated_at = now
        links = db.scalars(
            select(QuotationSigningLink)
            .where(
                QuotationSigningLink.document_id == document.id,
                QuotationSigningLink.revoked_at.is_(None),
            )
            .with_for_update()
        ).all()
        for link in links:
            link.revoked_at = now
    return len(documents)


def activate_document_link(db: Session, *, link_id: int, delivery_id: int):
    """Activate only after this specific SMTP delivery was accepted.

    Must be called under the quotation row lock and committed with status sent.
    """
    link = db.scalar(
        select(QuotationSigningLink)
        .where(QuotationSigningLink.id == link_id)
        .with_for_update()
    )
    delivery = db.scalar(
        select(EmailDelivery)
        .where(EmailDelivery.id == delivery_id)
        .with_for_update()
    )
    if link is None or link.revoked_at is not None or delivery is None:
        _deny()
    document = db.get(QuotationSigningDocument, link.document_id)
    if (
        document is None or document.invalidated_at is not None
        or delivery.status != "sent" or delivery.sent_at is None
        or delivery.related_entity_type != "quotation"
        or delivery.related_entity_id != document.quotation_id
        or delivery.template_key != "quotation_send_signing"
        or link.delivery_id != delivery_id
        or link.recipient_email.lower() not in {
            address.lower() for address in (delivery.to_json or [])
        }
    ):
        _deny()
    if link.activated_at is not None:
        if link.delivery_id != delivery_id:
            _deny()
        return link
    activated_at = delivery.sent_at
    if activated_at.tzinfo is None:
        activated_at = activated_at.replace(tzinfo=timezone.utc)
    if activated_at > _as_utc(link.expires_at) - timedelta(days=15):
        _deny()
    link.activated_at = activated_at
    link.expires_at = activated_at + timedelta(days=15)
    link.delivery_id = delivery_id
    db.flush()
    return link
