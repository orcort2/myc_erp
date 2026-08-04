from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PortalMembershipCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: int
    user_id: int
    role_codes: list[str] = Field(min_length=1)
    is_primary_contact: bool = False


class PortalMembershipRead(BaseModel):
    id: int
    client_id: int
    user_id: int
    username: str
    email: str
    full_name: str
    status: str
    is_primary_contact: bool
    role_codes: list[str]
    created_at: datetime


class PortalMembershipReason(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class PortalMembershipRolesUpdate(BaseModel):
    role_codes: list[str] = Field(min_length=1)


class PortalLinkRequestCreate(BaseModel):
    registration_id: int
    client_id: int
    reason: str | None = None


class PortalLinkRequestResolve(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
    role_codes: list[str] = Field(default_factory=lambda: ["viewer"], min_length=1)


class PortalLinkRequestRead(BaseModel):
    id: int
    portal_registration_id: int
    proposed_client_id: int
    status: str
    request_reason: str | None
    resolution_reason: str | None
    resulting_membership_id: int | None
    created_at: datetime
