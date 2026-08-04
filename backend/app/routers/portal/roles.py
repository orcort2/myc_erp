from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.portal.role import PortalPermissionRead, PortalRoleCreate, PortalRoleRead
from app.services.auth import require_permission
from app.services.portal.role_service import archive_role, create_role, list_permissions, list_roles

router = APIRouter(prefix="/client-portal/roles", tags=["client-portal-roles"])


@router.get("", response_model=list[PortalRoleRead])
def get_roles(client_id: int | None = None, db: Session = Depends(get_db), _actor: User = Depends(require_permission("users.manage"))):
    return list_roles(db, client_id)


@router.get("/permissions", response_model=list[PortalPermissionRead])
def get_permissions(db: Session = Depends(get_db), _actor: User = Depends(require_permission("users.manage"))):
    return list_permissions(db)


@router.post("", response_model=PortalRoleRead, status_code=201)
def post_role(payload: PortalRoleCreate, db: Session = Depends(get_db), _actor: User = Depends(require_permission("users.manage"))):
    return create_role(db, **payload.model_dump())


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(role_id: int, response: Response, db: Session = Depends(get_db), _actor: User = Depends(require_permission("users.manage"))):
    archive_role(db, role_id)
    response.status_code = status.HTTP_204_NO_CONTENT
