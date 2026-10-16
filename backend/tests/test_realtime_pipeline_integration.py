"""Integración del trigger instalado con el listener PostgreSQL."""

import asyncio
import os
from unittest.mock import AsyncMock

import psycopg
import pytest

from app.realtime.postgres_bus import listen_invalidations


TEST_DSN = os.getenv("MYC_REALTIME_TEST_DATABASE_URL")


@pytest.mark.skipif(
    not TEST_DSN,
    reason="Base PostgreSQL de integración no configurada",
)
def test_installed_trigger_reaches_resource_handler():
    async def scenario():
        dsn = TEST_DSN.replace(
            "postgresql+psycopg://",
            "postgresql://",
            1,
        )

        if dsn.split("?", 1)[0].rsplit("/", 1)[-1] != "erp_myc_realtime_test":
            raise RuntimeError("Destino de integración no autorizado")

        stop_event = asyncio.Event()
        received = asyncio.Event()
        resource_handler = AsyncMock()

        async def connection_factory():
            return await psycopg.AsyncConnection.connect(
                dsn,
                connect_timeout=5,
            )

        async def handle_resource(change):
            await resource_handler(change)
            received.set()

        async def handle_invalidation(_event):
            pass

        task = asyncio.create_task(
            listen_invalidations(
                connection_factory,
                handle_invalidation,
                stop_event=stop_event,
                resource_handler=handle_resource,
            )
        )

        try:
            # Esperar a que LISTEN esté activo antes de emitir el cambio.
            async with await psycopg.AsyncConnection.connect(dsn) as probe:
                await probe.set_autocommit(True)

                for _ in range(50):
                    count = await probe.execute(
                        """
                        SELECT count(*)
                        FROM pg_stat_activity
                        WHERE datname = current_database()
                          AND state = 'idle'
                          AND query LIKE 'LISTEN myc_erp_resource_changes_v1%'
                        """
                    )
                    if (await count.fetchone())[0] > 0:
                        break
                    await asyncio.sleep(0.1)
                else:
                    raise AssertionError("El listener no inició")

            async with await psycopg.AsyncConnection.connect(dsn) as writer:
                await writer.execute(
                    "UPDATE users SET id = id WHERE id = -1"
                )
                await writer.commit()

            await asyncio.wait_for(received.wait(), timeout=5)

            resource_handler.assert_awaited_once()
            change = resource_handler.await_args.args[0]
            assert change.resource == "users"

        finally:
            stop_event.set()
            await asyncio.wait_for(task, timeout=10)

    asyncio.run(scenario())
