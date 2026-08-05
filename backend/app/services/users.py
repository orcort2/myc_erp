from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password
from app.models.user import Role, User
from app.models.audit_log import AuditLog
from app.models.client_portal_membership import ClientPortalMembership
from app.core.portal.constants import PortalAccountType, UserAccountStatus
from app.schemas.user import UserAdminCreate
from app.services.audit_logs import write_audit_log
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


def _serialize_user_for_audit(user: User) -> dict:
    return {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "role_names": [role.name for role in user.roles],
    }


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
            .where(User.account_type == PortalAccountType.INTERNAL.value)
            .options(selectinload(User.roles))
            .order_by(User.created_at.desc())
        ).all()
    )


def list_roles(db: Session) -> list[Role]:
    ensure_initial_roles(db)
    return list(db.scalars(select(Role).order_by(Role.name)).all())


def list_user_activity(db: Session, user_id: int) -> list[AuditLog]:
    membership_ids = select(ClientPortalMembership.id).where(
        ClientPortalMembership.user_id == user_id
    )
    return list(
        db.scalars(
            select(AuditLog)
            .where(
                or_(
                    (AuditLog.entity == "users") & (AuditLog.entity_id == user_id),
                    (AuditLog.entity == "client_portal_memberships")
                    & (AuditLog.entity_id.in_(membership_ids)),
                    AuditLog.user_id == user_id,
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(100)
        ).all()
    )


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.scalar(
        select(User)
        .where(User.id == user_id, User.account_type == PortalAccountType.INTERNAL.value)
        .options(selectinload(User.roles))
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return user


def create_user_admin(
    db: Session,
    payload: UserAdminCreate,
    current_user: User | None = None,
) -> User:
    normalized_email = payload.email.strip().lower()
    normalized_username = payload.username.strip().lower()
    normalized_name = payload.full_name.strip()

    existing_user = db.scalar(
        select(User).where(
            or_(
                func.lower(User.email) == normalized_email,
                func.lower(User.username) == normalized_username,
            )
        )
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese correo o nombre de usuario.",
        )

    roles = _resolve_active_roles(db, payload.role_names)
    user = User(
        username=normalized_username,
        email=normalized_email,
        full_name=normalized_name,
        hashed_password=hash_password(payload.password),
        account_type=PortalAccountType.INTERNAL.value,
        status=UserAccountStatus.ACTIVE.value,
        is_active=True,
    )
    _assign_roles(user, roles)
    db.add(user)
    db.flush()
    write_audit_log(
        db,
        action="user.created",
        entity="users",
        entity_id=user.id,
        user_id=current_user.id if current_user else None,
        previous_values=None,
        new_values=_serialize_user_for_audit(user),
        comment="Usuario creado desde configuracion",
    )
    db.commit()
    return get_user_or_404(db, user.id)


def update_user_roles(
    db: Session,
    user_id: int,
    role_names: list[str],
    current_user: User | None = None,
) -> User:
    user = get_user_or_404(db, user_id)
    previous_values = _serialize_user_for_audit(user)
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
    write_audit_log(
        db,
        action="user.role_changed",
        entity="users",
        entity_id=user.id,
        user_id=current_user.id if current_user else None,
        previous_values=previous_values,
        new_values=_serialize_user_for_audit(user),
        comment="Cambio de rol de usuario",
    )
    db.commit()
    return get_user_or_404(db, user.id)


def update_user_status(
    db: Session,
    user_id: int,
    is_active: bool,
    current_user: User | None = None,
) -> User:
    user = get_user_or_404(db, user_id)
    previous_values = _serialize_user_for_audit(user)
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

    user.status = (
        UserAccountStatus.ACTIVE.value if is_active else UserAccountStatus.DISABLED.value
    )
    user.is_active = is_active
    db.add(user)
    write_audit_log(
        db,
        action="user.activated" if is_active else "user.deactivated",
        entity="users",
        entity_id=user.id,
        user_id=current_user.id if current_user else None,
        previous_values=previous_values,
        new_values=_serialize_user_for_audit(user),
        comment="Cambio de estado de usuario",
    )
    db.commit()
    return get_user_or_404(db, user.id)


def update_user_admin(
    db: Session,
    user_id: int,
    username: str | None = None,
    email: str | None = None,
    full_name: str | None = None,
    role_names: list[str] | None = None,
    is_active: bool | None = None,
    current_user: User | None = None,
    profile_values: dict | None = None,
) -> User:
    user = get_user_or_404(db, user_id)
    previous_values = _serialize_user_for_audit(user)
    changed_fields: set[str] = set()

    if username is not None:
        normalized_username = username.strip().lower()
        collision = db.scalar(
            select(User).where(
                func.lower(User.username) == normalized_username,
                User.id != user_id,
            )
        )
        if collision is not None:
            raise HTTPException(status_code=409, detail="El nombre de usuario ya está registrado.")
        if user.username != normalized_username:
            user.username = normalized_username
            changed_fields.add("username")

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
        if user.email != normalized_email:
            user.email = normalized_email
            changed_fields.add("email")

    if full_name is not None:
        normalized_name = full_name.strip()
        if user.full_name != normalized_name:
            user.full_name = normalized_name
            changed_fields.add("full_name")

    for key, value in (profile_values or {}).items():
        if value is not None and getattr(user, key) != value:
            setattr(user, key, value)
            changed_fields.add(key)

    if is_active is not None and user.is_active != is_active:
        update_user_status(db, user_id, is_active, current_user)
        user = get_user_or_404(db, user_id)
        previous_values = _serialize_user_for_audit(user)

    if role_names is not None:
        updated_user = update_user_roles(db, user_id, role_names, current_user)
        user = updated_user
        previous_values = _serialize_user_for_audit(user)

    if changed_fields:
        db.add(user)
        write_audit_log(
            db,
            action="user.updated",
            entity="users",
            entity_id=user.id,
            user_id=current_user.id if current_user else None,
            previous_values=previous_values,
            new_values=_serialize_user_for_audit(user),
            comment=f"Campos actualizados: {', '.join(sorted(changed_fields))}",
        )
        db.commit()

    return get_user_or_404(db, user.id)
