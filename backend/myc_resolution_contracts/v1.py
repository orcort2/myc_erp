"""Contrato público v1, deliberadamente independiente del paquete ``app``."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.0"


class PublicContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ApiError(PublicContract):
    code: str
    category: Literal[
        "authentication",
        "authorization",
        "validation",
        "conflict",
        "not_found",
        "internal",
    ]
    message: str
    correlation_id: str
    details: dict[str, Any] = Field(default_factory=dict)


class ProblemInput(PublicContract):
    code: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=500)
    detected_by: str = Field(min_length=1, max_length=100)
    detected_at: AwareDatetime
    description: str | None = Field(default=None, max_length=4000)
    external_reference: str | None = Field(default=None, max_length=240)
    severity: Literal["low", "normal", "high", "critical"] = "normal"
    observed_state: dict[str, Any] = Field(default_factory=dict)
    source_payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Any] = Field(default_factory=list, max_length=100)


class CreateResolutionRequest(PublicContract):
    resolution_type: str = Field(min_length=1, max_length=160)
    definition_version: str | None = Field(default=None, max_length=32)
    subject_type: str = Field(min_length=1, max_length=100)
    subject_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    reason: str | None = Field(default=None, max_length=4000)
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    requires_authorization: bool = False
    problem: ProblemInput
    metadata: dict[str, Any] = Field(default_factory=dict)


class TimelineEntry(PublicContract):
    sequence: int
    kind: str
    occurred_at: datetime
    actor_id: str | None
    correlation_id: str | None
    summary: str
    integrity: str


class ResolutionResource(PublicContract):
    id: str
    resolution_type: str
    definition_version: str
    status: str
    priority: str
    source: str
    subject_type: str
    subject_id: str
    title: str
    description: str | None
    reason: str | None
    version: int
    correlation_id: str | None
    created_at: datetime
    updated_at: datetime
    audit_valid: bool
    record_hash: str
    timeline: tuple[TimelineEntry, ...] = ()


class ResolutionCollection(PublicContract):
    items: tuple[ResolutionResource, ...]
    next_cursor: str | None = None
    limit: int


class ApiCapabilities(PublicContract):
    api: Literal["MYC Resolution Engine API"] = "MYC Resolution Engine API"
    contract_version: Literal["1.0"] = CONTRACT_VERSION
    supported_resolution_types: tuple[str, ...]
    operations: tuple[str, ...]
    max_page_size: int = 100
