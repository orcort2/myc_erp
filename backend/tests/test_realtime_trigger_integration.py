"""Prueba PostgreSQL real del trigger de invalidación."""

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
    reason="Base PostgreSQL de pruebas no configurada",
)
def test_trigger_emits_only_committed_changes():
    async def scenario():
        dsn = TEST_DSN.replace(
            "postgresql+psycopg://",
            "postgresql://",
            1,
        )

        async with await psycopg.AsyncConnection.connect(dsn) as listener:
            await listener.set_autocommit(True)

            await listener.execute(
                f"LISTEN {RESOURCE_CHANGE_CHANNEL}"
            )

            async with await psycopg.AsyncConnection.connect(dsn) as writer:
                try:
                    await writer.execute("""
                        CREATE TABLE myc_realtime_trigger_test (
                            id integer PRIMARY KEY,
                            value text
                        )
                    """)

                    await writer.execute("""
                        CREATE FUNCTION myc_realtime_test_notify()
                        RETURNS trigger
                        LANGUAGE plpgsql
                        AS $$
                        BEGIN
                            PERFORM pg_notify(
                                'myc_erp_resource_changes_v1',
                                json_build_object(
                                    'version', 1,
                                    'resource', TG_ARGV[0]
                                )::text
                            );
                            RETURN NULL;
                        END;
                        $$;
                    """)

                    await writer.execute("""
                        CREATE TRIGGER myc_realtime_test_trigger
                        AFTER INSERT OR UPDATE OR DELETE
                        ON myc_realtime_trigger_test
                        FOR EACH STATEMENT
                        EXECUTE FUNCTION
                            myc_realtime_test_notify('users')
                    """)

                    await writer.commit()

                    await writer.execute("""
                        INSERT INTO myc_realtime_trigger_test
                        VALUES (1, 'initial')
                    """)
                    await writer.commit()

                    await writer.execute("""
                        UPDATE myc_realtime_trigger_test
                        SET value = 'changed'
                        WHERE id = 1
                    """)
                    await writer.commit()

                    await writer.execute("""
                        DELETE FROM myc_realtime_trigger_test
                        WHERE id = 1
                    """)
                    await writer.rollback()

                    events = []

                    async for notification in listener.notifies(
                        timeout=3
                    ):
                        events.append(
                            parse_resource_change(
                                notification.payload
                            )
                        )

                    assert [event.resource for event in events] == [
                        "users",
                        "users",
                    ]

                finally:
                    await writer.rollback()

                    await writer.execute("""
                        DROP TABLE IF EXISTS
                        myc_realtime_trigger_test
                    """)

                    await writer.execute("""
                        DROP FUNCTION IF EXISTS
                        myc_realtime_test_notify()
                    """)

                    await writer.commit()

    asyncio.run(scenario())
