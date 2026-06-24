from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.user import (
    RoleRead,
    UserAdminCreate,
    UserAdminRead,
    UserAdminUpdate,
    UserRolesUpdate,
    UserStatusUpdate,
)
from app.services.auth import require_permission
from app.services.users import (
    create_user_admin,
    list_roles,
    list_users,
    update_user_admin,
    update_user_roles,
    update_user_status,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserAdminRead, status_code=201)
def post_user_admin(
    payload: UserAdminCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
) -> User:
    return create_user_admin(db, payload, current_user)


@router.patch("/{user_id}", response_model=UserAdminRead)
def patch_user_admin(
    user_id: int,
    payload: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
) -> User:
    return update_user_admin(
        db=db,
        user_id=user_id,
        email=payload.email,
        full_name=payload.full_name,
        role_names=payload.role_names,
        is_active=payload.is_active,
        current_user=current_user,
    )

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
    return update_user_roles(db, user_id, payload.role_names, current_user)


@router.patch("/{user_id}/status", response_model=UserAdminRead)
def patch_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage")),
) -> User:
    return update_user_status(db, user_id, payload.is_active, current_user)
