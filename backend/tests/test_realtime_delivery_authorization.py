from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.realtime.authentication import RealtimeIdentity
from app.realtime.delivery_authorization import can_deliver_conversation


def identity(
    *,
    user_id=25,
    actor_type="client",
    client_id=7,
    membership_id=80,
):
    return RealtimeIdentity(
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        actor_type=actor_type,
        client_id=client_id,
        membership_id=membership_id,
        permissions=frozenset({"communications.view"}),
    )


@pytest.mark.parametrize(
    "connected,current,access,expected",
    [
        (identity(), identity(), True, True),
        (
            identity(),
            identity(client_id=999),
            True,
            False,
        ),
        (
            identity(),
            identity(membership_id=999),
            True,
            False,
        ),
        (
            identity(actor_type="internal", client_id=None, membership_id=None),
            identity(actor_type="internal", client_id=None, membership_id=None),
            True,
            True,
        ),
        (identity(), identity(), False, False),
    ],
)
def test_conversation_delivery_authorization(
    connected,
    current,
    access,
    expected,
):
    connection = SimpleNamespace(
        user_id=connected.user_id,
        identity=connected,
        websocket=MagicMock(),
    )

    session = MagicMock()
    session_context = MagicMock()
    session_context.__enter__.return_value = session

    with (
        patch(
            "app.realtime.delivery_authorization.SessionLocal",
            return_value=session_context,
        ),
        patch(
            "app.realtime.delivery_authorization.authenticate_websocket",
            return_value=current,
        ),
        patch(
            "app.routers.realtime._can_access_conversation",
            return_value=access,
        ) as authorize,
    ):
        result = can_deliver_conversation(connection, 7)

    assert result is expected

    if (
        connected.user_id == current.user_id
        and connected.actor_type == current.actor_type
        and connected.client_id == current.client_id
        and connected.membership_id == current.membership_id
    ):
        authorize.assert_called_once_with(
            session,
            conversation_id=7,
            identity=current,
        )
    else:
        authorize.assert_not_called()
