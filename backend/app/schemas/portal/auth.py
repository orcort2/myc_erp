from pydantic import BaseModel, ConfigDict, Field


class PortalLogin(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class PortalRefresh(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str = Field(min_length=20)


class PortalTokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    permissions: list[str]
