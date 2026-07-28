"""Modelo puro de coordinación distribuida y reintentos deterministas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.exceptions import InvalidResolutionValueError


class DistributedWorkKind(StrEnum):
    EXECUTION = "execution"
    COMPENSATION = "compensation"
    OUTBOX_PUBLICATION = "outbox_publication"


class DistributedWorkStatus(StrEnum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    RETRY_WAIT = "retry_wait"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class WorkerNodeStatus(StrEnum):
    ACTIVE = "active"
    DRAINING = "draining"
    OFFLINE = "offline"


class WorkFailureCertainty(StrEnum):
    NO_EFFECT = "no_effect"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class DeterministicRetryPolicy:
    """Backoff exponencial estable; no incorpora jitter no reproducible."""

    max_attempts: int = 5
    base_delay: timedelta = timedelta(seconds=5)
    maximum_delay: timedelta = timedelta(minutes=5)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise InvalidResolutionValueError("max_attempts must be positive")
        if self.base_delay.total_seconds() <= 0:
            raise InvalidResolutionValueError("base_delay must be positive")
        if self.maximum_delay < self.base_delay:
            raise InvalidResolutionValueError(
                "maximum_delay must be greater than or equal to base_delay"
            )

    def delay_after(self, failed_attempt: int) -> timedelta:
        if failed_attempt < 1:
            raise InvalidResolutionValueError(
                "failed_attempt must be positive"
            )
        seconds = self.base_delay.total_seconds() * (2 ** (failed_attempt - 1))
        return timedelta(
            seconds=min(seconds, self.maximum_delay.total_seconds())
        )


@dataclass(frozen=True, slots=True)
class DistributedWorkRequest:
    work_key: str
    resolution_id: int
    organization_id: str
    kind: DistributedWorkKind
    payload: Mapping[str, Any]
    correlation_id: str
    priority: int = 0
    available_at: datetime | None = None
    retry_policy: DeterministicRetryPolicy = field(
        default_factory=DeterministicRetryPolicy
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", DistributedWorkKind(self.kind))
        for name in ("work_key", "organization_id", "correlation_id"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise InvalidResolutionValueError(f"{name} is required")
            object.__setattr__(self, name, value)
        if self.resolution_id <= 0:
            raise InvalidResolutionValueError(
                "resolution_id must be positive"
            )
        if not -1000 <= self.priority <= 1000:
            raise InvalidResolutionValueError(
                "priority must be between -1000 and 1000"
            )
        if self.available_at is not None and self.available_at.tzinfo is None:
            raise InvalidResolutionValueError(
                "available_at must include timezone"
            )
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    @property
    def request_hash(self) -> str:
        return canonical_sha256(
            {
                "work_key": self.work_key,
                "resolution_id": self.resolution_id,
                "organization_id": self.organization_id,
                "kind": self.kind.value,
                "payload": dict(self.payload),
                "correlation_id": self.correlation_id,
                "priority": self.priority,
                "available_at": (
                    self.available_at.isoformat()
                    if self.available_at is not None
                    else None
                ),
                "max_attempts": self.retry_policy.max_attempts,
                "base_delay_seconds": (
                    self.retry_policy.base_delay.total_seconds()
                ),
                "maximum_delay_seconds": (
                    self.retry_policy.maximum_delay.total_seconds()
                ),
            }
        )


@dataclass(frozen=True, slots=True)
class DistributedWorkItem:
    id: int
    work_key: str
    resolution_id: int
    organization_id: str
    kind: DistributedWorkKind
    status: DistributedWorkStatus
    payload: Mapping[str, Any]
    request_hash: str
    correlation_id: str
    priority: int
    available_at: datetime
    attempt_count: int
    max_attempts: int
    claimed_by: str | None = None
    lease_token: str | None = None
    lease_version: int = 0
    lease_expires_at: datetime | None = None
    effect_started_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", DistributedWorkKind(self.kind))
        object.__setattr__(self, "status", DistributedWorkStatus(self.status))
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


@dataclass(frozen=True, slots=True)
class DistributedWorkResult:
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    @property
    def result_hash(self) -> str:
        return canonical_sha256(dict(self.payload))


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    requeued: int = 0
    blocked_uncertain: int = 0
    offline_nodes: int = 0


@dataclass(frozen=True, slots=True)
class DistributionSnapshot:
    queued: int = 0
    claimed: int = 0
    retry_wait: int = 0
    succeeded: int = 0
    failed: int = 0
    blocked: int = 0
    active_nodes: int = 0
    draining_nodes: int = 0
    offline_nodes: int = 0
