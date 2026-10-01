"""Quotation email: backend-built preview and send on top of EmailService.

The client may only choose recipients. Subject, body, template context and the
PDF attachment are always built here from the authorized quotation, so what
the staff previews is exactly what is sent (same renderer, same PDF generator).
Sending an email never changes ``quotation.status``.
"""

from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.email import EmailDelivery
from app.models.quotation import Quotation
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
from app.services.quotations import get_quotation

TEMPLATE_KEY = "quotation_send"
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
    rendered = preview_email(db, template_key=TEMPLATE_KEY, context=context, settings=settings or get_settings())
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
    chosen_to, chosen_cc, suggestions = _resolve_recipients(quotation, to, cc)
    context = build_context(quotation, chosen_to[0], suggestions)
    pdf, filename = generate_quotation_pdf(db, quotation_id)  # the official PDF, nothing else
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
        )
    except EmailError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.message) from exc
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
