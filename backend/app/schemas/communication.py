from datetime import datetime
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


class CommunicationMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class CommunicationMessageRead(BaseModel):
    id: int
    conversation_id: int
    body: str
    message_type: str
    created_at: datetime
    sender: CommunicationActorRead
    model_config = ConfigDict(from_attributes=True)


class CommunicationConversationCreate(BaseModel):
    conversation_type: str = Field(pattern="^(internal|client)$")
    participant_user_id: int | None = None
    client_id: int | None = None
    initial_message: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def validate_target(self):
        if self.conversation_type == "internal" and not self.participant_user_id:
            raise ValueError("participant_user_id es obligatorio para conversaciones internas")
        if self.conversation_type == "client" and not self.client_id:
            raise ValueError("client_id es obligatorio para conversaciones con clientes")
        return self


class CommunicationConversationRead(BaseModel):
    id: int
    conversation_type: str
    title: str
    client: CommunicationClientRead | None = None
    participants: list[CommunicationActorRead] = Field(default_factory=list)
    last_message: CommunicationMessageRead | None = None
    last_message_at: datetime | None = None
    created_at: datetime


class CommunicationConversationDetail(CommunicationConversationRead):
    messages: list[CommunicationMessageRead] = Field(default_factory=list)


class CommunicationDirectoryRead(BaseModel):
    users: list[CommunicationActorRead]
    clients: list[CommunicationClientRead]
