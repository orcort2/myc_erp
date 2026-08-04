"""Puerto de correo del portal; nunca persiste ni registra tokens en claro."""

from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings


class PortalMailAdapter(Protocol):
    def send_verification(self, *, email: str, token: str) -> None: ...
    def send_invitation(self, *, email: str, token: str) -> None: ...


@dataclass(frozen=True)
class DevelopmentPortalMail:
    kind: str
    email: str
    token: str


development_outbox: list[DevelopmentPortalMail] = []


def send_verification_email(*, email: str, token: str) -> None:
    if settings.environment.lower() not in {"production", "prod"}:
        development_outbox.append(DevelopmentPortalMail("verification", email, token))


def send_invitation_email(*, email: str, token: str) -> None:
    if settings.environment.lower() not in {"production", "prod"}:
        development_outbox.append(DevelopmentPortalMail("invitation", email, token))
