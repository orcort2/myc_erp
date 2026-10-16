import asyncio
from unittest.mock import AsyncMock

from app.realtime.postgres_bus import listen_invalidations


class FakeNotifications:
    def __aiter__(self):
        return self

    async def __anext__(self):
        await asyncio.sleep(3600)
        raise StopAsyncIteration


class FakeCursor:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def execute(self, _statement):
        return None


class FakeConnection:
    def __init__(self):
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        self.closed = True
        return False

    async def set_autocommit(self, _value):
        return None

    def cursor(self):
        return FakeCursor()

    def notifies(self):
        return FakeNotifications()


def test_listener_stops_and_closes_connection():
    async def scenario():
        connection = FakeConnection()
        stop_event = asyncio.Event()
        handler = AsyncMock()

        async def factory():
            return connection

        task = asyncio.create_task(
            listen_invalidations(
                factory,
                handler,
                stop_event=stop_event,
            )
        )

        await asyncio.sleep(0.05)
        stop_event.set()

        await asyncio.wait_for(task, timeout=3)

        assert connection.closed
        handler.assert_not_awaited()

    asyncio.run(scenario())
