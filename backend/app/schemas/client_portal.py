from pydantic import BaseModel, ConfigDict, Field


class ClientPortalConfigurationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str | None = None
    logo_path: str | None = None
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    language: str = "es-MX"
    timezone: str = "America/Mexico_City"
    default_home_page: str = "dashboard"
    welcome_message: str | None = None
    allow_self_registration: bool = True
    allow_invitations: bool = True
    require_mfa: bool = False
    session_timeout_minutes: int = Field(default=480, ge=15, le=1440)
    password_expiration_days: int | None = Field(default=None, ge=1, le=3650)
    email_notifications_enabled: bool = True
    is_enabled: bool = True


class ClientPortalConfigurationRead(ClientPortalConfigurationUpdate):
    id: int
    client_id: int
