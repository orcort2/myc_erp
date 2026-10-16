import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.realtime.events import publish_communication_to_users


def test_only_currently_authorized_recipients_receive_messages():
    async def scenario():
        with (
            patch(
                "app.realtime.events.eligible_communication_recipients",
                return_value={10, 30},
            ) as eligible,
            patch(
                "app.realtime.events.publish_to_users",
                new_callable=AsyncMock,
            ) as publish,
        ):
            await publish_communication_to_users(
                {10, 20, 30},
                "message.created",
                {"conversation_id": 7, "body": "Prueba"},
                conversation_id=7,
            )

            eligible.assert_called_once_with(7, {10, 20, 30})
            publish.assert_awaited_once_with(
                {10, 30},
                "message.created",
                {"conversation_id": 7, "body": "Prueba"},
            )

    asyncio.run(scenario())


def test_revoked_participant_receives_nothing():
    async def scenario():
        with (
            patch(
                "app.realtime.events.eligible_communication_recipients",
                return_value=set(),
            ),
            patch(
                "app.realtime.events.publish_to_users",
                new_callable=AsyncMock,
            ) as publish,
        ):
            await publish_communication_to_users(
                {20},
                "message.created",
                {"conversation_id": 7},
                conversation_id=7,
            )

            publish.assert_not_awaited()

    asyncio.run(scenario())


def test_database_error_does_not_publish():
    async def scenario():
        with (
            patch(
                "app.realtime.events.eligible_communication_recipients",
                side_effect=RuntimeError("Database unavailable"),
            ),
            patch(
                "app.realtime.events.publish_to_users",
                new_callable=AsyncMock,
            ) as publish,
        ):
            with pytest.raises(RuntimeError, match="Database unavailable"):
                await publish_communication_to_users(
                    {20},
                    "message.created",
                    {"conversation_id": 7},
                    conversation_id=7,
                )

            publish.assert_not_awaited()

    asyncio.run(scenario())


def test_publication_enforces_conversation_id():
    async def scenario():
        with (
            patch(
                "app.realtime.events.eligible_communication_recipients",
                return_value={10},
            ),
            patch(
                "app.realtime.events.publish_to_users",
                new_callable=AsyncMock,
            ) as publish,
        ):
            await publish_communication_to_users(
                {10},
                "message.created",
                {"body": "Mensaje sin identificador"},
                conversation_id=7,
            )

            publish.assert_awaited_once_with(
                {10},
                "message.created",
                {
                    "body": "Mensaje sin identificador",
                    "conversation_id": 7,
                },
            )

    asyncio.run(scenario())


def test_publication_overrides_foreign_conversation_id():
    async def scenario():
        with (
            patch(
                "app.realtime.events.eligible_communication_recipients",
                return_value={10},
            ),
            patch(
                "app.realtime.events.publish_to_users",
                new_callable=AsyncMock,
            ) as publish,
        ):
            await publish_communication_to_users(
                {10},
                "message.created",
                {
                    "conversation_id": 999,
                    "body": "Mensaje",
                },
                conversation_id=7,
            )

            publish.assert_awaited_once_with(
                {10},
                "message.created",
                {
                    "conversation_id": 7,
                    "body": "Mensaje",
                },
            )

    asyncio.run(scenario())
