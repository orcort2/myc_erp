"""Invoice email: backend-built preview and send on top of EmailService.

The client may only choose recipients. Subject, body, template context and
attachments are always reconstructed from the authorized invoice.

Draft invoices send the institutional MYC PDF only and are explicitly marked
as non-fiscal pre-comprobantes. Issued invoices send the institutional MYC
PDF plus the stored fiscal XML. The Facturama PDF is never an email authority.

Sending an email never issues, stamps, pays or otherwise changes invoice state.
"""

from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.models.email import EmailDelivery
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.email import (
    InvoiceEmailAttachmentInfo,
    InvoiceEmailDeliveryRead,
    InvoiceEmailPreview,
    InvoiceEmailRecipient,
    InvoiceEmailSendResult,
)
from app.services.audit_logs import write_audit_log
from app.services.email import EmailAttachment, preview_email, send_email
from app.services.email.errors import EmailError
from app.services.email.transport import normalize_addresses
from app.services.invoice_pdfs import generate_invoice_pdf, get_invoice_fiscal_xml
from app.services.invoices import get_invoice


ENTITY_TYPE = "invoice"
DRAFT_TEMPLATE_KEY = "invoice_draft_send"
ISSUED_TEMPLATE_KEY = "invoice_send"

PDF_CONTENT_TYPE = "application/pdf"
XML_CONTENT_TYPE = "application/xml"


def _client_name(invoice: Invoice) -> str:
    return invoice.client.commercial_name or invoice.client.legal_name


def _validated_quotation(invoice: Invoice):
    quotation = invoice.quotation

    if invoice.quotation_id is None or quotation is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La factura no tiene una cotización de origen válida.",
        )

    if quotation.client_id != invoice.client_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La factura y su cotización de origen pertenecen a clientes distintos.",
        )

    normalized = (quotation.status or "").strip().lower().replace(" ", "_")
    if normalized not in {"approved", "aprobada", "accepted", "aceptada"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La factura requiere una cotización de origen aprobada.",
        )

    return quotation

def _document_mode(invoice: Invoice) -> str:
    has_uuid = bool((invoice.cfdi_uuid or "").strip())
    has_xml_reference = bool((invoice.facturama_xml_path or "").strip())

    if has_uuid != has_xml_reference:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La factura tiene evidencia fiscal incompleta y no puede enviarse por correo.",
        )

    return "issued" if has_uuid and has_xml_reference else "draft"


def _template_key(mode: str) -> str:
    return ISSUED_TEMPLATE_KEY if mode == "issued" else DRAFT_TEMPLATE_KEY

def available_recipients(invoice: Invoice) -> list[InvoiceEmailRecipient]:
    """Suggestions in precedence order: quotation contact, other contacts, client email."""
    quotation = _validated_quotation(invoice)

    found: list[InvoiceEmailRecipient] = []
    seen: set[str] = set()

    def add(
        email: str | None,
        name: str | None,
        source: str,
        contact_id: int | None,
    ) -> None:
        address = (email or "").strip()
        if not address or address.lower() in seen:
            return

        seen.add(address.lower())
        found.append(
            InvoiceEmailRecipient(
                email=address,
                name=name,
                source=source,
                contact_id=contact_id,
            )
        )

    main = quotation.contact
    if main is not None and main.client_id == invoice.client_id:
        add(main.email, main.name, "quotation_contact", main.id)

    for contact in sorted(invoice.client.contacts, key=lambda item: item.id):
        if contact.is_active:
            add(contact.email, contact.name, "client_contact", contact.id)

    add(
        invoice.client.email,
        _client_name(invoice),
        "client_email",
        None,
    )

    if found:
        found[0].selected = True

    return found


def _resolve_recipients(
    invoice: Invoice,
    to: list[str] | None,
    cc: list[str] | None,
) -> tuple[list[str], list[str], list[InvoiceEmailRecipient]]:
    suggestions = available_recipients(invoice)

    try:
        if to is None:
            chosen_to = [item.email for item in suggestions if item.selected]
        else:
            chosen_to = normalize_addresses(to)

        chosen_cc = normalize_addresses(cc or [])

    except EmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.message,
        ) from exc

    if not chosen_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Se requiere al menos un destinatario",
        )

    to_keys = {address.lower() for address in chosen_to}
    chosen_cc = [
        address
        for address in chosen_cc
        if address.lower() not in to_keys
    ]

    return chosen_to, chosen_cc, suggestions

def _money(value) -> str:
    return f"${value:,.2f}"


def build_context(
    invoice: Invoice,
    primary_to: str,
    suggestions: list[InvoiceEmailRecipient],
    *,
    mode: str,
) -> dict[str, str]:
    quotation = _validated_quotation(invoice)

    match = next(
        (
            item
            for item in suggestions
            if item.contact_id is not None
            and item.email.lower() == primary_to.lower()
        ),
        None,
    )

    contact_name = (
        match.name
        if match is not None and match.name
        else (
            quotation.contact.name
            if quotation.contact is not None
            else _client_name(invoice)
        )
    )

    context = {
        "contact_name": contact_name,
        "client_name": _client_name(invoice),
        "fiscal_identifier": invoice.folio,
        "total": _money(invoice.total),
    }

    if mode == "issued":
        context["cfdi_uuid"] = invoice.cfdi_uuid or ""

    return context

def _build_attachments(
    db: Session,
    invoice: Invoice,
    *,
    mode: str,
) -> tuple[list[EmailAttachment], list[InvoiceEmailAttachmentInfo]]:
    pdf, pdf_filename = generate_invoice_pdf(db, invoice.id, recalculate=False, read_only=True)

    email_attachments = [
        EmailAttachment(
            filename=pdf_filename,
            content=pdf,
            content_type=PDF_CONTENT_TYPE,
        )
    ]
    preview_attachments = [
        InvoiceEmailAttachmentInfo(
            filename=pdf_filename,
            content_type=PDF_CONTENT_TYPE,
            size=len(pdf),
        )
    ]

    if mode == "issued":
        xml, xml_filename = get_invoice_fiscal_xml(db, invoice.id, recalculate=False)

        email_attachments.append(
            EmailAttachment(
                filename=xml_filename,
                content=xml,
                content_type=XML_CONTENT_TYPE,
            )
        )
        preview_attachments.append(
            InvoiceEmailAttachmentInfo(
                filename=xml_filename,
                content_type=XML_CONTENT_TYPE,
                size=len(xml),
            )
        )

    return email_attachments, preview_attachments

def preview_invoice_email(
    db: Session,
    invoice_id: int,
    *,
    to: list[str] | None = None,
    cc: list[str] | None = None,
    settings: Settings | None = None,
) -> InvoiceEmailPreview:
    with db.no_autoflush:
        invoice = get_invoice(db, invoice_id, recalculate=False)
        _validated_quotation(invoice)

        mode = _document_mode(invoice)
        template_key = _template_key(mode)

        chosen_to, chosen_cc, suggestions = _resolve_recipients(
            invoice,
            to,
            cc,
        )

        context = build_context(
            invoice,
            chosen_to[0],
            suggestions,
            mode=mode,
        )

        rendered = preview_email(
            db,
            template_key=template_key,
            context=context,
            settings=settings or get_settings(),
        )

        _, preview_attachments = _build_attachments(
            db,
            invoice,
            mode=mode,
        )

        selected = {address.lower() for address in chosen_to}
        for item in suggestions:
            item.selected = item.email.lower() in selected

        return InvoiceEmailPreview(
            invoice_id=invoice.id,
            document_mode=mode,
            template_key=template_key,
            available_recipients=suggestions,
            to=chosen_to,
            cc=chosen_cc,
            subject=rendered.subject,
            body_text=rendered.body_text,
            body_html=rendered.body_html,
            attachments=preview_attachments,
        )

def send_invoice_email(
    db: Session,
    invoice_id: int,
    *,
    to: list[str],
    cc: list[str] | None,
    actor: User,
    settings: Settings | None = None,
    transport=None,
    delivery_session_factory=None,
) -> InvoiceEmailSendResult:
    with db.no_autoflush:
        invoice = get_invoice(db, invoice_id, recalculate=False)
        _validated_quotation(invoice)

        mode = _document_mode(invoice)
        template_key = _template_key(mode)

        chosen_to, chosen_cc, suggestions = _resolve_recipients(
            invoice,
            to,
            cc,
        )

        context = build_context(
            invoice,
            chosen_to[0],
            suggestions,
            mode=mode,
        )

        attachments, _ = _build_attachments(
            db,
            invoice,
            mode=mode,
        )

        folio = invoice.folio
        invoice_pk = invoice.id

    factory = delivery_session_factory or sessionmaker(
        bind=db.get_bind(),
        autoflush=False,
        expire_on_commit=False,
    )

    with factory() as delivery_db:
        try:
            result = send_email(
                delivery_db,
                template_key=template_key,
                context=context,
                to=chosen_to,
                cc=chosen_cc,
                attachments=attachments,
                related_entity_type=ENTITY_TYPE,
                related_entity_id=invoice_pk,
                requested_by_id=actor.id,
                settings=settings,
                transport=transport,
            )
        except EmailError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=exc.message,
            ) from exc

        hashes = {
            item.filename: sha256(item.content).hexdigest()
            for item in attachments
        }

        write_audit_log(
            delivery_db,
            action="invoice.email.sent" if result.sent else "invoice.email.failed",
            entity="invoices",
            entity_id=invoice_pk,
            user_id=actor.id,
            new_values={
                "invoice_folio": folio,
                "delivery_id": result.delivery_id,
                "status": result.status,
                "document_mode": mode,
                "attachment_sha256": hashes,
            },
        )

        delivery_db.commit()

    return InvoiceEmailSendResult(
        delivery_id=result.delivery_id,
        status=result.status,
        sent=result.sent,
        reason=result.reason,
    )

def list_invoice_email_deliveries(
    db: Session,
    invoice_id: int,
) -> list[InvoiceEmailDeliveryRead]:
    invoice = get_invoice(db, invoice_id, recalculate=False)
    _validated_quotation(invoice)

    rows = db.execute(
        select(EmailDelivery, User.full_name)
        .outerjoin(User, User.id == EmailDelivery.requested_by_id)
        .where(
            EmailDelivery.related_entity_type == ENTITY_TYPE,
            EmailDelivery.related_entity_id == invoice.id,
        )
        .order_by(
            EmailDelivery.created_at.desc(),
            EmailDelivery.id.desc(),
        )
    ).all()

    return [
        InvoiceEmailDeliveryRead(
            id=delivery.id,
            created_at=delivery.created_at,
            status=delivery.status,
            to=delivery.to_json,
            cc=delivery.cc_json,
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