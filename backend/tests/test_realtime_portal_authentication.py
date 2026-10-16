from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.realtime.authentication import (
    RealtimeAuthenticationError,
    authenticate_websocket,
)


def _websocket():
    return SimpleNamespace(
        headers={
            "sec-websocket-protocol": "myc.realtime.v1, auth.test-token"
        }
    )


def _payload(context="client_portal", token_type="access"):
    return {
        "sub": "25",
        "auth_context": context,
        "token_type": token_type,
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
    }


def test_portal_identity_preserves_client_scope_and_permissions():
    context = SimpleNamespace(
        user=SimpleNamespace(id=25),
        membership=SimpleNamespace(id=80, client_id=12),
        permissions=frozenset(
            {"portal.read", "communications.view"}
        ),
    )

    with (
        patch(
            "app.realtime.authentication.decode_token",
            return_value=_payload(),
        ),
        patch(
            "app.realtime.authentication.resolve_portal_token",
            return_value=context,
        ) as resolver,
    ):
        identity = authenticate_websocket(Mock(), _websocket())

    resolver.assert_called_once()
    assert identity.user_id == 25
    assert identity.actor_type == "client"
    assert identity.client_id == 12
    assert identity.membership_id == 80
    assert identity.permissions == frozenset(
        {"portal.read", "communications.view"}
    )


def test_portal_membership_rejection_denies_websocket():
    with (
        patch(
            "app.realtime.authentication.decode_token",
            return_value=_payload(),
        ),
        patch(
            "app.realtime.authentication.resolve_portal_token",
            side_effect=HTTPException(
                status_code=403,
                detail="Membresia suspendida",
            ),
        ),
    ):
        with pytest.raises(RealtimeAuthenticationError):
            authenticate_websocket(Mock(), _websocket())


def test_portal_refresh_token_cannot_authenticate_websocket():
    with (
        patch(
            "app.realtime.authentication.decode_token",
            return_value=_payload(token_type="refresh"),
        ),
        patch(
            "app.realtime.authentication.resolve_portal_token",
            side_effect=HTTPException(
                status_code=401,
                detail="Token del portal invalido",
            ),
        ),
    ):
        with pytest.raises(RealtimeAuthenticationError):
            authenticate_websocket(Mock(), _websocket())


def test_expired_portal_token_is_rejected():
    payload = _payload()
    payload["exp"] = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).timestamp()

    with (
        patch(
            "app.realtime.authentication.decode_token",
            return_value=payload,
        ),
        patch(
            "app.realtime.authentication.resolve_portal_token",
            return_value=SimpleNamespace(
                user=SimpleNamespace(id=25),
                membership=SimpleNamespace(id=80, client_id=12),
                permissions=frozenset({"communications.view"}),
            ),
        ),
    ):
        with pytest.raises(RealtimeAuthenticationError):
            authenticate_websocket(Mock(), _websocket())
