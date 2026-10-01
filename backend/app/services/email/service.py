"""EmailService: the only entry point business domains use to send email.

Transaction contract: callers MUST commit their own business changes before
calling ``send_email``. This service commits its own delivery records at each
state change and never raises for transport failures, so an SMTP outage can
not roll back (or surface as an error in) an already-confirmed operation.
Validation errors (unknown template/variables, invalid addresses) are raised
before anything is persisted.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.email import EmailDelivery
from app.services.audit_logs import write_audit_log
from app.services.email.errors import EmailError, EmailTemplateError
from app.services.email.renderer import RenderedEmail, render_email
from app.services.email.templates import get_definition, get_template
from app.services.email.transport import (
    EmailAttachment,
    OutgoingMessage,
    SmtpTransport,
    normalize_addresses,
    safe_attachment_filename,
)

logger = logging.getLogger(__name__)
MAX_RETRY_ATTEMPTS = 5
DISABLED_REASON = "email_disabled"


@dataclass(frozen=True)
class EmailResult:
    """``sent`` is True only when the SMTP relay accepted the message."""

    delivery_id: int
    status: str
    sent: bool
    reason: str | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def preview_email(
    db: Session, *, template_key: str, context: dict[str, object], settings: Settings | None = None
) -> RenderedEmail:
    """Render exactly what ``send_email`` would deliver (secrets included).

    Only call this with a context built by the backend from authorized entities.
    """
    settings = settings or get_settings()
    definition = get_definition(template_key)
    template = get_template(db, template_key)
    return render_email(
        definition,
        subject_template=template.subject_template,
        body_template=template.body_template,
        context=context,
        organization_name=settings.email_from_name,
    )


def _attachment_metadata(attachments: Sequence[EmailAttachment]) -> list[dict]:
    return [
        {
            "filename": safe_attachment_filename(item.filename),
            "content_type": item.content_type,
            "size": len(item.content),
            "sha256": sha256(item.content).hexdigest(),
        }
        for item in attachments
    ]


def _finish(
    db: Session,
    delivery: EmailDelivery,
    *,
    transport: SmtpTransport,
    settings: Settings,
    message: OutgoingMessage,
    actor_id: int | None,
) -> EmailResult:
    """Run one transport attempt; always leaves the delivery in sent/failed."""
    if not settings.email_enabled:
        delivery.status, delivery.failed_at = "failed", _utcnow()
        delivery.failure_code = DISABLED_REASON
        delivery.last_error = "EMAIL_ENABLED=false: el transporte está deshabilitado; el mensaje no se envió."
        _audit(db, delivery, "email.delivery.failed", actor_id, reason=DISABLED_REASON)
        db.commit()
        return EmailResult(delivery.id, "failed", False, DISABLED_REASON)

    delivery.status, delivery.attempt_count = "sending", delivery.attempt_count + 1
    db.commit()
    try:
        result = transport.send(message)
    except Exception as exc:  # noqa: BLE001 - any failure must end in 'failed', never 'sending'
        error = exc.message if isinstance(exc, EmailError) else f"{type(exc).__name__}"
        delivery.status, delivery.failed_at, delivery.last_error = "failed", _utcnow(), error
        delivery.failure_code = "transport_failed"
        _audit(db, delivery, "email.delivery.failed", actor_id, reason=type(exc).__name__)
        db.commit()
        logger.warning("Email delivery %s failed: %s", delivery.id, type(exc).__name__)
        return EmailResult(delivery.id, "failed", False, "transport_failed")
    delivery.status, delivery.sent_at, delivery.failed_at, delivery.last_error = "sent", _utcnow(), None, None
    delivery.failure_code = None
    delivery.provider_message_id, delivery.provider_response = result.message_id, result.response
    _audit(db, delivery, "email.delivery.sent", actor_id)
    db.commit()
    return EmailResult(delivery.id, "sent", True)


def _audit(db: Session, delivery: EmailDelivery, action: str, actor_id: int | None, **extra) -> None:
    write_audit_log(
        db,
        action=action,
        entity="email_deliveries",
        entity_id=delivery.id,
        user_id=actor_id,
        new_values={
            "template_key": delivery.template_key,
            "related_entity_type": delivery.related_entity_type,
            "related_entity_id": delivery.related_entity_id,
            "status": delivery.status,
            "attempt_count": delivery.attempt_count,
            **extra,
        },
    )


def send_email(
    db: Session,
    *,
    template_key: str,
    context: dict[str, object],
    to: Sequence[str],
    cc: Sequence[str] = (),
    bcc: Sequence[str] = (),
    attachments: Sequence[EmailAttachment] = (),
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
    requested_by_id: int | None = None,
    settings: Settings | None = None,
    transport: SmtpTransport | None = None,
) -> EmailResult:
    settings = settings or get_settings()
    transport = transport or SmtpTransport(settings)
    definition = get_definition(template_key)
    template = get_template(db, template_key)
    if not template.is_active:
        raise EmailTemplateError("La plantilla de correo está desactivada.")
    render_args = dict(
        subject_template=template.subject_template,
        body_template=template.body_template,
        context=context,
        organization_name=settings.email_from_name,
    )
    real = render_email(definition, **render_args)
    stored = render_email(definition, **render_args, redact_secrets=True)
    to_list, cc_list, bcc_list = (normalize_addresses(group) for group in (to, cc, bcc))
    if not to_list:
        raise EmailTemplateError("Se requiere al menos un destinatario.")

    delivery = EmailDelivery(
        template_key=template_key,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        to_json=to_list,
        cc_json=cc_list,
        bcc_json=bcc_list,
        subject=stored.subject,
        body_text_snapshot=stored.body_text,
        body_html_snapshot=stored.body_html,
        attachments_json=_attachment_metadata(attachments),
        status="pending",
        attempt_count=0,
        requested_by_id=requested_by_id,
    )
    db.add(delivery)
    db.commit()  # the intent is durable before any network I/O
    message = OutgoingMessage(real.subject, real.body_text, real.body_html, to_list, cc_list, bcc_list, tuple(attachments))
    return _finish(db, delivery, transport=transport, settings=settings, message=message, actor_id=requested_by_id)


class RetryNotAllowed(EmailError):
    code = "email_retry_not_allowed"


def retry_delivery(
    db: Session,
    delivery_id: int,
    *,
    actor_id: int,
    settings: Settings | None = None,
    transport: SmtpTransport | None = None,
) -> EmailResult:
    settings = settings or get_settings()
    transport = transport or SmtpTransport(settings)
    delivery = db.scalar(select(EmailDelivery).where(EmailDelivery.id == delivery_id).with_for_update())
    if delivery is None:
        raise RetryNotAllowed("Envío de correo no encontrado.")
    if delivery.status != "failed":
        raise RetryNotAllowed("Sólo se pueden reintentar envíos fallidos.")
    if delivery.failure_code == DISABLED_REASON:
        raise RetryNotAllowed("El envío falló porque el correo está deshabilitado (EMAIL_ENABLED=false); no hubo intento SMTP. Genere un nuevo envío.")
    if delivery.attempt_count >= MAX_RETRY_ATTEMPTS:
        raise RetryNotAllowed("Se alcanzó el máximo de reintentos.")
    if get_definition(delivery.template_key).has_secret:
        raise RetryNotAllowed(
            "Este correo contiene una credencial de un solo uso que no se conserva; genere una nueva solicitud."
        )
    if delivery.attachments_json:
        raise RetryNotAllowed("Los adjuntos no se conservan; vuelva a generar el envío desde su origen.")
    _audit(db, delivery, "email.delivery.retried", actor_id)
    message = OutgoingMessage(
        delivery.subject,
        delivery.body_text_snapshot,
        delivery.body_html_snapshot,
        delivery.to_json,
        delivery.cc_json,
        delivery.bcc_json,
    )
    return _finish(db, delivery, transport=transport, settings=settings, message=message, actor_id=actor_id)
