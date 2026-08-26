from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.client import Client
from app.models.client_portal_permission import ClientPortalPermission
from app.models.client_portal_role import ClientPortalRole
from app.models.client_portal_role_permission import ClientPortalRolePermission


def serialize(role: ClientPortalRole) -> dict:
    return {"id": role.id, "client_id": role.client_id, "code": role.code, "name": role.name, "description": role.description, "is_system": role.is_system, "permission_codes": [link.permission.code for link in role.role_permissions]}


def list_roles(
    db: Session,
    client_id: int | None = None,
    *,
    include_mobile: bool = True,
) -> list[dict]:
    query = select(ClientPortalRole).where(ClientPortalRole.is_active.is_(True)).options(selectinload(ClientPortalRole.role_permissions).selectinload(ClientPortalRolePermission.permission)).order_by(ClientPortalRole.is_system.desc(), ClientPortalRole.name)
    if client_id is not None:
        query = query.where((ClientPortalRole.client_id.is_(None)) | (ClientPortalRole.client_id == client_id))
    roles = [serialize(role) for role in db.scalars(query).all()]
    if not include_mobile:
        roles = [
            role for role in roles
            if "mobile.access" not in role["permission_codes"]
        ]
    return roles


def list_permissions(db: Session) -> list[ClientPortalPermission]:
    return list(db.scalars(select(ClientPortalPermission).where(ClientPortalPermission.is_active.is_(True)).order_by(ClientPortalPermission.module, ClientPortalPermission.code)).all())


def create_role(db: Session, *, client_id: int, code: str, name: str, description: str | None, permission_codes: list[str]) -> dict:
    if db.get(Client, client_id) is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    full_code = f"client_{client_id}_{code}"
    if db.scalar(select(ClientPortalRole).where(ClientPortalRole.code == full_code)):
        raise HTTPException(status_code=409, detail="El rol ya existe")
    permissions = list(db.scalars(select(ClientPortalPermission).where(ClientPortalPermission.code.in_(permission_codes), ClientPortalPermission.is_active.is_(True))).all())
    if {item.code for item in permissions} != set(permission_codes):
        raise HTTPException(status_code=422, detail="Uno o más permisos no existen")
    role = ClientPortalRole(client_id=client_id, code=full_code, name=name, description=description, is_system=False)
    db.add(role); db.flush()
    for permission in permissions:
        db.add(ClientPortalRolePermission(role_id=role.id, permission_id=permission.id))
    db.commit()
    return serialize(db.scalar(select(ClientPortalRole).where(ClientPortalRole.id == role.id).options(selectinload(ClientPortalRole.role_permissions).selectinload(ClientPortalRolePermission.permission))))


def archive_role(db: Session, role_id: int) -> None:
    role = db.get(ClientPortalRole, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if role.is_system:
        raise HTTPException(status_code=409, detail="Los roles base no pueden eliminarse")
    if role.membership_roles or role.invitation_roles:
        raise HTTPException(status_code=409, detail="El rol está en uso")
    role.is_active = False
    db.commit()
