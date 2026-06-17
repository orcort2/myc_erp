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
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    storage_root: str = "storage"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

