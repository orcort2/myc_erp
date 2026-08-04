from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.portal.constants import (
    PortalAccountType,
    UserAccountStatus,
)
from app.core.security import hash_password
from app.models.user import User
from app.services.audit_logs import write_audit_log


def normalize_portal_username(username: str) -> str:
    """
    Normaliza el nombre de usuario antes de consultar o persistir.

    El schema ya realiza esta normalización, pero el servicio también la
    aplica porque puede ser reutilizado por invitaciones, procesos internos
    o pruebas sin pasar necesariamente por el mismo schema.
    """

    normalized = username.strip().lower()

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El nombre de usuario es obligatorio.",
        )

    return normalized


def normalize_portal_email(email: str) -> str:
    """
    Normaliza el correo para mantener comparaciones consistentes.
    """

    normalized = email.strip().lower()

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El correo es obligatorio.",
        )

    return normalized


def normalize_portal_full_name(full_name: str) -> str:
    """
    Elimina espacios duplicados sin alterar deliberadamente mayúsculas,
    acentos o la escritura original del nombre de la persona.
    """

    normalized = " ".join(full_name.split())

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El nombre completo es obligatorio.",
        )

    return normalized


def get_user_by_username(
    db: Session,
    username: str,
) -> User | None:
    """
    Busca una cuenta por nombre de usuario sin distinguir mayúsculas.

    No filtra por `is_active` ni por borrado lógico porque los identificadores
    únicos no deben reutilizarse silenciosamente.
    """

    normalized = normalize_portal_username(username)

    return db.scalar(
        select(User).where(
            func.lower(User.username) == normalized,
        )
    )


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    """
    Busca una cuenta por correo sin distinguir mayúsculas.

    Incluye cuentas inactivas o eliminadas lógicamente para impedir que una
    identidad existente se registre otra vez con el mismo correo.
    """

    normalized = normalize_portal_email(email)

    return db.scalar(
        select(User).where(
            func.lower(User.email) == normalized,
        )
    )


def get_portal_user_or_404(
    db: Session,
    user_id: int,
) -> User:
    """
    Obtiene exclusivamente una cuenta perteneciente al Portal del Cliente.
    """

    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.account_type == PortalAccountType.CLIENT_PORTAL.value,
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuenta del portal no encontrada.",
        )

    return user


def ensure_portal_identity_available(
    db: Session,
    *,
    username: str,
    email: str,
) -> None:
    """
    Verifica que el usuario y el correo estén disponibles.

    Se consulta en una sola operación para reducir viajes a la base de datos.
    """

    normalized_username = normalize_portal_username(username)
    normalized_email = normalize_portal_email(email)

    existing_user = db.scalar(
        select(User).where(
            or_(
                func.lower(User.username) == normalized_username,
                func.lower(User.email) == normalized_email,
            )
        )
    )

    if existing_user is None:
        return

    username_conflict = (
        existing_user.username.strip().lower() == normalized_username
    )
    email_conflict = (
        existing_user.email.strip().lower() == normalized_email
    )

    if username_conflict and email_conflict:
        detail = (
            "Ya existe una cuenta con ese nombre de usuario y correo."
        )
    elif username_conflict:
        detail = "El nombre de usuario ya está registrado."
    else:
        detail = "El correo ya está registrado."

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


def create_portal_account(
    db: Session,
    *,
    username: str,
    email: str,
    full_name: str,
    password: str,
    initial_status: UserAccountStatus = UserAccountStatus.PENDING,
    email_verified_at: datetime | None = None,
    created_by_user_id: int | None = None,
    audit_comment: str = "Cuenta creada para el Portal del Cliente.",
) -> User:
    """
    Crea una identidad autenticable para el Portal del Cliente.

    Responsabilidades:

    - normalizar identidad;
    - validar duplicados;
    - cifrar la contraseña;
    - establecer el tipo y estado de cuenta;
    - registrar auditoría;
    - ejecutar `flush`, pero no `commit`.

    La transacción pertenece al servicio orquestador. Por ejemplo,
    `PortalRegistrationService` debe crear conjuntamente:

    - User
    - PortalRegistration
    - token de verificación
    - notificaciones y auditoría asociada

    y realizar un único `commit` al final.
    """

    normalized_username = normalize_portal_username(username)
    normalized_email = normalize_portal_email(email)
    normalized_full_name = normalize_portal_full_name(full_name)

    ensure_portal_identity_available(
        db,
        username=normalized_username,
        email=normalized_email,
    )

    user = User(
        username=normalized_username,
        email=normalized_email,
        full_name=normalized_full_name,
        hashed_password=hash_password(password),
        account_type=PortalAccountType.CLIENT_PORTAL.value,
        status=initial_status.value,
        email_verified_at=email_verified_at,
        last_login_at=None,
        password_changed_at=datetime.now(timezone.utc),
        must_change_password=False,
        failed_login_attempts=0,
        locked_until=None,
        role_id=None,
        is_active=True,
    )

    try:
        # El SAVEPOINT permite convertir una colisión concurrente en 409
        # sin cancelar obligatoriamente toda la transacción exterior.
        with db.begin_nested():
            db.add(user)
            db.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No fue posible crear la cuenta porque el usuario o correo "
                "ya está registrado."
            ),
        ) from exc

    write_audit_log(
        db,
        action="portal.account.created",
        entity="users",
        entity_id=user.id,
        user_id=created_by_user_id,
        previous_values=None,
        new_values={
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "account_type": user.account_type,
            "status": user.status,
            "email_verified": user.email_verified_at is not None,
            "is_active": user.is_active,
        },
        comment=audit_comment,
    )

    return user


def mark_portal_email_verified(
    db: Session,
    *,
    user: User,
    verified_at: datetime | None = None,
    actor_user_id: int | None = None,
) -> User:
    """
    Marca el correo como verificado sin habilitar todavía una membresía.

    La verificación del correo confirma la identidad del buzón, pero no
    autoriza acceso a los datos de ningún cliente.
    """

    if user.account_type != PortalAccountType.CLIENT_PORTAL.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La cuenta indicada no pertenece al Portal del Cliente.",
        )

    if user.email_verified_at is not None:
        return user

    previous_values = {
        "email_verified_at": None,
        "status": user.status,
    }

    verification_time = verified_at or datetime.now(timezone.utc)

    user.email_verified_at = verification_time

    if user.status == UserAccountStatus.PENDING.value:
        # La cuenta sigue pendiente de vinculación, pero el correo ya quedó
        # validado. El acceso efectivo dependerá de una membresía activa.
        user.status = UserAccountStatus.ACTIVE.value

    db.add(user)
    db.flush()

    write_audit_log(
        db,
        action="portal.account.email_verified",
        entity="users",
        entity_id=user.id,
        user_id=actor_user_id,
        previous_values=previous_values,
        new_values={
            "email_verified_at": user.email_verified_at.isoformat(),
            "status": user.status,
        },
        comment="Correo de cuenta del portal verificado.",
    )

    return user