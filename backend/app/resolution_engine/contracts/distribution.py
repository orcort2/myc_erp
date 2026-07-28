"""Puertos internos para despacho, workers y observabilidad distribuida."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from app.resolution_engine.domain.distribution import (
    DistributedWorkItem,
    DistributedWorkKind,
    DistributedWorkRequest,
    DistributedWorkResult,
    DistributionSnapshot,
    RecoveryReport,
    WorkFailureCertainty,
)


@dataclass(frozen=True, slots=True)
class WorkerRegistration:
    node_id: str
    instance_id: str
    capacity: int = 1


@dataclass(frozen=True, slots=True)
class WorkLease:
    item: DistributedWorkItem


class DistributedWorkHandler(Protocol):
    kind: DistributedWorkKind

    def execute(
        self,
        item: DistributedWorkItem,
        /,
    ) -> DistributedWorkResult:
        """Ejecuta mediante el servicio canónico y conserva idempotencia."""


class DistributedWorkStore(Protocol):
    def register_node(
        self,
        registration: WorkerRegistration,
        *,
        occurred_at: datetime,
        lease_ttl: timedelta,
    ) -> None: ...

    def heartbeat_node(
        self,
        registration: WorkerRegistration,
        *,
        occurred_at: datetime,
        lease_ttl: timedelta,
    ) -> None: ...

    def drain_node(
        self,
        registration: WorkerRegistration,
        *,
        occurred_at: datetime,
    ) -> None: ...

    def enqueue(
        self,
        request: DistributedWorkRequest,
        *,
        occurred_at: datetime,
    ) -> DistributedWorkItem: ...

    def claim_next(
        self,
        registration: WorkerRegistration,
        *,
        occurred_at: datetime,
        lease_ttl: timedelta,
        lease_token: str,
    ) -> WorkLease | None: ...

    def renew_lease(
        self,
        lease: WorkLease,
        *,
        occurred_at: datetime,
        lease_ttl: timedelta,
    ) -> WorkLease: ...

    def mark_effect_started(
        self,
        lease: WorkLease,
        *,
        occurred_at: datetime,
    ) -> WorkLease: ...

    def complete(
        self,
        lease: WorkLease,
        result: DistributedWorkResult,
        *,
        occurred_at: datetime,
    ) -> DistributedWorkItem: ...

    def fail(
        self,
        lease: WorkLease,
        *,
        error_code: str,
        error_message: str,
        certainty: WorkFailureCertainty,
        retryable: bool,
        occurred_at: datetime,
    ) -> DistributedWorkItem: ...

    def recover_expired(
        self,
        *,
        occurred_at: datetime,
    ) -> RecoveryReport: ...

    def snapshot(
        self,
        *,
        organization_id: str | None = None,
    ) -> DistributionSnapshot: ...
