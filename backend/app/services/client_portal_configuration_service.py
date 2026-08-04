from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.client_portal import ClientPortal
from app.services.audit_logs import write_audit_log


def get_configuration(db: Session, client_id: int) -> ClientPortal | None:
    return db.scalar(select(ClientPortal).where(ClientPortal.client_id == client_id, ClientPortal.is_active.is_(True)))


def save_configuration(db: Session, client_id: int, values: dict, actor_id: int) -> ClientPortal:
    if db.get(Client, client_id) is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    item = get_configuration(db, client_id)
    if item is None:
        item = ClientPortal(client_id=client_id, created_by=actor_id, **values)
        db.add(item)
    else:
        for key, value in values.items():
            setattr(item, key, value)
        item.updated_by = actor_id
    db.flush()
    write_audit_log(db, action="portal.configuration.updated", entity="client_portals", entity_id=item.id, user_id=actor_id, new_values={"client_id": client_id, **values})
    db.commit()
    db.refresh(item)
    return item
