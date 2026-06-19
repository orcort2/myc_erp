from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    is_active: bool


class UserAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    roles: list[RoleRead] = Field(default_factory=list)


class UserRolesUpdate(BaseModel):
    role_names: list[str] = Field(default_factory=list)


class UserStatusUpdate(BaseModel):
    is_active: bool