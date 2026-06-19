from datetime import datetime

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: int
    user_id: int | None
    user_name: str | None = None
    action: str
    entity: str
    entity_id: int | None
    previous_values: dict | None
    new_values: dict | None
    comment: str | None
    created_at: datetime
