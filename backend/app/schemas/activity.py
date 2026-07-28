from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ActivityUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: str


class ActivityAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_name: str
    content_type: str | None = None
    size_bytes: int
    is_official_evidence: bool
    created_at: datetime


class ActivityMentionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mentioned_user_id: int
    read_at: datetime | None = None
    revoked_at: datetime | None = None
    mentioned_user: ActivityUserRead


class ActivityRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    previous_body: str
    new_body: str
    reason: str | None = None
    created_at: datetime
    edited_by_id: int


class ActivityMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    mentioned_user_ids: list[int] = Field(default_factory=list)


class ActivityMessageUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    reason: str | None = Field(default=None, max_length=255)
    mentioned_user_ids: list[int] = Field(default_factory=list)


class ActivityMessageWithdraw(BaseModel):
    reason: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=500)


class ActivityMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    thread_id: int
    message_type: str
    body: str
    is_system: bool
    is_formal: bool
    edited_at: datetime | None = None
    withdrawn_at: datetime | None = None
    withdrawal_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    author: ActivityUserRead | None = None
    mentions: list[ActivityMentionRead] = Field(default_factory=list)
    attachments: list[ActivityAttachmentRead] = Field(default_factory=list)
    revisions: list[ActivityRevisionRead] = Field(default_factory=list)


class ActivityThreadRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    created_at: datetime
    messages: list[ActivityMessageRead] = Field(default_factory=list)
