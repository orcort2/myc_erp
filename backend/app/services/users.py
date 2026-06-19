from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password
from app.models.user import Role, User
from app.schemas.user import UserAdminCreate
from app.services.auth import ensure_initial_roles


def _normalize_role_names(role_names: list[str]) -> list[str]:
    normalized = [name.strip() for name in role_names if name and name.strip()]
    unique_names = list(dict.fromkeys(normalized))
    if not unique_names:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Debes asignar al menos un rol activo al usuario.",
        )
    return unique_names


def _resolve_active_roles(db: Session, role_names: list[str]) -> list[Role]:
    ensure_initial_roles(db)
    normalized_names = _normalize_role_names(role_names)
    roles = list(
        db.scalars(
            select(Role)
            .where(Role.name.in_(normalized_names))
            .where(Role.is_active == True)
            .order_by(Role.name)
        ).all()
    )
    found = {role.name for role in roles}
    missing = sorted(set(normalized_names) - found)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Roles no encontrados", "roles": missing},
        )
    return sorted(roles, key=lambda role: normalized_names.index(role.name))


def _assign_roles(user: User, roles: list[Role]) -> None:
    user.roles = roles
    primary_role = roles[0] if roles else None
    user.role_id = primary_role.id if primary_role else None


def count_active_admins(db: Session) -> int:
    return (
        db.scalar(
            select(func.count(User.id))
            .join(User.roles)
            .where(Role.name == "Administrador")
            .where(User.is_active == True)
        )
        or 0
    )


def list_users(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .options(selectinload(User.roles))
            .order_by(User.created_at.desc())
        ).all()
    )


def list_roles(db: Session) -> list[Role]:
    ensure_initial_roles(db)
    return list(db.scalars(select(Role).order_by(Role.name)).all())


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles))
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return user


def create_user_admin(db: Session, payload: UserAdminCreate) -> User:
    normalized_email = payload.email.strip().lower()
    normalized_name = payload.full_name.strip()

    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese correo.",
        )

    roles = _resolve_active_roles(db, payload.role_names)
    user = User(
        email=normalized_email,
        full_name=normalized_name,
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    _assign_roles(user, roles)
    db.add(user)
    db.commit()
    return get_user_or_404(db, user.id)


def update_user_roles(
    db: Session,
    user_id: int,
    role_names: list[str],
    current_user: User | None = None,
) -> User:
    user = get_user_or_404(db, user_id)
    roles = _resolve_active_roles(db, role_names)

    current_roles = {role.name for role in user.roles}
    new_roles = {role.name for role in roles}
    is_removing_admin = "Administrador" in current_roles and "Administrador" not in new_roles

    if is_removing_admin:
        if current_user and current_user.id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes quitarte a ti mismo el rol Administrador.",
            )
        if user.is_active and count_active_admins(db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes quitar el rol Administrador al último administrador activo.",
            )

    _assign_roles(user, roles)
    db.add(user)
    db.commit()
    return get_user_or_404(db, user.id)


def update_user_status(
    db: Session,
    user_id: int,
    is_active: bool,
    current_user: User | None = None,
) -> User:
    user = get_user_or_404(db, user_id)
    current_roles = {role.name for role in user.roles}

    if user.is_active and not is_active:
        if current_user and current_user.id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes desactivar tu propia cuenta.",
            )
        if "Administrador" in current_roles and count_active_admins(db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes desactivar al último administrador activo.",
            )

    user.is_active = is_active
    db.add(user)
    db.commit()
    return get_user_or_404(db, user.id)


def update_user_admin(
    db: Session,
    user_id: int,
    email: str | None = None,
    full_name: str | None = None,
    role_names: list[str] | None = None,
    is_active: bool | None = None,
    current_user: User | None = None,
) -> User:
    user = get_user_or_404(db, user_id)

    if email is not None:
        normalized_email = email.strip().lower()
        existing_user = db.scalar(
            select(User).where(User.email == normalized_email, User.id != user_id)
        )
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un usuario con ese correo.",
            )
        user.email = normalized_email

    if full_name is not None:
        user.full_name = full_name.strip()

    if is_active is not None and user.is_active != is_active:
        update_user_status(db, user_id, is_active, current_user)
        user = get_user_or_404(db, user_id)

    if role_names is not None:
        updated_user = update_user_roles(db, user_id, role_names, current_user)
        user = updated_user

    if email is not None or full_name is not None:
        db.add(user)
        db.commit()

    return get_user_or_404(db, user.id)
