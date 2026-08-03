"""Identidad y aislamiento del portal cliente sin aceptar tenant desde el cliente HTTP."""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.client import Client, ClientContact
from app.models.user import User
from app.services.auth import get_current_user, user_has_permission


@dataclass(frozen=True, slots=True)
class PortalClientContext:
    user: User
    client: Client


def resolve_portal_client(db: Session, user: User) -> Client:
    """Resolve exactly one active client from the authenticated portal identity."""
    role_names = {role.name for role in user.roles if role.is_active}
    if "Cliente" not in role_names or not user_has_permission(user, "portal.read"):
        raise HTTPException(status_code=403, detail="Cuenta sin acceso al portal cliente")

    normalized_email = user.email.strip().lower()
    direct_ids = set(
        db.scalars(
            select(Client.id).where(
                Client.is_active.is_(True),
                func.lower(Client.email) == normalized_email,
            )
        ).all()
    )
    contact_ids = set(
        db.scalars(
            select(ClientContact.client_id)
            .join(Client, Client.id == ClientContact.client_id)
            .where(
                Client.is_active.is_(True),
                ClientContact.is_active.is_(True),
                func.lower(ClientContact.email) == normalized_email,
            )
        ).all()
    )
    client_ids = direct_ids | contact_ids
    if len(client_ids) != 1:
        raise HTTPException(
            status_code=403,
            detail="La cuenta no tiene un vínculo de cliente único y activo",
        )
    client = db.get(Client, client_ids.pop())
    if client is None or not client.is_active:
        raise HTTPException(status_code=403, detail="Cuenta sin acceso al portal cliente")
    return client


def get_portal_client_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortalClientContext:
    return PortalClientContext(
        user=current_user,
        client=resolve_portal_client(db, current_user),
    )
