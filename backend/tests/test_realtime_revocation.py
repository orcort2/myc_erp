import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.realtime.revocation import revoke_invalid_connections


def make_connection(user_id):
    return SimpleNamespace(
        user_id=user_id,
        websocket=AsyncMock(),
        send_lock=asyncio.Lock(),
    )


def test_revoked_connection_is_closed_without_reconnect():
    async def scenario():
        connection = make_connection(10)
        hub = AsyncMock()
        hub.active_connections.return_value = (connection,)

        with patch(
            "app.realtime.revocation.connection_is_authorized",
            return_value=False,
        ):
            result = await revoke_invalid_connections(hub)

        assert result == 1
        hub.disconnect.assert_awaited_once_with(connection)
        connection.websocket.close.assert_awaited_once_with(
            code=4401,
            reason="session_revoked",
        )

    asyncio.run(scenario())


def test_valid_connection_reconnects_to_refresh_authority():
    async def scenario():
        connection = make_connection(20)
        hub = AsyncMock()
        hub.active_connections.return_value = (connection,)

        with patch(
            "app.realtime.revocation.connection_is_authorized",
            return_value=True,
        ):
            result = await revoke_invalid_connections(hub)

        assert result == 1
        hub.disconnect.assert_awaited_once_with(connection)
        connection.websocket.close.assert_awaited_once_with(
            code=1012,
            reason="authority_refresh",
        )

    asyncio.run(scenario())


def test_database_failure_does_not_mass_revoke():
    async def scenario():
        connection = make_connection(30)
        hub = AsyncMock()
        hub.active_connections.return_value = (connection,)

        with patch(
            "app.realtime.revocation.connection_is_authorized",
            side_effect=RuntimeError("database unavailable"),
        ):
            result = await revoke_invalid_connections(hub)

        assert result == 0
        hub.disconnect.assert_not_awaited()
        connection.websocket.close.assert_not_awaited()

    asyncio.run(scenario())


def test_mixed_connections_receive_correct_close_codes():
    async def scenario():
        revoked = make_connection(10)
        valid = make_connection(20)
        hub = AsyncMock()
        hub.active_connections.return_value = (revoked, valid)

        def authorize(websocket, identity=None):
            return websocket is valid.websocket

        with patch(
            "app.realtime.revocation.connection_is_authorized",
            side_effect=authorize,
        ):
            result = await revoke_invalid_connections(hub)

        assert result == 2
        assert hub.disconnect.await_count == 2

        revoked.websocket.close.assert_awaited_once_with(
            code=4401,
            reason="session_revoked",
        )
        valid.websocket.close.assert_awaited_once_with(
            code=1012,
            reason="authority_refresh",
        )

    asyncio.run(scenario())
