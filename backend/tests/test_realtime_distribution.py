import asyncio
from unittest.mock import AsyncMock

from app.realtime.distribution import distribute_invalidation
from app.realtime.invalidation import ResourceInvalidation


def test_distribution_targets_only_authorized_user_rooms():
    hub = AsyncMock()
    hub.publish_to_user.return_value = 1

    event = ResourceInvalidation(
        event_id="123e4567-e89b-42d3-a456-426614174000",
        resources=("users",),
        user_ids=(3, 1, 3),
    )

    delivered = asyncio.run(
        distribute_invalidation(hub, event)
    )

    assert delivered == 2

    assert hub.publish_to_user.await_count == 2

    recipients = [
        call.args[0]
        for call in hub.publish_to_user.await_args_list
    ]

    assert recipients == [1, 3]

    for call in hub.publish_to_user.await_args_list:
        envelope = call.args[1]

        assert envelope["event"] == "resource.changed"
        assert envelope["data"] == {"resources": ["users"]}
        assert envelope["event_id"] == event.event_id
