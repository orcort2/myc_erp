"""BIOMETRIC-2: opaque biometric login credentials. Never the same token space as refresh credentials."""

import hashlib
import secrets


def generate_biometric_credential() -> str:
    return secrets.token_urlsafe(48)


def hash_biometric_credential(credential: str) -> str:
    return hashlib.sha256(credential.encode("utf-8")).hexdigest()
