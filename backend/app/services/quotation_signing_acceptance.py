"""Transaction-scoped customer acceptance of a frozen quotation document.

This service intentionally exposes no HTTP route. The caller must commit.
"""
from datetime import datetime, timezone
from hashlib import sha256

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.quotation import Quotation
from app.models.quotation_acceptance import QuotationAcceptance
from app.models.quotation_signing_challenge import QuotationSigningChallenge
from app.services.quotation_signing_authority import (
    authorize_document_link,
    invalidate_document_links,
)
from app.services.audit_logs import write_audit_log


CONSENT_TEXT = (
    "He revisado la cotización identificada por su versión y huella digital. "
    "Confirmo mi aceptación de sus condiciones comerciales y autorizo "
    "registrar esta aceptación mediante verificación de mi correo electrónico."
)


def accept_signed_quotation(
    db: Session,
    *,
    signing_token: str,
    challenge_id: int,
    signer_name: str,
    consent: bool,
    settings: Settings | None = None,
) -> QuotationAcceptance:
    """Atomically consume a verified OTP and persist acceptance evidence.

    The caller is responsible for creating/reusing the ETS within this same
    transaction, and for committing only after all steps have succeeded.
    """
    settings = settings or get_settings()
    if not settings.quotation_signing_enabled or settings.uses_development_secret:
        raise HTTPException(status_code=503, detail="Mesa de Firmado MYC no habilitada")
    if not consent:
        raise HTTPException(status_code=422, detail="Se requiere consentimiento explícito")
    name = signer_name.strip() if isinstance(signer_name, str) else ""
    if not 2 <= len(name) <= 180:
        raise HTTPException(status_code=422, detail="Nombre del firmante inválido")

    # Verify signature first, then serialize all writes under the quotation lock.
    document, link = authorize_document_link(db, signing_token, settings=settings)
    quotation = db.scalar(
        select(Quotation)
        .where(Quotation.id == document.quotation_id, Quotation.is_active.is_(True))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if quotation is None or quotation.status not in {"sent", "waiting"}:
        raise HTTPException(status_code=409, detail="Cotización no disponible")
    # Re-authorize under the quotation lock to detect concurrent revocations.
    document, link = authorize_document_link(db, signing_token, settings=settings)

    challenge = db.scalar(
        select(QuotationSigningChallenge)
        .where(
            QuotationSigningChallenge.id == challenge_id,
            QuotationSigningChallenge.quotation_id == quotation.id,
        )
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if (
        challenge is None
        or challenge.signing_link_id != link.id
        or challenge.snapshot_id != document.snapshot_id
        or challenge.recipient_email.lower() != link.recipient_email.lower()
        or challenge.verified_at is None
        or challenge.consumed_at is not None
        or challenge.revoked_at is not None
        or challenge.expires_at <= now
        or sha256(document.pdf_bytes).hexdigest() != document.pdf_sha256
    ):
        raise HTTPException(status_code=409, detail="Verificación no disponible")

    existing = db.scalar(
        select(QuotationAcceptance)
        .where(
            QuotationAcceptance.quotation_id == quotation.id,
            QuotationAcceptance.invalidated_at.is_(None),
        )
        .with_for_update()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="La cotización ya fue aceptada")

    # Validate prerequisites before consuming the OTP or changing quotation status.
    if quotation.advisor_id is None:
        raise HTTPException(
            status_code=409,
            detail="La cotización necesita un asesor asignado para generar la ETS",
        )

    previous_status = quotation.status
    acceptance = QuotationAcceptance(
        quotation_id=quotation.id,
        snapshot_id=document.snapshot_id,
        pdf_sha256=document.pdf_sha256,
        pdf_bytes=document.pdf_bytes,
        signer_name=name,
        signer_email=link.recipient_email,
        consent_text=CONSENT_TEXT,
        evidence={
            "method": "email_otp",
            "signing_link_id": link.id,
            "signing_document_id": document.id,
            "challenge_id": challenge.id,
            "snapshot_sha256": document.snapshot_sha256,
            "pdf_sha256": document.pdf_sha256,
            "consent": True,
            "verified_at": challenge.verified_at.isoformat(),
            "accepted_at": now.isoformat(),
        },
        verified_at=challenge.verified_at,
        accepted_at=now,
    )
    db.add(acceptance)
    challenge.consumed_at = now
    quotation.status = "accepted"
    db.flush()
    # Reuse the existing ETS orchestration, which is idempotent by quotation.
    # Never commit here: evidence, OTP consumption and ETS must be atomic.
    from app.schemas.service_order import ServiceOrderCreate
    from app.services.service_orders import create_service_order
    create_service_order(
        db,
        ServiceOrderCreate(
            client_id=quotation.client_id,
            quotation_id=quotation.id,
            advisor_id=quotation.advisor_id,
            notes=f"ETS generado al aprobar {quotation.folio}",
        ),
        user_id=quotation.advisor_id,
        commit=False,
    )
    invalidate_document_links(db, quotation_id=quotation.id)
    write_audit_log(
        db,
        action="quotation.electronic_acceptance",
        entity="quotations",
        entity_id=quotation.id,
        user_id=None,
        previous_values={"status": previous_status},
        new_values={
            "acceptance_id": acceptance.id,
            "snapshot_id": acceptance.snapshot_id,
            "pdf_sha256": acceptance.pdf_sha256,
            "signing_link_id": link.id,
        },
    )
    return acceptance
