"""Pure OTP primitives; no SMTP credentials or production dependencies."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone


def generate_code() -> str:
    """Six digits, preserving leading zeroes; cryptographic RNG."""
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_nonce() -> str:
    return secrets.token_hex(24)


def code_digest(code: str, *, nonce: str, secret_key: str) -> str:
    """Keyed digest prevents offline enumeration of six-digit codes."""
    if not secret_key or not nonce:
        raise ValueError("A signing secret and nonce are required")
    return hmac.new(
        secret_key.encode("utf-8"),
        f"quotation-signing-otp:v1:{nonce}:{code}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_code(code: str, *, expected_digest: str, nonce: str, secret_key: str) -> bool:
    if len(code) != 6 or not code.isascii() or not code.isdecimal():
        return False
    return hmac.compare_digest(
        code_digest(code, nonce=nonce, secret_key=secret_key),
        expected_digest,
    )


def expiry(minutes: int, *, now: datetime | None = None) -> datetime:
    if not 1 <= minutes <= 30:
        raise ValueError("Invalid OTP lifetime")
    return (now or datetime.now(timezone.utc)) + timedelta(minutes=minutes)


def is_usable(*, expires_at: datetime, attempts: int, max_attempts: int,
              verified_at: datetime | None = None, consumed_at: datetime | None = None,
              revoked_at: datetime | None = None, now: datetime | None = None) -> bool:
    if expires_at.tzinfo is None:
        raise ValueError("OTP expiry must be timezone aware")
    current = now or datetime.now(timezone.utc)
    return (
        current < expires_at
        and attempts < max_attempts
        and verified_at is None
        and consumed_at is None
        and revoked_at is None
    )
