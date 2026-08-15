from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.activity import ActivityUserRead


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    notification_type: str
    event_key: str | None = None

    title: str
    body: str | None = None

    priority: str

    entity_type: str | None = None
    entity_id: int | None = None

    activity_message_id: int | None = None

    metadata_json: dict = Field(default_factory=dict)

    read_at: datetime | None = None
    delivery_status: str
    push_attempted_at: datetime | None = None
    push_delivered_at: datetime | None = None
    error_code: str | None = None
    dismissed_at: datetime | None = None
    revoked_at: datetime | None = None

    created_at: datetime
    updated_at: datetime

    actor_user: ActivityUserRead | None = None


class NotificationListRead(BaseModel):
    items: list[NotificationRead]
    total: int


class NotificationUnreadCountRead(BaseModel):
    count: int


class NotificationMarkRead(BaseModel):
    success: bool


class PushDeviceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expo_push_token: str = Field(min_length=20, max_length=255)
    platform: str = Field(pattern="^(ios|android)$")
    device_name: str | None = Field(default=None, max_length=160)
    app_version: str | None = Field(default=None, max_length=40)


class PushDeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform: str
    device_name: str | None
    app_version: str | None
    is_active: bool
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime
