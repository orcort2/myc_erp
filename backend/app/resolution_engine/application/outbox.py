"""Publicación explícita del outbox, sin scheduler, worker ni retry."""

from __future__ import annotations

from app.resolution_engine.contracts.execution import (
    EventPublisher,
    OutboxPublicationReport,
    OutboxStore,
    PublishOutboxCommand,
)
from app.resolution_engine.contracts.runtime import Clock


class OutboxPublicationService:
    """Publica un lote solicitado y conserva cada resultado."""

    def __init__(
        self,
        *,
        store: OutboxStore,
        publisher: EventPublisher,
        clock: Clock,
    ) -> None:
        self._store = store
        self._publisher = publisher
        self._clock = clock

    def publish_available(
        self,
        command: PublishOutboxCommand,
        /,
    ) -> OutboxPublicationReport:
        if command.limit <= 0:
            raise ValueError("limit must be positive")
        requested_at = self._clock.now()
        self._store.verify_publication(
            command,
            occurred_at=requested_at,
        )
        messages = self._store.pending(
            organization_id=command.organization_id,
            available_at=requested_at,
            limit=command.limit,
        )
        published = 0
        failed = 0
        for message in messages:
            try:
                self._publisher.publish(message)
            except Exception as exc:
                self._store.mark_failed(
                    message.id,
                    error=str(exc),
                    failed_at=self._clock.now(),
                )
                failed += 1
            else:
                self._store.mark_published(
                    message.id,
                    published_at=self._clock.now(),
                )
                published += 1
        return OutboxPublicationReport(
            published=published,
            failed=failed,
        )
