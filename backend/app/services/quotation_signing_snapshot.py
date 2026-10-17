"""Canonical commercial snapshot fingerprint."""

import hashlib
import json
import math
from datetime import date, datetime
from decimal import Decimal


def _normalize(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite snapshot number")
        raise ValueError("Floating point values are not permitted")

    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Non-finite decimal")
        return format(value, "f")

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, list):
        return [_normalize(item) for item in value]

    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("Snapshot keys must be strings")
        return {
            key: _normalize(item)
            for key, item in value.items()
        }

    raise ValueError(f"Unsupported snapshot type: {type(value).__name__}")


def canonical_snapshot_bytes(snapshot_data: dict) -> bytes:
    if not isinstance(snapshot_data, dict):
        raise ValueError("Commercial snapshot must be an object")

    return json.dumps(
        _normalize(snapshot_data),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def snapshot_digest(snapshot_data: dict) -> str:
    return hashlib.sha256(
        b"myc:quotation-commercial-snapshot:v1:"
        + canonical_snapshot_bytes(snapshot_data)
    ).hexdigest()
