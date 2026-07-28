from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "ERP MYC"
    app_version: str = "0.4.0"
    environment: str = "development"
    database_url: str = Field(
        default="postgresql+psycopg://localhost:5432/erp_myc"
    )
    secret_key: str = "change-this-secret-key"
    access_token_expire_minutes: int = 60 * 8
    refresh_token_expire_minutes: int = 60 * 24 * 30
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    storage_root: str = "storage"
    libreoffice_executable: str = Field(
        default="",
        validation_alias=AliasChoices("LIBREOFFICE_EXECUTABLE", "OFFICE_CONVERTER_BINARY"),
    )
    office_converter_timeout_seconds: float = Field(default=60, gt=0)
    public_verify_base_url: str = "https://api-erp.mycmetrology.com.mx"
    facturama_enabled: bool = False
    facturama_environment: Literal["sandbox", "production"] = "sandbox"
    facturama_username: SecretStr = SecretStr("")
    facturama_password: SecretStr = SecretStr("")
    facturama_sandbox_url: str = ""
    facturama_production_url: str = ""
    facturama_timeout_seconds: float = Field(default=30, gt=0)
    resolution_center_organization_id: str = "myc"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
