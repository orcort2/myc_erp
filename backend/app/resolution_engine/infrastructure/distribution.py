"""Coordinación SQL multinodo con leases y fencing tokens."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.resolution_engine.contracts.distribution import (
    WorkerRegistration,
    WorkLease,
)
from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.distribution import (
    DistributedWorkItem,
    DistributedWorkRequest,
    DistributedWorkResult,
    DistributionSnapshot,
    RecoveryReport,
    WorkFailureCertainty,
)
from app.resolution_engine.domain.exceptions import (
    DistributedLeaseLostError,
    DistributedWorkConflictError,
    WorkerNodeUnavailableError,
)
from app.resolution_engine.infrastructure.persistence import (
    ResolutionWorkerNode,
    ResolutionWorkEvent,
    ResolutionWorkItem,
)


class SqlAlchemyDistributedWorkStore:
    """Cola durable compartida por procesos; cada método es transaccional."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def register_node(
        self,
        registration: WorkerRegistration,
        *,
        occurred_at: datetime,
        lease_ttl: timedelta,
    ) -> None:
        self._validate_registration(registration, lease_ttl)
        with self._session_factory() as session, session.begin():
            row = session.get(
                ResolutionWorkerNode,
                registration.node_id,
                with_for_update=True,
            )
            if row is None:
                session.add(
                    ResolutionWorkerNode(
                        node_id=registration.node_id,
                        instance_id=registration.instance_id,
                        status="active",
                        capacity=registration.capacity,
                        started_at=occurred_at,
                        last_heartbeat_at=occurred_at,
                        lease_expires_at=occurred_at + lease_ttl,
                        metadata_json={},
                    )
                )
                return
            if (
                row.instance_id != registration.instance_id
                and self._aware(row.lease_expires_at) > occurred_at
                and row.status != "offline"
            ):
                raise WorkerNodeUnavailableError(
                    f"worker node is owned by another live instance: "
                    f"{registration.node_id}"
                )
            row.instance_id = registration.instance_id
            row.status = "active"
            row.capacity = registration.capacity
            row.started_at = occurred_at
            row.last_heartbeat_at = occurred_at
            row.lease_expires_at = occurred_at + lease_ttl

    def heartbeat_node(
        self,
        registration: WorkerRegistration,
        *,
        occurred_at: datetime,
        lease_ttl: timedelta,
    ) -> None:
        with self._session_factory() as session, session.begin():
            row = self._active_node(
                session,
                registration,
                occurred_at=occurred_at,
                for_update=True,
            )
            row.last_heartbeat_at = occurred_at
            row.lease_expires_at = occurred_at + lease_ttl

    def drain_node(
        self,
        registration: WorkerRegistration,
        *,
        occurred_at: datetime,
    ) -> None:
        with self._session_factory() as session, session.begin():
            row = self._active_node(
                session,
                registration,
                occurred_at=occurred_at,
                for_update=True,
            )
            row.status = "draining"
            row.last_heartbeat_at = occurred_at

    def enqueue(
        self,
        request: DistributedWorkRequest,
        *,
        occurred_at: datetime,
    ) -> DistributedWorkItem:
        try:
            with self._session_factory() as session, session.begin():
                existing = session.scalar(
                    select(ResolutionWorkItem).where(
                        ResolutionWorkItem.work_key == request.work_key
                    )
                )
                if existing is not None:
                    return self._matching_existing(existing, request)
                row = ResolutionWorkItem(
                    resolution_id=request.resolution_id,
                    work_key=request.work_key,
                    organization_id=request.organization_id,
                    kind=request.kind.value,
                    status="queued",
                    payload=dict(request.payload),
                    request_hash=request.request_hash,
                    correlation_id=request.correlation_id,
                    priority=request.priority,
                    available_at=request.available_at or occurred_at,
                    attempt_count=0,
                    max_attempts=request.retry_policy.max_attempts,
                    retry_base_seconds=int(
                        request.retry_policy.base_delay.total_seconds()
                    ),
                    retry_maximum_seconds=int(
                        request.retry_policy.maximum_delay.total_seconds()
                    ),
                    claimed_by=None,
                    lease_token=None,
                    lease_version=0,
                    lease_expires_at=None,
                    effect_started_at=None,
                    result_payload={},
                )
                session.add(row)
                session.flush()
                self._event(
                    session,
                    row,
                    "work.enqueued",
                    occurred_at=occurred_at,
                    payload={"request_hash": row.request_hash},
                )
                return self._item(row)
        except IntegrityError:
            with self._session_factory() as session:
                existing = session.scalar(
                    select(ResolutionWorkItem).where(
                        ResolutionWorkItem.work_key == request.work_key
                    )
                )
                if existing is None:
                    raise
                return self._matching_existing(existing, request)

    def claim_next(
        self,
        registration: WorkerRegistration,
        *,
        occurred_at: datetime,
        lease_ttl: timedelta,
        lease_token: str,
    ) -> WorkLease | None:
        try:
            with self._session_factory() as session, session.begin():
                node = self._active_node(
                    session,
                    registration,
                    occurred_at=occurred_at,
                    for_update=True,
                )
                active_claims = session.scalar(
                    select(func.count(ResolutionWorkItem.id)).where(
                        ResolutionWorkItem.claimed_by == registration.node_id,
                        ResolutionWorkItem.status == "claimed",
                        ResolutionWorkItem.lease_expires_at > occurred_at,
                    )
                ) or 0
                if active_claims >= node.capacity:
                    return None
                competing = aliased(ResolutionWorkItem)
                query = (
                    select(ResolutionWorkItem)
                    .where(
                        ResolutionWorkItem.status.in_(
                            ("queued", "retry_wait")
                        ),
                        ResolutionWorkItem.available_at <= occurred_at,
                        ResolutionWorkItem.attempt_count
                        < ResolutionWorkItem.max_attempts,
                        ~select(competing.id)
                        .where(
                            competing.resolution_id
                            == ResolutionWorkItem.resolution_id,
                            competing.status == "claimed",
                        )
                        .exists(),
                    )
                    .order_by(
                        ResolutionWorkItem.priority.desc(),
                        ResolutionWorkItem.available_at,
                        ResolutionWorkItem.id,
                    )
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                row = session.scalar(query)
                if row is None:
                    return None
                row.status = "claimed"
                row.claimed_by = registration.node_id
                row.lease_token = lease_token
                row.lease_version += 1
                row.lease_expires_at = occurred_at + lease_ttl
                row.effect_started_at = None
                row.attempt_count += 1
                row.last_error_code = None
                row.last_error_message = None
                self._event(
                    session,
                    row,
                    "work.claimed",
                    occurred_at=occurred_at,
                    payload={
                        "lease_expires_at": row.lease_expires_at.isoformat(),
                    },
                )
                session.flush()
                return WorkLease(item=self._item(row))
        except IntegrityError:
            # El índice parcial cierra la carrera entre dos snapshots que
            # intentaron reclamar trabajos distintos de la misma resolución.
            return None

    def renew_lease(
        self,
        lease: WorkLease,
        *,
        occurred_at: datetime,
        lease_ttl: timedelta,
    ) -> WorkLease:
        with self._session_factory() as session, session.begin():
            row = self._owned_claim(
                session, lease, occurred_at=occurred_at
            )
            row.lease_expires_at = occurred_at + lease_ttl
            session.flush()
            return WorkLease(item=self._item(row))

    def mark_effect_started(
        self,
        lease: WorkLease,
        *,
        occurred_at: datetime,
    ) -> WorkLease:
        with self._session_factory() as session, session.begin():
            row = self._owned_claim(
                session, lease, occurred_at=occurred_at
            )
            if row.effect_started_at is None:
                row.effect_started_at = occurred_at
                self._event(
                    session,
                    row,
                    "work.effect_started",
                    occurred_at=occurred_at,
                    payload={},
                )
            session.flush()
            return WorkLease(item=self._item(row))

    def complete(
        self,
        lease: WorkLease,
        result: DistributedWorkResult,
        *,
        occurred_at: datetime,
    ) -> DistributedWorkItem:
        with self._session_factory() as session, session.begin():
            row = self._owned_claim(
                session, lease, occurred_at=occurred_at
            )
            row.status = "succeeded"
            row.completed_at = occurred_at
            row.result_payload = dict(result.payload)
            row.result_hash = result.result_hash
            self._event(
                session,
                row,
                "work.succeeded",
                occurred_at=occurred_at,
                payload={"result_hash": row.result_hash},
            )
            self._release(row)
            session.flush()
            return self._item(row)

    def fail(
        self,
        lease: WorkLease,
        *,
        error_code: str,
        error_message: str,
        certainty: WorkFailureCertainty,
        retryable: bool,
        occurred_at: datetime,
    ) -> DistributedWorkItem:
        certainty = WorkFailureCertainty(certainty)
        with self._session_factory() as session, session.begin():
            row = self._owned_claim(
                session, lease, occurred_at=occurred_at
            )
            may_retry = (
                retryable
                and certainty is WorkFailureCertainty.NO_EFFECT
                and row.attempt_count < row.max_attempts
            )
            row.last_error_code = error_code[:160]
            row.last_error_message = error_message
            if may_retry:
                row.status = "retry_wait"
                delay_seconds = min(
                    row.retry_base_seconds * (2 ** (row.attempt_count - 1)),
                    row.retry_maximum_seconds,
                )
                row.available_at = occurred_at + timedelta(
                    seconds=delay_seconds
                )
                row.effect_started_at = None
                event_type = "work.retry_scheduled"
            elif certainty is WorkFailureCertainty.UNCERTAIN:
                row.status = "blocked"
                row.completed_at = occurred_at
                event_type = "work.blocked_uncertain"
            else:
                row.status = "failed"
                row.completed_at = occurred_at
                event_type = "work.failed"
            self._event(
                session,
                row,
                event_type,
                occurred_at=occurred_at,
                payload={
                    "error_code": row.last_error_code,
                    "certainty": certainty.value,
                    "retryable": may_retry,
                    "available_at": (
                        row.available_at.isoformat() if may_retry else None
                    ),
                },
            )
            self._release(row)
            session.flush()
            return self._item(row)

    def recover_expired(
        self,
        *,
        occurred_at: datetime,
    ) -> RecoveryReport:
        requeued = 0
        blocked = 0
        offline = 0
        with self._session_factory() as session, session.begin():
            nodes = session.scalars(
                select(ResolutionWorkerNode)
                .where(
                    ResolutionWorkerNode.status.in_(("active", "draining")),
                    ResolutionWorkerNode.lease_expires_at <= occurred_at,
                )
                .with_for_update(skip_locked=True)
            ).all()
            for node in nodes:
                node.status = "offline"
                offline += 1
            rows = session.scalars(
                select(ResolutionWorkItem)
                .where(
                    ResolutionWorkItem.status == "claimed",
                    ResolutionWorkItem.lease_expires_at <= occurred_at,
                )
                .order_by(ResolutionWorkItem.id)
                .with_for_update(skip_locked=True)
            ).all()
            for row in rows:
                if row.effect_started_at is not None:
                    row.status = "blocked"
                    row.completed_at = occurred_at
                    row.last_error_code = "distributed_lease_expired_uncertain"
                    row.last_error_message = (
                        "worker lease expired after effect execution began"
                    )
                    event_type = "work.recovery_blocked_uncertain"
                    blocked += 1
                elif row.attempt_count < row.max_attempts:
                    row.status = "retry_wait"
                    row.available_at = occurred_at
                    row.last_error_code = "distributed_lease_expired"
                    row.last_error_message = (
                        "worker lease expired before effect execution began"
                    )
                    event_type = "work.recovery_requeued"
                    requeued += 1
                else:
                    row.status = "failed"
                    row.completed_at = occurred_at
                    row.last_error_code = "distributed_attempts_exhausted"
                    row.last_error_message = (
                        "worker lease expired and no attempts remain"
                    )
                    event_type = "work.recovery_failed"
                self._event(
                    session,
                    row,
                    event_type,
                    occurred_at=occurred_at,
                    payload={},
                )
                self._release(row)
        return RecoveryReport(
            requeued=requeued,
            blocked_uncertain=blocked,
            offline_nodes=offline,
        )

    def snapshot(
        self,
        *,
        organization_id: str | None = None,
    ) -> DistributionSnapshot:
        with self._session_factory() as session:
            work_query = select(
                ResolutionWorkItem.status,
                func.count(ResolutionWorkItem.id),
            ).group_by(ResolutionWorkItem.status)
            if organization_id is not None:
                work_query = work_query.where(
                    ResolutionWorkItem.organization_id == organization_id
                )
            work_counts = dict(session.execute(work_query).all())
            node_counts = dict(
                session.execute(
                    select(
                        ResolutionWorkerNode.status,
                        func.count(ResolutionWorkerNode.node_id),
                    ).group_by(ResolutionWorkerNode.status)
                ).all()
            )
            return DistributionSnapshot(
                queued=work_counts.get("queued", 0),
                claimed=work_counts.get("claimed", 0),
                retry_wait=work_counts.get("retry_wait", 0),
                succeeded=work_counts.get("succeeded", 0),
                failed=work_counts.get("failed", 0),
                blocked=work_counts.get("blocked", 0),
                active_nodes=node_counts.get("active", 0),
                draining_nodes=node_counts.get("draining", 0),
                offline_nodes=node_counts.get("offline", 0),
            )

    @staticmethod
    def _validate_registration(
        registration: WorkerRegistration,
        lease_ttl: timedelta,
    ) -> None:
        if not registration.node_id.strip() or not registration.instance_id.strip():
            raise ValueError("node_id and instance_id are required")
        if registration.capacity < 1:
            raise ValueError("worker capacity must be positive")
        if lease_ttl.total_seconds() <= 0:
            raise ValueError("lease_ttl must be positive")

    def _active_node(
        self,
        session: Session,
        registration: WorkerRegistration,
        *,
        occurred_at: datetime,
        for_update: bool,
    ) -> ResolutionWorkerNode:
        query = select(ResolutionWorkerNode).where(
            ResolutionWorkerNode.node_id == registration.node_id
        )
        if for_update:
            query = query.with_for_update()
        row = session.scalar(query)
        if (
            row is None
            or row.instance_id != registration.instance_id
            or row.status != "active"
            or self._aware(row.lease_expires_at) <= occurred_at
        ):
            raise WorkerNodeUnavailableError(
                f"worker node is not active: {registration.node_id}"
            )
        return row

    def _owned_claim(
        self,
        session: Session,
        lease: WorkLease,
        *,
        occurred_at: datetime,
    ) -> ResolutionWorkItem:
        row = session.scalar(
            select(ResolutionWorkItem)
            .where(
                ResolutionWorkItem.id == lease.item.id,
                ResolutionWorkItem.status == "claimed",
                ResolutionWorkItem.claimed_by == lease.item.claimed_by,
                ResolutionWorkItem.lease_token == lease.item.lease_token,
                ResolutionWorkItem.lease_version == lease.item.lease_version,
            )
            .with_for_update()
        )
        if (
            row is None
            or row.lease_expires_at is None
            or self._aware(row.lease_expires_at) <= occurred_at
        ):
            raise DistributedLeaseLostError(
                f"distributed work lease is no longer valid: {lease.item.id}"
            )
        return row

    def _matching_existing(
        self,
        row: ResolutionWorkItem,
        request: DistributedWorkRequest,
    ) -> DistributedWorkItem:
        if row.request_hash != request.request_hash:
            raise DistributedWorkConflictError(
                f"work key already represents another request: "
                f"{request.work_key}"
            )
        return self._item(row)

    def _event(
        self,
        session: Session,
        row: ResolutionWorkItem,
        event_type: str,
        *,
        occurred_at: datetime,
        payload: dict,
    ) -> None:
        with session.no_autoflush:
            sequence = (
                session.scalar(
                    select(func.max(ResolutionWorkEvent.sequence)).where(
                        ResolutionWorkEvent.work_item_id == row.id
                    )
                )
                or 0
            ) + 1
        session.add(
            ResolutionWorkEvent(
                work_item_id=row.id,
                resolution_id=row.resolution_id,
                sequence=sequence,
                event_type=event_type,
                attempt_number=row.attempt_count,
                node_id=row.claimed_by,
                lease_version=(
                    row.lease_version if row.lease_version else None
                ),
                occurred_at=occurred_at,
                correlation_id=row.correlation_id,
                payload=payload,
                payload_hash=canonical_sha256(payload),
            )
        )

    @staticmethod
    def _release(row: ResolutionWorkItem) -> None:
        row.claimed_by = None
        row.lease_token = None
        row.lease_expires_at = None

    @staticmethod
    def _item(row: ResolutionWorkItem) -> DistributedWorkItem:
        return DistributedWorkItem(
            id=row.id,
            work_key=row.work_key,
            resolution_id=row.resolution_id,
            organization_id=row.organization_id,
            kind=row.kind,
            status=row.status,
            payload=row.payload,
            request_hash=row.request_hash,
            correlation_id=row.correlation_id,
            priority=row.priority,
            available_at=row.available_at,
            attempt_count=row.attempt_count,
            max_attempts=row.max_attempts,
            claimed_by=row.claimed_by,
            lease_token=row.lease_token,
            lease_version=row.lease_version,
            lease_expires_at=row.lease_expires_at,
            effect_started_at=row.effect_started_at,
        )

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(
            tzinfo=timezone.utc
        )
