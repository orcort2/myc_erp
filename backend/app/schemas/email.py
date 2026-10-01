from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmailTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    template_key: str
    name: str
    subject_template: str
    body_template: str
    is_active: bool
    updated_at: datetime
    allowed_variables: list[str] = []


class EmailTemplateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=180)
    subject_template: str | None = Field(default=None, min_length=1, max_length=300)
    body_template: str | None = Field(default=None, min_length=1, max_length=20000)
    is_active: bool | None = None


class EmailDeliverySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_key: str
    related_entity_type: str | None
    related_entity_id: int | None
    to_json: list[str]
    subject: str
    status: str
    attempt_count: int
    sent_at: datetime | None
    failed_at: datetime | None
    created_at: datetime


class EmailDeliveryRead(EmailDeliverySummary):
    cc_json: list[str]
    bcc_json: list[str]
    body_text_snapshot: str
    body_html_snapshot: str
    attachments_json: list[dict]
    provider_message_id: str | None
    provider_response: str | None
    last_error: str | None
    failure_code: str | None
    requested_by_id: int | None


class EmailRetryResult(BaseModel):
    delivery_id: int
    status: str
    sent: bool
    reason: str | None = None


class EmailTransportStatus(BaseModel):
    """Configuration only. It does not prove the relay is reachable."""

    enabled: bool
    configured: bool
    host: str | None
    port: int
    starttls: bool
    authentication_mode: str
    from_address: str | None
