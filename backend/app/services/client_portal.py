"""Identidad y aislamiento del portal cliente sin aceptar tenant desde el cliente HTTP."""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.client import Client
from app.models.user import User
from app.core.portal.security import PortalSecurityContext, get_portal_context, resolve_active_membership


@dataclass(frozen=True, slots=True)
class PortalClientContext:
    user: User
    client: Client


def resolve_portal_client(db: Session, user: User) -> Client:
    """Compatibilidad: el cliente proviene sólo de una membresía activa."""
    return resolve_active_membership(db, user.id).client


def get_portal_client_context(
    security: PortalSecurityContext = Depends(get_portal_context),
) -> PortalClientContext:
    return PortalClientContext(
        user=security.user,
        client=security.client,
    )
