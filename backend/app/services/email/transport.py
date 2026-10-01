"""SMTP transport: the only place in the codebase that speaks SMTP."""

import re
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Callable, Sequence

from app.core.config import Settings
from app.services.email.errors import EmailAddressError, EmailTransportError

ADDRESS = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}$")
SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._ -]")


def normalize_address(value: str) -> str:
    address = (value or "").strip()
    if len(address) > 254 or not ADDRESS.fullmatch(address) or ".." in address:
        raise EmailAddressError("Dirección de correo inválida.")
    return address


def normalize_addresses(values: Sequence[str]) -> list[str]:
    seen: dict[str, str] = {}
    for value in values:
        address = normalize_address(value)
        seen.setdefault(address.lower(), address)
    return list(seen.values())


def safe_attachment_filename(filename: str) -> str:
    name = SAFE_FILENAME.sub("_", (filename or "").replace("\\", "/").rsplit("/", 1)[-1]).strip(" .")
    return name or "adjunto"


@dataclass(frozen=True)
class EmailAttachment:
    """In-memory attachment produced by trusted backend code, never a client path."""

    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


@dataclass(frozen=True)
class OutgoingMessage:
    subject: str
    body_text: str
    body_html: str
    to: Sequence[str]
    cc: Sequence[str] = ()
    bcc: Sequence[str] = ()
    attachments: Sequence[EmailAttachment] = field(default_factory=tuple)


@dataclass(frozen=True)
class TransportResult:
    message_id: str
    response: str


class SmtpTransport:
    def __init__(self, settings: Settings, smtp_factory: Callable[..., smtplib.SMTP] = smtplib.SMTP) -> None:
        self._settings = settings
        self._smtp_factory = smtp_factory

    @property
    def authenticates(self) -> bool:
        return bool(self._settings.smtp_username and self._settings.smtp_password.get_secret_value())

    def build_message(self, message: OutgoingMessage) -> tuple[EmailMessage, list[str]]:
        settings = self._settings
        sender = normalize_address(settings.email_from_address)
        to, cc, bcc = (normalize_addresses(group) for group in (message.to, message.cc, message.bcc))
        if not to:
            raise EmailAddressError("Se requiere al menos un destinatario.")
        subject = message.subject
        if "\r" in subject or "\n" in subject:
            raise EmailAddressError("El asunto no puede contener saltos de línea.")

        email = EmailMessage()
        email["From"] = formataddr((" ".join(settings.email_from_name.split()), sender))
        email["To"] = ", ".join(to)
        if cc:
            email["Cc"] = ", ".join(cc)
        if settings.email_reply_to:
            email["Reply-To"] = normalize_address(settings.email_reply_to)
        email["Subject"] = subject
        email["Message-ID"] = make_msgid(domain=sender.rsplit("@", 1)[1])
        email.set_content(message.body_text)
        email.add_alternative(message.body_html, subtype="html")
        for attachment in message.attachments:
            maintype, _, subtype = attachment.content_type.partition("/")
            email.add_attachment(
                attachment.content,
                maintype=maintype or "application",
                subtype=subtype or "octet-stream",
                filename=safe_attachment_filename(attachment.filename),
            )
        # Bcc is an envelope-only recipient: it never appears in headers.
        return email, [*to, *cc, *bcc]

    def send(self, message: OutgoingMessage) -> TransportResult:
        settings = self._settings
        if not settings.smtp_host:
            raise EmailTransportError("SMTP_HOST no está configurado.")
        email, recipients = self.build_message(message)
        password = settings.smtp_password.get_secret_value()
        try:
            server = self._smtp_factory(settings.smtp_host, settings.smtp_port, timeout=settings.email_timeout_seconds)
            try:
                server.ehlo()
                if settings.smtp_use_starttls:
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                if settings.smtp_username and password:
                    server.login(settings.smtp_username, password)
                refused = server.send_message(email, from_addr=normalize_address(settings.email_from_address), to_addrs=recipients)
            finally:
                try:
                    server.quit()
                except Exception:  # noqa: BLE001 - closing must never mask the real result
                    pass
        except EmailAddressError:
            raise
        except smtplib.SMTPRecipientsRefused as exc:
            raise EmailTransportError("El servidor SMTP rechazó a todos los destinatarios.") from exc
        except smtplib.SMTPAuthenticationError as exc:
            raise EmailTransportError("Autenticación SMTP rechazada.") from exc
        except (TimeoutError, OSError, smtplib.SMTPException) as exc:
            raise EmailTransportError(self._safe_error(exc, password)) from None
        response = "250 accepted" if not refused else f"accepted with {len(refused)} refused recipient(s)"
        return TransportResult(message_id=email["Message-ID"], response=response)

    def _safe_error(self, exc: Exception, password: str) -> str:
        text = f"{type(exc).__name__}: {exc}"
        for secret in (password, self._settings.smtp_username):
            if secret:
                text = text.replace(secret, "[redacted]")
        return text[:300]
