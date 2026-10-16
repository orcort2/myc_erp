"""Transporte PostgreSQL para invalidaciones entre procesos del ERP."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.realtime.invalidation import (
    INVALIDATION_CHANNEL,
    ResourceInvalidation,
    build_invalidation_payload,
    parse_invalidation_payload,
)

from app.realtime.resource_changes import (
    RESOURCE_CHANGE_CHANNEL,
    ResourceChange,
    parse_resource_change,
)

logger = logging.getLogger(__name__)

InvalidationHandler = Callable[[ResourceInvalidation], Awaitable[None]]


def notify_resources(
    db: Session,
    resources: list[str] | tuple[str, ...],
    *,
    user_ids: list[int] | tuple[int, ...],
) -> None:
    """Encola NOTIFY en la transacción actual; no ejecuta commit."""

    payload = build_invalidation_payload(
        resources,
        user_ids=user_ids,
    )

    db.execute(
        text("SELECT pg_notify(:channel, :payload)"),
        {
            "channel": INVALIDATION_CHANNEL,
            "payload": payload,
        },
    )


async def listen_invalidations(
    connection_factory,
    handler: InvalidationHandler,
    *,
    stop_event: asyncio.Event,
    resource_handler: Callable[[ResourceChange], Awaitable[None]] | None = None,
) -> None:
    """Escucha PostgreSQL con reconexión y cancelación asíncrona."""

    while not stop_event.is_set():
        try:
            async with await connection_factory() as connection:
                await connection.set_autocommit(True)

                async with connection.cursor() as cursor:
                    await cursor.execute(
                        f"LISTEN {INVALIDATION_CHANNEL}"
                    )

                if resource_handler is not None:
                    async with connection.cursor() as cursor:
                        await cursor.execute(
                            f"LISTEN {RESOURCE_CHANGE_CHANNEL}"
                        )

                logger.info("PostgreSQL invalidation listener connected")

                while not stop_event.is_set():
                    async for notification in connection.notifies(
                        timeout=1.0
                    ):

                        if notification.channel == RESOURCE_CHANGE_CHANNEL:
                            if resource_handler is None:
                                continue
                            try:
                                change = parse_resource_change(
                                    notification.payload
                                )
                            except ValueError:
                                logger.warning(
                                    "Invalid resource change discarded"
                                )
                                continue
                            try:
                                await resource_handler(change)
                            except Exception:
                                logger.exception(
                                    "Resource change delivery failed"
                                )
                            continue

                        if notification.channel != INVALIDATION_CHANNEL:
                            continue

                        try:
                            event = parse_invalidation_payload(
                                notification.payload
                            )
                        except ValueError:
                            logger.warning(
                                "Invalid PostgreSQL invalidation discarded"
                            )
                            continue

                        try:
                            await handler(event)
                        except Exception:
                            logger.exception(
                                "PostgreSQL invalidation delivery failed"
                            )

        except asyncio.CancelledError:
            raise
        except Exception:
            if stop_event.is_set():
                break

            logger.exception(
                "PostgreSQL invalidation listener disconnected"
            )

            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=2,
                )
            except TimeoutError:
                pass
