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


class UserAdminCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=180)
    password: str = Field(min_length=8, max_length=128)
    role_names: list[str] = Field(min_length=1)


class UserAdminUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role_names: list[str] | None = None
    is_active: bool | None = None
