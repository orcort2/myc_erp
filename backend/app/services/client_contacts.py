"""Granular ClientContact management.

Contacts are people that belong to a Client. Their ids are referenced by
quotations (``Quotation.contact_id``), so they are edited in place and
deactivated (soft delete), never replaced or hard-deleted.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import Client, ClientContact
from app.schemas.client import ClientContactCreate, ClientContactUpdate
from app.services.audit_logs import write_audit_log


def _client_or_404(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None or not client.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return client


def get_client_contact(db: Session, client_id: int, contact_id: int) -> ClientContact:
    """The contact must belong to the client in the route: no cross-client access."""
    contact = db.scalar(
        select(ClientContact).where(ClientContact.id == contact_id, ClientContact.client_id == client_id)
    )
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado")
    return contact


def _clean(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _snapshot(contact: ClientContact) -> dict:
    return {
        "name": contact.name,
        "email": contact.email,
        "phone": contact.phone,
        "position": contact.position,
        "is_active": contact.is_active,
    }


def list_client_contacts(db: Session, client_id: int, *, include_inactive: bool = True) -> list[ClientContact]:
    _client_or_404(db, client_id)
    query = select(ClientContact).where(ClientContact.client_id == client_id).order_by(ClientContact.id)
    if not include_inactive:
        query = query.where(ClientContact.is_active.is_(True))
    return list(db.scalars(query).all())


def create_client_contact(
    db: Session, client_id: int, payload: ClientContactCreate, *, user_id: int | None = None
) -> ClientContact:
    _client_or_404(db, client_id)
    contact = ClientContact(
        client_id=client_id,
        name=payload.name.strip(),
        email=_clean(payload.email),
        phone=_clean(payload.phone),
        position=_clean(payload.position),
    )
    db.add(contact)
    db.flush()
    write_audit_log(
        db,
        action="client.contact.created",
        entity="client_contacts",
        entity_id=contact.id,
        user_id=user_id,
        new_values={"client_id": client_id, **_snapshot(contact)},
    )
    db.commit()
    return contact


def update_client_contact(
    db: Session, client_id: int, contact_id: int, payload: ClientContactUpdate, *, user_id: int | None = None
) -> ClientContact:
    _client_or_404(db, client_id)
    contact = get_client_contact(db, client_id, contact_id)
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and not (updates["name"] or "").strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="El nombre del contacto es obligatorio")
    previous = _snapshot(contact)
    for key, value in updates.items():
        setattr(contact, key, (value or "").strip() if key == "name" else _clean(value))
    write_audit_log(
        db,
        action="client.contact.updated",
        entity="client_contacts",
        entity_id=contact.id,
        user_id=user_id,
        previous_values={"client_id": client_id, **previous},
        new_values={"client_id": client_id, **_snapshot(contact)},
    )
    db.commit()
    return contact


def set_client_contact_active(
    db: Session, client_id: int, contact_id: int, *, active: bool, user_id: int | None = None
) -> ClientContact:
    _client_or_404(db, client_id)
    contact = get_client_contact(db, client_id, contact_id)
    if contact.is_active == active:
        return contact
    contact.is_active = active
    contact.deleted_at = None if active else datetime.now(timezone.utc)
    contact.deleted_by = None if active else user_id
    write_audit_log(
        db,
        action="client.contact.restored" if active else "client.contact.deactivated",
        entity="client_contacts",
        entity_id=contact.id,
        user_id=user_id,
        previous_values={"is_active": not active},
        new_values={"client_id": client_id, "is_active": active},
    )
    db.commit()
    return contact
