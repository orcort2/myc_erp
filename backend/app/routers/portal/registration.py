from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.portal.registration import (
    PortalRegistrationCreate,
    PortalRegistrationCreated,
    PortalRegistrationEmailResend,
    PortalRegistrationEmailVerification,
    PortalRegistrationStatusRead,
    PortalRegistrationVerificationResult,
)
from app.services.portal.registration_service import (
    create_public_registration,
    get_registration_or_404,
    registration_has_portal_access,
    resend_registration_verification,
    verify_registration_email,
)
from app.models.user import User
from app.services.auth import require_permission


router = APIRouter(
    prefix="/portal/registration",
    tags=["portal-registration"],
)


@router.post(
    "",
    response_model=PortalRegistrationCreated,
    status_code=status.HTTP_201_CREATED,
)
def register_portal_account(
    payload: PortalRegistrationCreate,
    db: Session = Depends(get_db),
) -> PortalRegistrationCreated:
    """
    Registra una cuenta externa sin invitación previa.

    La cuenta queda pendiente hasta que:

    1. verifique su correo;
    2. MYC revise la empresa declarada;
    3. se apruebe una vinculación con un cliente existente.

    El token original no se devuelve en la respuesta pública.
    """

    result = create_public_registration(
        db,
        payload=payload,
    )

    return PortalRegistrationCreated(
        registration=result.registration,
        verification_required=True,
        portal_access_enabled=False,
        message=(
            "Tu cuenta fue registrada. Verifica tu correo para continuar "
            "con el proceso de vinculación."
        ),
    )


@router.post(
    "/verify-email",
    response_model=PortalRegistrationVerificationResult,
)
def verify_portal_registration_email(
    payload: PortalRegistrationEmailVerification,
    db: Session = Depends(get_db),
) -> PortalRegistrationVerificationResult:
    """
    Verifica el correo mediante un token de un solo uso.

    Verificar el correo no concede acceso a información del cliente.
    La cuenta todavía requiere una membresía aprobada.
    """

    registration = verify_registration_email(
        db,
        token=payload.token,
    )

    return PortalRegistrationVerificationResult(
        registration_id=registration.id,
        status=registration.status,
        email_verified=registration.email_verified_at is not None,
        portal_access_enabled=registration_has_portal_access(
            registration
        ),
        message=(
            "Correo verificado correctamente. Tu registro está pendiente "
            "de revisión y vinculación con la empresa."
        ),
    )


@router.post(
    "/resend-verification",
    status_code=status.HTTP_202_ACCEPTED,
)
def resend_portal_registration_email(
    payload: PortalRegistrationEmailResend,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Genera un nuevo token de verificación cuando corresponde.

    La respuesta es deliberadamente genérica para evitar enumeración de
    cuentas. No revela si el correo existe, ya fue verificado o está bloqueado.

    El token generado deberá enviarse mediante el adaptador institucional de
    correo. No debe devolverse al cliente HTTP.
    """

    resend_registration_verification(
        db,
        email=str(payload.email),
    )

    return {
        "message": (
            "Si existe un registro pendiente para ese correo, recibirás "
            "un nuevo enlace de verificación."
        )
    }


@router.get(
    "/{registration_id}/status",
    response_model=PortalRegistrationStatusRead,
)
def get_portal_registration_status(
    registration_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("users.manage")),
) -> PortalRegistrationStatusRead:
    """
    Consulta temporal del estado del registro.

    Este endpoint no expone notas internas, candidatos de cliente,
    comentarios administrativos ni tokens.
    """

    registration = get_registration_or_404(
        db,
        registration_id,
    )

    return PortalRegistrationStatusRead(
        registration_id=registration.id,
        user_id=registration.user_id,
        status=registration.status,
        email_verified=registration.email_verified_at is not None,
        portal_access_enabled=registration_has_portal_access(
            registration
        ),
        declared_company_name=registration.declared_company_name,
        created_at=registration.created_at,
        updated_at=registration.updated_at,
    )
