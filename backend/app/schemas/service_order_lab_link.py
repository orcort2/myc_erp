from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


LinkReason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ServiceOrderLabLinkCreate(BaseModel):
    work_order_id: int = Field(gt=0)


class ServiceOrderLabLinkReplace(ServiceOrderLabLinkCreate):
    reason: LinkReason


class ServiceOrderLabLinkUnlink(BaseModel):
    reason: LinkReason


class ServiceOrderLabLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_order_id: int
    lab_root_work_order_id: int
    root_folio: int
    # Proyección de lectura: OT actuales del grupo LAB (resueltas por la raíz).
    group_work_order_count: int = 1
    status: Literal["active", "unlinked", "replaced"]
    linked_at: datetime
    linked_by_user_id: int
    linked_by_name: str
    unlinked_at: datetime | None
    unlinked_by_user_id: int | None
    unlinked_by_name: str | None
    unlink_reason: str | None
    replaced_by_link_id: int | None
    created_at: datetime
    updated_at: datetime


class ServiceOrderLabCandidateRead(BaseModel):
    root_id: int
    root_folio: int
    group_folios: list[int]
    client_name: str
    status: str
    work_order_count: int
    equipment_count: int
    active_service_order_id: int | None
    linked_to_other_service_order: bool
