from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.portal.constants import (
    DEFAULT_EMAIL_VERIFICATION_TOKEN_TTL_HOURS,
    PortalRegistrationStatus,
    UserAccountStatus,
)
from app.models.notification import Notification
from app.models.portal_registration import PortalRegistration
from app.models.user import Role, User
from app.schemas.portal.registration import PortalRegistrationCreate
from app.services.audit_logs import write_audit_log
from app.services.portal.account_service import (
    create_portal_account,
    get_user_by_email,
    mark_portal_email_verified,
    normalize_portal_email,
)


PORTAL_REGISTRATION_NOTIFICATION_TYPE = "portal_registration_created"

PORTAL_REGISTRATION_REVIEW_ROLES = frozenset(
    {
        "Administrador",
        "Comercial",
    }
)


@dataclass(frozen=True, slots=True)
class PortalRegistrationCreationResult:
    """
    Resultado interno de la creación de un registro.

    ``verification_token`` contiene el token original que deberá enviarse al
    correo de la persona. Nunca debe persistirse ni incluirse en respuestas
    públicas de la API.
    """

    registration: PortalRegistration
    verification_token: str


@dataclass(frozen=True, slots=True)
class PortalRegistrationResendResult:
    """
    Resultado interno del reenvío de verificación.

    Cuando no existe una cuenta elegible, ``verification_token`` será nulo.
    Esto permite que el endpoint devuelva una respuesta uniforme y evite
    revelar qué correos están registrados.
    """

    registration: PortalRegistration | None
    verification_token: str | None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_verification_token() -> str:
    """
    Genera un token criptográficamente seguro para verificar el correo.
    """

    return secrets.token_urlsafe(48)


def hash_verification_token(token: str) -> str:
    """
    Produce el hash SHA-256 persistido en la base de datos.

    El token original sólo existe durante la solicitud que lo genera y se
    entrega posteriormente al mecanismo de correo.
    """

    normalized = token.strip()

    if not normalized:
        raise ValueError("El token de verificación no puede estar vacío.")

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_registration_by_id(
    db: Session,
    registration_id: int,
) -> PortalRegistration | None:
    return db.scalar(
        select(PortalRegistration)
        .options(joinedload(PortalRegistration.user))
        .where(
            PortalRegistration.id == registration_id,
            PortalRegistration.deleted_at.is_(None),
        )
    )


def get_registration_or_404(
    db: Session,
    registration_id: int,
) -> PortalRegistration:
    registration = get_registration_by_id(
        db,
        registration_id,
    )

    if registration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro del portal no encontrado.",
        )

    return registration


def get_registration_by_user_id(
    db: Session,
    user_id: int,
) -> PortalRegistration | None:
    return db.scalar(
        select(PortalRegistration)
        .options(joinedload(PortalRegistration.user))
        .where(
            PortalRegistration.user_id == user_id,
            PortalRegistration.deleted_at.is_(None),
        )
    )


def get_registration_by_email(
    db: Session,
    email: str,
) -> PortalRegistration | None:
    normalized_email = normalize_portal_email(email)

    return db.scalar(
        select(PortalRegistration)
        .join(
            User,
            User.id == PortalRegistration.user_id,
        )
        .options(joinedload(PortalRegistration.user))
        .where(
            User.email == normalized_email,
            PortalRegistration.deleted_at.is_(None),
        )
    )


def list_internal_registration_reviewers(
    db: Session,
) -> list[User]:
    """
    Obtiene usuarios internos activos con rol Administrador o Comercial.

    Considera tanto el rol principal histórico ``role`` como la relación
    muchos-a-muchos ``roles``.
    """

    reviewer_roles = tuple(PORTAL_REGISTRATION_REVIEW_ROLES)

    reviewers = list(
        db.scalars(
            select(User)
            .where(
                User.account_type == "internal",
                User.status == UserAccountStatus.ACTIVE.value,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                or_(
                    User.role.has(
                        Role.name.in_(reviewer_roles),
                    ),
                    User.roles.any(
                        Role.name.in_(reviewer_roles),
                    ),
                ),
            )
            .order_by(User.id.asc())
        )
        .unique()
        .all()
    )

    return reviewers


def create_registration_notifications(
    db: Session,
    *,
    registration: PortalRegistration,
) -> list[Notification]:
    """
    Notifica al personal Comercial y Administrador sobre el nuevo registro.

    No ejecuta ``commit``. Las notificaciones forman parte de la misma
    transacción que el registro.
    """

    reviewers = list_internal_registration_reviewers(db)

    notifications: list[Notification] = []

    for reviewer in reviewers:
        notification = Notification(
            recipient_user_id=reviewer.id,
            actor_user_id=None,
            notification_type=PORTAL_REGISTRATION_NOTIFICATION_TYPE,
            title="Nuevo usuario registrado en el portal",
            body=(
                f"{registration.user.full_name} registró una cuenta para "
                f"{registration.declared_company_name}."
            ),
            entity_type="portal_registration",
            entity_id=registration.id,
            activity_message_id=None,
            priority="normal",
            metadata_json={
                "registration_id": registration.id,
                "user_id": registration.user_id,
                "email": registration.user.email,
                "declared_company_name": (
                    registration.declared_company_name
                ),
                "declared_company_rfc": (
                    registration.declared_company_rfc
                ),
                "frontend_path": (
                    f"/settings/users?registration_id={registration.id}"
                ),
            },
        )

        db.add(notification)
        notifications.append(notification)

    return notifications


def create_public_registration(
    db: Session,
    *,
    payload: PortalRegistrationCreate,
) -> PortalRegistrationCreationResult:
    """
    Crea un registro público pendiente de verificación.

    La operación se confirma como una sola transacción:

    - cuenta de usuario;
    - registro público;
    - token de verificación;
    - auditoría;
    - notificaciones internas.

    El envío del correo debe realizarse después del commit. Si ese envío falla,
    el usuario podrá solicitar otro token mediante el flujo de reenvío.
    """

    verification_token = generate_verification_token()
    token_hash = hash_verification_token(verification_token)
    now = utc_now()

    try:
        user = create_portal_account(
            db,
            username=payload.username,
            email=str(payload.email),
            full_name=payload.full_name,
            password=payload.password,
            initial_status=UserAccountStatus.PENDING,
            email_verified_at=None,
            created_by_user_id=None,
            audit_comment=(
                "Cuenta creada mediante registro público del Portal del "
                "Cliente."
            ),
        )

        registration = PortalRegistration(
            user_id=user.id,
            declared_company_name=payload.declared_company_name,
            declared_company_rfc=payload.declared_company_rfc,
            contact_phone=payload.contact_phone,
            job_title=payload.job_title,
            status=(
                PortalRegistrationStatus
                .PENDING_EMAIL_VERIFICATION
                .value
            ),
            email_verified_at=None,
            verification_token_hash=token_hash,
            verification_token_expires_at=(
                now
                + timedelta(
                    hours=(
                        DEFAULT_EMAIL_VERIFICATION_TOKEN_TTL_HOURS
                    )
                )
            ),
            last_internal_review_at=None,
            internal_notes=None,
            is_active=True,
        )

        db.add(registration)
        db.flush()

        # Garantiza que la relación esté disponible para notificaciones y
        # serialización sin depender de una recarga posterior.
        registration.user = user

        create_registration_notifications(
            db,
            registration=registration,
        )

        write_audit_log(
            db,
            action="portal.registration.created",
            entity="portal_registrations",
            entity_id=registration.id,
            user_id=None,
            previous_values=None,
            new_values={
                "user_id": registration.user_id,
                "declared_company_name": (
                    registration.declared_company_name
                ),
                "declared_company_rfc": (
                    registration.declared_company_rfc
                ),
                "contact_phone": registration.contact_phone,
                "job_title": registration.job_title,
                "status": registration.status,
                "verification_token_expires_at": (
                    registration
                    .verification_token_expires_at
                    .isoformat()
                ),
            },
            comment="Registro público del Portal del Cliente creado.",
        )

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No fue posible completar el registro porque la cuenta "
                "ya existe o los datos entraron en conflicto."
            ),
        ) from exc

    except Exception:
        db.rollback()
        raise

    registration = get_registration_or_404(
        db,
        registration.id,
    )

    return PortalRegistrationCreationResult(
        registration=registration,
        verification_token=verification_token,
    )


def verify_registration_email(
    db: Session,
    *,
    token: str,
) -> PortalRegistration:
    """
    Verifica el correo asociado con un registro público.

    La verificación es idempotente: si el registro ya fue verificado,
    devuelve su estado actual sin volver a ejecutar la transición.
    """

    token_hash = hash_verification_token(token)
    now = utc_now()

    registration = db.scalar(
        select(PortalRegistration)
        .options(joinedload(PortalRegistration.user))
        .where(
            PortalRegistration.verification_token_hash == token_hash,
            PortalRegistration.deleted_at.is_(None),
            PortalRegistration.is_active.is_(True),
        )
    )

    if registration is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de verificación no es válido.",
        )

    if registration.email_verified_at is not None:
        return registration

    if (
        registration.verification_token_expires_at is None
        or registration.verification_token_expires_at <= now
    ):
        registration.status = (
            PortalRegistrationStatus.EXPIRED.value
        )

        db.add(registration)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "El enlace de verificación venció. Solicita uno nuevo."
            ),
        )

    previous_values = {
        "status": registration.status,
        "email_verified_at": None,
        "verification_token_expires_at": (
            registration.verification_token_expires_at.isoformat()
        ),
    }

    try:
        mark_portal_email_verified(
            db,
            user=registration.user,
            verified_at=now,
            actor_user_id=None,
        )

        registration.email_verified_at = now
        registration.status = (
            PortalRegistrationStatus.PENDING_REVIEW.value
        )
        registration.verification_token_hash = None
        registration.verification_token_expires_at = None

        db.add(registration)

        write_audit_log(
            db,
            action="portal.registration.email_verified",
            entity="portal_registrations",
            entity_id=registration.id,
            user_id=registration.user_id,
            previous_values=previous_values,
            new_values={
                "status": registration.status,
                "email_verified_at": (
                    registration.email_verified_at.isoformat()
                ),
                "verification_token_expires_at": None,
            },
            comment=(
                "Correo del registro público del portal verificado."
            ),
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return get_registration_or_404(
        db,
        registration.id,
    )


def resend_registration_verification(
    db: Session,
    *,
    email: str,
) -> PortalRegistrationResendResult:
    """
    Renueva el token de verificación cuando el registro sigue pendiente.

    No lanza 404 cuando el correo no existe. El endpoint debe devolver siempre
    un mensaje genérico para evitar enumeración de cuentas.
    """

    normalized_email = normalize_portal_email(email)

    user = get_user_by_email(
        db,
        normalized_email,
    )

    if user is None:
        return PortalRegistrationResendResult(
            registration=None,
            verification_token=None,
        )

    registration = get_registration_by_user_id(
        db,
        user.id,
    )

    if registration is None:
        return PortalRegistrationResendResult(
            registration=None,
            verification_token=None,
        )

    if registration.email_verified_at is not None:
        return PortalRegistrationResendResult(
            registration=None,
            verification_token=None,
        )

    if registration.status in {
        PortalRegistrationStatus.REJECTED.value,
        PortalRegistrationStatus.CANCELLED.value,
        PortalRegistrationStatus.LINKED.value,
    }:
        return PortalRegistrationResendResult(
            registration=None,
            verification_token=None,
        )

    verification_token = generate_verification_token()
    now = utc_now()

    previous_values = {
        "status": registration.status,
        "verification_token_expires_at": (
            registration.verification_token_expires_at.isoformat()
            if registration.verification_token_expires_at
            else None
        ),
    }

    try:
        registration.status = (
            PortalRegistrationStatus
            .PENDING_EMAIL_VERIFICATION
            .value
        )
        registration.verification_token_hash = (
            hash_verification_token(verification_token)
        )
        registration.verification_token_expires_at = (
            now
            + timedelta(
                hours=DEFAULT_EMAIL_VERIFICATION_TOKEN_TTL_HOURS
            )
        )

        db.add(registration)

        write_audit_log(
            db,
            action="portal.registration.verification_resent",
            entity="portal_registrations",
            entity_id=registration.id,
            user_id=registration.user_id,
            previous_values=previous_values,
            new_values={
                "status": registration.status,
                "verification_token_expires_at": (
                    registration
                    .verification_token_expires_at
                    .isoformat()
                ),
            },
            comment=(
                "Token de verificación del registro público renovado."
            ),
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return PortalRegistrationResendResult(
        registration=get_registration_or_404(
            db,
            registration.id,
        ),
        verification_token=verification_token,
    )


def registration_has_portal_access(
    registration: PortalRegistration,
) -> bool:
    """
    El registro público sólo concede acceso cuando su vinculación terminó.

    La validación final de acceso deberá comprobar además la existencia de una
    membresía activa. Esta función únicamente resume el estado del registro.
    """

    return registration.status == PortalRegistrationStatus.LINKED.value