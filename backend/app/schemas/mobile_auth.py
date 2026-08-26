from typing import Literal

from pydantic import BaseModel, EmailStr


class MobileLogin(BaseModel):
    email: EmailStr
    password: str


class MobileRefreshTokenRequest(BaseModel):
    refresh_token: str


class MobileUserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    permissions: list[str]
    actor_type: Literal["internal", "client"]
    client_id: int | None = None
    membership_id: int | None = None


class MobileTokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: MobileUserRead
