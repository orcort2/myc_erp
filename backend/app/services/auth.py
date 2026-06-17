from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import Role, User
from app.schemas.auth import UserLogin, UserRegister


INITIAL_ROLES = {
    "Administrador": "Acceso total al sistema.",
    "Comercial": "Gestion comercial, clientes y cotizaciones.",
    "Tecnico": "Gestion tecnica de equipos y hojas de campo.",
    "Captura": "Captura y generacion documental.",
    "Calidad": "Revision y aprobacion de certificados.",
    "Finanzas": "Pagos, facturacion y liberacion financiera.",
    "Cliente": "Acceso limitado para cliente externo.",
}

ROLE_PERMISSIONS = {
    "Administrador": {"*"},
    "Comercial": {"clients.*", "quotations.*", "service_orders.*"},
    "Tecnico": {"equipment.*", "field_sheets.*"},
    "Captura": {"certificates.create", "certificates.generate", "field_sheets.read"},
    "Calidad": {"certificates.quality", "certificates.approve", "field_sheets.read"},
    "Finanzas": {"payments.*", "invoices.*", "release.*"},
    "Cliente": {"portal.read"},
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def ensure_initial_roles(db: Session) -> None:
    existing_names = set(db.scalars(select(Role.name)).all())
    for name, description in INITIAL_ROLES.items():
        if name not in existing_names:
            db.add(Role(name=name, description=description))
    db.flush()


def _get_roles_by_names(db: Session, role_names: list[str]) -> list[Role]:
    ensure_initial_roles(db)
    roles = list(db.scalars(select(Role).where(Role.name.in_(role_names))).all())
    found = {role.name for role in roles}
    missing = sorted(set(role_names) - found)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Roles no encontrados", "roles": missing},
        )
    return roles


def _get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User)
        .where(User.email == email)
        .options(selectinload(User.roles))
    )


def _build_tokens(user: User) -> dict:
    role_names = [role.name for role in user.roles if role.is_active]
    claims = {"roles": role_names}
    return {
        "access_token": create_access_token(str(user.id), extra_claims=claims),
        "refresh_token": create_refresh_token(str(user.id), extra_claims=claims),
        "token_type": "bearer",
        "user": user,
    }


def register_user(db: Session, payload: UserRegister) -> dict:
    ensure_initial_roles(db)
    existing_user = _get_user_by_email(db, payload.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya esta registrado",
        )

    user_count = db.scalar(select(func.count(User.id))) or 0
    role_names = payload.role_names
    if not role_names:
        role_names = ["Administrador"] if user_count == 0 else ["Cliente"]
    roles = _get_roles_by_names(db, role_names)
    primary_role = roles[0] if roles else None

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role_id=primary_role.id if primary_role else None,
    )
    user.roles = roles
    db.add(user)
    db.commit()
    return _build_tokens(_get_user(db, user.id))


def authenticate_user(db: Session, payload: UserLogin) -> dict:
    user = _get_user_by_email(db, payload.email)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
        )
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
        )
    return _build_tokens(user)


def _get_user(db: Session, user_id: int) -> User:
    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles))
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no autenticado",
        )
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        ) from exc
    return _get_user(db, user_id)


def refresh_tokens(db: Session, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
        if payload.get("token_type") != "refresh":
            raise ValueError("Token no es refresh")
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido",
        ) from exc
    return _build_tokens(_get_user(db, user_id))


def user_has_permission(user: User, permission: str) -> bool:
    for role in user.roles:
        if not role.is_active:
            continue
        permissions = ROLE_PERMISSIONS.get(role.name, set())
        if "*" in permissions or permission in permissions:
            return True
        prefix = permission.split(".", 1)[0]
        if f"{prefix}.*" in permissions:
            return True
    return False


def require_permission(permission: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not user_has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permiso insuficiente",
            )
        return current_user

    return dependency
