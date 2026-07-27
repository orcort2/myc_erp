"""Persistencia y consulta del outbox de publicación explícita."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Mapping

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.resolution_engine.contracts.execution import OutboxMessage
from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.enums import OutboxStatus
from app.resolution_engine.infrastructure.persistence import (
    ResolutionOutboxEvent,
)


def enqueue_outbox_event(
    session: Session,
    *,
    resolution_id: int,
    event_key: str,
    event_type: str,
    aggregate_id: str,
    payload: Mapping[str, Any],
    occurred_at: datetime,
    correlation_id: str | None,
) -> ResolutionOutboxEvent:
    """Agrega un mensaje en la misma transacción del cambio fuente."""

    normalized_payload = dict(payload)
    event = ResolutionOutboxEvent(
        resolution_id=resolution_id,
        event_key=event_key,
        event_type=event_type,
        aggregate_type="resolution",
        aggregate_id=aggregate_id,
        payload=normalized_payload,
        payload_hash=canonical_sha256(normalized_payload),
        status=OutboxStatus.PENDING.value,
        occurred_at=occurred_at,
        available_at=occurred_at,
        attempts=0,
        correlation_id=correlation_id,
    )
    session.add(event)
    return event


class SqlAlchemyOutboxStore:
    """Publica por invocación explícita; no agenda ni reintenta mensajes."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def pending(
        self,
        *,
        available_at: datetime,
        limit: int,
    ) -> tuple[OutboxMessage, ...]:
        with self._session_factory() as session:
            rows = tuple(
                session.scalars(
                    select(ResolutionOutboxEvent)
                    .where(
                        ResolutionOutboxEvent.status
                        == OutboxStatus.PENDING.value,
                        ResolutionOutboxEvent.available_at <= available_at,
                    )
                    .order_by(ResolutionOutboxEvent.id)
                    .limit(limit)
                )
            )
            return tuple(self._message(row) for row in rows)

    def mark_published(
        self,
        message_id: int,
        *,
        published_at: datetime,
    ) -> None:
        with self._session_factory() as session:
            with session.begin():
                session.execute(
                    update(ResolutionOutboxEvent)
                    .where(
                        ResolutionOutboxEvent.id == message_id,
                        ResolutionOutboxEvent.status
                        == OutboxStatus.PENDING.value,
                    )
                    .values(
                        status=OutboxStatus.PUBLISHED.value,
                        published_at=published_at,
                        attempts=ResolutionOutboxEvent.attempts + 1,
                        last_error=None,
                    )
                )

    def mark_failed(
        self,
        message_id: int,
        *,
        error: str,
        failed_at: datetime,
    ) -> None:
        del failed_at
        with self._session_factory() as session:
            with session.begin():
                session.execute(
                    update(ResolutionOutboxEvent)
                    .where(
                        ResolutionOutboxEvent.id == message_id,
                        ResolutionOutboxEvent.status
                        == OutboxStatus.PENDING.value,
                    )
                    .values(
                        status=OutboxStatus.FAILED.value,
                        attempts=ResolutionOutboxEvent.attempts + 1,
                        last_error=error[:2000],
                    )
                )

    @staticmethod
    def _message(row: ResolutionOutboxEvent) -> OutboxMessage:
        return OutboxMessage(
            id=row.id,
            event_key=row.event_key,
            event_type=row.event_type,
            aggregate_type=row.aggregate_type,
            aggregate_id=row.aggregate_id,
            payload=dict(row.payload),
            payload_hash=row.payload_hash,
            occurred_at=row.occurred_at,
            correlation_id=row.correlation_id,
        )
