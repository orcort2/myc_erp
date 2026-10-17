from datetime import datetime, timedelta, timezone

import pytest

from app.services.quotation_signing_otp import (
    code_digest,
    expiry,
    generate_code,
    generate_nonce,
    is_usable,
    verify_code,
)


def test_code_is_six_digits():
    assert all(len(generate_code()) == 6 and generate_code().isascii() for _ in range(100))


def test_code_hash_is_keyed_and_nonce_scoped():
    nonce = generate_nonce()
    digest = code_digest("000123", nonce=nonce, secret_key="test-secret")
    assert "000123" not in digest
    assert verify_code("000123", expected_digest=digest, nonce=nonce, secret_key="test-secret")
    assert not verify_code("000124", expected_digest=digest, nonce=nonce, secret_key="test-secret")
    assert not verify_code("000123", expected_digest=digest, nonce=generate_nonce(), secret_key="test-secret")
    assert not verify_code("000123", expected_digest=digest, nonce=nonce, secret_key="wrong-secret")
    assert not verify_code("123", expected_digest=digest, nonce=nonce, secret_key="test-secret")


def test_expiration_and_attempts():
    now = datetime.now(timezone.utc)
    end = expiry(10, now=now)
    base = dict(expires_at=end, attempts=0, max_attempts=5, now=now)
    assert is_usable(**base)
    assert not is_usable(**(base | {"now": end}))
    assert not is_usable(**(base | {"attempts": 5}))
    assert not is_usable(**(base | {"verified_at": now}))
    assert not is_usable(**(base | {"consumed_at": now}))
    assert not is_usable(**(base | {"revoked_at": now}))


def test_invalid_expiry():
    with pytest.raises(ValueError):
        expiry(0)
