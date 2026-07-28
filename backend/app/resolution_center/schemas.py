"""Contratos HTTP internos y versionados del Centro de Resoluciones."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CenterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResolutionDefinitionResource(CenterModel):
    resolution_type: str
    version: str
    name: str
    description: str
    domain: str
    object_type: str
    object_route: str | None = None
    risk_level: Literal["low", "medium", "high", "critical"]
    capabilities: tuple[str, ...]
    required_permissions: tuple[str, ...]
    supports_simulation: bool
    supports_compensation: bool
    parameter_schema: dict[str, Any]
    labels: dict[str, str]
    warnings: tuple[str, ...] = ()


class ResolutionListItem(CenterModel):
    public_id: str
    resolution_type: str
    title: str
    subject_type: str
    subject_id: str
    subject_label: str | None = None
    requester: str | None = None
    authorizer: str | None = None
    lifecycle_status: str
    execution_status: str | None = None
    distributed_status: str | None = None
    result: str | None = None
    created_at: datetime
    authorized_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: int | None = None
    attempt_count: int = 0
    has_retries: bool = False
    is_blocked: bool = False
    is_compensated: bool = False


class ResolutionCollection(CenterModel):
    items: tuple[ResolutionListItem, ...]
    next_cursor: str | None = None
    limit: int


class ResolutionCenterIndicators(CenterModel):
    total: int
    pending: int
    authorized: int
    executing: int
    completed: int
    failed: int
    blocked: int
    compensated: int
    with_retries: int


class TimelineEntry(CenterModel):
    occurred_at: datetime
    category: str
    event_type: str
    label: str
    status: str | None = None
    actor: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    technical: bool = False


class ResolutionDetail(CenterModel):
    summary: ResolutionListItem
    description: str | None = None
    reason: str | None = None
    priority: str
    definition_version: str
    correlation_id: str | None = None
    subject: dict[str, Any]
    parameters: dict[str, Any] = Field(default_factory=dict)
    analysis: dict[str, Any] | None = None
    lifecycle: tuple[TimelineEntry, ...]
    distributed: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    simulation: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    attempts: tuple[dict[str, Any], ...] = ()
    recovery: tuple[dict[str, Any], ...] = ()
    compensations: tuple[dict[str, Any], ...] = ()
    evidence: dict[str, Any] = Field(default_factory=dict)
    capabilities: tuple[str, ...] = ()


class CreateAdministrativeResolutionRequest(CenterModel):
    resolution_type: str
    definition_version: str
    subject_type: str
    subject_id: str
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    reason: str = Field(min_length=1, max_length=2000)
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    parameters: dict[str, Any] = Field(default_factory=dict)


class OperationAccepted(CenterModel):
    public_id: str
    lifecycle_status: str
    message: str
    distributed_status: str | None = None
    work_key: str | None = None


class AuthorizationRequest(CenterModel):
    comment: str | None = Field(default=None, max_length=1000)


class CenterCapabilities(CenterModel):
    can_read: bool
    can_create: bool
    can_prepare: bool
    can_analyze: bool
    can_plan: bool
    can_simulate: bool
    can_authorize: bool
    can_execute: bool
    can_audit: bool
    can_view_infrastructure: bool
