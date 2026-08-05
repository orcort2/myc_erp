from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def normalize_username(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized or not normalized[0].isalnum() or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in normalized
    ):
        raise ValueError(
            "El usuario debe iniciar con letra o número y usar sólo letras, números, puntos, guiones o guion bajo."
        )
    return normalized


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    is_active: bool


class UserAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    full_name: str
    phone: str | None = None
    job_title: str | None = None
    area: str | None = None
    language: str
    timezone: str
    account_type: str
    status: str
    is_active: bool
    email_verified_at: datetime | None = None
    last_login_at: datetime | None = None
    password_changed_at: datetime | None = None
    must_change_password: bool
    failed_login_attempts: int
    locked_until: datetime | None = None
    created_at: datetime
    roles: list[RoleRead] = Field(default_factory=list)


class UserRolesUpdate(BaseModel):
    role_names: list[str] = Field(default_factory=list)


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserAdminCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=180)
    password: str = Field(min_length=8, max_length=128)
    role_names: list[str] = Field(min_length=1)

    _normalize_username = field_validator("username")(normalize_username)


class UserAdminUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=80)
    email: EmailStr | None = None
    full_name: str | None = None
    role_names: list[str] | None = None
    is_active: bool | None = None
    phone: str | None = Field(default=None, max_length=40)
    job_title: str | None = Field(default=None, max_length=120)
    area: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=10)
    timezone: str | None = Field(default=None, max_length=80)
    must_change_password: bool | None = None

    @field_validator("username")
    @classmethod
    def normalize_optional_username(cls, value: str | None) -> str | None:
        return normalize_username(value) if value is not None else None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value:
            try:
                ZoneInfo(value)
            except ZoneInfoNotFoundError as exc:
                raise ValueError("Zona horaria no válida.") from exc
        return value


class UserActivityRead(BaseModel):
    id: int
    action: str
    entity: str
    entity_id: int | None
    comment: str | None
    created_at: datetime
    previous_values: dict | None
    new_values: dict | None
