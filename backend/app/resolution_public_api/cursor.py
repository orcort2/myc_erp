"""Cursores públicos opacos, versionados y ligados a la consulta completa."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.resolution_engine.domain.canonical import canonical_sha256
from myc_resolution_contracts.v1 import CONTRACT_VERSION

CURSOR_ENVELOPE_VERSION = "c1"
CURSOR_CONTRACT_VERSION = CONTRACT_VERSION
CURSOR_DIRECTION = "forward"
_AAD = b"myc-resolution-public-api:cursor:c1"


class CursorValidationError(ValueError):
    """Rechazo seguro sin exponer contenido ni posición del cursor."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class CursorQueryIdentity:
    contract_version: str
    consumer_key: str
    organization_id: str
    filters_hash: str
    sort: str
    direction: str
    page_size: int

    @classmethod
    def build(
        cls,
        *,
        contract_version: str,
        consumer_key: str,
        organization_id: str,
        filters: dict[str, str | None],
        sort: str,
        direction: str,
        page_size: int,
    ) -> "CursorQueryIdentity":
        return cls(
            contract_version=contract_version,
            consumer_key=consumer_key,
            organization_id=organization_id,
            filters_hash=canonical_sha256(filters),
            sort=sort,
            direction=direction,
            page_size=page_size,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "consumer_key": self.consumer_key,
            "organization_id": self.organization_id,
            "filters_hash": self.filters_hash,
            "sort": self.sort,
            "direction": self.direction,
            "page_size": self.page_size,
        }


@dataclass(frozen=True, slots=True)
class CursorPosition:
    created_at: datetime
    internal_id: int

    def snapshot(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "internal_id": self.internal_id,
        }


class PublicCursorCodec:
    """Cifra y autentica identidad de consulta y posición keyset."""

    def __init__(self, secret_key: str) -> None:
        self._key = hmac.new(
            secret_key.encode(),
            b"resolution-public-api:cursor-encryption:c1",
            hashlib.sha256,
        ).digest()

    def encode(
        self,
        *,
        identity: CursorQueryIdentity,
        position: CursorPosition,
    ) -> str:
        payload = json.dumps(
            {
                "envelope_version": CURSOR_ENVELOPE_VERSION,
                "query": identity.snapshot(),
                "position": position.snapshot(),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self._key).encrypt(nonce, payload, _AAD)
        return (
            f"{CURSOR_ENVELOPE_VERSION}."
            f"{_base64url_encode(nonce + ciphertext)}"
        )

    def decode(
        self,
        token: str,
        *,
        expected_identity: CursorQueryIdentity,
    ) -> CursorPosition:
        try:
            envelope_version, encoded = token.split(".", 1)
        except ValueError:
            raise CursorValidationError("cursor_version_unsupported") from None
        if envelope_version != CURSOR_ENVELOPE_VERSION:
            raise CursorValidationError("cursor_version_unsupported")
        try:
            protected = _base64url_decode(encoded)
            if len(protected) <= 28:
                raise ValueError
            payload = AESGCM(self._key).decrypt(
                protected[:12],
                protected[12:],
                _AAD,
            )
            document = json.loads(payload)
        except (InvalidTag, ValueError, TypeError, json.JSONDecodeError):
            raise CursorValidationError("cursor_authentication_failed") from None
        if (
            document.get("envelope_version") != CURSOR_ENVELOPE_VERSION
            or document.get("query") != expected_identity.snapshot()
        ):
            raise CursorValidationError("cursor_query_mismatch")
        try:
            position = document["position"]
            created_at = datetime.fromisoformat(position["created_at"])
            internal_id = int(position["internal_id"])
            if internal_id <= 0:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise CursorValidationError("cursor_position_invalid") from None
        return CursorPosition(
            created_at=created_at,
            internal_id=internal_id,
        )


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _base64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
