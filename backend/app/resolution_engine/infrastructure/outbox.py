"""Persistencia y consulta del outbox de publicación explícita."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Mapping

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.resolution_engine.contracts.execution import (
    OutboxMessage,
    OutboxPublicationReport,
    OutboxReservationResult,
    PublishOutboxCommand,
    outbox_security_operation_payload,
)
from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.enums import OutboxStatus
from app.resolution_engine.domain.exceptions import ExecutionNotReadyError
from app.resolution_engine.domain.security import SecurityDecisionUseMode
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionOutboxEvent,
    ResolutionSecurityDecision,
    ResolutionSecurityDecisionUse,
)
from app.resolution_engine.infrastructure.security_decisions import (
    SecurityDecisionExpectation,
    SqlAlchemySecurityDecisionVerifier,
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
        self._security = SqlAlchemySecurityDecisionVerifier()

    def verify_publication(
        self,
        command: PublishOutboxCommand,
        *,
        occurred_at: datetime,
    ) -> None:
        with self._session_factory() as session:
            reasons = self._security.verify(
                session,
                self._expectation(command, occurred_at=occurred_at),
            )
        if reasons:
            raise ExecutionNotReadyError(
                "exact outbox publication authorization is invalid: "
                + ", ".join(reasons)
            )

    def reserve_publication(
        self,
        command: PublishOutboxCommand,
        *,
        occurred_at: datetime,
    ) -> OutboxReservationResult:
        """Consume la concesión y congela el lote en una transacción."""

        with self._session_factory() as session:
            with session.begin():
                session.scalar(
                    select(ResolutionSecurityDecision)
                    .where(
                        ResolutionSecurityDecision.id
                        == command.security_decision_id
                    )
                    .with_for_update()
                )
                existing_use = session.scalar(
                    select(ResolutionSecurityDecisionUse).where(
                        ResolutionSecurityDecisionUse.security_decision_id
                        == command.security_decision_id
                    )
                )
                if existing_use is None:
                    rows = tuple(
                        session.scalars(
                            select(ResolutionOutboxEvent)
                            .join(
                                Resolution,
                                Resolution.id
                                == ResolutionOutboxEvent.resolution_id,
                            )
                            .where(
                                Resolution.organization_id
                                == command.organization_id,
                                ResolutionOutboxEvent.status
                                == OutboxStatus.PENDING.value,
                                ResolutionOutboxEvent.available_at
                                <= occurred_at,
                                ResolutionOutboxEvent
                                .publication_operation_id
                                .is_(None),
                            )
                            .order_by(ResolutionOutboxEvent.id)
                            .limit(command.limit)
                            .with_for_update()
                        )
                    )
                    event_ids = [row.id for row in rows]
                    claim, reasons = self._security.claim(
                        session,
                        self._expectation(
                            command,
                            occurred_at=occurred_at,
                        ),
                        operation_context={"event_ids": event_ids},
                    )
                    if reasons:
                        raise ExecutionNotReadyError(
                            "exact outbox publication authorization is "
                            "invalid: " + ", ".join(reasons)
                        )
                    for row in rows:
                        row.publication_operation_id = command.operation_id
                    session.flush()
                    return OutboxReservationResult(
                        messages=tuple(self._message(row) for row in rows)
                    )

                claim, reasons = self._security.claim(
                    session,
                    self._expectation(command, occurred_at=occurred_at),
                )
                if reasons or claim is None:
                    raise ExecutionNotReadyError(
                        "exact outbox publication authorization is "
                        "invalid: " + ", ".join(reasons)
                    )
                event_ids = tuple(
                    int(value)
                    for value in claim.operation_context.get(
                        "event_ids",
                        (),
                    )
                )
                rows = (
                    tuple(
                        session.scalars(
                            select(ResolutionOutboxEvent).where(
                                ResolutionOutboxEvent.id.in_(event_ids),
                                ResolutionOutboxEvent
                                .publication_operation_id
                                == command.operation_id,
                            )
                        )
                    )
                    if event_ids
                    else ()
                )
                return OutboxReservationResult(
                    previous_report=OutboxPublicationReport(
                        published=sum(
                            row.status == OutboxStatus.PUBLISHED.value
                            for row in rows
                        ),
                        failed=sum(
                            row.status == OutboxStatus.FAILED.value
                            for row in rows
                        ),
                    )
                )

    def pending(
        self,
        *,
        organization_id: str,
        available_at: datetime,
        limit: int,
    ) -> tuple[OutboxMessage, ...]:
        with self._session_factory() as session:
            rows = tuple(
                session.scalars(
                    select(ResolutionOutboxEvent)
                    .join(
                        Resolution,
                        Resolution.id
                        == ResolutionOutboxEvent.resolution_id,
                    )
                    .where(
                        Resolution.organization_id == organization_id,
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
                        failed_at=failed_at,
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

    @staticmethod
    def _expectation(
        command: PublishOutboxCommand,
        *,
        occurred_at: datetime,
    ) -> SecurityDecisionExpectation:
        return SecurityDecisionExpectation(
            decision_id=command.security_decision_id,
            action="resolution.outbox.publish",
            resource_type="resolution_outbox",
            resource_id=command.organization_id,
            actor=command.actor,
            required_permissions=(
                ComponentKey("resolution.outbox.publish"),
            ),
            occurred_at=occurred_at,
            use_mode=SecurityDecisionUseMode.SINGLE_OPERATION,
            operation_id=command.operation_id,
            operation_payload=outbox_security_operation_payload(
                organization_id=command.organization_id,
                limit=command.limit,
            ),
            context={"limit": command.limit},
        )
