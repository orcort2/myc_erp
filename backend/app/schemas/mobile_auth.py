from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from uuid import UUID


class MobileSecurityDeviceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_uuid: str = Field(min_length=1, max_length=128)
    platform: Literal["ios", "android"]
    device_name: str | None = Field(default=None, max_length=160)
    app_version: str | None = Field(default=None, max_length=40)

    @field_validator("device_uuid")
    @classmethod
    def normalize_uuid(cls, value: str) -> str:
        return str(UUID(value))


class MobileLogin(BaseModel):
    email: EmailStr
    password: str
    device: MobileSecurityDeviceInput


class MobileRefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=8192)
    device: MobileSecurityDeviceInput | None = None


class MobileUserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    permissions: list[str]
    can_resolve_own_lab_folios: bool = False
    actor_type: Literal["internal", "client"]
    client_id: int | None = None
    membership_id: int | None = None


class MobileTokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: MobileUserRead


class MobileBiometricEnrollResponse(BaseModel):
    biometric_credential: str
    expires_at: datetime


class MobileBiometricExchangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    biometric_credential: str = Field(min_length=1, max_length=8192)
