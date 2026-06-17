from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.client import Client, ClientContact
from app.schemas.client import ClientCreate, ClientUpdate
from app.services.audit_logs import write_audit_log


def list_clients(db: Session, *, include_inactive: bool = False) -> list[Client]:
    query = select(Client).options(selectinload(Client.contacts)).order_by(Client.legal_name)
    if not include_inactive:
        query = query.where(Client.is_active.is_(True))
    return list(db.scalars(query).all())


def get_client(db: Session, client_id: int) -> Client:
    client = db.scalar(
        select(Client)
        .where(Client.id == client_id)
        .options(selectinload(Client.contacts))
    )
    if client is None or not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return client


def create_client(db: Session, payload: ClientCreate, *, user_id: int | None = None) -> Client:
    client = Client(**payload.model_dump(exclude={"contacts"}))
    client.contacts = [
        ClientContact(**contact.model_dump()) for contact in payload.contacts
    ]
    db.add(client)
    db.flush()
    write_audit_log(
        db,
        action="client.created",
        entity="clients",
        entity_id=client.id,
        user_id=user_id,
        new_values={"legal_name": client.legal_name, "rfc": client.rfc},
    )
    db.commit()
    db.refresh(client)
    return get_client(db, client.id)


def update_client(
    db: Session,
    client_id: int,
    payload: ClientUpdate,
    *,
    user_id: int | None = None,
) -> Client:
    client = get_client(db, client_id)
    updates = payload.model_dump(exclude_unset=True)
    previous_values = {key: getattr(client, key) for key in updates}
    for key, value in updates.items():
        setattr(client, key, value)
    write_audit_log(
        db,
        action="client.updated",
        entity="clients",
        entity_id=client.id,
        user_id=user_id,
        previous_values=previous_values,
        new_values=updates,
    )
    db.commit()
    db.refresh(client)
    return get_client(db, client.id)


def deactivate_client(
    db: Session,
    client_id: int,
    *,
    user_id: int | None = None,
) -> Client:
    client = get_client(db, client_id)
    client.is_active = False
    client.deleted_at = datetime.now(timezone.utc)
    client.deleted_by = user_id
    write_audit_log(
        db,
        action="client.deactivated",
        entity="clients",
        entity_id=client.id,
        user_id=user_id,
        previous_values={"is_active": True},
        new_values={"is_active": False},
    )
    db.commit()
    db.refresh(client)
    return client

