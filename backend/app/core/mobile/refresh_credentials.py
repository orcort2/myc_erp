"""Mobile-only credentials and bounded legacy rollout; never used by Web auth."""

import base64
import binascii
import hashlib
import re
import secrets
from datetime import datetime, timezone


# One 30-day refresh lifetime after the BIOMETRIC-1 rollout window begins.
# Never extend automatically on restart. Remove the fallback after this date.
LEGACY_REFRESH_DEADLINE = datetime(2026, 10, 22, tzinfo=timezone.utc)
_JWT_FORMAT = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def is_legacy_refresh_format(credential: str) -> bool:
    # Format dispatch only; signature, type, expiry and Mobile scope are checked separately.
    return _JWT_FORMAT.fullmatch(credential) is not None


def has_canonical_legacy_signature(credential: str) -> bool:
    # Some JWT decoders accept nonzero unused base64 bits. Reject alternate
    # encodings of the same signature so they cannot bypass the single-use hash.
    signature = credential.rsplit(".", 1)[-1]
    try:
        decoded = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
    except (ValueError, binascii.Error):
        return False
    return base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") == signature


def generate_refresh_credential() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_credential(credential: str) -> str:
    return hashlib.sha256(credential.encode("utf-8")).hexdigest()
