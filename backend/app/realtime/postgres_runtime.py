"""Administración del listener PostgreSQL durante la vida de FastAPI."""

from __future__ import annotations

import asyncio
import logging

import psycopg

from app.core.config import settings
from app.realtime.conversation_revocation import (
    revoke_invalid_conversation_rooms,
)
from app.realtime.distribution import distribute_invalidation
from app.realtime.resource_distribution import distribute_resource_change
from app.realtime.revocation import revoke_invalid_connections
from app.realtime.portal_revocation import refresh_portal_connections
from app.realtime.postgres_bus import listen_invalidations
from app.realtime.runtime import realtime_hub

logger = logging.getLogger(__name__)


class PostgresRealtimeRuntime:
    def __init__(self) -> None:
        self.stop_event = asyncio.Event()
        self.task: asyncio.Task | None = None

    async def start(self) -> None:
        if self.task is not None:
            return

        if not settings.database_url.startswith("postgresql+psycopg://"):
            raise RuntimeError(
                "El transporte realtime requiere PostgreSQL con psycopg"
            )

        self.stop_event.clear()

        dsn = settings.database_url.replace(
            "postgresql+psycopg://",
            "postgresql://",
            1,
        )

        async def connection_factory():
            return await psycopg.AsyncConnection.connect(
                dsn, connect_timeout=5
            )

        async def handler(event):
            await distribute_invalidation(realtime_hub, event)

        async def resource_handler(change):
            if change.resource == "users":
                await revoke_invalid_connections(realtime_hub)

            if change.resource == "communication_authority":
                await revoke_invalid_conversation_rooms(realtime_hub)
                return

            if change.resource == "portal_authority":
                await refresh_portal_connections(realtime_hub)
                return

            await distribute_resource_change(realtime_hub, change)

        self.task = asyncio.create_task(
            listen_invalidations(
                connection_factory,
                handler,
                stop_event=self.stop_event,
                resource_handler=resource_handler,
            ),
            name="myc-postgres-realtime-listener",
        )

        logger.info("PostgreSQL realtime listener task started")

    async def stop(self) -> None:
        if self.task is None:
            return

        self.stop_event.set()

        try:
            await asyncio.wait_for(self.task, timeout=15)
        except TimeoutError:
            logger.error("PostgreSQL realtime listener shutdown timed out")
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        finally:
            self.task = None
