from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.user import Role, User
from app.services.auth import ensure_initial_roles


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


def update_user_roles(db: Session, user_id: int, role_names: list[str]) -> User:
    ensure_initial_roles(db)

    user = get_user_or_404(db, user_id)

    roles = list(db.scalars(select(Role).where(Role.name.in_(role_names))).all())
    found = {role.name for role in roles}
    missing = sorted(set(role_names) - found)

    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Roles no encontrados", "roles": missing},
        )

    user.roles = roles
    user.role_id = roles[0].id if roles else None

    db.add(user)
    db.commit()
    db.refresh(user)

    return get_user_or_404(db, user.id)


def update_user_status(db: Session, user_id: int, is_active: bool) -> User:
    user = get_user_or_404(db, user_id)
    user.is_active = is_active

    db.add(user)
    db.commit()
    db.refresh(user)

    return get_user_or_404(db, user.id)