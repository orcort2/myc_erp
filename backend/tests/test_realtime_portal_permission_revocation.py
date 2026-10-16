"""Regresión: revocación del permiso de acceso al Portal del Cliente."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.realtime.authentication import (
    RealtimeAuthenticationError,
    authenticate_websocket,
)
from app.core.portal.security import resolve_portal_token


def token_payload():
    return {
        "sub": "25",
        "membership_id": 80,
        "client_id": 12,
        "auth_context": "client_portal",
        "token_type": "access",
        "exp": (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).timestamp(),
    }


def active_user():
    from app.core.portal.security import (
        PortalAccountType,
        UserAccountStatus,
    )

    return SimpleNamespace(
        id=25,
        account_type=PortalAccountType.CLIENT_PORTAL.value,
        status=UserAccountStatus.ACTIVE.value,
        is_active=True,
    )


def active_membership():
    return SimpleNamespace(
        id=80,
        client_id=12,
        client=SimpleNamespace(id=12, is_active=True),
    )


def test_portal_token_rejected_after_portal_read_revocation():
    db = MagicMock()
    db.get.return_value = active_user()

    with (
        patch(
            "app.core.portal.security.decode_token",
            return_value=token_payload(),
        ),
        patch(
            "app.core.portal.security.resolve_active_membership",
            return_value=active_membership(),
        ),
        patch(
            "app.core.portal.security.resolve_permissions",
            return_value=frozenset({"communications.view"}),
        ),
    ):
        with pytest.raises(HTTPException) as error:
            resolve_portal_token(db, "previously-valid-token")

    assert error.value.status_code == 403
    assert "portal" in str(error.value.detail).lower()


def test_portal_token_remains_valid_with_portal_read():
    db = MagicMock()
    db.get.return_value = active_user()

    with (
        patch(
            "app.core.portal.security.decode_token",
            return_value=token_payload(),
        ),
        patch(
            "app.core.portal.security.resolve_active_membership",
            return_value=active_membership(),
        ),
        patch(
            "app.core.portal.security.resolve_permissions",
            return_value=frozenset(
                {"portal.read", "communications.view"}
            ),
        ),
    ):
        context = resolve_portal_token(
            db, "previously-valid-token"
        )

    assert context.user.id == 25
    assert context.membership.id == 80
    assert "portal.read" in context.permissions


def test_realtime_rejects_revoked_portal_permission():
    websocket = SimpleNamespace(
        headers={
            "sec-websocket-protocol":
                "myc.realtime.v1, auth.previously-valid-token"
        }
    )

    db = MagicMock()
    db.get.return_value = active_user()

    with (
        patch(
            "app.realtime.authentication.decode_token",
            return_value=token_payload(),
        ),
        patch(
            "app.core.portal.security.decode_token",
            return_value=token_payload(),
        ),
        patch(
            "app.core.portal.security.resolve_active_membership",
            return_value=active_membership(),
        ),
        patch(
            "app.core.portal.security.resolve_permissions",
            return_value=frozenset({"communications.view"}),
        ),
    ):
        with pytest.raises(RealtimeAuthenticationError):
            authenticate_websocket(db, websocket)
