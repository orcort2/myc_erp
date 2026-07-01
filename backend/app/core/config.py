from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "ERP MYC"
    app_version: str = "0.1.0"
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
    public_verify_base_url: str = "https://api-erp.mycmetrology.com.mx"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
