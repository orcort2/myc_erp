"""Quotation email: backend-built preview and send on top of EmailService.

The client may only choose recipients. Subject, body, template context and the
PDF attachment are always built here from the authorized quotation, so what
the staff previews is exactly what is sent (same renderer, same PDF generator).
An SMTP-accepted email advances a draft quotation to sent; failed attempts do not.
"""

from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.email import EmailDelivery
from app.models.quotation import Quotation, QuotationSnapshot
from app.models.quotation_signing_document import QuotationSigningLink
from app.services.quotation_signing_authority import freeze_document, create_document_link, activate_document_link
from app.models.user import User
from app.schemas.email import (
    QuotationEmailAttachmentInfo,
    QuotationEmailDeliveryRead,
    QuotationEmailPreview,
    QuotationEmailRecipient,
    QuotationEmailSendResult,
)
from app.services.audit_logs import write_audit_log
from app.services.email import EmailAttachment, preview_email, send_email
from app.services.email.errors import EmailError
from app.services.email.transport import normalize_addresses
from app.services.quotation_pdfs import _format_date, _format_money, generate_quotation_pdf
from app.services.quotations import get_quotation, status_event_key
from app.services.activity import publish_event

TEMPLATE_KEY = "quotation_send_signing"
ENTITY_TYPE = "quotation"
PDF_CONTENT_TYPE = "application/pdf"
NO_VALIDITY_TEXT = "la fecha indicada en la cotización"
NO_ADVISOR_TEXT = "Equipo comercial MYC"


def _client_name(quotation: Quotation) -> str:
    return quotation.client.commercial_name or quotation.client.legal_name


def available_recipients(quotation: Quotation) -> list[QuotationEmailRecipient]:
    """Suggestions in precedence order: quotation contact, other contacts, client email."""
    found: list[QuotationEmailRecipient] = []
    seen: set[str] = set()

    def add(email: str | None, name: str | None, source: str, contact_id: int | None) -> None:
        address = (email or "").strip()
        if not address or address.lower() in seen:
            return
        seen.add(address.lower())
        found.append(QuotationEmailRecipient(email=address, name=name, source=source, contact_id=contact_id))

    main = quotation.contact
    if main is not None and main.client_id == quotation.client_id:
        add(main.email, main.name, "quotation_contact", main.id)
    for contact in sorted(quotation.client.contacts, key=lambda item: item.id):
        if contact.is_active:
            add(contact.email, contact.name, "client_contact", contact.id)
    add(quotation.client.email, _client_name(quotation), "client_email", None)
    if found:
        found[0].selected = True  # default selection = first by precedence
    return found


def _resolve_recipients(
    quotation: Quotation, to: list[str] | None, cc: list[str] | None
) -> tuple[list[str], list[str], list[QuotationEmailRecipient]]:
    suggestions = available_recipients(quotation)
    try:
        if to is None:
            chosen_to = [item.email for item in suggestions if item.selected]
        else:
            chosen_to = normalize_addresses(to)
        chosen_cc = normalize_addresses(cc or [])
    except EmailError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.message) from exc
    if not chosen_to:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Se requiere al menos un destinatario")
    # An address present in TO is never repeated in CC.
    to_keys = {address.lower() for address in chosen_to}
    chosen_cc = [address for address in chosen_cc if address.lower() not in to_keys]
    return chosen_to, chosen_cc, suggestions


def build_context(quotation: Quotation, primary_to: str, suggestions: list[QuotationEmailRecipient]) -> dict[str, str]:
    """Template variables, from the entity only. No invented names."""
    match = next(
        (item for item in suggestions if item.contact_id is not None and item.email.lower() == primary_to.lower()),
        None,
    )
    return {
        "contact_name": match.name if match is not None and match.name else _client_name(quotation),
        "client_name": _client_name(quotation),
        "quotation_folio": quotation.folio,
        "advisor_name": quotation.advisor_name or NO_ADVISOR_TEXT,
        "total": _format_money(quotation.total),
        "valid_until": _format_date(quotation.valid_until) if quotation.valid_until else NO_VALIDITY_TEXT,
    }


def preview_quotation_email(
    db: Session, quotation_id: int, *, to: list[str] | None = None, cc: list[str] | None = None,
    settings: Settings | None = None,
) -> QuotationEmailPreview:
    quotation = get_quotation(db, quotation_id)
    chosen_to, chosen_cc, suggestions = _resolve_recipients(quotation, to, cc)
    context = build_context(quotation, chosen_to[0], suggestions)
    # Preview never issues a signing token; renderer masks this secret URL.
    context["signing_url"] = "https://example.invalid/quotation-signing"
    rendered = preview_email(
        db, template_key=TEMPLATE_KEY, context=context,
        settings=settings or get_settings(), redact_secrets=True,
    )
    pdf, filename = generate_quotation_pdf(db, quotation_id)
    selected = {address.lower() for address in chosen_to}
    for item in suggestions:
        item.selected = item.email.lower() in selected
    return QuotationEmailPreview(
        quotation_id=quotation.id,
        template_key=TEMPLATE_KEY,
        available_recipients=suggestions,
        to=chosen_to,
        cc=chosen_cc,
        subject=rendered.subject,
        body_text=rendered.body_text,
        body_html=rendered.body_html,
        attachments=[QuotationEmailAttachmentInfo(filename=filename, content_type=PDF_CONTENT_TYPE, size=len(pdf))],
    )


def send_quotation_email(
    db: Session, quotation_id: int, *, to: list[str], cc: list[str] | None, actor: User,
    settings: Settings | None = None, transport=None,
) -> QuotationEmailSendResult:
    quotation = get_quotation(db, quotation_id)
    # Reject terminal quotations before triggering irreversible SMTP I/O.
    if quotation.status not in {"draft", "in_revision", "sent", "waiting"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La cotización no admite envío por correo en su estado actual")
    chosen_to, chosen_cc, suggestions = _resolve_recipients(quotation, to, cc)
    settings = settings or get_settings()
    if not settings.effective_public_base_url:
        raise HTTPException(status_code=503, detail="Configure PUBLIC_APP_BASE_URL.")
    if len(chosen_to) != 1 or chosen_cc:
        raise HTTPException(status_code=422, detail="El firmado requiere un destinatario y ningún CC.")
    context = build_context(quotation, chosen_to[0], suggestions)
    pdf, filename = generate_quotation_pdf(db, quotation_id)
    latest = db.scalar(
        select(QuotationSnapshot)
        .where(QuotationSnapshot.quotation_id == quotation_id)
        .order_by(QuotationSnapshot.snapshot_number.desc(), QuotationSnapshot.id.desc())
        .limit(1)
    )
    if latest is None:
        raise HTTPException(status_code=409, detail="La cotización no tiene snapshot.")
    document = freeze_document(
        db, quotation_id=quotation_id, snapshot_id=latest.id,
        pdf_bytes=pdf, filename=filename, settings=settings, staged=True,
    )
    token, link = create_document_link(
        db, document_id=document.id, recipient_email=chosen_to[0],
        settings=settings, staged=True,
    )
    from urllib.parse import quote
    context["signing_url"] = (
        settings.effective_public_base_url + "/quotation-signing#token="
        + quote(token, safe="")
    )
    folio, quotation_pk = quotation.folio, quotation.id
    try:
        result = send_email(
            db,
            template_key=TEMPLATE_KEY,
            context=context,
            to=chosen_to,
            cc=chosen_cc,
            attachments=[EmailAttachment(filename=filename, content=pdf, content_type=PDF_CONTENT_TYPE)],
            related_entity_type=ENTITY_TYPE,
            related_entity_id=quotation_pk,
            requested_by_id=actor.id,
            settings=settings,
            transport=transport,
            staged_signing_link_id=link.id,
        )
    except EmailError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.message) from exc
    # Reconcile against the persisted SMTP delivery rather than trusting only
    # this request's in-memory result. Safe to invoke again after a crash.
    if result.sent:
        reconcile_quotation_email_status(db, quotation_pk, actor_id=actor.id)
    else:
        from datetime import datetime, timezone
        link.revoked_at = datetime.now(timezone.utc)
    write_audit_log(
        db,
        action="quotation.email.sent" if result.sent else "quotation.email.failed",
        entity="quotations",
        entity_id=quotation_pk,
        user_id=actor.id,
        new_values={
            "quotation_folio": folio,
            "delivery_id": result.delivery_id,
            "status": result.status,
            "attachment_sha256": sha256(pdf).hexdigest(),
        },
    )
    db.commit()
    return QuotationEmailSendResult(
        delivery_id=result.delivery_id, status=result.status, sent=result.sent, reason=result.reason
    )



def reconcile_quotation_email_status(db: Session, quotation_id: int, *, actor_id: int | None = None) -> bool:
    """Recover draft -> sent from a durable SMTP-accepted quotation delivery.

    Never resends mail. The quotation row lock serializes concurrent status
    transitions on PostgreSQL; terminal and already-progressed states are left
    untouched. Returns True only when a transition was committed.
    """
    quotation = db.scalar(
        select(Quotation)
        .where(Quotation.id == quotation_id, Quotation.is_active.is_(True))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if quotation is None or quotation.status not in {"draft", "in_revision", "sent", "waiting"}:
        return False
    deliveries = db.scalars(
        select(EmailDelivery)
        .where(
            EmailDelivery.related_entity_type == ENTITY_TYPE,
            EmailDelivery.related_entity_id == quotation_id,
            EmailDelivery.template_key == TEMPLATE_KEY,
            EmailDelivery.status == "sent",
            EmailDelivery.sent_at.is_not(None),
        )
        .order_by(EmailDelivery.sent_at.asc(), EmailDelivery.id.asc())
    ).all()
    first_delivery = None
    for delivery in deliveries:
        links = db.scalars(
            select(QuotationSigningLink)
            .where(
                QuotationSigningLink.delivery_id == delivery.id,
                QuotationSigningLink.revoked_at.is_(None),
            )
            .with_for_update()
        ).all()
        for link in links:
            if link.activated_at is None:
                activate_document_link(db, link_id=link.id, delivery_id=delivery.id)
            if first_delivery is None:
                first_delivery = delivery
    if first_delivery is None:
        return False
    if quotation.status not in {"draft", "in_revision"}:
        db.commit()
        return False
    delivery = first_delivery
    previous_status = quotation.status
    quotation.status = "sent"
    write_audit_log(
        db,
        action="quotation.sent",
        entity="quotations",
        entity_id=quotation_id,
        user_id=actor_id or delivery.requested_by_id,
        previous_values={"status": previous_status},
        new_values={"status": "sent", "delivery_id": delivery.id, "source": "smtp_reconciliation"},
    )
    publish_event(
        db,
        entity_type="quotation",
        entity_id=quotation_id,
        event_code=(
            "quotation.revision_resent"
            if previous_status == "in_revision"
            else "quotation.status_changed"
        ),
        idempotency_key=status_event_key(db, quotation_id, "sent"),
        body=(
            "Nueva versión de la cotización reenviada al cliente."
            if previous_status == "in_revision"
            else "Estado actualizado de draft a sent."
        ),
        actor_id=actor_id or delivery.requested_by_id,
        metadata={"previous_status": previous_status, "status": "sent"},
    )
    db.commit()
    return True


def list_quotation_email_deliveries(db: Session, quotation_id: int) -> list[QuotationEmailDeliveryRead]:
    quotation = get_quotation(db, quotation_id)  # 404 for unknown/inactive quotations
    rows = db.execute(
        select(EmailDelivery, User.full_name)
        .outerjoin(User, User.id == EmailDelivery.requested_by_id)
        .where(EmailDelivery.related_entity_type == ENTITY_TYPE, EmailDelivery.related_entity_id == quotation.id)
        .order_by(EmailDelivery.created_at.desc(), EmailDelivery.id.desc())
    ).all()
    return [
        QuotationEmailDeliveryRead(
            id=delivery.id,
            created_at=delivery.created_at,
            status=delivery.status,
            to=delivery.to_json,
            cc=delivery.cc_json,  # BCC is intentionally not exposed
            subject=delivery.subject,
            sent_at=delivery.sent_at,
            failed_at=delivery.failed_at,
            failure_code=delivery.failure_code,
            last_error=delivery.last_error,
            attempt_count=delivery.attempt_count,
            requested_by_id=delivery.requested_by_id,
            requested_by_name=full_name,
            attachments=delivery.attachments_json or [],
        )
        for delivery, full_name in rows
    ]
