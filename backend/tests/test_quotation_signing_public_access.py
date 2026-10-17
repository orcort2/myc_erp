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
