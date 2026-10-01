"""Adapter del Portal hacia la infraestructura central de correo (EmailService).

El token en claro sólo vive aquí el tiempo necesario para construir el enlace:
EmailService lo redacta en el historial y nunca se registra en logs. Un fallo
de correo jamás revierte el registro/invitación ya confirmados.
"""

import logging
from dataclasses import dataclass
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.email import send_email
from app.services.email.urls import resolve_public_base_url

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DevelopmentPortalMail:
    kind: str
    email: str
    token: str


# Sólo desarrollo/pruebas: nunca se llena en producción.
development_outbox: list[DevelopmentPortalMail] = []


def _is_production() -> bool:
    return settings.environment.lower() in {"production", "prod"}


def _base_url() -> str | None:
    return resolve_public_base_url(settings)


def _deliver(db: Session, *, kind: str, template_key: str, email: str, token: str, path: str, context: dict, entity_type: str, entity_id: int | None) -> None:
    if not _is_production():
        development_outbox.append(DevelopmentPortalMail(kind, email, token))
    base_url = _base_url()
    if base_url is None:
        logger.error("PUBLIC_APP_BASE_URL no está configurado; no se envió el correo %s.", template_key)
        return
    try:
        send_email(
            db,
            template_key=template_key,
            context={**context, ("verification_url" if kind == "verification" else "invitation_url"): f"{base_url}{path}"},
            to=[email],
            related_entity_type=entity_type,
            related_entity_id=entity_id,
        )
    except Exception as exc:  # noqa: BLE001 - email must never undo a confirmed operation
        db.rollback()
        logger.error("No se pudo enviar el correo %s: %s", template_key, type(exc).__name__)


def send_verification_email(db: Session, *, email: str, token: str, recipient_name: str | None = None, registration_id: int | None = None) -> None:
    _deliver(
        db,
        kind="verification",
        template_key="portal_email_verification",
        email=email,
        token=token,
        path=f"/portal/verificar-correo?token={quote(token, safe='')}",
        context={"recipient_name": recipient_name or "usuario"},
        entity_type="portal_registration",
        entity_id=registration_id,
    )


def send_invitation_email(
    db: Session, *, email: str, token: str, recipient_name: str | None = None, client_name: str | None = None, invitation_id: int | None = None
) -> None:
    _deliver(
        db,
        kind="invitation",
        template_key="portal_invitation",
        email=email,
        token=token,
        path=f"/portal/invitacion/{quote(token, safe='')}",
        context={"recipient_name": recipient_name or "usuario", "client_name": client_name or "MYC"},
        entity_type="portal_invitation",
        entity_id=invitation_id,
    )
