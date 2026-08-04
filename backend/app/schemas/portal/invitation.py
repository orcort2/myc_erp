from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PortalInvitationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: int
    email: EmailStr
    full_name: str | None = None
    role_codes: list[str] = Field(min_length=1)
    notes: str | None = None


class PortalInvitationRead(BaseModel):
    id: int
    client_id: int
    email: EmailStr
    full_name: str | None
    status: str
    expires_at: datetime
    role_codes: list[str]
    invitation_url: str | None = None


class PortalInvitationValidate(BaseModel):
    email: EmailStr
    full_name: str | None
    client_name: str
    role_names: list[str]
    expires_at: datetime


class PortalInvitationAccept(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=80)
    full_name: str = Field(min_length=2, max_length=180)
    password: str = Field(min_length=8, max_length=128)


class PortalInvitationAccepted(BaseModel):
    user_id: int
    membership_id: int
    client_id: int
    message: str
