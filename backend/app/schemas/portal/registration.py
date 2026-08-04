from datetime import datetime

# ============================================================================
# TODO(TD-024)
#
# Separar los esquemas de registro del Portal del Cliente en módulos
# especializados cuando el flujo funcional quede estabilizado.
#
# Prioridad:
# Baja
#
# Motivo:
# Evitar archivos excesivamente grandes (>500 líneas) y facilitar el
# mantenimiento.
#
# Estado:
# Pendiente para post-MVP.
# ============================================================================

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.core.portal.constants import (
    MAXIMUM_PORTAL_PASSWORD_LENGTH,
    MINIMUM_PORTAL_PASSWORD_LENGTH,
    PortalRegistrationStatus,
)


class PortalRegistrationCreate(BaseModel):
    """
    Datos requeridos para el registro público en el Portal del Cliente.

    Este flujo no presupone que la empresa declarada coincida con un cliente
    existente. La vinculación se resolverá posteriormente mediante una
    ClientLinkRequest aprobada por personal autorizado de MYC.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    username: str = Field(
        min_length=3,
        max_length=80,
    )

    email: EmailStr

    full_name: str = Field(
        min_length=2,
        max_length=180,
    )

    password: str = Field(
        min_length=MINIMUM_PORTAL_PASSWORD_LENGTH,
        max_length=MAXIMUM_PORTAL_PASSWORD_LENGTH,
    )

    password_confirmation: str = Field(
        min_length=MINIMUM_PORTAL_PASSWORD_LENGTH,
        max_length=MAXIMUM_PORTAL_PASSWORD_LENGTH,
    )

    declared_company_name: str = Field(
        min_length=2,
        max_length=255,
    )

    declared_company_rfc: str | None = Field(
        default=None,
        min_length=12,
        max_length=13,
    )

    contact_phone: str | None = Field(
        default=None,
        max_length=40,
    )

    job_title: str | None = Field(
        default=None,
        max_length=120,
    )

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip().lower()

        if not value:
            raise ValueError("El nombre de usuario es obligatorio.")

        if not value[0].isalnum():
            raise ValueError(
                "El nombre de usuario debe iniciar con una letra o número."
            )

        allowed = set(
            "abcdefghijklmnopqrstuvwxyz0123456789._-"
        )

        invalid = {
            character
            for character in value
            if character not in allowed
        }

        if invalid:
            raise ValueError(
                "El nombre de usuario sólo puede contener letras, "
                "números, puntos, guiones y guiones bajos."
            )

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator(
        "full_name",
        "declared_company_name",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        value = " ".join(value.split())

        if not value:
            raise ValueError(
                "El valor no puede estar vacío."
            )

        return value

    @field_validator("declared_company_rfc")
    @classmethod
    def normalize_rfc(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip().upper().replace(" ", "")

        if not value:
            return None

        if len(value) not in {12, 13}:
            raise ValueError(
                "El RFC debe contener 12 o 13 caracteres."
            )

        if not value.isalnum():
            raise ValueError(
                "El RFC sólo puede contener letras y números."
            )

        return value

    @field_validator(
        "contact_phone",
        "job_title",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = " ".join(value.split())

        return value or None

    @model_validator(mode="after")
    def validate_password_confirmation(self):
        if self.password != self.password_confirmation:
            raise ValueError(
                "Las contraseñas no coinciden."
            )

        if self.password.lower() in {
            self.username.lower(),
            str(self.email).lower(),
        }:
            raise ValueError(
                "La contraseña no puede coincidir con el usuario o correo."
            )

        return self


class PortalRegistrationEmailVerification(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    token: str = Field(
        min_length=32,
        max_length=512,
    )


class PortalRegistrationEmailResend(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class PortalRegistrationUserRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    username: str
    email: EmailStr
    full_name: str
    account_type: str
    status: str
    email_verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PortalRegistrationRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    user_id: int
    declared_company_name: str
    declared_company_rfc: str | None = None
    contact_phone: str | None = None
    job_title: str | None = None
    status: PortalRegistrationStatus
    email_verified_at: datetime | None = None
    last_internal_review_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    user: PortalRegistrationUserRead


class PortalRegistrationCreated(BaseModel):
    registration: PortalRegistrationRead
    verification_required: bool = True
    portal_access_enabled: bool = False
    message: str = (
        "Tu cuenta fue registrada. Verifica tu correo para continuar con el proceso."
    )


class PortalRegistrationVerificationResult(BaseModel):
    registration_id: int
    status: PortalRegistrationStatus
    email_verified: bool
    portal_access_enabled: bool
    message: str


class PortalRegistrationStatusRead(BaseModel):
    registration_id: int
    user_id: int
    status: PortalRegistrationStatus
    email_verified: bool
    portal_access_enabled: bool
    declared_company_name: str
    created_at: datetime
    updated_at: datetime