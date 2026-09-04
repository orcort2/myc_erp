from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommunicationActorRead(BaseModel):
    id: int
    full_name: str
    email: str | None = None
    model_config = ConfigDict(from_attributes=True)


class CommunicationClientRead(BaseModel):
    id: int
    name: str
    email: str | None = None


class CommunicationMentionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["user", "all", "role", "work_order"]
    user_id: int | None = None
    work_order_id: int | None = Field(default=None, gt=0)
    key: str | None = Field(default=None, min_length=1, max_length=80)

    @model_validator(mode="after")
    def validate_target(self):
        if self.kind == "user" and self.user_id is None:
            raise ValueError("user_id es obligatorio para una mención individual")
        if self.kind == "role" and not self.key:
            raise ValueError("key es obligatorio para una mención de grupo")
        if self.kind == "work_order" and self.work_order_id is None:
            raise ValueError("work_order_id es obligatorio para una mención de OT")
        return self


class CommunicationMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=10000)
    client_message_id: str | None = Field(default=None, min_length=8, max_length=80)
    mentions: list[CommunicationMentionCreate] = Field(default_factory=list, max_length=50)


class CommunicationReceiptRead(BaseModel):
    user_id: int
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class CommunicationMentionRead(BaseModel):
    mentioned_user_id: int
    mention_kind: str
    mention_key: str | None = None
    read_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class CommunicationWorkOrderMentionRead(BaseModel):
    work_order_id: int


class CommunicationMessageRead(BaseModel):
    id: int
    conversation_id: int
    client_message_id: str | None = None
    sequence: int
    body: str
    message_type: str
    created_at: datetime
    edited_at: datetime | None = None
    sender: CommunicationActorRead
    receipts: list[CommunicationReceiptRead] = Field(default_factory=list)
    mentions: list[CommunicationMentionRead] = Field(default_factory=list)
    work_order_mentions: list[CommunicationWorkOrderMentionRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class CommunicationConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_type: Literal["internal", "group", "client"]
    participant_user_id: int | None = None
    participant_user_ids: list[int] = Field(default_factory=list, max_length=100)
    client_id: int | None = None
    ticket_id: int | None = None
    title: str | None = Field(default=None, max_length=180)
    initial_message: str | None = Field(default=None, max_length=10000)
    initial_client_message_id: str | None = Field(default=None, min_length=8, max_length=80)

    @model_validator(mode="after")
    def validate_target(self):
        if self.conversation_type == "internal" and not self.participant_user_id:
            raise ValueError("participant_user_id es obligatorio para conversaciones directas")
        if self.conversation_type == "group":
            if len(set(self.participant_user_ids)) < 2:
                raise ValueError("Una conversación grupal requiere al menos dos participantes adicionales")
            if not self.title or not self.title.strip():
                raise ValueError("title es obligatorio para conversaciones grupales")
        if self.conversation_type == "client" and not self.client_id:
            raise ValueError("client_id es obligatorio para conversaciones con clientes")
        return self


class CommunicationConversationRead(BaseModel):
    id: int
    conversation_type: str
    title: str
    client: CommunicationClientRead | None = None
    ticket_id: int | None = None
    participants: list[CommunicationActorRead] = Field(default_factory=list)
    last_message: CommunicationMessageRead | None = None
    last_message_at: datetime | None = None
    latest_sequence: int = 0
    unread_count: int = 0
    created_at: datetime


class CommunicationConversationDetail(CommunicationConversationRead):
    messages: list[CommunicationMessageRead] = Field(default_factory=list)
    next_before_sequence: int | None = None


class CommunicationMessagePage(BaseModel):
    items: list[CommunicationMessageRead]
    next_before_sequence: int | None = None
    latest_sequence: int = 0
    unread_count: int = 0


class CommunicationSyncRead(BaseModel):
    items: list[CommunicationMessageRead]
    latest_sequence: int
    unread_count: int
    has_more: bool = False


class CommunicationReceiptUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["delivered", "read"]
    message_ids: list[int] = Field(min_length=1, max_length=100)


class CommunicationReceiptBatchRead(BaseModel):
    conversation_id: int
    state: Literal["delivered", "read"]
    message_ids: list[int]
    user_id: int
    occurred_at: datetime


class CommunicationMentionGroupRead(BaseModel):
    key: str
    label: str


class CommunicationWorkOrderSuggestionRead(BaseModel):
    work_order_id: int
    folio: int
    client_name: str
    status: str
    label: str


class CommunicationDirectoryRead(BaseModel):
    users: list[CommunicationActorRead]
    clients: list[CommunicationClientRead]
    mention_groups: list[CommunicationMentionGroupRead] = Field(default_factory=list)


class CommunicationMentionInboxItem(BaseModel):
    message: CommunicationMessageRead
    conversation_title: str
    read_at: datetime | None = None
