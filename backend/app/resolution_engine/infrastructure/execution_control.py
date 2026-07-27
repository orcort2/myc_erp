"""Primitivas SQL de locks e idempotencia, sin reglas de ejecución."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.resolution_engine.domain.enums import (
    IdempotencyScope,
    IdempotencyStatus,
    ResolutionLockType,
)
from app.resolution_engine.domain.exceptions import (
    ExecutionAlreadyInProgressError,
    ExecutionIdempotencyConflictError,
    ExecutionLockLostError,
    ExecutionLockUnavailableError,
)
from app.resolution_engine.infrastructure.persistence import (
    ResolutionIdempotencyRecord,
    ResolutionLock,
)


class SqlAlchemyExecutionControl:
    """Opera registros de control dentro de una transacción recibida."""

    @staticmethod
    def acquire_lock(
        session: Session,
        *,
        resolution_id: int,
        lock_key: str,
        owner: str,
        token: str,
        acquired_at: datetime,
        expires_at: datetime,
        lock_type: ResolutionLockType = ResolutionLockType.EXECUTION,
    ) -> ResolutionLock:
        session.execute(
            update(ResolutionLock)
            .where(
                ResolutionLock.lock_type == lock_type.value,
                ResolutionLock.lock_key == lock_key,
                ResolutionLock.released_at.is_(None),
                ResolutionLock.expires_at <= acquired_at,
            )
            .values(released_at=acquired_at)
        )
        active = session.scalar(
            select(ResolutionLock).where(
                ResolutionLock.lock_type == lock_type.value,
                ResolutionLock.lock_key == lock_key,
                ResolutionLock.released_at.is_(None),
            )
        )
        if active is not None:
            raise ExecutionLockUnavailableError(
                f"Execution lock is held by {active.owner}"
            )
        lock = ResolutionLock(
            resolution_id=resolution_id,
            lock_type=lock_type.value,
            lock_key=lock_key,
            owner=owner,
            token=token,
            acquired_at=acquired_at,
            expires_at=expires_at,
            metadata_json={},
        )
        session.add(lock)
        session.flush()
        return lock

    @staticmethod
    def renew_lock(
        session: Session,
        *,
        resolution_id: int,
        token: str,
        occurred_at: datetime,
        expires_at: datetime,
        lock_type: ResolutionLockType = ResolutionLockType.EXECUTION,
    ) -> None:
        result = session.execute(
            update(ResolutionLock)
            .where(
                ResolutionLock.resolution_id == resolution_id,
                ResolutionLock.lock_type == lock_type.value,
                ResolutionLock.token == token,
                ResolutionLock.released_at.is_(None),
                ResolutionLock.expires_at > occurred_at,
            )
            .values(expires_at=expires_at)
        )
        if result.rowcount != 1:
            raise ExecutionLockLostError(
                f"Execution lock is no longer valid: {token}"
            )

    @staticmethod
    def assert_lock(
        session: Session,
        *,
        resolution_id: int,
        token: str,
        occurred_at: datetime,
        for_update: bool = False,
        lock_type: ResolutionLockType = ResolutionLockType.EXECUTION,
    ) -> ResolutionLock:
        query = select(ResolutionLock).where(
            ResolutionLock.resolution_id == resolution_id,
            ResolutionLock.lock_type == lock_type.value,
            ResolutionLock.token == token,
            ResolutionLock.released_at.is_(None),
            ResolutionLock.expires_at > occurred_at,
        )
        if for_update:
            query = query.with_for_update()
        lock = session.scalar(query)
        if lock is None:
            raise ExecutionLockLostError(
                f"Execution lock is no longer valid: {token}"
            )
        return lock

    @staticmethod
    def release_lock(
        session: Session,
        *,
        resolution_id: int,
        token: str,
        released_at: datetime,
        required: bool = True,
        lock_type: ResolutionLockType = ResolutionLockType.EXECUTION,
    ) -> None:
        result = session.execute(
            update(ResolutionLock)
            .where(
                ResolutionLock.resolution_id == resolution_id,
                ResolutionLock.lock_type == lock_type.value,
                ResolutionLock.token == token,
                ResolutionLock.released_at.is_(None),
            )
            .values(released_at=released_at)
        )
        if required and result.rowcount != 1:
            raise ExecutionLockLostError(
                f"Execution lock cannot be released: {token}"
            )

    @staticmethod
    def find_idempotency(
        session: Session,
        *,
        scope: IdempotencyScope,
        key: str,
    ) -> ResolutionIdempotencyRecord | None:
        return session.scalar(
            select(ResolutionIdempotencyRecord).where(
                ResolutionIdempotencyRecord.scope == scope.value,
                ResolutionIdempotencyRecord.idempotency_key == key,
            )
        )

    @staticmethod
    def validate_idempotency(
        record: ResolutionIdempotencyRecord,
        *,
        request_hash: str,
    ) -> Mapping[str, Any] | None:
        if record.request_hash != request_hash:
            raise ExecutionIdempotencyConflictError(
                f"Idempotency key has another request: "
                f"{record.idempotency_key}"
            )
        if record.status == IdempotencyStatus.IN_PROGRESS.value:
            raise ExecutionAlreadyInProgressError(
                f"Idempotent operation is in progress: "
                f"{record.idempotency_key}"
            )
        return record.response_payload

    @staticmethod
    def create_idempotency(
        session: Session,
        *,
        scope: IdempotencyScope,
        key: str,
        operation_key: str,
        request_hash: str,
        resolution_id: int,
        execution_id: int,
        step_execution_id: int | None = None,
    ) -> ResolutionIdempotencyRecord:
        record = ResolutionIdempotencyRecord(
            scope=scope.value,
            idempotency_key=key,
            resolution_id=resolution_id,
            execution_id=execution_id,
            step_execution_id=step_execution_id,
            operation_key=operation_key,
            status=IdempotencyStatus.IN_PROGRESS.value,
            request_hash=request_hash,
            metadata_json={},
        )
        session.add(record)
        session.flush()
        return record

    @staticmethod
    def finish_idempotency(
        record: ResolutionIdempotencyRecord,
        *,
        succeeded: bool,
        response_payload: Mapping[str, Any],
        completed_at: datetime,
    ) -> None:
        record.status = (
            IdempotencyStatus.COMPLETED.value
            if succeeded
            else IdempotencyStatus.FAILED.value
        )
        record.response_payload = dict(response_payload)
        record.completed_at = completed_at
