import asyncio
from unittest.mock import AsyncMock, patch

from app.realtime.resource_changes import (
    ResourceChange,
    parse_resource_change,
)
from app.realtime.resource_distribution import (
    distribute_resource_change,
)


def test_valid_resource_change():
    event = parse_resource_change(
        '{"version":1,"resource":"users"}'
    )
    assert event.resource == "users"


def test_unknown_resource_rejected():
    try:
        parse_resource_change(
            '{"version":1,"resource":"secrets"}'
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown resource was accepted")


def test_no_recipients_no_publication():
    async def scenario():
        hub = AsyncMock()
        hub.active_connections.return_value = [
            type("Connection", (), {"user_id": 10})()
        ]

        with patch(
            "app.realtime.resource_distribution.eligible_user_ids",
            return_value=[],
        ):
            delivered = await distribute_resource_change(
                hub,
                ResourceChange("users"),
            )

        assert delivered == 0
        hub.publish_to_user.assert_not_awaited()

    asyncio.run(scenario())


def test_only_eligible_users_receive_change():
    async def scenario():
        hub = AsyncMock()
        hub.active_connections.return_value = [
            type("Connection", (), {"user_id": 10})(),
            type("Connection", (), {"user_id": 20})(),
        ]
        hub.publish_to_user.return_value = 1

        with patch(
            "app.realtime.resource_distribution.eligible_user_ids",
            return_value=[10, 20],
        ):
            delivered = await distribute_resource_change(
                hub,
                ResourceChange("users"),
            )

        assert delivered == 2
        assert hub.publish_to_user.await_count == 2

        calls = hub.publish_to_user.await_args_list

        assert [call.args[0] for call in calls] == [10, 20]

        for call in calls:
            envelope = call.args[1]
            assert envelope["event"] == "resource.changed"
            assert envelope["data"] == {"resources": ["users"]}

    asyncio.run(scenario())
