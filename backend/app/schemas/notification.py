from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.activity import ActivityUserRead


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    notification_type: str

    title: str
    body: str | None = None

    priority: str

    entity_type: str | None = None
    entity_id: int | None = None

    activity_message_id: int | None = None

    metadata_json: dict = Field(default_factory=dict)

    read_at: datetime | None = None
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
    