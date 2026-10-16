"""Integración real de LISTEN/NOTIFY con PostgreSQL.

Requiere MYC_REALTIME_TEST_DATABASE_URL.
No utiliza la base operativa predeterminada.
"""

import asyncio
import os
from uuid import uuid4

import psycopg
import pytest

from app.realtime.invalidation import (
    INVALIDATION_CHANNEL,
    build_invalidation_payload,
    parse_invalidation_payload,
)


TEST_DSN = os.getenv("MYC_REALTIME_TEST_DATABASE_URL")


@pytest.mark.skipif(
    not TEST_DSN,
    reason="MYC_REALTIME_TEST_DATABASE_URL no configurada",
)
def test_postgres_notify_commit_and_rollback():
    async def scenario():
        dsn = TEST_DSN.replace(
            "postgresql+psycopg://",
            "postgresql://",
            1,
        )

        async with await psycopg.AsyncConnection.connect(
            dsn,
            connect_timeout=5,
        ) as listener:
            await listener.set_autocommit(True)

            await listener.execute(
                f"LISTEN {INVALIDATION_CHANNEL}"
            )

            async with await psycopg.AsyncConnection.connect(
                dsn,
                connect_timeout=5,
            ) as writer:

                rollback_payload = build_invalidation_payload(
                    ["users"],
                    user_ids=[1],
                )

                await writer.execute(
                    "SELECT pg_notify(%s, %s)",
                    (INVALIDATION_CHANNEL, rollback_payload),
                )
                await writer.rollback()

                commit_payload = build_invalidation_payload(
                    ["users"],
                    user_ids=[1],
                )

                await writer.execute(
                    "SELECT pg_notify(%s, %s)",
                    (INVALIDATION_CHANNEL, commit_payload),
                )

                await writer.commit()

            received = []

            async for notification in listener.notifies(
                timeout=3,
            ):
                received.append(
                    parse_invalidation_payload(
                        notification.payload
                    )
                )

            assert len(received) == 1
            assert received[0].resources == ("users",)

    asyncio.run(scenario())
