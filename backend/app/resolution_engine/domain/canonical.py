"""Serialización y hashing deterministas para evidencia futura."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence, Set
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from app.resolution_engine.domain.exceptions import CanonicalizationError


def canonical_data(value: Any) -> Any:
    """Convierte un objeto soportado a datos JSON deterministas."""

    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalizationError("non-finite floats are not canonical")
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalizationError("non-finite decimals are not canonical")
        normalized = value.normalize()
        if normalized == 0:
            normalized = Decimal(0)
        return format(normalized, "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise CanonicalizationError("naive datetimes are not canonical")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return canonical_data(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: canonical_data(getattr(value, item.name))
            for item in fields(value)
            if not item.name.startswith("_")
        }
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalizationError("canonical mappings require string keys")
        return {
            key: canonical_data(item)
            for key, item in sorted(value.items(), key=lambda pair: pair[0])
        }
    if isinstance(value, Set) and not isinstance(value, (str, bytes, bytearray)):
        normalized_items = [canonical_data(item) for item in value]
        return sorted(normalized_items, key=_encoded_sort_key)
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return [canonical_data(item) for item in value]
    raise CanonicalizationError(
        f"unsupported canonical value type: {type(value).__qualname__}"
    )


def canonical_json(value: Any) -> str:
    """Serializa con claves y separadores estables, sin valores NaN."""

    return json.dumps(
        canonical_data(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def canonical_sha256(value: Any) -> str:
    """Calcula SHA-256 hexadecimal sobre UTF-8 canónico."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _encoded_sort_key(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
