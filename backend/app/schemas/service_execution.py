from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ServiceStageCategory = Literal[
    "diagnosis", "repair", "maintenance", "calibration", "verification",
    "qualification", "validation", "training", "consulting", "other",
]
ServiceStageStatus = Literal[
    "planned", "pending_quote", "pending_approval", "authorized", "in_progress",
    "paused", "completed", "client_rejected", "not_executable",
    "exception_closed", "cancelled",
]


class ServiceStageCreate(BaseModel):
    category: ServiceStageCategory
    origin: str = Field(default="quotation", min_length=1, max_length=40)
    source_stage_id: int | None = None
    quotation_item_id: int | None = None
    responsible_user_id: int | None = None
    status: ServiceStageStatus = "planned"


class ServiceStageUpdate(BaseModel):
    status: ServiceStageStatus
    evidence_summary: dict | None = None
    result: dict | None = None


class ServiceUnitCreate(BaseModel):
    work_order_id: int | None = None
    equipment_id: int | None = None
    origin_service_order_item_id: int | None = None
    name: str = Field(default="Equipo", min_length=1, max_length=180)
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    identification_notes: str | None = None
    initial_stages: list[ServiceStageCreate] = Field(default_factory=list, min_length=1)


class ServiceUnitBatchCreate(BaseModel):
    units: list[ServiceUnitCreate] = Field(min_length=1)


class ServiceStageDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    controlled_document_id: int | None = None
    document_role: str
    external_reference: str | None = None


class ServiceStageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    service_unit_id: int
    sequence: int
    category: ServiceStageCategory
    status: ServiceStageStatus
    origin: str
    source_stage_id: int | None = None
    quotation_item_id: int | None = None
    commercial_decision_id: int | None = None
    responsible_user_id: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    evidence_summary: dict | None = None
    result: dict | None = None
    documents: list[ServiceStageDocumentRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ServiceUnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    service_order_id: int
    work_order_id: int
    equipment_id: int | None = None
    origin_service_order_item_id: int | None = None
    initial_category: str
    evolution_enabled: bool
    name: str
    brand: str | None = None
    model: str | None = None
    serial_number: str | None = None
    identification_status: str
    identification_notes: str | None = None
    status: str
    stages: list[ServiceStageRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TechnicalServiceRequestCreate(BaseModel):
    summary: str = Field(min_length=3, max_length=4000)
    requested_categories: list[ServiceStageCategory] = Field(min_length=1)
    source_message_id: int | None = None


class TechnicalServiceRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    service_order_id: int
    service_unit_id: int
    source_stage_id: int
    source_message_id: int | None = None
    requested_by_id: int
    status: str
    summary: str
    requested_categories: list[ServiceStageCategory]
    created_at: datetime
    updated_at: datetime


class ServiceTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_message_id: int | None = None
    created_by_id: int
    service_order_id: int | None = None
    service_unit_id: int | None = None
    service_stage_id: int | None = None
    title: str
    status: str
    due_at: datetime | None = None
    completed_at: datetime | None = None
    assignee_user_ids: list[int] = Field(default_factory=list)


class ServiceExecutionBoardRead(BaseModel):
    service_order_id: int
    categories: list[ServiceStageCategory]
    units: list[ServiceUnitRead]
    tasks: list[ServiceTaskRead]
    technical_requests: list[TechnicalServiceRequestRead]


class QuotationItemDecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approved", "rejected"]
    source: Literal["internal"] = "internal"
    comment: str | None = Field(default=None, max_length=2000)
    enabled_stage_categories: list[ServiceStageCategory] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_enabled_stages(self):
        if self.decision == "approved" and not self.enabled_stage_categories:
            raise ValueError("Una partida aprobada debe indicar al menos una etapa habilitada")
        if self.decision == "rejected" and self.enabled_stage_categories:
            raise ValueError("Una partida rechazada no puede habilitar etapas")
        return self


class QuotationItemDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    quotation_item_id: int
    decision: str
    decided_by_id: int
    decided_at: datetime
    source: str
    comment: str | None = None
    enabled_stage_categories: list[ServiceStageCategory]
    created_stage_ids: list[int] = Field(default_factory=list)
