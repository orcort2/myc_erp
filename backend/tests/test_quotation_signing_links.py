import pytest

from app.services.quotation_signing_links import (
    SigningLinkError,
    issue_signing_link,
    verify_signing_link,
)


SECRET = "myc-test-secret-for-signing-links-2026-123456789"
HASH = "a" * 64


def issue(**overrides):
    values = dict(
        quotation_id=18,
        snapshot_id=27,
        pdf_sha256=HASH,
        secret_key=SECRET,
        lifetime_seconds=3600,
        now=100000,
    )
    values.update(overrides)
    return issue_signing_link(**values)


def test_valid_link():
    claims = verify_signing_link(
        issue(), secret_key=SECRET, now=100001
    )
    assert claims.quotation_id == 18
    assert claims.snapshot_id == 27
    assert claims.pdf_sha256 == HASH
    assert len(claims.token_id) == 32


def test_expired_link():
    with pytest.raises(SigningLinkError):
        verify_signing_link(
            issue(), secret_key=SECRET, now=103600
        )


def test_tampered_link():
    token = issue()
    payload, signature = token.split(".")
    changed = ("A" if payload[0] != "A" else "B") + payload[1:]

    with pytest.raises(SigningLinkError):
        verify_signing_link(
            changed + "." + signature,
            secret_key=SECRET,
            now=100001,
        )


def test_wrong_secret():
    with pytest.raises(SigningLinkError):
        verify_signing_link(
            issue(),
            secret_key="another-test-secret-12345678901234567890",
            now=100001,
        )


def test_links_have_unique_identifiers():
    first = verify_signing_link(
        issue(), secret_key=SECRET, now=100001
    )
    second = verify_signing_link(
        issue(), secret_key=SECRET, now=100001
    )
    assert first.token_id != second.token_id


def test_invalid_pdf_hash():
    with pytest.raises(ValueError):
        issue(pdf_sha256="invalid")


def test_excessive_lifetime():
    with pytest.raises(ValueError):
        issue(lifetime_seconds=16 * 24 * 60 * 60)


def test_empty_token():
    with pytest.raises(SigningLinkError):
        verify_signing_link(
            "", secret_key=SECRET, now=100001
        )


def test_token_does_not_expose_secret():
    token = issue()
    assert SECRET not in token
