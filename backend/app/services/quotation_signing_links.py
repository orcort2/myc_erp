"""Cryptographic capabilities for version-bound quotation signing links.

No database access, HTTP endpoints or SMTP operations are performed here.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass


DOMAIN = b"myc:quotation-signing-link:v1:"
MAX_TOKEN_LENGTH = 2048
MAX_LIFETIME_SECONDS = 15 * 24 * 60 * 60


class SigningLinkError(ValueError):
    """Invalid, expired or tampered signing capability."""


@dataclass(frozen=True)
class SigningLinkClaims:
    quotation_id: int
    snapshot_id: int
    pdf_sha256: str
    expires_at: int
    token_id: str


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    if not value or not value.isascii():
        raise SigningLinkError("Invalid token encoding")

    if any(character not in
           "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
           for character in value):
        raise SigningLinkError("Invalid token encoding")

    try:
        result = base64.urlsafe_b64decode(
            value + "=" * (-len(value) % 4)
        )
    except (ValueError, Exception) as exc:
        raise SigningLinkError("Invalid token encoding") from exc

    if _encode(result) != value:
        raise SigningLinkError("Noncanonical token encoding")

    return result


def _secret(secret_key: str) -> bytes:
    if not isinstance(secret_key, str) or len(secret_key.encode("utf-8")) < 32:
        raise ValueError("A signing key of at least 32 bytes is required")
    return secret_key.encode("utf-8")


def _validate_hash(value: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("Expected lowercase SHA-256 hex digest")


def issue_signing_link(
    *,
    quotation_id: int,
    snapshot_id: int,
    pdf_sha256: str,
    secret_key: str,
    lifetime_seconds: int = MAX_LIFETIME_SECONDS,
    now: int | None = None,
) -> str:
    """Issue a signed, expiring, version-bound capability."""
    if quotation_id <= 0 or snapshot_id <= 0:
        raise ValueError("Invalid quotation or snapshot ID")

    _validate_hash(pdf_sha256)
    key = _secret(secret_key)

    if not 1 <= lifetime_seconds <= MAX_LIFETIME_SECONDS:
        raise ValueError("Invalid signing link lifetime")

    issued_at = int(time.time()) if now is None else int(now)

    payload = {
        "v": 1,
        "q": quotation_id,
        "s": snapshot_id,
        "h": pdf_sha256,
        "exp": issued_at + lifetime_seconds,
        "jti": secrets.token_hex(16),
    }

    encoded = _encode(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )

    signature = hmac.new(
        key,
        DOMAIN + encoded.encode("ascii"),
        hashlib.sha256,
    ).digest()

    return encoded + "." + _encode(signature)


def verify_signing_link(
    token: str,
    *,
    secret_key: str,
    now: int | None = None,
) -> SigningLinkClaims:
    """Validate integrity and expiry; DB authorization remains mandatory."""
    key = _secret(secret_key)

    if (
        not isinstance(token, str)
        or len(token) > MAX_TOKEN_LENGTH
        or token.count(".") != 1
    ):
        raise SigningLinkError("Invalid signing link")

    encoded, encoded_signature = token.split(".", 1)

    expected = hmac.new(
        key,
        DOMAIN + encoded.encode("ascii", errors="ignore"),
        hashlib.sha256,
    ).digest()

    signature = _decode(encoded_signature)

    if not hmac.compare_digest(signature, expected):
        raise SigningLinkError("Invalid signing link")

    try:
        payload = json.loads(_decode(encoded))
    except (ValueError, UnicodeDecodeError) as exc:
        raise SigningLinkError("Invalid signing link") from exc

    if not isinstance(payload, dict) or set(payload) != {
        "v", "q", "s", "h", "exp", "jti"
    }:
        raise SigningLinkError("Invalid signing link")

    if type(payload["v"]) is not int or payload["v"] != 1:
        raise SigningLinkError("Unsupported signing link version")

    for field in ("q", "s", "exp"):
        if type(payload[field]) is not int or payload[field] <= 0:
            raise SigningLinkError("Invalid signing link claims")

    try:
        _validate_hash(payload["h"])
    except ValueError as exc:
        raise SigningLinkError("Invalid PDF fingerprint") from exc

    token_id = payload["jti"]
    if (
        not isinstance(token_id, str)
        or len(token_id) != 32
        or any(c not in "0123456789abcdef" for c in token_id)
    ):
        raise SigningLinkError("Invalid token identifier")

    current = int(time.time()) if now is None else int(now)

    if payload["exp"] <= current:
        raise SigningLinkError("Signing link expired")

    if payload["exp"] > current + MAX_LIFETIME_SECONDS:
        raise SigningLinkError("Signing link lifetime exceeds policy")

    return SigningLinkClaims(
        quotation_id=payload["q"],
        snapshot_id=payload["s"],
        pdf_sha256=payload["h"],
        expires_at=payload["exp"],
        token_id=token_id,
    )
