"""DEV-0: opaque Developer session tokens. Own token space -- never the same
as biometric credentials or Mobile refresh tokens."""

import hashlib
import secrets


def generate_developer_token() -> str:
    return secrets.token_urlsafe(48)


def hash_developer_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
