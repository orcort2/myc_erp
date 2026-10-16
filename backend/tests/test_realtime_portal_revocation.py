"""Pruebas de aislamiento de sesiones realtime del portal."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.realtime.authentication import RealtimeIdentity
from app.realtime.hub import InMemoryRealtimeHub
from app.realtime.portal_revocation import refresh_portal_connections
from app.realtime.resource_changes import parse_resource_change


def identity(user_id, actor_type, client_id=None, membership_id=None):
    return RealtimeIdentity(
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        actor_type=actor_type,
        client_id=client_id,
        membership_id=membership_id,
    )


def test_portal_authority_event_is_recognized():
    change = parse_resource_change(
        '{"version":1,"resource":"portal_authority"}'
    )
    assert change.resource == "portal_authority"


def test_internal_connection_is_not_closed():
    async def scenario():
        hub = InMemoryRealtimeHub()
        socket = AsyncMock()

        await hub.connect(
            socket,
            10,
            identity=identity(10, "internal"),
        )

        with patch(
            "app.realtime.portal_revocation.connection_is_authorized",
            return_value=False,
        ) as authorize:
            closed = await refresh_portal_connections(hub)

        assert closed == 0
        assert await hub.connection_count() == 1
        socket.close.assert_not_awaited()
        authorize.assert_not_called()

    asyncio.run(scenario())


def test_revoked_client_is_closed_with_4401():
    async def scenario():
        hub = InMemoryRealtimeHub()
        socket = AsyncMock()

        await hub.connect(
            socket,
            20,
            identity=identity(20, "client", 5, 8),
        )

        with patch(
            "app.realtime.portal_revocation.connection_is_authorized",
            return_value=False,
        ):
            closed = await refresh_portal_connections(hub)

        assert closed == 1
        assert await hub.connection_count() == 0
        socket.close.assert_awaited_once_with(
            code=4401,
            reason="session_revoked",
        )

    asyncio.run(scenario())


def test_authorized_client_reconnects_with_1012():
    async def scenario():
        hub = InMemoryRealtimeHub()
        socket = AsyncMock()

        await hub.connect(
            socket,
            30,
            identity=identity(30, "client", 6, 9),
        )

        with patch(
            "app.realtime.portal_revocation.connection_is_authorized",
            return_value=True,
        ):
            closed = await refresh_portal_connections(hub)

        assert closed == 1
        assert await hub.connection_count() == 0
        socket.close.assert_awaited_once_with(
            code=1012,
            reason="authority_refresh",
        )

    asyncio.run(scenario())


def test_database_error_does_not_close_connections():
    async def scenario():
        hub = InMemoryRealtimeHub()
        socket = AsyncMock()

        await hub.connect(
            socket,
            40,
            identity=identity(40, "client", 7, 10),
        )

        with patch(
            "app.realtime.portal_revocation.connection_is_authorized",
            side_effect=RuntimeError("database unavailable"),
        ):
            closed = await refresh_portal_connections(hub)

        assert closed == 0
        assert await hub.connection_count() == 1
        socket.close.assert_not_awaited()

    asyncio.run(scenario())


def test_mixed_connections_only_refresh_clients():
    async def scenario():
        hub = InMemoryRealtimeHub()

        internal_socket = AsyncMock()
        client_socket = AsyncMock()

        await hub.connect(
            internal_socket,
            50,
            identity=identity(50, "internal"),
        )

        await hub.connect(
            client_socket,
            60,
            identity=identity(60, "client", 8, 11),
        )

        with patch(
            "app.realtime.portal_revocation.connection_is_authorized",
            return_value=True,
        ):
            closed = await refresh_portal_connections(hub)

        assert closed == 1
        assert await hub.connection_count() == 1

        internal_socket.close.assert_not_awaited()
        client_socket.close.assert_awaited_once_with(
            code=1012,
            reason="authority_refresh",
        )

    asyncio.run(scenario())
