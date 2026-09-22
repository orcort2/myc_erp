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
    # BIOMETRIC-2: independent of refresh_token_expire_minutes on purpose; a
    # biometric credential unlocks the device, it is not a session lifetime.
    mobile_biometric_credential_expire_days: int = 90
    # DEV-0: a DeveloperSession is a short-lived infrastructure-control
    # authority, not an operational session -- it never renews silently and
    # never survives logout. See docs/architecture/MOBILE_DEVELOPER_AUTHORITY.md.
    developer_session_expire_minutes: int = 10
    # DEV-1A/1B: optional Developer Broker boundary. Disabled by default; the
    # ERP starts normally without it and Broker routes fail closed (503). The
    # HMAC secret, the LOGICAL pipe name (never a path) and the two Windows
    # identities (canonical SIDs) come only from external configuration.
    # "named_pipe" is the only transport; outside Windows it fails closed.
    # See docs/architecture/MOBILE_DEVELOPER_BROKER.md.
    developer_broker_enabled: bool = False
    developer_broker_transport: Literal["named_pipe"] = "named_pipe"
    developer_broker_pipe_name: str = ""
    developer_broker_secret: SecretStr = SecretStr("")
    developer_broker_timeout_seconds: float = Field(default=5, gt=0)
    # Expected identity of the Broker pipe SERVER: verified before any byte
    # of a request is written (anti pipe-squatting).
    developer_broker_service_sid: str = ""
    # Identity this ERP process runs as (the pipe CLIENT). Optional here; when
    # set, the ERP refuses to talk to the Broker unless it really runs as it.
    developer_broker_client_sid: str = ""
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    storage_root: str = "storage"
    upload_activity_max_bytes: int = Field(default=15 * 1024 * 1024, gt=0)
    upload_capture_max_bytes: int = Field(default=40 * 1024 * 1024, gt=0)
    upload_document_max_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    upload_certificate_pdf_max_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    upload_tax_constancy_max_bytes: int = Field(default=15 * 1024 * 1024, gt=0)
    upload_archive_max_members: int = Field(default=250, gt=0)
    upload_archive_max_uncompressed_bytes: int = Field(default=120 * 1024 * 1024, gt=0)
    upload_archive_max_member_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    upload_archive_max_ratio: float = Field(default=100, gt=1)
    upload_archive_max_depth: int = Field(default=8, gt=0)
    upload_image_max_pixels: int = Field(default=40_000_000, gt=0)
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
    expo_push_url: str = "https://exp.host/--/api/v2/push/send"
    expo_push_timeout_seconds: float = Field(default=5, gt=0)

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
