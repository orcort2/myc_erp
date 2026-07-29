from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ActivityUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: str
    role_name: str | None = None

class ActivityMentionableUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role_name: str | None = None

class ActivityAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_name: str
    content_type: str | None = None
    size_bytes: int
    is_official_evidence: bool
    created_at: datetime
    preview_available: bool = False


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


class ActivityAttentionCreate(BaseModel):
    assigned_user_id: int | None = Field(default=None, gt=0)
    assigned_area: str | None = Field(default=None, max_length=80)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")

    @model_validator(mode="after")
    def validate_target(self):
        if self.assigned_user_id is None and not (
            self.assigned_area and self.assigned_area.strip()
        ):
            raise ValueError("La atención requiere usuario o área")
        return self


class ActivityAttentionResolve(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class ActivityAttentionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: int
    requested_by_id: int
    assigned_user_id: int | None = None
    assigned_area: str | None = None
    priority: str
    status: str
    resolved_at: datetime | None = None
    resolved_by_id: int | None = None
    resolution_note: str | None = None
    created_at: datetime
    requested_by: ActivityUserRead
    assigned_user: ActivityUserRead | None = None
    resolved_by: ActivityUserRead | None = None


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
    event_code: str | None = None
    related_entity_type: str | None = None
    related_entity_id: int | None = None
    metadata_json: dict | None = None
    created_at: datetime
    updated_at: datetime
    author: ActivityUserRead | None = None
    mentions: list[ActivityMentionRead] = Field(default_factory=list)
    attachments: list[ActivityAttachmentRead] = Field(default_factory=list)
    revisions: list[ActivityRevisionRead] = Field(default_factory=list)
    attention_requests: list[ActivityAttentionRead] = Field(default_factory=list)


class ActivityEntityRead(BaseModel):
    entity_type: str
    entity_id: int
    label: str
    reference: str
    frontend_path: str


class ActivityCapabilitiesRead(BaseModel):
    can_read: bool = True
    can_create: bool = False
    can_edit_own: bool = False
    can_delete_own: bool = False
    can_moderate: bool = False
    can_attach_files: bool = False
    can_mention: bool = False
    can_request_attention: bool = False
    can_resolve_attention: bool = False
    can_view_audit: bool = False


class ActivityThreadRead(BaseModel):
    id: int | None = None
    entity_type: str
    entity_id: int
    created_at: datetime | None = None
    entity: ActivityEntityRead
    capabilities: ActivityCapabilitiesRead
    unread_count: int = 0
    pending_attention_count: int = 0
    messages: list[ActivityMessageRead] = Field(default_factory=list)


class ActivityInboxItemRead(BaseModel):
    thread_id: int
    entity: ActivityEntityRead
    last_message: ActivityMessageRead
    unread_count: int
    pending_attention_count: int


class ActivityInboxRead(BaseModel):
    items: list[ActivityInboxItemRead]
    total: int
    unread_count: int
    pending_attention_count: int


class ActivityEntityDefinitionRead(BaseModel):
    code: str
    label: str
    read_permission: str
    frontend_path: str


class ActivityUnreadRead(BaseModel):
    unread_count: int
