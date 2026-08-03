from functools import lru_cache
import math
from collections import Counter
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "ERP MYC"
    app_version: str = "0.4.0"
    environment: str = "development"
    database_url: str = Field(
        default="postgresql+psycopg://localhost:5432/erp_myc"
    )
    secret_key: str = "development-only-change-me"
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
    enable_api_docs: bool = False
    enable_developer_portal: bool = False

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        if self.environment.strip().lower() not in {"production", "prod"}:
            return self

        secret = self.secret_key.strip()
        rejected_values = {
            "",
            "change-this-secret-key",
            "development-only-change-me",
            "replace-me",
            "replace-with-a-secure-random-secret",
            "secret",
            "password",
        }
        character_classes = sum(
            any(check(character) for character in secret)
            for check in (str.islower, str.isupper, str.isdigit, lambda value: not value.isalnum())
        )
        frequencies = Counter(secret)
        entropy = -sum(
            (count / len(secret)) * math.log2(count / len(secret))
            for count in frequencies.values()
        ) * len(secret) if secret else 0.0

        if (
            secret.lower() in rejected_values
            or len(secret) < 32
            or len(set(secret)) < 12
            or character_classes < 3
            or entropy < 100
        ):
            raise ValueError(
                "SECRET_KEY inseguro para producción: configure un valor aleatorio "
                "de al menos 32 caracteres y 100 bits estimados de entropía."
            )
        return self

    @property
    def uses_development_secret(self) -> bool:
        return self.secret_key.strip().lower() in {
            "",
            "change-this-secret-key",
            "development-only-change-me",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
