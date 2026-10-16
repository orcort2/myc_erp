"""Prueba de triggers instalados mediante Alembic."""

import asyncio
import os

import psycopg
import pytest

from app.realtime.resource_changes import (
    RESOURCE_CHANGE_CHANNEL,
    parse_resource_change,
)

TEST_DSN = os.getenv("MYC_REALTIME_TEST_DATABASE_URL")


@pytest.mark.skipif(
    not TEST_DSN,
    reason="Base PostgreSQL de integración no configurada",
)
def test_installed_user_trigger_notifies():
    async def scenario():
        dsn = TEST_DSN.replace(
            "postgresql+psycopg://",
            "postgresql://",
            1,
        )

        if dsn.split("?", 1)[0].rsplit("/", 1)[-1] != "erp_myc_realtime_test":
            raise RuntimeError("Destino de integración no autorizado")

        async with await psycopg.AsyncConnection.connect(
            dsn
        ) as listener:
            await listener.set_autocommit(True)

            await listener.execute(
                f"LISTEN {RESOURCE_CHANGE_CHANNEL}"
            )

            async with await psycopg.AsyncConnection.connect(
                dsn
            ) as writer:
                await writer.execute(
                    "UPDATE users SET id = id WHERE id = -1"
                )
                await writer.commit()

            events = []

            async for notification in listener.notifies(
                timeout=3
            ):
                events.append(
                    parse_resource_change(notification.payload)
                )

            assert [event.resource for event in events] == ["users"]

    asyncio.run(scenario())
