from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeveloperUnlockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    biometric_credential: str = Field(min_length=1, max_length=8192)


class DeveloperSessionOpened(BaseModel):
    developer_token: str
    expires_at: datetime
    session_id: int


class DeveloperSessionStatus(BaseModel):
    active: bool
    expires_at: datetime | None = None
    remaining_seconds: int | None = None
    user_id: int | None = None
    device_id: int | None = None


class DeveloperBrokerHealth(BaseModel):
    """DEV-1A: explicit DTO for ``broker.health`` -- never the Broker's raw
    frame, never configuration, secrets or host details."""

    status: str
    protocol: str
    protocol_version: int
    supported_versions: list[int]
    broker_instance_id: str
    broker_timestamp_ms: int
    operations: list[str]
    features: list[str]
