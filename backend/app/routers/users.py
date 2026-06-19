from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.user import RoleRead, UserAdminRead, UserRolesUpdate, UserStatusUpdate
from app.services.auth import require_permission
from app.services.users import (
    list_roles,
    list_users,
    update_user_roles,
    update_user_status,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserAdminRead])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.read")),
) -> list[User]:
    return list_users(db)


@router.get("/roles", response_model=list[RoleRead])
def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.read")),
) -> list:
    return list_roles(db)


@router.patch("/{user_id}/roles", response_model=UserAdminRead)
def patch_user_roles(
    user_id: int,
    payload: UserRolesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
) -> User:
    return update_user_roles(db, user_id, payload.role_names)


@router.patch("/{user_id}/status", response_model=UserAdminRead)
def patch_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
) -> User:
    return update_user_status(db, user_id, payload.is_active)