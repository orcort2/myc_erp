"""Validación de identidad original en conexiones realtime."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.realtime.authentication import RealtimeIdentity
from app.realtime.revocation import connection_is_authorized


def identity(
    user_id=10,
    actor_type="client",
    client_id=5,
    membership_id=8,
):
    return RealtimeIdentity(
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        actor_type=actor_type,
        client_id=client_id,
        membership_id=membership_id,
    )


@pytest.mark.parametrize(
    "current,expected",
    [
        (identity(), True),
        (identity(user_id=11), False),
        (identity(actor_type="internal"), False),
        (identity(client_id=6), False),
        (identity(membership_id=9), False),
    ],
    ids=[
        "identidad_igual",
        "usuario_diferente",
        "actor_diferente",
        "cliente_diferente",
        "membresia_diferente",
    ],
)
def test_revalidation_compares_original_identity(current, expected):
    original = identity()
    websocket = MagicMock()

    with (
        patch("app.realtime.revocation.SessionLocal") as session,
        patch(
            "app.realtime.revocation.authenticate_websocket",
            return_value=current,
        ) as authenticate,
    ):
        result = connection_is_authorized(websocket, original)

    assert result is expected
    authenticate.assert_called_once()
    session.assert_called_once()


def test_database_error_propagates_for_safe_retry():
    original = identity()

    with (
        patch("app.realtime.revocation.SessionLocal"),
        patch(
            "app.realtime.revocation.authenticate_websocket",
            side_effect=RuntimeError("database unavailable"),
        ),
    ):
        with pytest.raises(RuntimeError, match="database unavailable"):
            connection_is_authorized(MagicMock(), original)


def test_original_identity_is_not_modified():
    original = identity()
    current = identity(client_id=99)

    with (
        patch("app.realtime.revocation.SessionLocal"),
        patch(
            "app.realtime.revocation.authenticate_websocket",
            return_value=current,
        ),
    ):
        assert connection_is_authorized(MagicMock(), original) is False

    assert original.client_id == 5
    assert original.membership_id == 8



def test_missing_original_identity_is_rejected():
    with (
        patch("app.realtime.revocation.SessionLocal") as session,
        patch(
            "app.realtime.revocation.authenticate_websocket"
        ) as authenticate,
    ):
        result = connection_is_authorized(MagicMock(), None)

    assert result is False
    session.assert_not_called()
    authenticate.assert_not_called()


def test_missing_identity_cannot_be_authorized_by_valid_token():
    current = identity()

    with (
        patch("app.realtime.revocation.SessionLocal"),
        patch(
            "app.realtime.revocation.authenticate_websocket",
            return_value=current,
        ) as authenticate,
    ):
        result = connection_is_authorized(MagicMock())

    assert result is False
    authenticate.assert_not_called()
