from datetime import datetime
from pydantic import BaseModel, EmailStr


class PortalProfileRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    client_id: int
    client_name: str
    membership_id: int
    permissions: list[str]
    last_login_at: datetime | None


class PortalProfileUpdate(BaseModel):
    full_name: str
