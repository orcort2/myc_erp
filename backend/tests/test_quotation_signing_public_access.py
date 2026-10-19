"""Access classification for the capability-only quotation signing API."""
import pytest

from app.security.api_access import AccessType, classify_operation


@pytest.mark.parametrize("path", [
    "/api/public/quotation-signing/document",
    "/api/public/quotation-signing/pdf",
    "/api/public/quotation-signing/otp/request",
    "/api/public/quotation-signing/otp/verify",
    "/api/public/quotation-signing/accept",
])
def test_signing_endpoints_are_explicitly_signed_public(path):
    policy = classify_operation("POST", path, ["quotation-signing-public"])
    assert policy is not None
    assert policy.access_type == AccessType.PUBLIC_SIGNED


def test_unlisted_signing_operation_is_not_public():
    policy = classify_operation(
        "GET", "/api/public/quotation-signing/accept",
        ["quotation-signing-public"],
    )
    assert policy is None or policy.access_type != AccessType.PUBLIC_SIGNED

def test_accept_endpoint_dispatches_only_after_successful_acceptance():
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    from app.routers.quotation_signing_public import AcceptanceRequest, accept_quotation

    db = MagicMock()
    acceptance = SimpleNamespace(quotation_id=18, snapshot_id=12, id=40)
    request = AcceptanceRequest(
        token="a" * 20, challenge_id=30, signer_name="Persona Autorizada", consent=True
    )
    with (
        patch(
            "app.routers.quotation_signing_public.accept_signed_quotation",
            return_value=acceptance,
        ) as accept,
        patch(
            "app.routers.quotation_signing_public.commit_and_dispatch_notifications"
        ) as dispatch,
    ):
        result = accept_quotation(request, db=db)
    accept.assert_called_once()
    dispatch.assert_called_once_with(db)
    db.commit.assert_not_called()
    assert result["acceptance_id"] == 40
    assert result["accepted"] is True


def test_accept_endpoint_rolls_back_and_clears_queued_notifications_on_error():
    from unittest.mock import MagicMock, patch

    from app.routers.quotation_signing_public import AcceptanceRequest, accept_quotation

    db = MagicMock()
    db.info = {"push_notification_ids": [42]}
    request = AcceptanceRequest(
        token="a" * 20, challenge_id=30, signer_name="Persona Autorizada", consent=True
    )
    with (
        patch(
            "app.routers.quotation_signing_public.accept_signed_quotation",
            side_effect=RuntimeError("acceptance_failed"),
        ),
        patch(
            "app.routers.quotation_signing_public.commit_and_dispatch_notifications"
        ) as dispatch,
    ):
        with pytest.raises(RuntimeError, match="acceptance_failed"):
            accept_quotation(request, db=db)
    dispatch.assert_not_called()
    db.rollback.assert_called_once()
    assert "push_notification_ids" not in db.info
