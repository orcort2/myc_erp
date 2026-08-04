from pydantic import BaseModel, ConfigDict, Field


class PortalRoleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: int
    code: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    permission_codes: list[str] = Field(min_length=1)


class PortalRoleRead(BaseModel):
    id: int
    client_id: int | None
    code: str
    name: str
    description: str | None
    is_system: bool
    permission_codes: list[str]


class PortalPermissionRead(BaseModel):
    code: str
    name: str
    description: str | None
    module: str
